"""Service for ingesting code repositories"""
import os
import ast
import logging
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sentence_transformers import SentenceTransformer
import tree_sitter_go as tsgo
from tree_sitter import Language, Parser

from app.models.code_repository import CodeRepository, CodeChunk, Contributor, Commit
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize tree-sitter for Go
GO_LANGUAGE = Language(tsgo.language())
go_parser = Parser(GO_LANGUAGE)

# File extensions to index
CODE_EXTENSIONS = {
    '.py': 'python',
    '.js': 'javascript',
    '.ts': 'typescript',
    '.jsx': 'react',
    '.tsx': 'react',
    '.go': 'go'
}

# Directories to skip
SKIP_DIRECTORIES = {
    'node_modules', 'venv', 'env', '__pycache__', '.git',
    'dist', 'build', 'target', '.next', '.nuxt', 'coverage',
    '.pytest_cache', '__generated__', 'migrations'
}


class CodeIngestionService:
    """Service for ingesting and indexing code repositories"""
    
    def __init__(self, db: Session):
        self.db = db
        self.embedding_model = None
        
    def _load_embedding_model(self):
        """Lazy load embedding model"""
        if self.embedding_model is None:
            logger.info("Loading embedding model...")
            self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
        return self.embedding_model
    
    def ingest_repository(
        self,
        repo_path: str,
        repo_name: Optional[str] = None,
        git_url: Optional[str] = None,
        branch: str = 'main'
    ) -> CodeRepository:
        """
        Ingest a code repository
        
        Args:
            repo_path: Local path to repository
            repo_name: Repository name (defaults to directory name)
            git_url: Optional Git URL
            branch: Git branch name
            
        Returns:
            CodeRepository instance
        """
        if not os.path.exists(repo_path):
            raise ValueError(f"Repository path does not exist: {repo_path}")
        
        if not repo_name:
            repo_name = os.path.basename(repo_path)
        
        logger.info(f"Ingesting repository: {repo_name} from {repo_path}")
        
        # Check if repo already exists
        existing_repo = self.db.query(CodeRepository).filter_by(local_path=repo_path).first()
        if existing_repo:
            logger.info(f"Repository already exists, updating: {existing_repo.id}")
            repo = existing_repo
            # Delete old chunks
            self.db.query(CodeChunk).filter_by(repository_id=repo.id).delete()
        else:
            repo = CodeRepository(
                name=repo_name,
                local_path=repo_path,
                git_url=git_url,
                branch=branch
            )
            self.db.add(repo)
            self.db.flush()  # 🐛 FIX: Flush to get repo.id before creating chunks
        
        # Scan repository
        code_files = self._scan_repository(repo_path)
        logger.info(f"Found {len(code_files)} code files")
        
        # Detect primary language
        lang_counts = {}
        for file in code_files:
            lang = file['language']
            lang_counts[lang] = lang_counts.get(lang, 0) + 1
        
        if lang_counts:
            repo.primary_language = max(lang_counts, key=lang_counts.get)
        
        # Extract Git commits
        total_commits_count = self._extract_git_commits(repo_path, repo)
        
        # Process files
        total_chunks = 0
        total_functions = 0
        total_classes = 0
        total_lines = 0
        
        for file_info in code_files:
            chunks = self._process_file(file_info, repo)
            total_chunks += len(chunks)
            
            for chunk in chunks:
                self.db.add(chunk)
                if chunk.chunk_type == 'function':
                    total_functions += 1
                elif chunk.chunk_type == 'class':
                    total_classes += 1
                total_lines += (chunk.end_line - chunk.start_line + 1)
        
        # Update repository stats
        repo.total_files = len(code_files)
        repo.total_functions = total_functions
        repo.total_classes = total_classes
        repo.lines_of_code = total_lines
        repo.total_commits = total_commits_count
        repo.last_synced = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(repo)
        
        logger.info(f"Ingestion complete: {total_chunks} chunks, {total_functions} functions, {total_classes} classes")
        
        return repo
    
    def _scan_repository(self, repo_path: str) -> List[Dict]:
        """Scan repository for code files"""
        code_files = []
        
        for root, dirs, files in os.walk(repo_path):
            # Skip directories
            dirs[:] = [d for d in dirs if d not in SKIP_DIRECTORIES]
            
            for file in files:
                _, ext = os.path.splitext(file)
                if ext in CODE_EXTENSIONS:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, repo_path)
                    
                    code_files.append({
                        'absolute_path': file_path,
                        'relative_path': rel_path,
                        'language': CODE_EXTENSIONS[ext]
                    })
        
        return code_files
    
    def _process_file(self, file_info: Dict, repo: CodeRepository) -> List[CodeChunk]:
        """Process a single file and extract chunks"""
        try:
            with open(file_info['absolute_path'], 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.warning(f"Could not read file {file_info['relative_path']}: {e}")
            return []
        
        language = file_info['language']
        
        if language == 'python':
            return self._chunk_python_file(content, file_info, repo)
        elif language == 'go':
            return self._chunk_go_file(content, file_info, repo)
        else:
            # Fallback: create file-level chunk
            return self._chunk_file_level(content, file_info, repo)
    
    def _chunk_python_file(self, content: str, file_info: Dict, repo: CodeRepository) -> List[CodeChunk]:
        """Extract functions and classes from Python file using AST"""
        chunks = []
        
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_info['relative_path']}: {e}")
            return self._chunk_file_level(content, file_info, repo)
        
        # Extract top-level functions and classes
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef):
                chunk = self._create_function_chunk(node, content, file_info, repo)
                if chunk:
                    chunks.append(chunk)
            
            elif isinstance(node, ast.ClassDef):
                chunk = self._create_class_chunk(node, content, file_info, repo)
                if chunk:
                    chunks.append(chunk)
                
                # Extract methods from class
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method_chunk = self._create_method_chunk(
                            item, node.name, content, file_info, repo
                        )
                        if method_chunk:
                            chunks.append(method_chunk)
        
        return chunks
    
    def _create_function_chunk(
        self,
        node: ast.FunctionDef,
        content: str,
        file_info: Dict,
        repo: CodeRepository
    ) -> Optional[CodeChunk]:
        """Create chunk for a function"""
        try:
            lines = content.split('\n')
            start_line = node.lineno
            end_line = node.end_lineno if node.end_lineno else start_line
            
            # Extract function source
            func_lines = lines[start_line - 1:end_line]
            code_content = '\n'.join(func_lines)
            
            # Extract docstring
            docstring = ast.get_docstring(node)
            
            # Build signature
            args = [arg.arg for arg in node.args.args]
            signature = f"def {node.name}({', '.join(args)})"
            
            chunk = CodeChunk(
                repository_id=repo.id,
                file_path=file_info['relative_path'],
                language=file_info['language'],
                chunk_type='function',
                chunk_name=node.name,
                full_name=node.name,
                code_content=code_content,
                docstring=docstring,
                signature=signature,
                start_line=start_line,
                end_line=end_line
            )
            
            return chunk
            
        except Exception as e:
            logger.warning(f"Error creating function chunk: {e}")
            return None
    
    def _create_class_chunk(
        self,
        node: ast.ClassDef,
        content: str,
        file_info: Dict,
        repo: CodeRepository
    ) -> Optional[CodeChunk]:
        """Create chunk for a class"""
        try:
            lines = content.split('\n')
            start_line = node.lineno
            end_line = node.end_lineno if node.end_lineno else start_line
            
            # Extract class source
            class_lines = lines[start_line - 1:end_line]
            code_content = '\n'.join(class_lines)
            
            # Extract docstring
            docstring = ast.get_docstring(node)
            
            # Build signature
            bases = [base.id if isinstance(base, ast.Name) else 'object' for base in node.bases]
            signature = f"class {node.name}({', '.join(bases)})" if bases else f"class {node.name}"
            
            chunk = CodeChunk(
                repository_id=repo.id,
                file_path=file_info['relative_path'],
                language=file_info['language'],
                chunk_type='class',
                chunk_name=node.name,
                full_name=node.name,
                code_content=code_content,
                docstring=docstring,
                signature=signature,
                start_line=start_line,
                end_line=end_line
            )
            
            return chunk
            
        except Exception as e:
            logger.warning(f"Error creating class chunk: {e}")
            return None
    
    def _create_method_chunk(
        self,
        node: ast.FunctionDef,
        class_name: str,
        content: str,
        file_info: Dict,
        repo: CodeRepository
    ) -> Optional[CodeChunk]:
        """Create chunk for a class method"""
        try:
            lines = content.split('\n')
            start_line = node.lineno
            end_line = node.end_lineno if node.end_lineno else start_line
            
            # Extract method source
            method_lines = lines[start_line - 1:end_line]
            code_content = '\n'.join(method_lines)
            
            # Extract docstring
            docstring = ast.get_docstring(node)
            
            # Build signature
            args = [arg.arg for arg in node.args.args]
            signature = f"def {node.name}({', '.join(args)})"
            
            chunk = CodeChunk(
                repository_id=repo.id,
                file_path=file_info['relative_path'],
                language=file_info['language'],
                chunk_type='method',
                chunk_name=node.name,
                full_name=f"{class_name}.{node.name}",
                code_content=code_content,
                docstring=docstring,
                signature=signature,
                start_line=start_line,
                end_line=end_line
            )
            
            return chunk
            
        except Exception as e:
            logger.warning(f"Error creating method chunk: {e}")
            return None
    
    def _chunk_go_file(self, content: str, file_info: Dict, repo: CodeRepository) -> List[CodeChunk]:
        """Extract functions, methods, and types from Go file using tree-sitter"""
        chunks = []
        
        try:
            tree = go_parser.parse(bytes(content, 'utf8'))
            root_node = tree.root_node
            
            lines = content.split('\n')
            
            # Query for functions, methods, and type declarations
            def walk_tree(node):
                if node.type == 'function_declaration':
                    chunk = self._create_go_function_chunk(node, lines, file_info, repo)
                    if chunk:
                        chunks.append(chunk)
                
                elif node.type == 'method_declaration':
                    chunk = self._create_go_method_chunk(node, lines, file_info, repo)
                    if chunk:
                        chunks.append(chunk)
                
                elif node.type == 'type_declaration':
                    # Extract struct, interface declarations
                    chunk = self._create_go_type_chunk(node, lines, file_info, repo)
                    if chunk:
                        chunks.append(chunk)
                
                # Recursively walk children
                for child in node.children:
                    walk_tree(child)
            
            walk_tree(root_node)
            
            # If no chunks extracted, fallback to file-level
            if not chunks:
                chunks = self._chunk_file_level(content, file_info, repo)
                
        except Exception as e:
            logger.warning(f"Error parsing Go file {file_info['relative_path']}: {e}")
            chunks = self._chunk_file_level(content, file_info, repo)
        
        return chunks
    
    def _create_go_function_chunk(self, node, lines: List[str], file_info: Dict, repo: CodeRepository) -> Optional[CodeChunk]:
        """Create chunk for a Go function"""
        try:
            start_line = node.start_point[0] + 1
            end_line = node.end_point[0] + 1
            
            # Extract function name
            name_node = node.child_by_field_name('name')
            func_name = name_node.text.decode('utf8') if name_node else 'unknown'
            
            # Extract signature
            signature_text = lines[start_line - 1].strip()
            
            # Extract code content
            code_content = '\n'.join(lines[start_line - 1:end_line])
            
            chunk = CodeChunk(
                repository_id=repo.id,
                file_path=file_info['relative_path'],
                language='go',
                chunk_type='function',
                chunk_name=func_name,
                full_name=func_name,
                code_content=code_content,
                docstring=None,  # Could extract comments above
                signature=signature_text,
                start_line=start_line,
                end_line=end_line
            )
            
            return chunk
        except Exception as e:
            logger.warning(f"Error creating Go function chunk: {e}")
            return None
    
    def _create_go_method_chunk(self, node, lines: List[str], file_info: Dict, repo: CodeRepository) -> Optional[CodeChunk]:
        """Create chunk for a Go method"""
        try:
            start_line = node.start_point[0] + 1
            end_line = node.end_point[0] + 1
            
            # Extract receiver type
            receiver_node = node.child_by_field_name('receiver')
            receiver_text = receiver_node.text.decode('utf8') if receiver_node else ''
            
            # Extract method name
            name_node = node.child_by_field_name('name')
            method_name = name_node.text.decode('utf8') if name_node else 'unknown'
            
            # Extract signature
            signature_text = lines[start_line - 1].strip()
            
            # Extract code content
            code_content = '\n'.join(lines[start_line - 1:end_line])
            
            # Build full name with receiver
            full_name = f"{receiver_text}.{method_name}" if receiver_text else method_name
            
            chunk = CodeChunk(
                repository_id=repo.id,
                file_path=file_info['relative_path'],
                language='go',
                chunk_type='method',
                chunk_name=method_name,
                full_name=full_name,
                code_content=code_content,
                docstring=None,
                signature=signature_text,
                start_line=start_line,
                end_line=end_line
            )
            
            return chunk
        except Exception as e:
            logger.warning(f"Error creating Go method chunk: {e}")
            return None
    
    def _create_go_type_chunk(self, node, lines: List[str], file_info: Dict, repo: CodeRepository) -> Optional[CodeChunk]:
        """Create chunk for a Go type (struct/interface)"""
        try:
            start_line = node.start_point[0] + 1
            end_line = node.end_point[0] + 1
            
            # Extract type spec
            type_spec = None
            for child in node.children:
                if child.type == 'type_spec':
                    type_spec = child
                    break
            
            if not type_spec:
                return None
            
            # Extract type name
            name_node = type_spec.child_by_field_name('name')
            type_name = name_node.text.decode('utf8') if name_node else 'unknown'
            
            # Determine if struct or interface
            type_node = type_spec.child_by_field_name('type')
            chunk_type = 'struct' if type_node and type_node.type == 'struct_type' else 'interface'
            
            # Extract signature
            signature_text = lines[start_line - 1].strip()
            
            # Extract code content
            code_content = '\n'.join(lines[start_line - 1:end_line])
            
            chunk = CodeChunk(
                repository_id=repo.id,
                file_path=file_info['relative_path'],
                language='go',
                chunk_type=chunk_type,
                chunk_name=type_name,
                full_name=type_name,
                code_content=code_content,
                docstring=None,
                signature=signature_text,
                start_line=start_line,
                end_line=end_line
            )
            
            return chunk
        except Exception as e:
            logger.warning(f"Error creating Go type chunk: {e}")
            return None
    
    def _chunk_file_level(self, content: str, file_info: Dict, repo: CodeRepository) -> List[CodeChunk]:
        """Create a file-level chunk (fallback for non-Python or unparseable files)"""
        lines = content.split('\n')
        
        chunk = CodeChunk(
            repository_id=repo.id,
            file_path=file_info['relative_path'],
            language=file_info['language'],
            chunk_type='file',
            chunk_name=os.path.basename(file_info['relative_path']),
            full_name=file_info['relative_path'],
            code_content=content[:10000],  # Limit to first 10k chars
            start_line=1,
            end_line=len(lines)
        )
        
        return [chunk]
    
    def _extract_git_commits(self, repo_path: str, repo: CodeRepository) -> int:
        """Extract Git commits from repository"""
        try:
            import git
        except ImportError:
            logger.warning("GitPython not installed, skipping commit extraction")
            return 0
        
        try:
            git_repo = git.Repo(repo_path)
            active_branch = git_repo.active_branch
            logger.info(f"Extracting commits from branch: {active_branch.name}")
            
            commit_count = 0
            for commit in git_repo.iter_commits(active_branch, max_count=100):
                # Get or create contributor
                contributor = self.db.query(Contributor).filter_by(email=commit.author.email).first()
                if not contributor:
                    contributor = Contributor(
                        name=commit.author.name,
                        email=commit.author.email
                    )
                    self.db.add(contributor)
                    self.db.flush()
                
                # Check if commit already exists
                existing_commit = self.db.query(Commit).filter_by(sha=commit.hexsha).first()
                if not existing_commit:
                    new_commit = Commit(
                        sha=commit.hexsha,
                        message=commit.message,
                        authored_date=datetime.fromtimestamp(commit.authored_date),
                        repository_id=repo.id,
                        author_id=contributor.id
                    )
                    self.db.add(new_commit)
                    commit_count += 1
            
            logger.info(f"Extracted {commit_count} commits")
            return commit_count
            
        except Exception as e:
            logger.warning(f"Could not extract Git commits: {e}")
            return 0

