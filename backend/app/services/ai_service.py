"""
AI Service - Document summarization, entity extraction, and metadata generation
"""

import logging
from typing import List, Dict, Optional
from openai import AzureOpenAI
from sqlalchemy.orm import Session

from app.config import settings
from app.models.document import Document

logger = logging.getLogger(__name__)


class AIService:
    """Service for AI-powered document processing"""
    
    def __init__(self):
        """Initialize AI service with Azure OpenAI"""
        if settings.AI_PROVIDER == "azure":
            self.client = AzureOpenAI(
                api_key=settings.AZURE_OPENAI_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
            )
            self.model = settings.AZURE_OPENAI_DEPLOYMENT
            logger.info(f"Initialized Azure OpenAI with deployment: {self.model}")
        else:
            logger.warning("AI provider not configured, AI features will be limited")
            self.client = None
            self.model = None
    
    def generate_summary(self, text: str, max_words: int = 100) -> Optional[str]:
        """
        Generate a concise summary of the document
        
        Args:
            text: Document text to summarize
            max_words: Maximum words in summary
            
        Returns:
            Summary text or None if failed
        """
        if not self.client or not text.strip():
            return None
        
        try:
            # Truncate text if too long (keep first 4000 chars for context)
            truncated_text = text[:4000] if len(text) > 4000 else text
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a technical documentation assistant. Provide concise, accurate summaries of technical documents."
                    },
                    {
                        "role": "user",
                        "content": f"Summarize the following document in {max_words} words or less. Focus on key points, technical details, and main outcomes:\n\n{truncated_text}"
                    }
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            summary = response.choices[0].message.content.strip()
            logger.info(f"Generated summary: {len(summary)} characters")
            return summary
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return None
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract entities from document (people, systems, products)
        
        Args:
            text: Document text to analyze
            
        Returns:
            Dictionary with entity types and lists
        """
        if not self.client or not text.strip():
            return {"people": [], "systems": [], "products": [], "teams": []}
        
        try:
            # Truncate text if too long
            truncated_text = text[:4000] if len(text) > 4000 else text
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an entity extraction assistant for technical documents. 
Extract entities and return them in JSON format with these categories:
- people: Names of individuals mentioned
- systems: Technical systems, services, APIs mentioned
- products: Product names mentioned
- teams: Team names mentioned

Return ONLY valid JSON, no other text."""
                    },
                    {
                        "role": "user",
                        "content": f"Extract entities from this document:\n\n{truncated_text}"
                    }
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            import json
            entities_text = response.choices[0].message.content.strip()
            
            # Try to parse JSON response
            try:
                # Remove markdown code blocks if present
                if entities_text.startswith("```"):
                    entities_text = entities_text.split("```")[1]
                    if entities_text.startswith("json"):
                        entities_text = entities_text[4:]
                
                entities = json.loads(entities_text)
                logger.info(f"Extracted entities: {sum(len(v) for v in entities.values())} total")
                return entities
                
            except json.JSONDecodeError:
                logger.warning("Failed to parse entities JSON, using defaults")
                return {"people": [], "systems": [], "products": [], "teams": []}
            
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return {"people": [], "systems": [], "products": [], "teams": []}
    
    def suggest_tags(self, text: str, title: str = "") -> List[str]:
        """
        Suggest relevant tags for the document
        
        Args:
            text: Document text
            title: Document title
            
        Returns:
            List of suggested tags
        """
        if not self.client or not text.strip():
            return []
        
        try:
            # Truncate text if too long
            truncated_text = text[:3000] if len(text) > 3000 else text
            
            context = f"Title: {title}\n\n{truncated_text}" if title else truncated_text
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are a document tagging assistant. Suggest 3-7 tags as category/subcategory. Domain: {settings.DOMAIN}. Return ONLY a comma-separated list of tags."""
                    },
                    {
                        "role": "user",
                        "content": f"Suggest tags for this document:\n\n{context}"
                    }
                ],
                temperature=0.2,
                max_tokens=100
            )
            
            tags_text = response.choices[0].message.content.strip()
            tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]
            
            logger.info(f"Suggested {len(tags)} tags")
            return tags[:7]  # Limit to 7 tags
            
        except Exception as e:
            logger.error(f"Error suggesting tags: {e}")
            return []
    
    def detect_document_type(self, text: str, title: str = "") -> str:
        """
        Detect the type of document (PRD, tech-spec, meeting, etc.)
        
        Args:
            text: Document text
            title: Document title
            
        Returns:
            Document type string
        """
        if not text.strip():
            return "doc"
        
        # Simple heuristic-based detection first
        title_lower = title.lower() if title else ""
        text_lower = text[:1000].lower()
        
        if "tech spec" in title_lower or "technical specification" in text_lower:
            return "tech-spec"
        elif "prd" in title_lower or "product requirements" in text_lower:
            return "prd"
        elif "meeting" in title_lower or "notes:" in text_lower or "attendees:" in text_lower:
            return "meeting"
        elif "knowledge transfer" in title_lower or "kt" in title_lower:
            return "kt"
        elif "runbook" in title_lower or "playbook" in title_lower:
            return "runbook"
        else:
            return "doc"
    
    def process_document(
        self,
        db: Session,
        document: Document,
        generate_summary: bool = True,
        extract_entities: bool = True,
        suggest_tags: bool = True
    ) -> Dict:
        """
        Process a document with AI to generate metadata
        
        Args:
            db: Database session
            document: Document to process
            generate_summary: Whether to generate summary
            extract_entities: Whether to extract entities
            suggest_tags: Whether to suggest tags
            
        Returns:
            Dictionary with generated metadata
        """
        content = document.content_md or ""
        if not content.strip():
            logger.warning(f"Document {document.id} has no content to process")
            return {}
        
        metadata = document.metadata_json or {}
        
        # Generate summary
        if generate_summary and self.client:
            logger.info(f"Generating summary for document {document.id}...")
            summary = self.generate_summary(content)
            if summary:
                metadata['summary'] = summary
        
        # Extract entities
        if extract_entities and self.client:
            logger.info(f"Extracting entities for document {document.id}...")
            entities = self.extract_entities(content)
            if entities:
                metadata['entities'] = entities
        
        # Suggest tags
        if suggest_tags and self.client:
            logger.info(f"Suggesting tags for document {document.id}...")
            tags = self.suggest_tags(content, document.title)
            if tags:
                # Merge with existing tags if any
                existing_tags = metadata.get('tags', [])
                all_tags = list(set(existing_tags + tags))
                metadata['tags'] = all_tags
        
        # Detect document type
        doc_type = self.detect_document_type(content, document.title)
        metadata['type'] = doc_type
        
        # Mark as AI processed
        metadata['ai_processed'] = True
        
        # Update document
        document.metadata_json = metadata
        db.commit()
        
        logger.info(f"AI processing complete for document {document.id}")
        return metadata
    
    def batch_process_documents(
        self,
        db: Session,
        document_ids: Optional[List[str]] = None,
        force_reprocess: bool = False
    ) -> Dict[str, int]:
        """
        Process multiple documents in batch
        
        Args:
            db: Database session
            document_ids: Optional list of document IDs to process (None = all)
            force_reprocess: If True, reprocess even if already processed
            
        Returns:
            Dictionary with processing stats
        """
        # Get documents to process
        query = db.query(Document)
        if document_ids:
            query = query.filter(Document.id.in_(document_ids))
        
        documents = query.all()
        
        stats = {
            'total': len(documents),
            'processed': 0,
            'skipped': 0,
            'failed': 0
        }
        
        logger.info(f"Processing {stats['total']} documents with AI")
        
        for doc in documents:
            try:
                # Check if already processed
                if not force_reprocess:
                    metadata = doc.metadata_json or {}
                    if metadata.get('ai_processed'):
                        logger.info(f"Document {doc.id} already AI processed, skipping")
                        stats['skipped'] += 1
                        continue
                
                # Process document
                self.process_document(db, doc)
                stats['processed'] += 1
                
            except Exception as e:
                logger.error(f"Failed to process document {doc.id}: {e}")
                stats['failed'] += 1
        
        logger.info(f"Batch AI processing complete: {stats}")
        return stats
    
    async def analyze_spreadsheet_data(self, csv_data: str, sheet_title: str) -> Optional[Dict]:
        """
        Use AI to analyze spreadsheet data and extract insights
        
        Args:
            csv_data: CSV data string
            sheet_title: Title of the spreadsheet
            
        Returns:
            Dictionary with analysis or None
        """
        if not self.client or not csv_data.strip():
            return None
        
        try:
            # Truncate CSV if too large (keep first 50 rows)
            import csv
            import io
            reader = csv.reader(io.StringIO(csv_data))
            rows = list(reader)[:50]
            truncated_csv = '\n'.join(','.join(row) for row in rows)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a data analysis assistant. 
Analyze the spreadsheet data and provide:
1. Brief summary of what the data represents (1-2 sentences)
2. Key metrics or insights (bullet points)
3. Notable trends or patterns
4. Important values or outliers

Keep the analysis concise and focused on what makes this data searchable."""
                    },
                    {
                        "role": "user",
                        "content": f"Analyze this spreadsheet titled '{sheet_title}':\n\n{truncated_csv}"
                    }
                ],
                temperature=0.3,
                max_tokens=400
            )
            
            analysis = response.choices[0].message.content.strip()
            
            logger.info(f"Generated spreadsheet analysis: {len(analysis)} characters")
            return {
                'summary': analysis,
                'data_type': 'spreadsheet',
                'sheet_title': sheet_title,
                'row_count': len(rows)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing spreadsheet: {e}")
            return None


# Global instance
_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    """Get or create the global AI service instance"""
    global _ai_service
    
    if _ai_service is None:
        _ai_service = AIService()
    
    return _ai_service


    def analyze_spreadsheet_with_context(
        self,
        csv_data: str,
        parent_doc_title: str,
        parent_doc_summary: str = "",
        sheet_title: str = "",
        max_rows_for_analysis: int = 20
    ) -> Dict:
        """
        Analyze spreadsheet data with context from the parent document
        
        Args:
            csv_data: Raw CSV data
            parent_doc_title: Title of the parent document
            parent_doc_summary: Summary or content snippet from parent doc
            sheet_title: Title of the spreadsheet
            max_rows_for_analysis: Maximum rows to include in AI analysis
            
        Returns:
            Dictionary with analysis including summary, insights, patterns
        """
        if not self.client or not csv_data.strip():
            # Fallback to basic analysis
            lines = csv_data.strip().split('\n')
            return {
                "summary": f"Spreadsheet with approximately {len(lines)-1} rows of data",
                "ai_enhanced": False
            }
        
        try:
            import csv
            import io
            
            # Parse CSV
            reader = csv.reader(io.StringIO(csv_data))
            rows = list(reader)
            
            if not rows:
                return {"summary": "Empty spreadsheet", "ai_enhanced": False}
            
            headers = rows[0] if rows else []
            total_rows = len(rows) - 1  # Exclude header
            
            # Sample data for AI (first N rows)
            sample_rows = rows[:min(max_rows_for_analysis + 1, len(rows))]
            sample_csv = '\n'.join([','.join(row) for row in sample_rows])
            
            # Analyze data structure and content
            data_analysis = self._analyze_spreadsheet_data_structure(rows, headers)
            
            # Create comprehensive context-aware prompt
            prompt = f"""Perform a deep analysis of this spreadsheet data in the context of its parent document.

**PARENT DOCUMENT CONTEXT:**
- Document: {parent_doc_title}
{f'- Summary: {parent_doc_summary[:400]}' if parent_doc_summary else ''}

**SPREADSHEET DETAILS:**
- Title: {sheet_title or 'Untitled'}
- Dimensions: {total_rows} rows × {len(headers)} columns
- Headers: {', '.join(headers)}

**DATA STRUCTURE ANALYSIS:**
- Column Types: {data_analysis['column_types']}
- Data Patterns: {data_analysis['patterns']}
- Unique Values: {data_analysis['unique_counts']}
- Empty Cells: {data_analysis['empty_cells']} cells

**ACTUAL DATA SAMPLE (first {min(max_rows_for_analysis, total_rows)} rows):**
```csv
{sample_csv}
```

**ANALYSIS REQUIREMENTS:**

Provide a comprehensive analysis that examines the ACTUAL DATA CONTENT:

1. **Data Type & Purpose**: What kind of data is this? (e.g., API endpoints, metrics, user data, configuration, test cases, pricing, features)

2. **Content Analysis**: 
   - What specific values, patterns, or categories are present?
   - Are there any notable data points, outliers, or interesting entries?
   - What ranges, frequencies, or distributions do you observe?

3. **Column Semantics**:
   - What does each column represent?
   - How do the columns relate to each other?
   - Are there any calculated or derived columns?

4. **Data Quality**:
   - Are there missing values, inconsistencies, or anomalies?
   - Is the data complete and well-structured?
   - Any data validation or quality issues?

5. **Business Context**:
   - How does this data support the parent document's purpose?
   - What decisions or insights does this data enable?
   - What are the most important or frequently referenced entries?

6. **Key Observations**:
   - List 3-5 specific, data-driven insights
   - Mention actual values, categories, or examples from the data
   - Highlight trends, patterns, or significant findings

Return ONLY valid JSON with these keys:
- "summary": Complete analysis paragraph (6-8 sentences) discussing ACTUAL data content
- "data_type": Brief classification
- "column_descriptions": Object with key columns and what they represent
- "key_insights": Array of 4-5 specific insights with actual data references
- "data_quality": Brief assessment of completeness and quality
- "notable_entries": Array of 2-3 interesting/important rows or values from the actual data
- "relationship_to_doc": How this data supports the parent document"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a data analysis assistant. Provide insightful analysis of spreadsheet data in technical documentation context. Always respond with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.4,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            import json
            analysis = json.loads(response.choices[0].message.content)
            analysis['ai_enhanced'] = True
            analysis['total_rows'] = total_rows
            analysis['total_columns'] = len(headers)
            analysis['headers'] = headers
            analysis['data_structure'] = data_analysis
            
            logger.info(f"Generated deep AI analysis for spreadsheet '{sheet_title}' with {total_rows} rows")
            return analysis
            
        except Exception as e:
            logger.error(f"Error in AI spreadsheet analysis: {e}")
            # Fallback to basic analysis
            lines = csv_data.strip().split('\n')
            return {
                "summary": f"Spreadsheet with approximately {len(lines)-1} rows of data. AI analysis unavailable.",
                "ai_enhanced": False,
                "error": str(e)
            }

    def _analyze_spreadsheet_data_structure(self, rows: list, headers: list) -> Dict:
        """
        Analyze the structure and content of spreadsheet data
        
        Args:
            rows: List of rows from CSV (including header)
            headers: List of column headers
            
        Returns:
            Dictionary with structural analysis
        """
        if not rows or len(rows) < 2:
            return {
                'column_types': {},
                'patterns': 'Insufficient data',
                'unique_counts': {},
                'empty_cells': 0
            }
        
        data_rows = rows[1:]  # Exclude header
        num_cols = len(headers)
        
        column_types = {}
        unique_counts = {}
        empty_cells = 0
        
        for col_idx, header in enumerate(headers):
            col_values = [row[col_idx] if col_idx < len(row) else '' for row in data_rows]
            
            # Count empty cells
            empty_in_col = sum(1 for v in col_values if not v or not v.strip())
            empty_cells += empty_in_col
            
            # Determine column type
            non_empty_values = [v for v in col_values if v and v.strip()]
            if not non_empty_values:
                column_types[header] = 'empty'
                unique_counts[header] = 0
                continue
            
            # Check if numeric
            numeric_count = sum(1 for v in non_empty_values if self._is_numeric(v))
            if numeric_count > len(non_empty_values) * 0.7:  # 70% threshold
                column_types[header] = 'numeric'
            # Check if boolean
            elif all(v.lower() in ['true', 'false', 'yes', 'no', 'y', 'n', '0', '1'] for v in non_empty_values):
                column_types[header] = 'boolean'
            # Check if URL
            elif sum(1 for v in non_empty_values if v.startswith('http')) > len(non_empty_values) * 0.5:
                column_types[header] = 'url'
            # Check if date
            elif sum(1 for v in non_empty_values if self._is_date_like(v)) > len(non_empty_values) * 0.5:
                column_types[header] = 'date'
            else:
                column_types[header] = 'text'
            
            # Count unique values
            unique_counts[header] = len(set(non_empty_values))
        
        # Identify patterns
        patterns = []
        if len(data_rows) > 10:
            # Check for sorted data
            first_col_values = [row[0] if len(row) > 0 else '' for row in data_rows]
            if self._is_sorted(first_col_values):
                patterns.append('sorted_by_first_column')
            
            # Check for grouping
            if self._has_grouping(data_rows):
                patterns.append('grouped_data')
        
        # Calculate data density
        total_cells = len(data_rows) * num_cols
        density = ((total_cells - empty_cells) / total_cells * 100) if total_cells > 0 else 0
        
        return {
            'column_types': column_types,
            'patterns': ', '.join(patterns) if patterns else 'flat_table',
            'unique_counts': unique_counts,
            'empty_cells': empty_cells,
            'data_density': f'{density:.1f}%',
            'row_count': len(data_rows)
        }
    
    def _is_numeric(self, value: str) -> bool:
        """Check if a string represents a numeric value"""
        try:
            value = value.strip().replace(',', '').replace('$', '').replace('%', '')
            float(value)
            return True
        except (ValueError, AttributeError):
            return False
    
    def _is_date_like(self, value: str) -> bool:
        """Check if a string looks like a date"""
        date_indicators = ['-', '/', '\\', 'jan', 'feb', 'mar', 'apr', 'may', 'jun', 
                          'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
        value_lower = value.lower()
        return any(ind in value_lower for ind in date_indicators)
    
    def _is_sorted(self, values: list) -> bool:
        """Check if values are sorted"""
        if not values or len(values) < 3:
            return False
        non_empty = [v for v in values if v and v.strip()]
        if len(non_empty) < 3:
            return False
        return non_empty == sorted(non_empty) or non_empty == sorted(non_empty, reverse=True)
    
    def _has_grouping(self, rows: list) -> bool:
        """Check if data appears to be grouped"""
        if not rows or len(rows) < 5:
            return False
        # Simple heuristic: check if first column has consecutive duplicates
        first_col = [row[0] if len(row) > 0 else '' for row in rows]
        consecutive_duplicates = sum(1 for i in range(1, len(first_col)) if first_col[i] == first_col[i-1])
        return consecutive_duplicates > len(first_col) * 0.2  # 20% threshold
