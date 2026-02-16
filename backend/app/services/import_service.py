"""Import service for orchestrating Google Docs imports"""
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import json
import logging

from app.services.google_docs_service import GoogleDocsService
from app.services.google_sheets_service import GoogleSheetsService
from app.services.pdf_service import PDFService
from app.services.document_service import DocumentService
from app.models.import_job import ImportJob, ImportStatus
from app.models.document import DocumentSource
from app.models.spreadsheet import SpreadsheetData
from app.config import settings

logger = logging.getLogger(__name__)


class ImportService:
    """Service for importing Google Docs into the knowledge base"""
    
    def __init__(self, db: Session, access_token: str):
        self.db = db
        self.access_token = access_token
        self.google_docs_service = GoogleDocsService(access_token)
        self.google_sheets_service = GoogleSheetsService(access_token)
        path = (getattr(settings, "PDF2MD_PATH", None) or "").strip() or ""
        self.pdf_service = PDFService(pdf2md_path=path)
        self.document_service = DocumentService(db)
    
    async def import_from_url(
        self,
        url: str,
        user_email: Optional[str] = None,
        recursive: bool = True,
        job_id: Optional[str] = None
    ) -> ImportJob:
        """Import document(s) from Google Docs URL
        
        Args:
            url: Google Docs URL
            user_email: Email of user initiating import
            recursive: Whether to import linked documents
            job_id: Optional existing job ID (if called from background task)
            
        Returns:
            ImportJob tracking the import progress
        """
        
        # Get or create import job
        if job_id:
            job = self.db.query(ImportJob).filter(ImportJob.id == job_id).first()
            if not job:
                raise ValueError(f"Import job {job_id} not found")
        else:
            job = ImportJob(
                source_url=url,
                status=ImportStatus.PENDING,
                user_email=user_email,
                total_docs=1,  # Will update as we discover linked docs
            )
            self.db.add(job)
            self.db.commit()
            self.db.refresh(job)
        
        try:
            # Update status to processing
            job.status = ImportStatus.PROCESSING
            self.db.commit()
            
            # Extract document ID
            doc_id = self.google_docs_service.extract_doc_id(url)
            if not doc_id:
                job.status = ImportStatus.FAILED
                job.error_message = "Invalid Google Docs URL"
                job.completed_at = datetime.utcnow()
                self.db.commit()
                return job
            
            # Import main document
            imported_doc_ids = []
            failed_imports = []
            
            # Check if main document already exists
            existing_main = self.document_service.get_document_by_source_url(
                f"https://docs.google.com/document/d/{doc_id}"
            )
            
            if existing_main:
                # Document already imported, just return it
                imported_doc_ids.append(existing_main.id)
                job.processed_docs += 1
                job.status = ImportStatus.COMPLETED
                job.imported_doc_ids = json.dumps(imported_doc_ids)
                job.completed_at = datetime.utcnow()
                self.db.commit()
                return job
            
            result = await self._import_single_document(doc_id, user_email)
            if result['success']:
                imported_doc_ids.append(result['document_id'])
                job.processed_docs += 1
            else:
                failed_imports.append({
                    'doc_id': doc_id,
                    'error': result['error']
                })
                job.failed_docs += 1
            
            # Import linked documents if recursive
            if recursive and result['success'] and result.get('linked_doc_ids'):
                linked_ids = result['linked_doc_ids']
                job.total_docs += len(linked_ids)
                self.db.commit()
                
                for linked_id in linked_ids:
                    # Check if already imported
                    existing = self.document_service.get_document_by_source_url(
                        f"https://docs.google.com/document/d/{linked_id}"
                    )
                    
                    if existing:
                        imported_doc_ids.append(existing.id)
                        job.processed_docs += 1
                        continue
                    
                    # Import linked document
                    linked_result = await self._import_single_document(linked_id, user_email)
                    if linked_result['success']:
                        imported_doc_ids.append(linked_result['document_id'])
                        job.processed_docs += 1
                    else:
                        failed_imports.append({
                            'doc_id': linked_id,
                            'error': linked_result['error']
                        })
                        job.failed_docs += 1
                    
                    self.db.commit()
            
            # Finalize job
            job.imported_doc_ids = json.dumps(imported_doc_ids)
            
            if failed_imports:
                job.error_details = json.dumps(failed_imports)
                job.status = ImportStatus.PARTIAL if imported_doc_ids else ImportStatus.FAILED
            else:
                job.status = ImportStatus.COMPLETED
            
            job.completed_at = datetime.utcnow()
            self.db.commit()
            
        except Exception as e:
            job.status = ImportStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            self.db.commit()
        
        return job
    
    async def _import_single_document(
        self,
        doc_id: str,
        user_email: Optional[str] = None
    ) -> Dict:
        """Import a single Google Doc with images and sheets
        
        Returns:
            Dict with 'success', 'document_id', 'linked_doc_ids', and optional 'error'
        """
        try:
            # Get document with links and metadata
            document, linked_doc_ids, metadata = await self.google_docs_service.get_document_with_links(doc_id)
            
            if not document:
                return {
                    'success': False,
                    'error': 'Failed to fetch document'
                }
            
            # Convert to markdown
            markdown_content, title = self.google_docs_service.convert_to_markdown(document)
            
            # Extract author from metadata
            author = None
            if metadata and 'owners' in metadata:
                owners = metadata['owners']
                if owners:
                    author = owners[0].get('displayName', owners[0].get('emailAddress'))
            
            # Build additional metadata
            additional_metadata = {}
            if metadata:
                if 'createdTime' in metadata:
                    additional_metadata['google_created'] = metadata['createdTime']
                if 'modifiedTime' in metadata:
                    additional_metadata['google_modified'] = metadata['modifiedTime']
                if 'description' in metadata:
                    additional_metadata['description'] = metadata['description']
            
            # STEP 1: Extract and process images from PDF
            logger.info(f"[IMAGES] Extracting images for document: {title}")
            try:
                images_result = await self._process_document_images(doc_id, title)
                if images_result and images_result['image_count'] > 0:
                    logger.info(f"[IMAGES] ✓ Extracted {images_result['image_count']} images")
                    additional_metadata['images_extracted'] = True
                    additional_metadata['image_count'] = images_result['image_count']
                    additional_metadata['demo_mode'] = False
                    
                    # Append images to markdown content
                    markdown_content += "\n\n---\n\n## 📷 Extracted Images\n\n"
                    markdown_content += f"*{images_result['image_count']} image(s) extracted from the PDF*\n\n"
                    for img_path in images_result['image_paths']:
                        markdown_content += f"![Image]({img_path})\n\n"
                else:
                    logger.info(f"[IMAGES] No images found in document")
                    additional_metadata['images_extracted'] = False
            except Exception as e:
                logger.error(f"[IMAGES] Error extracting images: {e}")
                additional_metadata['images_extracted'] = False
            
            # Create document in database
            doc_url = f"https://docs.google.com/document/d/{doc_id}"
            db_document = self.document_service.create_document(
                title=title,
                content_md=markdown_content,
                source_url=doc_url,
                source_type=DocumentSource.GOOGLE_DOCS,
                metadata=additional_metadata,
                author=author,
                imported_by=user_email,
            )
            
            # STEP 2: Extract and process Google Sheets
            logger.info(f"[SHEETS] Detecting sheets in document: {title}")
            sheets_links = self.google_docs_service.extract_sheets_links(document)
            
            if sheets_links:
                logger.info(f"[SHEETS] Found {len(sheets_links)} sheet(s)")
                sheets_processed = await self._process_document_sheets(
                    db_document.id,
                    sheets_links,
                    markdown_content
                )
                
                if sheets_processed:
                    logger.info(f"[SHEETS] ✓ Processed {sheets_processed['count']} sheet(s)")
                    # Update markdown with sheet data
                    markdown_content = sheets_processed['updated_markdown']
                    db_document.content_md = markdown_content
                    self.db.commit()
            else:
                logger.info(f"[SHEETS] No sheets found in document")
            
            # Save to vault (with images and sheets embedded)
            self.document_service.save_to_vault(db_document)
            
            return {
                'success': True,
                'document_id': db_document.id,
                'linked_doc_ids': linked_doc_ids,
                'title': title,
                'images_extracted': images_result['image_count'] if images_result else 0,
                'sheets_processed': len(sheets_links) if sheets_links else 0
            }
            
        except Exception as e:
            logger.error(f"Error importing document {doc_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _process_document_images(
        self,
        doc_id: str,
        doc_title: str
    ) -> Optional[Dict]:
        """Extract images from Google Doc via PDF
        
        Returns:
            Dict with image info or None
        """
        try:
            result = await self.pdf_service.process_document_images(
                doc_id=doc_id,
                doc_title=doc_title,
                access_token=self.access_token,
                vault_path=settings.effective_obsidian_vault_path
            )
            return result
        except Exception as e:
            logger.error(f"Error processing images for {doc_id}: {e}")
            return None
    
    async def _process_document_sheets(
        self,
        document_id: str,
        sheets_links: List[str],
        current_markdown: str
    ) -> Optional[Dict]:
        """Process Google Sheets linked in document
        
        Returns:
            Dict with updated markdown and count
        """
        try:
            from app.services.ai_service import get_ai_service
            ai_service = get_ai_service()
            
            sheets_markdown = "\n\n## 📊 Linked Spreadsheets\n\n"
            processed_count = 0
            
            for sheet_url in sheets_links:
                try:
                    # Extract sheet ID
                    sheet_id = self.google_sheets_service.extract_sheet_id(sheet_url)
                    if not sheet_id:
                        logger.warning(f"Could not extract sheet ID from {sheet_url}")
                        continue
                    
                    # Get metadata
                    metadata = await self.google_sheets_service.get_sheet_metadata(sheet_id)
                    if not metadata:
                        logger.warning(f"Could not fetch metadata for sheet {sheet_id}")
                        continue
                    
                    sheet_title = metadata.get('title', 'Untitled')
                    logger.info(f"[SHEETS] Processing: {sheet_title}")
                    
                    # Get CSV data
                    csv_data = await self.google_sheets_service.get_sheet_as_csv(sheet_id)
                    if not csv_data:
                        logger.warning(f"Could not fetch CSV for sheet {sheet_id}")
                        continue
                    
                    # Convert to markdown table
                    markdown_table = self.google_sheets_service.csv_to_markdown_table(
                        csv_data,
                        max_rows=50
                    )
                    
                    # Get AI analysis
                    ai_analysis = await ai_service.analyze_spreadsheet_data(csv_data, sheet_title)
                    
                    # Add to markdown
                    sheets_markdown += f"### 📊 {sheet_title}\n\n"
                    sheets_markdown += f"**Source:** [{sheet_title}]({sheet_url})\n\n"
                    
                    if ai_analysis:
                        sheets_markdown += f"**AI Analysis:**\n{ai_analysis['summary']}\n\n"
                    
                    sheets_markdown += f"**Data Preview:**\n\n{markdown_table}\n\n"
                    sheets_markdown += "---\n\n"
                    
                    # Store in database
                    sheet_data = SpreadsheetData(
                        document_id=document_id,
                        sheet_url=sheet_url,
                        sheet_id=sheet_id,
                        sheet_title=sheet_title,
                        csv_data=csv_data,
                        markdown_table=markdown_table,
                        ai_analysis=ai_analysis,
                        metadata_json=metadata
                    )
                    self.db.add(sheet_data)
                    processed_count += 1
                    
                    logger.info(f"[SHEETS] ✓ Processed: {sheet_title}")
                    
                except Exception as e:
                    logger.error(f"Error processing sheet {sheet_url}: {e}")
                    continue
            
            self.db.commit()
            
            # Update markdown with all sheets
            updated_markdown = current_markdown + sheets_markdown
            
            return {
                'count': processed_count,
                'updated_markdown': updated_markdown
            }
            
        except Exception as e:
            logger.error(f"Error processing sheets: {e}")
            return None
    
    def get_import_job(self, job_id: str) -> Optional[ImportJob]:
        """Get import job by ID"""
        return self.db.query(ImportJob).filter(ImportJob.id == job_id).first()
    
    def list_import_jobs(
        self,
        user_email: Optional[str] = None,
        limit: int = 50
    ) -> List[ImportJob]:
        """List import jobs"""
        query = self.db.query(ImportJob).order_by(ImportJob.started_at.desc())
        
        if user_email:
            query = query.filter(ImportJob.user_email == user_email)
        
        return query.limit(limit).all()

