"""AI Review Service - Generate persona-based document reviews"""
import logging
import os
import re
import uuid
from typing import Optional, Dict, List
from datetime import datetime
from sqlalchemy.orm import Session
from pathlib import Path

from app.models.document import Document
from app.models.document_review import DocumentReview, ReviewStatus, ReviewType
from app.services.document_service import DocumentService
from app.config import settings

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

logger = logging.getLogger(__name__)


class AIReviewService:
    """Service for AI-powered document reviews"""
    
    async def stream_review(
        self,
        document: Document,
        review_type: str,
        personas: List[str],
        model: str = "sonnet-4.5"
    ):
        """Stream review content in real-time"""
        import asyncio
        import json
        
        # Build prompt
        prompt = self._build_review_prompt(
            document.title,
            document.doc_type.value if document.doc_type else "document",
            review_type,
            personas
        )
        
        full_content = f"# {document.title}\n\n{document.content_md}"
        
        full_prompt = f"""{prompt}

---

Document to review:

{full_content}

---

Now review this document. Remember:
- Quote relevant sections first (using `> `)
- Then add your comment in Obsidian callout format
- Focus on high-value insights only
- The original document will be linked, so you don't need to reproduce it
- Return ONLY quoted sections with comments, no preamble or conclusion.
"""
        
        import tempfile
        
        env = os.environ.copy()
        if self.cursor_api_key:
            env['CURSOR_API_KEY'] = self.cursor_api_key
        
        # Write prompt to temporary file for large documents
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as tmp:
            tmp.write(full_content)
            tmp_path = tmp.name
        
        logger.info(f"📝 Wrote document to temp file: {tmp_path} ({len(full_content)} bytes)")
        
        # Create a shorter prompt that references the file
        file_prompt = f"""{prompt}

---

I've saved the document to review in a file at: {tmp_path}

Please read the file, review it according to the instructions above, and provide the FULL reviewed document with inline comments inserted at relevant sections.
Use the Obsidian callout format as specified above.
Return ONLY the reviewed markdown document, no additional commentary.

Read the file now and provide your review.
"""
        
        # Build command with file-based prompt
        cmd = [
            self.cursor_agent_path,
            '--print',
            '--model', model,
            '--output-format', 'stream-json',
            '--stream-partial-output',
            file_prompt
        ]
        
        logger.info(f"🚀 Starting Cursor Agent with file reference: model={model}")
        
        # Start Cursor Agent process asynchronously
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        
        # Stream output asynchronously
        logger.info(f"📡 Starting to read from Cursor Agent stdout...")
        line_count = 0
        
        try:
            while True:
                line = await process.stdout.readline()
                if not line:
                    logger.info(f"📭 EOF reached after {line_count} lines")
                    break
                
                line_count += 1
                line_str = line.decode('utf-8').strip()
                
                if line_str:
                    logger.debug(f"📨 Line {line_count}: {line_str[:100]}...")
                    try:
                        data = json.loads(line_str)
                        delta = data.get('delta') or data.get('content') or data.get('text', '')
                        if delta:
                            yield delta
                    except json.JSONDecodeError:
                        # Plain text fallback
                        yield line_str
            
            # Check for errors
            return_code = await process.wait()
            if return_code != 0:
                stderr = await process.stderr.read()
                error_msg = stderr.decode('utf-8') if stderr else "Unknown error"
                logger.error(f"❌ Cursor Agent failed with code {return_code}: {error_msg}")
                raise Exception(f"Cursor Agent failed: {error_msg}")
            
            logger.info(f"✅ Cursor Agent completed successfully, streamed {line_count} lines")
            
        except Exception as e:
            logger.error(f"❌ Error during streaming: {e}", exc_info=True)
            # Try to read stderr for debugging
            try:
                stderr = await process.stderr.read()
                if stderr:
                    logger.error(f"Stderr: {stderr.decode('utf-8')}")
            except:
                pass
            raise
        finally:
            # Clean up temp file
            try:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                    logger.info(f"🗑️ Cleaned up temp file: {tmp_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temp file {tmp_path}: {e}")
    
    async def stream_review_claude(
        self,
        document: Document,
        review_type: str,
        personas: List[str],
        model: str = "claude-sonnet-4.5-20250514"
    ):
        """Stream review content using Claude API directly (more stable than Cursor Agent)"""
        if not ANTHROPIC_AVAILABLE:
            raise Exception("Anthropic library not installed. Run: pip install anthropic")
        
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise Exception("ANTHROPIC_API_KEY environment variable not set")
        
        # Build prompt
        prompt = self._build_review_prompt(
            document.title,
            document.doc_type.value if document.doc_type else "document",
            review_type,
            personas
        )
        
        full_content = f"# {document.title}\n\n{document.content_md}"
        
        full_prompt = f"""{prompt}

---

Document to review:

{full_content}

---

Now review this document. Remember:
- Quote relevant sections first (using `> `)
- Then add your comment in Obsidian callout format
- Focus on high-value insights only
- The original document will be linked, so you don't need to reproduce it
- Return ONLY quoted sections with comments, no preamble or conclusion.
"""
        
        logger.info(f"🚀 Starting Claude API stream: model={model}, document_length={len(full_content)}")
        
        client = Anthropic(api_key=api_key)
        
        try:
            # Use Claude's streaming API
            with client.messages.stream(
                model=model,
                max_tokens=16000,
                messages=[{"role": "user", "content": full_prompt}],
                temperature=0.3
            ) as stream:
                for text in stream.text_stream:
                    if text:
                        yield text
            
            logger.info(f"✅ Claude API stream completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Claude API error: {e}", exc_info=True)
            raise Exception(f"Claude API failed: {str(e)}")
    
    async def stream_review_claude_code(
        self,
        document: Document,
        review_type: str,
        personas: List[str],
        model: str = "claude-code"
    ):
        """Stream review content using Claude Code CLI (installed locally)"""
        import asyncio
        import json
        
        # Check if claude CLI is available
        claude_path = os.getenv('CLAUDE_CLI_PATH', 'claude')
        
        # Build prompt
        prompt = self._build_review_prompt(
            document.title,
            document.doc_type.value if document.doc_type else "document",
            review_type,
            personas
        )
        
        full_content = f"# {document.title}\n\n{document.content_md}"
        
        full_prompt = f"""{prompt}

---

Document to review:

{full_content}

---

Now review this document. Remember:
- Quote relevant sections first (using `> `)
- Then add your comment in Obsidian callout format
- Focus on high-value insights only
- The original document will be linked, so you don't need to reproduce it
- Return ONLY quoted sections with comments, no preamble or conclusion.
"""
        
        logger.info(f"🚀 Starting Claude Code CLI stream: document_length={len(full_content)}")
        
        # Build command (without the prompt - we'll send via stdin)
        cmd = [
            claude_path,
            '--print',
            '--verbose',
            '--output-format', 'stream-json',
            '--include-partial-messages',
            '--tools', ''  # Disable all tools for pure text generation
        ]
        
        logger.info(f"🚀 Running: {' '.join(cmd)}")
        
        # Start Claude Code process asynchronously with stdin
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Send prompt via stdin
        try:
            process.stdin.write(full_prompt.encode('utf-8'))
            await process.stdin.drain()
            process.stdin.close()
            logger.info(f"📤 Sent prompt via stdin ({len(full_prompt)} bytes)")
        except Exception as e:
            logger.error(f"❌ Failed to write to stdin: {e}")
            raise
        
        # Stream output asynchronously
        logger.info(f"📡 Starting to read from Claude Code stdout...")
        line_count = 0
        in_text_block = False
        
        try:
            while True:
                line = await process.stdout.readline()
                if not line:
                    logger.info(f"📭 EOF reached after {line_count} lines")
                    break
                
                line_count += 1
                line_str = line.decode('utf-8').strip()
                
                if line_str:
                    try:
                        data = json.loads(line_str)
                        
                        # Handle different event types
                        if data.get('type') == 'stream_event':
                            event = data.get('event', {})
                            event_type = event.get('type')
                            
                            if event_type == 'content_block_start':
                                content_block = event.get('content_block', {})
                                if content_block.get('type') == 'text':
                                    in_text_block = True
                            
                            elif event_type == 'content_block_delta' and in_text_block:
                                delta = event.get('delta', {})
                                if delta.get('type') == 'text_delta':
                                    text = delta.get('text', '')
                                    if text:
                                        yield text
                            
                            elif event_type == 'content_block_stop':
                                in_text_block = False
                        
                    except json.JSONDecodeError:
                        logger.debug(f"Non-JSON line: {line_str[:100]}")
                        continue
            
            # Check for errors
            return_code = await process.wait()
            if return_code != 0:
                stderr = await process.stderr.read()
                error_msg = stderr.decode('utf-8') if stderr else f"Process exited with code {return_code}"
                
                # Log detailed error
                logger.error(f"❌ Claude Code failed (exit code {return_code})")
                logger.error(f"Error output: {error_msg}")
                logger.error(f"Streamed {line_count} lines before failure")
                
                # If we got some content, it might have been a timeout or model limit
                if line_count > 100:
                    raise Exception(f"Claude Code stopped after processing {line_count} chunks. The document may be too large or complex. Try using 'Quick' review type.")
                else:
                    raise Exception(f"Claude Code failed: {error_msg}")
            
            logger.info(f"✅ Claude Code completed successfully, processed {line_count} lines")
            
        except Exception as e:
            logger.error(f"❌ Error during Claude Code streaming: {e}", exc_info=True)
            # Try to read stderr for debugging
            try:
                stderr = await process.stderr.read()
                if stderr:
                    logger.error(f"Stderr: {stderr.decode('utf-8')}")
            except:
                pass
            raise
    
    def __init__(self, db: Session):
        self.db = db
        self.document_service = DocumentService(db)
        
        # Check for API keys and Cursor CLI
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        self.cursor_api_key = os.getenv('CURSOR_API_KEY')
        self.cursor_agent_path = os.getenv('CURSOR_AGENT_PATH', os.path.expanduser('~/.local/bin/cursor-agent'))
        
        # Determine which provider to use (priority order)
        if self._check_cursor_cli():
            self.provider = 'cursor'
            logger.info("Using Cursor CLI (headless mode) for AI reviews")
        elif self.anthropic_api_key:
            self.provider = 'anthropic'
            logger.info("Using Anthropic (Claude) for AI reviews")
        elif self.openai_api_key:
            self.provider = 'openai'
            logger.info("Using OpenAI (GPT-4) for AI reviews")
        else:
            self.provider = 'mock'
            logger.warning("No AI providers available - using MOCK mode for testing")
    
    async def create_review_job(
        self,
        document_id: str,
        review_type: str = ReviewType.COMPREHENSIVE.value,
        focus_areas: Optional[List[str]] = None,
        created_by: Optional[str] = None,
        model: Optional[str] = "sonnet-4.5"
    ) -> DocumentReview:
        """Create a new review job"""
        
        # Validate document exists
        document = self.document_service.get_document_by_id(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        # Create review job
        review = DocumentReview(
            original_document_id=document_id,
            review_type=review_type,
            focus_areas=focus_areas or ["architecture", "technical"],
            status=ReviewStatus.PENDING.value,
            created_by=created_by,
            ai_model=f"{self.provider}-{model}" if self.provider == 'cursor' else self._get_model_name(),
            metadata_json={"requested_model": model}
        )
        
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)
        
        return review
    
    async def process_review(self, review_id: str, model: Optional[str] = "sonnet-4.5") -> DocumentReview:
        """Process a review job"""
        
        review = self.db.query(DocumentReview).filter(DocumentReview.id == review_id).first()
        if not review:
            raise ValueError(f"Review {review_id} not found")
        
        try:
            # Update status to processing
            review.status = ReviewStatus.PROCESSING.value
            review.started_at = datetime.utcnow()
            review.streaming_content = ""
            self.db.commit()
            
            # Get original document
            original_doc = review.original_document
            if not original_doc or not original_doc.content_md:
                raise ValueError("Document has no content to review")
            
            # Get requested model from metadata or use default
            requested_model = model
            if review.metadata_json and 'requested_model' in review.metadata_json:
                requested_model = review.metadata_json['requested_model']
            
            # Generate review with streaming updates
            reviewed_content, comment_stats = await self._generate_review_with_streaming(
                review,
                original_doc,
                review.review_type,
                review.focus_areas or [],
                requested_model
            )
            
            # Create reviewed document
            reviewed_doc = self._create_reviewed_document(
                original_doc,
                reviewed_content,
                review
            )
            
            # Update review job
            review.reviewed_document_id = reviewed_doc.id
            review.status = ReviewStatus.COMPLETED.value
            review.completed_at = datetime.utcnow()
            review.streaming_content = reviewed_content  # Final content
            review.total_comments = comment_stats['total']
            review.comment_categories = comment_stats['categories']
            
            self.db.commit()
            self.db.refresh(review)
            
            logger.info(f"Review {review_id} completed successfully with {comment_stats['total']} comments")
            
            return review
            
        except Exception as e:
            logger.error(f"Review {review_id} failed: {e}")
            review.status = ReviewStatus.FAILED.value
            review.error_message = str(e)
            review.completed_at = datetime.utcnow()
            self.db.commit()
            raise
    
    async def _generate_review_with_streaming(
        self,
        review: DocumentReview,
        document: Document,
        review_type: str,
        focus_areas: List[str],
        model: str = "sonnet-4.5"
    ) -> tuple[str, Dict]:
        """Generate review with real-time streaming updates to database"""
        
        # Build prompt
        prompt = self._build_review_prompt(
            document.title,
            document.doc_type.value if document.doc_type else "document",
            review_type,
            focus_areas
        )
        
        full_content = f"# {document.title}\n\n{document.content_md}"
        doc_length = len(full_content)
        logger.info(f"Document length: {doc_length} characters ({doc_length // 1000}K)")
        
        # Stream content from Cursor Agent
        if self.provider == 'cursor':
            reviewed_content = await self._generate_with_cursor_streaming(review, prompt, full_content, model)
        else:
            # Fallback to non-streaming for other providers
            reviewed_content = await self._generate_review(document, review_type, focus_areas, model)[0]
        
        # Count comments
        comment_stats = self._count_comments(reviewed_content)
        
        return reviewed_content, comment_stats
    
    async def _generate_review(
        self,
        document: Document,
        review_type: str,
        focus_areas: List[str],
        model: str = "sonnet-4.5"
    ) -> tuple[str, Dict]:
        """Generate AI review with inline comments"""
        
        # Build persona-based prompt
        prompt = self._build_review_prompt(
            document.title,
            document.doc_type.value if document.doc_type else "document",
            review_type,
            focus_areas
        )
        
        # Prepare the full content for review
        full_content = f"# {document.title}\n\n{document.content_md}"
        
        # Check document length
        doc_length = len(full_content)
        logger.info(f"Document length: {doc_length} characters ({doc_length // 1000}K)")
        
        if doc_length > 100000:  # 100K characters
            logger.warning(f"Document is very long ({doc_length // 1000}K chars). Review may take 15-20 minutes.")
        
        # Route to appropriate provider
        if self.provider == 'cursor':
            reviewed_content = await self._generate_with_cursor(prompt, full_content, model)
        elif self.provider == 'anthropic':
            reviewed_content = await self._generate_with_anthropic(prompt, full_content)
        elif self.provider == 'openai':
            reviewed_content = await self._generate_with_openai(prompt, full_content)
        else:
            reviewed_content = self._generate_mock_review(document, full_content)
        
        # Count comments by category
        comment_stats = self._count_comments(reviewed_content)
        
        return reviewed_content, comment_stats
    
    def _check_cursor_cli(self) -> bool:
        """Check if Cursor Agent is available"""
        import subprocess
        import os as os_module
        
        # Check if cursor-agent exists
        if not os_module.path.exists(self.cursor_agent_path):
            logger.debug(f"Cursor Agent not found at {self.cursor_agent_path}")
            return False
        
        try:
            # Check version
            result = subprocess.run(
                [self.cursor_agent_path, '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                logger.debug(f"Cursor Agent version check failed")
                return False
            
            logger.info(f"Cursor Agent found: {result.stdout.strip()}")
            
            # Cursor Agent is available - authentication will be checked when actually used
            return True
            
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.debug(f"Cursor Agent check failed: {e}")
            return False
    
    async def _generate_with_cursor_streaming(self, review: DocumentReview, prompt: str, content: str, model: str = "sonnet-4.5") -> str:
        """Generate review with real-time streaming to database"""
        import subprocess
        import os as os_module
        import asyncio
        import json
        
        try:
            full_prompt = f"""{prompt}

---

Document to review:

{content}

---

Now review this document. Remember:
- Quote relevant sections first (using `> `)
- Then add your comment in Obsidian callout format
- Focus on high-value insights only
- The original document will be linked, so you don't need to reproduce it
- Return ONLY quoted sections with comments, no preamble or conclusion.
"""
            
            env = os_module.environ.copy()
            if self.cursor_api_key:
                env['CURSOR_API_KEY'] = self.cursor_api_key
            
            logger.info(f"Running Cursor Agent with model: {model} (streaming mode)")
            
            # Start subprocess with streaming
            process = subprocess.Popen(
                [
                    self.cursor_agent_path,
                    '--model', model,
                    '--output-format', 'stream-json',
                    '--stream-partial-output',
                    '--print',
                    full_prompt
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )
            
            reviewed_content = ""
            update_counter = 0
            
            # Read streaming output line by line
            for line in iter(process.stdout.readline, ''):
                if not line:
                    break
                    
                line = line.strip()
                if line:
                    try:
                        data = json.loads(line)
                        delta = data.get('delta') or data.get('content') or data.get('text', '')
                        if delta:
                            reviewed_content += delta
                            update_counter += 1
                            
                            # Update database every 50 deltas (~every few seconds)
                            if update_counter % 50 == 0:
                                review.streaming_content = reviewed_content
                                self.db.commit()
                                logger.debug(f"Streaming update: {len(reviewed_content)} chars")
                    except json.JSONDecodeError:
                        # Not JSON, might be plain text
                        reviewed_content += line
            
            # Wait for process to complete
            process.wait(timeout=1200)
            
            if process.returncode != 0:
                error_msg = process.stderr.read().strip()
                raise ValueError(f"Cursor Agent failed: {error_msg}")
            
            # Final update
            review.streaming_content = reviewed_content
            self.db.commit()
            
            logger.info(f"Cursor Agent review completed ({len(reviewed_content)} chars)")
            return reviewed_content
            
        except Exception as e:
            logger.error(f"Cursor Agent streaming error: {e}")
            raise ValueError(f"Failed to generate review with Cursor Agent: {str(e)}")
    
    async def _generate_with_cursor(self, prompt: str, content: str, model: str = "sonnet-4.5") -> str:
        """Generate review using Cursor Agent in headless mode with retry logic"""
        import subprocess
        import os as os_module
        import asyncio
        
        max_retries = 3
        retry_delay = 5  # seconds
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.info(f"Retry attempt {attempt + 1}/{max_retries} after {retry_delay}s delay...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                
                return await self._run_cursor_agent(prompt, content, model, os_module)
                
            except ValueError as e:
                error_msg = str(e)
                
                # Don't retry on certain errors
                if "Authentication" in error_msg or "Cannot use this model" in error_msg:
                    raise
                
                # Retry on connection errors
                if ("ECONNRESET" in error_msg or "aborted" in error_msg or "connection lost" in error_msg.lower()) and attempt < max_retries - 1:
                    logger.warning(f"Connection error on attempt {attempt + 1}, will retry: {error_msg}")
                    continue
                
                # Last attempt or non-retryable error
                raise
        
        raise ValueError("Failed after maximum retries")
    
    async def _run_cursor_agent(self, prompt: str, content: str, model: str, os_module) -> str:
        """Run Cursor Agent subprocess"""
        import subprocess
        
        try:
            # Prepare the full prompt for Cursor Agent
            full_prompt = f"""{prompt}

---

Document to review:

{content}

---

Now review this document. Remember:
- Quote relevant sections first (using `> `)
- Then add your comment in Obsidian callout format
- Focus on high-value insights only
- The original document will be linked, so you don't need to reproduce it
- Return ONLY quoted sections with comments, no preamble or conclusion.
"""
            
            # Set up environment with API key if available
            env = os_module.environ.copy()
            if self.cursor_api_key:
                env['CURSOR_API_KEY'] = self.cursor_api_key
            
            # Run Cursor Agent in headless mode with streaming for stability
            logger.info(f"Running Cursor Agent with model: {model} (streaming mode)")
            
            result = subprocess.run(
                [
                    self.cursor_agent_path,
                    '--model', model,
                    '--output-format', 'stream-json',
                    '--stream-partial-output',
                    '--print',
                    full_prompt
                ],
                capture_output=True,
                text=True,
                timeout=1200,  # 20 minute timeout for comprehensive reviews
                env=env
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.strip()
                logger.error(f"Cursor Agent error: {error_msg}")
                
                if 'Authentication required' in error_msg:
                    raise ValueError(
                        "Cursor Agent authentication required. "
                        "Please run 'cursor-agent login' or set CURSOR_API_KEY environment variable"
                    )
                
                raise ValueError(f"Cursor Agent failed: {error_msg}")
            
            # Parse streaming JSON output
            import json
            output_lines = result.stdout.strip().split('\n')
            reviewed_content = ""
            
            for line in output_lines:
                if line.strip():
                    try:
                        data = json.loads(line)
                        if 'delta' in data:
                            reviewed_content += data['delta']
                        elif 'content' in data:
                            reviewed_content += data['content']
                        elif 'text' in data:
                            reviewed_content += data['text']
                    except json.JSONDecodeError:
                        # Fallback: treat as plain text if not JSON
                        reviewed_content = result.stdout.strip()
                        break
            
            if not reviewed_content:
                raise ValueError("Cursor Agent returned empty response")
            
            logger.info(f"Cursor Agent review completed ({len(reviewed_content)} chars)")
            return reviewed_content
            
        except subprocess.TimeoutExpired:
            logger.error("Cursor Agent timed out after 1200 seconds")
            raise ValueError("Review generation timed out (20 min limit). The document may be extremely long. Try 'Quick' review type for faster results.")
        except Exception as e:
            logger.error(f"Cursor Agent error: {e}")
            error_msg = str(e)
            
            # Provide helpful error messages
            if "ECONNRESET" in error_msg or "aborted" in error_msg:
                raise ValueError("Cursor Agent connection lost. The document may be too long. Try 'Quick' review type or use a shorter document.")
            elif "Authentication" in error_msg:
                raise ValueError("Cursor Agent authentication required. Run 'cursor-agent login' in terminal.")
            elif "Cannot use this model" in error_msg:
                raise ValueError(f"Model not available. {error_msg}")
            else:
                raise ValueError(f"Failed to generate review with Cursor Agent: {error_msg}")
    
    async def _generate_with_openai(self, prompt: str, content: str) -> str:
        """Generate review using OpenAI"""
        try:
            import openai
            openai.api_key = self.openai_api_key
            
            response = openai.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Please review this document:\n\n{content}"}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise ValueError(f"Failed to generate review with OpenAI: {str(e)}")
    
    async def _generate_with_anthropic(self, prompt: str, content: str) -> str:
        """Generate review using Anthropic Claude"""
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=self.anthropic_api_key)
            
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                temperature=0.7,
                system=prompt,
                messages=[
                    {"role": "user", "content": f"Please review this document:\n\n{content}"}
                ]
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise ValueError(f"Failed to generate review with Anthropic: {str(e)}")
    
    def _generate_mock_review(self, document: Document, content: str) -> str:
        """Generate a mock review for testing without API keys"""
        logger.info("Generating MOCK review (no API keys configured)")
        
        # Extract first few sections for mock comments
        sections = content.split('\n## ')[:3]  # First 3 sections
        
        mock_review = content + "\n\n---\n\n## 🤖 Mock AI Review Comments\n\n"
        
        # Add mock comments after each major section
        mock_comments = [
            {"type": "Strategic", "content": "Validate this approach with key stakeholders before rollout.", "context": "Early validation reduces rework.", "suggestion": "Run a small POC first."},
            {"type": "Technical", "content": "Architecture may need to scale under load.", "context": "Consider failure modes and observability.", "suggestion": "Add load testing and monitoring targets."},
            {"type": "Metrics", "content": "Success metrics and KPIs are not clearly defined.", "context": "Measurable outcomes help track progress.", "suggestion": "Define concrete metrics and targets."},
        ]
        
        for i, comment in enumerate(mock_comments[:3]):
            mock_review += f"\n> [!note] {comment['type']} (MOCK)\n"
            mock_review += f"> **{comment['type'].split()[1]}**: {comment['content']}\n"
            mock_review += f"> \n"
            mock_review += f"> **Context**: {comment['context']}\n"
            mock_review += f"> **Suggestion**: {comment['suggestion']}\n\n"
        
        mock_review += "\n---\n\n**Note**: This is a MOCK review generated for testing. "
        mock_review += "Configure OPENAI_API_KEY or ANTHROPIC_API_KEY for real AI reviews.\n"
        
        return mock_review
    
    def _get_model_name(self) -> str:
        """Get the model name based on provider"""
        if self.provider == 'cursor':
            return "cursor-cli-claude-4.5-sonnet"
        elif self.provider == 'anthropic':
            return "claude-3-5-sonnet-20241022"
        elif self.provider == 'openai':
            return "gpt-4-turbo-preview"
        else:
            return "mock-reviewer-v1"
    
    def _get_review_type_instructions(self, review_type: str) -> str:
        """Get specific instructions based on review type"""
        instructions = {
            "comprehensive": """
**Comprehensive Review Focus**:
- Deep dive into ALL aspects: strategy, execution, technical, business impact
- Cover: architecture, scalability, metrics, merchant impact, execution risks, competitive analysis
- Provide both high-level strategic feedback and granular technical details
- **Aim for 15-20 comments** covering different aspects
- **MAXIMUM 5000 characters total output**
- Be thorough but concise - quality over quantity
""",
            "quick": """
**Quick Review Focus - CRITICAL ISSUES ONLY**:
- Identify ONLY the most critical blockers, risks, and gaps
- What would cause this to fail? What's missing that's essential?
- Focus on: major technical risks, missing metrics/KPIs, unrealistic timelines, resource constraints
- **NO praise, NO minor suggestions, NO nice-to-haves**
- **NO hand-wavy comments** - be specific with examples and data
- If there are no critical issues, say so and stop
- **Quality over quantity** - 3-5 critical comments maximum
- Each comment must be actionable and high-impact
""",
            "technical": """
**Technical Review Focus**:
- Deep technical analysis: architecture, scalability, reliability, performance
- Add comments on technical concerns, edge cases, and engineering excellence
- Cover: system design, failure modes, observability, technical debt, maintainability
- Skip business/strategy - focus purely on technical soundness
- Don't be nitpicky about code style - focus on architectural and scalability concerns
""",
            "strategic": """
**Strategic Review Focus**:
- Business strategy, market positioning, competitive analysis, ROI
- Add comments on strategic alignment, business impact, and market opportunities
- Cover: GMV/NR impact, competitive landscape, merchant value prop, market timing
- Skip technical implementation details - focus on business outcomes and strategy
- Think like a founder/GM - what moves the needle for the business?
"""
        }
        return instructions.get(review_type, instructions["comprehensive"])
    
    def _build_review_prompt(
        self,
        title: str,
        doc_type: str,
        review_type: str,
        personas: List[str]
    ) -> str:
        """Build persona-based review prompt with multiple reviewer perspectives"""
        
        # Define persona profiles
        persona_profiles = {
            "engineering-leader": """
**Engineering Leader Persona** (Primary):
- Focus: Team capacity, execution feasibility, resource allocation, timelines
- Questions: Can we execute with current team? What is the impact on other priorities?
- Style: Pragmatic, execution-focused
""",
            "principal-engineer": """
**Principal Engineer Persona**:
- Focus: Architecture, scalability, technical debt, system design
- Questions: What are the failure modes? How do we handle edge cases? Will this scale?
- Style: Deep technical analysis, long-term maintainability
""",
            "product-strategist": """
**Product Strategist Persona**:
- Focus: Business impact, market positioning, competitive analysis
- Questions: What is the impact? How does this compare to alternatives? What is the value prop?
- Style: Strategic, data-driven
""",
            "startup-founder": """
**Startup Founder Persona**:
- Focus: MVP scope, time-to-market, resource efficiency
- Questions: What is the MVP? What can we defer? How to validate cheaply?
- Style: Pragmatic, focused on speed and learning
""",
            "process-champion": """
**Process Champion Persona**:
- Focus: Metrics, quality, reliability, compliance
- Questions: How do we measure success? What is the monitoring strategy?
- Style: Metrics-driven, risk-aware
""",
            "innovation-driver": """
**Innovation Persona**:
- Focus: Automation, productivity, emerging tech
- Questions: Can we use AI or automation here? What is the simplest solution?
- Style: Forward-thinking, practical
"""
        }
        
        # Build persona sections
        active_personas = []
        for persona in personas:
            if persona in persona_profiles:
                active_personas.append(persona_profiles[persona])
        
        personas_text = "\n".join(active_personas) if active_personas else persona_profiles["engineering-leader"]
        
        prompt = f"""You are reviewing this document from multiple perspectives.

**Review Perspectives** (use these personas for diverse feedback):
{personas_text}

**Document Context**:
- Type: {doc_type}
- Title: "{title}"
- Review Type: {review_type}

**Review Instructions**:
1. Review from EACH selected persona perspective
2. Add inline comments throughout the document
3. Each comment should clearly indicate which persona is speaking
4. Be specific and actionable
5. Balance critique with positive feedback
6. Provide alternatives, not just problems

**Comment Format**:

> [!note] AI Review ({'{'}Persona{'}'})
> **{'{'}Comment Type{'}'}**: [Your insight]
> **Context**: [Relevant context]
> **Suggestion**: [Actionable recommendation]

**Comment Types**: Strategic Question, Technical Concern, Data/Metrics, Positive, Suggestion, Execution Risk, Impact, Innovation

**Review Type: {review_type.upper()}**
{self._get_review_type_instructions(review_type)}

**CRITICAL OUTPUT FORMAT**:
DO NOT return the full document. Return ONLY inline comments in this format:

**Format for EACH comment:**
1. Quote 1-2 lines max from the document (the specific part you're commenting on)
2. Add a blank line
3. Add your comment in Obsidian callout format
4. Add a blank line before the next quote

**Example of GOOD critical comment (specific, data-driven, actionable):**

> "The current model's performance, characterized by 40% recall and a notably low 28% precision"

> [!note] AI Review (Principal Engineer)
> **Technical Concern**: 28% precision implies 72% false positive rate; this is business-critical.
> **Context**: Precision issues often stem from data quality or optimization metric choice.
> **Suggestion**: Check training objective (F1 vs precision-recall), analyze top false positives, try threshold adjustment.

**Example of BAD comment (vague, hand-wavy, not critical):**

> "This initiative aligns well with business goals"

> [!note] AI Review
> **Positive**: Good strategic thinking.
> **Suggestion**: Keep going.

**Review Instructions**:
1. Read through the entire document carefully
2. Identify sections that need comments (gaps, risks, opportunities, strengths)
3. For EACH comment:
   - Quote ONLY 1-2 lines (the specific sentence/phrase you're commenting on)
   - Add your comment in Obsidian callout format
4. **Quality over quantity** - aim for 10-20 high-value insights
5. Be specific and actionable - provide alternatives, not just problems
6. **Keep quotes SHORT** - just enough to identify what you're commenting on

**Comment Format** (use exactly this):

> "[Short quoted text - 1-2 lines max]"

> [!note] 💭 AI Review - Saurabh (Persona Name)
> **Comment Type**: [Your insight here]
> 
> **Context**: [Reference to relevant experience]
> **Suggestion**: [Actionable recommendation]

**Comment Types** (use ONLY these for critical issues):
- ⚠️ **Technical Concern** - Architecture flaws, scalability risks, reliability issues
- 📊 **Data/Metrics** - Missing critical KPIs, no measurement strategy
- 🎯 **Execution Risk** - Unrealistic timeline, resource constraints, blockers
- 💭 **Strategic Question** - Fundamental gaps in strategy or approach
- 🏪 **Merchant Impact** - Major UX/conversion issues

**DO NOT USE**: ✅ Positive, 💡 Suggestion (unless it solves a critical problem), 🚀 Innovation

**Critical Guidelines**:
- **Quote first, comment second** - show exactly what you're commenting on
- **Keep quotes to 1-2 lines MAXIMUM** - just the specific sentence/phrase
- **Clearly indicate which persona is speaking** in each comment
- **Be specific and data-driven** - cite examples, numbers, past experiences
- **NO praise, NO minor suggestions** - only critical, high-impact issues
- **Each comment must be actionable** - what specifically needs to change?
- The original document will be linked, so you don't need to reproduce it
- **Quality over quantity** - 3-10 critical comments depending on review type
- If there are no critical issues, output just 1-2 comments saying so

Now review the document and return ONLY the most critical issues as short quoted snippets with comments. NO preamble, NO conclusion, NO full paragraphs, NO hand-wavy feedback."""

        return prompt
    
    def _parse_document_sections(self, content: str) -> List[Dict]:
        """Parse markdown document into logical sections"""
        sections = []
        current_section = {"title": "", "content": "", "level": 0}
        
        for line in content.split('\n'):
            # Check for headers
            if line.startswith('#'):
                if current_section["content"]:
                    sections.append(current_section)
                
                level = len(line.split()[0])
                title = line.lstrip('#').strip()
                current_section = {"title": title, "content": "", "level": level}
            else:
                current_section["content"] += line + "\n"
        
        if current_section["content"]:
            sections.append(current_section)
        
        return sections
    
    def _count_comments(self, reviewed_content: str) -> Dict:
        """Count comments by category"""
        
        categories = {
            "strategic": len(re.findall(r'💭.*Strategic Question', reviewed_content)),
            "technical": len(re.findall(r'⚠️.*Technical Concern', reviewed_content)),
            "data_metrics": len(re.findall(r'📊.*Data/Metrics', reviewed_content)),
            "positive": len(re.findall(r'✅.*Positive', reviewed_content)),
            "suggestion": len(re.findall(r'💡.*Suggestion', reviewed_content)),
            "execution": len(re.findall(r'🎯.*Execution Risk', reviewed_content)),
            "merchant": len(re.findall(r'🏪.*Merchant Impact', reviewed_content))
        }
        
        total = sum(categories.values())
        
        return {
            "total": total,
            "categories": categories
        }
    
    def _create_reviewed_document(
        self,
        original_doc: Document,
        reviewed_content: str,
        review: DocumentReview
    ) -> Document:
        """Create a new document with the reviewed content"""
        
        # Generate title for reviewed document
        today = datetime.utcnow().strftime("%Y-%m-%d")
        reviewed_title = f"{original_doc.title.strip()} [AI Reviewed - {today}]"
        
        # Generate vault path for reviewed document
        # Save in dedicated AI Reviews directory
        sanitized_title = self._sanitize_filename(reviewed_title)
        vault_path = f"05 - AI/AI Reviews/{sanitized_title}.md"
        
        # Add review metadata header
        review_header = f"""---
original_document: {original_doc.title}
review_date: {today}
review_type: {review.review_type}
focus_areas: {', '.join(review.focus_areas or [])}
ai_model: {review.ai_model}
reviewed_by: Saurabh Mishra (AI Persona)
---

# AI Review Summary

This document has been reviewed by Saurabh Mishra's AI persona focusing on: {', '.join(review.focus_areas or [])}.

Look for inline comments marked with `> [!note] AI Review - Saurabh` throughout the document.

---

"""
        
        full_content = review_header + reviewed_content
        
        # Create new document with custom vault path
        reviewed_doc = Document(
            id=str(uuid.uuid4()),
            title=reviewed_title,
            content_md=full_content,
            source_url=original_doc.source_url,
            source_type=original_doc.source_type,
            doc_type=original_doc.doc_type,
            vault_path=vault_path,
            metadata_json={
                "original_document_id": original_doc.id,
                "review_id": review.id,
                "review_type": review.review_type,
                "ai_reviewed": True
            },
            author=original_doc.author,
            imported_by=review.created_by,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.db.add(reviewed_doc)
        self.db.commit()
        self.db.refresh(reviewed_doc)
        
        # Save to vault
        self.document_service.save_to_vault(reviewed_doc)
        
        logger.info(f"Created reviewed document: {reviewed_doc.id} at {reviewed_doc.vault_path}")
        
        return reviewed_doc
    
    def _sanitize_filename(self, title: str) -> str:
        """Sanitize title for use as filename"""
        # Replace invalid characters
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        sanitized = title
        for char in invalid_chars:
            sanitized = sanitized.replace(char, '_')
        
        # Limit length
        max_length = 200
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized.strip()
    
    def get_review_by_id(self, review_id: str) -> Optional[DocumentReview]:
        """Get review by ID"""
        return self.db.query(DocumentReview).filter(DocumentReview.id == review_id).first()
    
    def list_reviews(
        self,
        document_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[DocumentReview]:
        """List reviews with optional filters"""
        query = self.db.query(DocumentReview)
        
        if document_id:
            query = query.filter(DocumentReview.original_document_id == document_id)
        
        if status:
            query = query.filter(DocumentReview.status == status)
        
        return query.order_by(DocumentReview.started_at.desc()).limit(limit).all()

