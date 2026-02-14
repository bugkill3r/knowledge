"""
Google Sheets Service - Extract and analyze data from Google Sheets
"""

import logging
import re
import csv
import io
from typing import List, Dict, Optional
from google.auth.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class AccessTokenCredentials(Credentials):
    """Minimal credentials class for access token only"""
    def __init__(self, token):
        self.token = token
        self.token_uri = None
        self.client_id = None
        self.client_secret = None
        self.scopes = None

    def apply(self, headers):
        headers['Authorization'] = f'Bearer {self.token}'

    def before_request(self, request, method, url, headers):
        self.apply(headers)

    def refresh(self, request):
        raise NotImplementedError("Access token refresh not supported by this class.")


class GoogleSheetsService:
    """Service for interacting with Google Sheets API"""
    
    def __init__(self, access_token: str):
        """Initialize with access token"""
        self.credentials = AccessTokenCredentials(access_token)
        self.sheets_service = build('sheets', 'v4', credentials=self.credentials)
    
    def extract_sheet_id(self, url: str) -> Optional[str]:
        """
        Extract spreadsheet ID from Google Sheets URL
        
        Args:
            url: Google Sheets URL
            
        Returns:
            Spreadsheet ID or None
        """
        match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
        return match.group(1) if match else None
    
    async def get_sheet_metadata(self, sheet_id: str) -> Optional[Dict]:
        """
        Get spreadsheet metadata
        
        Args:
            sheet_id: Spreadsheet ID
            
        Returns:
            Metadata dictionary or None
        """
        try:
            metadata = self.sheets_service.spreadsheets().get(
                spreadsheetId=sheet_id
            ).execute()
            
            return {
                'title': metadata.get('properties', {}).get('title', ''),
                'sheets': [
                    {
                        'title': sheet['properties']['title'],
                        'index': sheet['properties']['index'],
                        'sheet_id': sheet['properties']['sheetId']
                    }
                    for sheet in metadata.get('sheets', [])
                ]
            }
        except HttpError as e:
            logger.error(f"Error fetching sheet metadata {sheet_id}: {e}")
            return None
    
    async def get_sheet_as_csv(self, sheet_id: str, sheet_name: Optional[str] = None) -> Optional[str]:
        """
        Export sheet as CSV
        
        Args:
            sheet_id: Spreadsheet ID
            sheet_name: Optional sheet name (uses first sheet if not provided)
            
        Returns:
            CSV string or None
        """
        try:
            # Get metadata to find sheet name
            metadata = await self.get_sheet_metadata(sheet_id)
            if not metadata:
                return None
            
            # Use first sheet if not specified
            if not sheet_name and metadata.get('sheets'):
                sheet_name = metadata['sheets'][0]['title']
            
            # Get values
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range=sheet_name
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                logger.warning(f"No data found in sheet {sheet_id}")
                return None
            
            # Convert to CSV
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerows(values)
            
            csv_data = output.getvalue()
            logger.info(f"Exported sheet {sheet_id} as CSV ({len(csv_data)} bytes)")
            
            return csv_data
        
        except HttpError as e:
            logger.error(f"Error exporting sheet {sheet_id}: {e}")
            return None
    
    def csv_to_markdown_table(self, csv_data: str, max_rows: int = 50) -> str:
        """
        Convert CSV to markdown table
        
        Args:
            csv_data: CSV string
            max_rows: Maximum rows to include (to avoid huge tables)
            
        Returns:
            Markdown table string
        """
        try:
            reader = csv.reader(io.StringIO(csv_data))
            rows = list(reader)[:max_rows]  # Limit rows
            
            if not rows:
                return ""
            
            # Create markdown table
            markdown = []
            
            # Header
            if rows:
                header = rows[0]
                markdown.append("| " + " | ".join(str(cell) for cell in header) + " |")
                markdown.append("| " + " | ".join(["---"] * len(header)) + " |")
            
            # Data rows
            for row in rows[1:]:
                # Pad row to match header length
                padded_row = row + [''] * (len(header) - len(row))
                markdown.append("| " + " | ".join(str(cell) for cell in padded_row[:len(header)]) + " |")
            
            result = "\n".join(markdown)
            
            # Add truncation notice if needed
            if len(list(csv.reader(io.StringIO(csv_data)))) > max_rows:
                result += f"\n\n*Table truncated to {max_rows} rows*"
            
            return result
        
        except Exception as e:
            logger.error(f"Error converting CSV to markdown: {e}")
            return ""
    
    def analyze_csv_structure(self, csv_data: str) -> Dict:
        """
        Analyze CSV structure and content
        
        Args:
            csv_data: CSV string
            
        Returns:
            Analysis dictionary with stats
        """
        try:
            reader = csv.reader(io.StringIO(csv_data))
            rows = list(reader)
            
            if not rows:
                return {'rows': 0, 'columns': 0, 'has_header': False}
            
            num_rows = len(rows)
            num_cols = len(rows[0]) if rows else 0
            
            # Heuristic: check if first row looks like a header
            has_header = False
            if num_rows > 1:
                first_row = rows[0]
                second_row = rows[1]
                
                # Check if first row has mostly text and second row has numbers
                first_row_text = sum(1 for cell in first_row if not cell.replace('.', '').replace('-', '').isdigit())
                second_row_nums = sum(1 for cell in second_row if cell.replace('.', '').replace('-', '').isdigit())
                
                if first_row_text > num_cols * 0.5:
                    has_header = True
            
            return {
                'rows': num_rows,
                'columns': num_cols,
                'has_header': has_header,
                'header': rows[0] if has_header else None,
                'sample_data': rows[1:3] if num_rows > 1 else []
            }
        
        except Exception as e:
            logger.error(f"Error analyzing CSV: {e}")
            return {'rows': 0, 'columns': 0, 'has_header': False}

