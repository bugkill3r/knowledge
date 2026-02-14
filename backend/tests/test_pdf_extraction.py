"""
Tests for PDF extraction and image processing
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch, AsyncMock
from app.services.pdf_service import PDFService


class TestPDFService:
    """Test PDF download and image extraction"""
    
    @pytest.fixture
    def pdf_service(self):
        """Create PDF service instance"""
        return PDFService()
    
    @pytest.mark.asyncio
    async def test_download_as_pdf(self, pdf_service):
        """Test PDF download from Google Docs"""
        # Mock the requests.get call
        mock_response = Mock()
        mock_response.content = b"PDF_CONTENT_HERE"
        mock_response.raise_for_status = Mock()
        
        with patch('requests.get', return_value=mock_response):
            with tempfile.TemporaryDirectory() as tmpdir:
                output_path = os.path.join(tmpdir, "test.pdf")
                
                result = await pdf_service.download_as_pdf(
                    doc_id="test_doc_id",
                    access_token="test_token",
                    output_path=output_path
                )
                
                assert result == output_path
                assert os.path.exists(output_path)
                
                with open(output_path, 'rb') as f:
                    assert f.read() == b"PDF_CONTENT_HERE"
    
    def test_extract_sheet_id(self, pdf_service):
        """Test sheet ID extraction from various URL formats"""
        from app.services.google_sheets_service import GoogleSheetsService
        
        sheets_service = GoogleSheetsService("test_token")
        
        # Test standard URL
        url1 = "https://docs.google.com/spreadsheets/d/1ABC123/edit"
        assert sheets_service.extract_sheet_id(url1) == "1ABC123"
        
        # Test URL with gid
        url2 = "https://docs.google.com/spreadsheets/d/1XYZ789/edit#gid=0"
        assert sheets_service.extract_sheet_id(url2) == "1XYZ789"
        
        # Test invalid URL
        url3 = "https://example.com/not-a-sheet"
        assert sheets_service.extract_sheet_id(url3) is None
    
    def test_csv_to_markdown_table(self):
        """Test CSV to markdown conversion"""
        from app.services.google_sheets_service import GoogleSheetsService
        
        sheets_service = GoogleSheetsService("test_token")
        
        csv_data = """Name,Age,City
John,30,NYC
Jane,25,LA
Bob,35,SF"""
        
        markdown = sheets_service.csv_to_markdown_table(csv_data, max_rows=10)
        
        assert "| Name | Age | City |" in markdown
        assert "| John | 30 | NYC |" in markdown
        assert "| Jane | 25 | LA |" in markdown
        assert "| Bob | 35 | SF |" in markdown
        assert "| --- | --- | --- |" in markdown
    
    def test_csv_to_markdown_table_truncation(self):
        """Test CSV truncation for large tables"""
        from app.services.google_sheets_service import GoogleSheetsService
        
        sheets_service = GoogleSheetsService("test_token")
        
        # Create CSV with 60 rows
        rows = ["Col1,Col2,Col3"]
        for i in range(60):
            rows.append(f"val{i},val{i+1},val{i+2}")
        
        csv_data = "\n".join(rows)
        
        markdown = sheets_service.csv_to_markdown_table(csv_data, max_rows=50)
        
        # Should be truncated
        assert "Table truncated to 50 rows" in markdown
    
    def test_extract_images_from_markdown(self, pdf_service):
        """Test extracting image references from markdown"""
        markdown_content = """
# Test Document

Some text here.

![Diagram 1](images/doc/image-0-0.png)

More text.

![Chart](images/doc/image-0-1.png)

End.
"""
        
        images = pdf_service.extract_images_from_markdown(
            tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md').name
        )
        
        # Write content
        with open(images[0] if images else '/tmp/test.md', 'w') as f:
            f.write(markdown_content)
        
        # Re-extract
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
            f.write(markdown_content)
            f.flush()
            
            images = pdf_service.extract_images_from_markdown(f.name)
        
        assert len(images) == 2
        assert images[0]['alt'] == 'Diagram 1'
        assert images[0]['path'] == 'images/doc/image-0-0.png'
        assert images[1]['alt'] == 'Chart'
        assert images[1]['path'] == 'images/doc/image-0-1.png'


class TestIntegration:
    """Integration tests for the full workflow"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_pdf_extraction_workflow(self):
        """Test complete workflow: download PDF → extract images → save to vault"""
        # This would require actual Google API credentials
        # For now, we'll skip in CI
        pytest.skip("Requires Google API credentials")
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_sheets_workflow(self):
        """Test complete workflow: detect sheets → export CSV → AI analysis"""
        # This would require actual Google API credentials
        # For now, we'll skip in CI
        pytest.skip("Requires Google API credentials")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

