"""PDF download and image extraction for Google Docs."""

import logging
import os
import re
import subprocess
import tempfile
import shutil
from typing import Optional, Dict, List, Tuple
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)


class PDFService:
    """Service for PDF download and image extraction"""
    
    def __init__(self, pdf2md_path: Optional[str] = None):
        self.pdf2md_path = pdf2md_path or ""
        if self.pdf2md_path and not os.path.exists(self.pdf2md_path):
            logger.warning("pdf2md not found at %s", self.pdf2md_path)
    
    async def download_as_pdf(
        self,
        doc_id: str,
        access_token: str,
        output_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Download Google Doc as PDF
        
        Args:
            doc_id: Google Docs document ID
            access_token: Google OAuth access token
            output_path: Optional output path (uses temp if not provided)
            
        Returns:
            Path to downloaded PDF or None
        """
        try:
            import requests
            
            # Google Docs export URL
            export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=pdf"
            
            # Download PDF
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            
            response = requests.get(export_url, headers=headers)
            response.raise_for_status()
            
            # Save to file
            if not output_path:
                temp_dir = tempfile.mkdtemp()
                output_path = os.path.join(temp_dir, f"{doc_id}.pdf")
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Downloaded PDF: {output_path} ({len(response.content)} bytes)")
            return output_path
            
        except Exception as e:
            logger.error(f"Error downloading PDF for {doc_id}: {e}")
            return None
    
    def extract_images_with_pdf2md(
        self,
        pdf_path: str,
        output_dir: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Extract images from PDF using pdf2md tool
        
        Args:
            pdf_path: Path to PDF file
            output_dir: Optional output directory
            
        Returns:
            Dictionary with markdown and image paths or None
        """
        try:
            if not os.path.exists(self.pdf2md_path):
                logger.error(f"pdf2md not found at {self.pdf2md_path}")
                return None
            
            if not os.path.exists(pdf_path):
                logger.error(f"PDF not found: {pdf_path}")
                return None
            
            # Create output directory if needed
            if not output_dir:
                output_dir = os.path.dirname(pdf_path)
            
            os.makedirs(output_dir, exist_ok=True)
            
            # Run pdf2md
            logger.info(f"Running pdf2md on {pdf_path}")
            
            result = subprocess.run(
                [self.pdf2md_path, pdf_path],
                cwd=output_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"pdf2md failed: {result.stderr}")
                return None
            
            # Find generated files
            pdf_name = Path(pdf_path).stem
            md_file = os.path.join(output_dir, f"{pdf_name}_converted.md")
            images_dir = os.path.join(output_dir, f"{pdf_name}_converted_images")
            
            if not os.path.exists(md_file):
                logger.warning(f"Markdown file not found: {md_file}")
                return None
            
            # Get list of images
            image_files = []
            if os.path.exists(images_dir):
                image_files = [
                    os.path.join(images_dir, f)
                    for f in os.listdir(images_dir)
                    if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))
                ]
            
            logger.info(f"Extracted {len(image_files)} images from PDF")
            
            return {
                'markdown_file': md_file,
                'images_dir': images_dir,
                'image_files': image_files,
                'image_count': len(image_files)
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"pdf2md timed out for {pdf_path}")
            return None
        except Exception as e:
            logger.error(f"Error extracting images: {e}")
            return None
    
    def extract_images_from_markdown(
        self,
        markdown_path: str
    ) -> List[Dict]:
        """
        Extract image references from markdown file
        
        Args:
            markdown_path: Path to markdown file
            
        Returns:
            List of image dictionaries with path and caption
        """
        try:
            with open(markdown_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find markdown images: ![alt](path)
            pattern = r'!\[(.*?)\]\((.*?)\)'
            matches = re.findall(pattern, content)
            
            images = []
            for alt, path in matches:
                images.append({
                    'alt': alt,
                    'path': path,
                    'caption': alt if alt else None
                })
            
            logger.info(f"Found {len(images)} image references in markdown")
            return images
            
        except Exception as e:
            logger.error(f"Error extracting images from markdown: {e}")
            return []
    
    def copy_images_to_vault(
        self,
        images_dir: str,
        vault_path: str,
        doc_title: str
    ) -> List[str]:
        """
        Copy images to Obsidian vault
        
        Args:
            images_dir: Source directory with images
            vault_path: Obsidian vault root path
            doc_title: Document title (for organizing images)
            
        Returns:
            List of relative paths to copied images
        """
        try:
            if not settings.obsidian_enabled:
                return []
            if not os.path.exists(images_dir):
                return []
            safe_title = re.sub(r'[^\w\s-]', '', doc_title).strip()
            safe_title = re.sub(r'[-\s]+', '-', safe_title)
            vault_images_dir = str(settings.vault_content_root / "Docs" / "Google Docs" / "images" / safe_title)
            
            os.makedirs(vault_images_dir, exist_ok=True)
            
            # Copy images
            copied_images = []
            for img_file in os.listdir(images_dir):
                if img_file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    src = os.path.join(images_dir, img_file)
                    dst = os.path.join(vault_images_dir, img_file)
                    
                    shutil.copy2(src, dst)
                    
                    # Return relative path from doc location
                    rel_path = os.path.join("images", safe_title, img_file)
                    copied_images.append(rel_path)
            
            logger.info(f"Copied {len(copied_images)} images to vault")
            return copied_images
            
        except Exception as e:
            logger.error(f"Error copying images to vault: {e}")
            return []
    
    async def process_document_images(
        self,
        doc_id: str,
        doc_title: str,
        access_token: str,
        vault_path: str
    ) -> Optional[Dict]:
        """
        Complete workflow: Download PDF, extract images, copy to vault
        
        Args:
            doc_id: Google Docs document ID
            doc_title: Document title
            access_token: Google OAuth access token
            vault_path: Obsidian vault path
            
        Returns:
            Dictionary with image info or None
        """
        try:
            # Step 1: Download as PDF
            pdf_path = await self.download_as_pdf(doc_id, access_token)
            if not pdf_path:
                return None
            
            # Step 2: Extract images with pdf2md
            extraction_result = self.extract_images_with_pdf2md(pdf_path)
            if not extraction_result or extraction_result['image_count'] == 0:
                logger.info(f"No images found in document {doc_id}")
                # Clean up temp PDF
                try:
                    os.remove(pdf_path)
                    temp_dir = os.path.dirname(pdf_path)
                    if temp_dir.startswith('/tmp'):
                        shutil.rmtree(temp_dir, ignore_errors=True)
                except:
                    pass
                return None
            
            # Step 3: Copy images to vault
            copied_images = self.copy_images_to_vault(
                extraction_result['images_dir'],
                vault_path,
                doc_title
            )
            
            # Step 4: Clean up temporary files
            try:
                os.remove(pdf_path)
                temp_dir = os.path.dirname(pdf_path)
                if temp_dir.startswith('/tmp'):
                    shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                logger.warning(f"Error cleaning up temp files: {e}")
            
            return {
                'image_count': len(copied_images),
                'image_paths': copied_images,
                'vault_location': os.path.join(vault_path, "images", doc_title)
            }
            
        except Exception as e:
            logger.error(f"Error processing document images: {e}")
            return None


# Global instance
_pdf_service: Optional[PDFService] = None


def get_pdf_service() -> PDFService:
    """Get or create the global PDF service instance"""
    global _pdf_service
    
    if _pdf_service is None:
        _pdf_service = PDFService()
    
    return _pdf_service

