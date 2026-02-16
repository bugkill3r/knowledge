"""Google Docs service for fetching and converting documents"""
import logging
import re
from typing import Optional, Dict, List, Tuple
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.credentials import Credentials as BaseCredentials
from bs4 import BeautifulSoup
from markdownify import markdownify as md

logger = logging.getLogger(__name__)


class AccessTokenCredentials(BaseCredentials):
    """Simple credentials class that only holds an access token"""
    
    def __init__(self, access_token: str):
        super().__init__()
        self.token = access_token
        self._expiry = None
    
    def refresh(self, request):
        """Refresh is not supported for access-token-only credentials"""
        pass
    
    def apply(self, headers, token=None):
        """Apply the token to the authentication header"""
        headers['Authorization'] = f'Bearer {self.token}'
    
    def before_request(self, request, method, url, headers):
        """Called before making a request"""
        self.apply(headers)
    
    @property
    def expired(self):
        """Token expiry is not tracked"""
        return False
    
    @property
    def valid(self):
        """Token is always considered valid"""
        return True


class GoogleDocsService:
    """Service for interacting with Google Docs API"""
    
    def __init__(self, access_token: str):
        """Initialize service with OAuth access token"""
        # Create custom credentials with just the access token
        credentials = AccessTokenCredentials(access_token)
        
        # Build services with credentials
        self.docs_service = build('docs', 'v1', credentials=credentials)
        self.drive_service = build('drive', 'v3', credentials=credentials)
    
    def extract_doc_id(self, url: str) -> Optional[str]:
        """Extract document ID from Google Docs URL"""
        patterns = [
            r'/document/d/([a-zA-Z0-9-_]+)',
            r'id=([a-zA-Z0-9-_]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    async def get_document(self, doc_id: str) -> Optional[Dict]:
        """Fetch document from Google Docs API"""
        try:
            document = self.docs_service.documents().get(documentId=doc_id).execute()
            return document
        except HttpError as e:
            logger.error("Error fetching document %s: %s", doc_id, e)
            return None
    
    async def get_document_metadata(self, doc_id: str) -> Optional[Dict]:
        """Get document metadata from Google Drive"""
        try:
            metadata = self.drive_service.files().get(
                fileId=doc_id,
                fields='id,name,createdTime,modifiedTime,owners,lastModifyingUser,description'
            ).execute()
            return metadata
        except HttpError as e:
            logger.error("Error fetching metadata for %s: %s", doc_id, e)
            return None
    
    def extract_links(self, document: Dict) -> List[str]:
        """Extract all Google Docs links from a document"""
        links = []
        
        def traverse_content(content, depth=0):
            """Recursively traverse document content"""
            if isinstance(content, dict):
                # Check for richLink elements (Google Docs smart chips)
                if 'richLink' in content:
                    rich_link_props = content['richLink'].get('richLinkProperties', {})
                    url = rich_link_props.get('uri', '')
                    if url and 'docs.google.com/document' in url:
                        links.append(url)
                        logger.debug("Found Google Doc richLink at depth %s: %s", depth, url)

                if 'textRun' in content:
                    text_style = content['textRun'].get('textStyle', {})
                    link = text_style.get('link', {})
                    url = link.get('url', '')
                    if url and 'docs.google.com/document' in url:
                        links.append(url)
                        logger.debug("Found Google Doc textRun link at depth %s: %s", depth, url)
                
                # Recursively check all dict values
                for key, value in content.items():
                    traverse_content(value, depth + 1)
            
            elif isinstance(content, list):
                for item in content:
                    traverse_content(item, depth + 1)
        
        traverse_content(document)
        logger.debug("Total Google Docs links found: %s", len(links))
        return list(set(links))

    def extract_sheets_links(self, document: Dict) -> List[str]:
        """Extract all Google Sheets links from a document"""
        sheets_links = []
        
        def traverse_content(content, depth=0):
            """Recursively traverse document content for Sheets links"""
            if isinstance(content, dict):
                # Check for richLink elements (Google Sheets smart chips)
                if 'richLink' in content:
                    rich_link_props = content['richLink'].get('richLinkProperties', {})
                    url = rich_link_props.get('uri', '')
                    mime_type = rich_link_props.get('mimeType', '')
                    if url and ('docs.google.com/spreadsheets' in url or mime_type == 'application/vnd.google-apps.spreadsheet'):
                        sheets_links.append(url)
                        logger.debug("Found Google Sheets richLink at depth %s: %s", depth, url)

                if 'textRun' in content:
                    text_style = content['textRun'].get('textStyle', {})
                    link = text_style.get('link', {})
                    url = link.get('url', '')
                    if url and 'docs.google.com/spreadsheets' in url:
                        sheets_links.append(url)
                        logger.debug("Found Google Sheets textRun link at depth %s: %s", depth, url)
                
                # Recursively check all dict values
                for key, value in content.items():
                    traverse_content(value, depth + 1)
            
            elif isinstance(content, list):
                for item in content:
                    traverse_content(item, depth + 1)
        
        traverse_content(document)
        logger.debug("Total Google Sheets links found: %s", len(sheets_links))
        return list(set(sheets_links))
    
    def convert_to_markdown(self, document: Dict) -> Tuple[str, str]:
        """Convert Google Docs document to markdown
        
        Returns:
            Tuple of (markdown_content, title)
        """
        title = document.get('title', 'Untitled')
        content = document.get('body', {}).get('content', [])
        
        # Build HTML first (easier to convert to markdown)
        html_parts = []
        
        for element in content:
            if 'paragraph' in element:
                html_parts.append(self._paragraph_to_html(element['paragraph']))
            elif 'table' in element:
                html_parts.append(self._table_to_html(element['table']))
            elif 'sectionBreak' in element:
                html_parts.append('<hr>')
        
        html_content = '\n'.join(html_parts)
        
        # Convert to markdown
        markdown_content = md(html_content, heading_style='ATX', bullets='*-+')
        
        return markdown_content, title
    
    def _paragraph_to_html(self, paragraph: Dict) -> str:
        """Convert paragraph element to HTML"""
        elements = paragraph.get('elements', [])
        style = paragraph.get('paragraphStyle', {})
        
        # Determine paragraph type
        named_style = style.get('namedStyleType', 'NORMAL_TEXT')
        
        # Build text content
        text_parts = []
        for element in elements:
            if 'textRun' in element:
                text_run = element['textRun']
                content = text_run.get('content', '')
                text_style = text_run.get('textStyle', {})
                
                # Apply text formatting
                if text_style.get('bold'):
                    content = f'<strong>{content}</strong>'
                if text_style.get('italic'):
                    content = f'<em>{content}</em>'
                if text_style.get('underline'):
                    content = f'<u>{content}</u>'
                if text_style.get('strikethrough'):
                    content = f'<del>{content}</del>'
                
                # Handle links
                link = text_style.get('link', {})
                if link.get('url'):
                    content = f'<a href="{link["url"]}">{content}</a>'
                
                text_parts.append(content)
        
        text = ''.join(text_parts)
        
        # Wrap in appropriate tag
        if named_style.startswith('HEADING_'):
            level = named_style.split('_')[1]
            return f'<h{level}>{text}</h{level}>'
        elif named_style == 'TITLE':
            return f'<h1>{text}</h1>'
        elif named_style == 'SUBTITLE':
            return f'<h2>{text}</h2>'
        else:
            return f'<p>{text}</p>'
    
    def _table_to_html(self, table: Dict) -> str:
        """Convert table element to HTML"""
        rows = table.get('tableRows', [])
        
        html = ['<table>']
        
        for row in rows:
            html.append('<tr>')
            cells = row.get('tableCells', [])
            
            for cell in cells:
                cell_content = []
                for content_element in cell.get('content', []):
                    if 'paragraph' in content_element:
                        cell_content.append(self._paragraph_to_html(content_element['paragraph']))
                
                html.append(f'<td>{"".join(cell_content)}</td>')
            
            html.append('</tr>')
        
        html.append('</table>')
        return ''.join(html)
    
    async def export_as_html(self, doc_id: str) -> Optional[str]:
        """Export document as HTML using Drive API"""
        try:
            # Export as HTML
            export_result = self.drive_service.files().export(
                fileId=doc_id,
                mimeType='text/html'
            ).execute()
            
            return export_result.decode('utf-8')
        except HttpError as e:
            logger.error("Error exporting document %s as HTML: %s", doc_id, e)
            return None
    
    async def get_document_with_links(self, doc_id: str) -> Tuple[Optional[Dict], List[str], Optional[Dict]]:
        """Get document, extract links, and get metadata
        
        Returns:
            Tuple of (document, linked_doc_ids, metadata)
        """
        # Fetch document
        document = await self.get_document(doc_id)
        if not document:
            return None, [], None
        
        # Get metadata
        metadata = await self.get_document_metadata(doc_id)
        
        # Extract linked documents
        linked_urls = self.extract_links(document)
        linked_doc_ids = []
        for url in linked_urls:
            linked_id = self.extract_doc_id(url)
            if linked_id and linked_id != doc_id:  # Don't include self-references
                linked_doc_ids.append(linked_id)
        
        return document, linked_doc_ids, metadata

