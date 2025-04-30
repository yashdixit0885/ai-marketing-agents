# agents/export_agent.py

import logging
from datetime import datetime
from .base_agent import BaseAgent
from services.api_clients.google_drive_client import GoogleDriveClient
from services.api_clients.google_docs_client import GoogleDocsClient
from models.content_models import Article, ArticleExport, SocialPost, Visual
from models import db_session
from utils.helpers import slugify
import os
import json
from typing import List, Dict, Any, Optional, Union

logger = logging.getLogger(__name__)

class ExportAgent(BaseAgent):
    """Agent responsible for exporting content to Google Docs for review."""
    
    def __init__(self):
        super().__init__("Export Agent", "Exports content to Google Docs for review")
        self.drive_client = GoogleDriveClient()
        self.docs_client = GoogleDocsClient()
    
    async def run(self, article_id, reviewer_email=None):
        """Export an article to Google Docs."""
        self.log_status(f"Starting export for article: {article_id}")
        
        # Retrieve the article
        article = db_session.get(Article, article_id)
        if not article:
            raise ValueError(f"Article with ID {article_id} not found")
        
        # Check if we need to create a root folder
        root_folder_id, root_folder_url = await self._get_or_create_root_folder()
        
        # Create or find a folder for the article
        safe_title = slugify(article.title)
        folder_name = f"Article-{article.id}-{safe_title}"
        folder_id, folder_url = await self.drive_client.find_folder_by_name(folder_name, root_folder_id)
        
        if not folder_id:
            # Folder doesn't exist, create it
            folder_id, folder_url = await self.drive_client.create_folder(folder_name, root_folder_id)
            self.log_status(f"Created new folder: {folder_name}")
        else:
            self.log_status(f"Found existing folder: {folder_name}")
        
        # Create or find main article doc
        doc_name = f"{article.title} - Content"
        doc_id, doc_url = await self.drive_client.find_doc_by_name(doc_name, folder_id)
        
        if not doc_id:
            # Document doesn't exist, create it
            doc_id, doc_url = await self.drive_client.create_doc(doc_name, folder_id)
            self.log_status(f"Created new document: {doc_name}")
        else:
            self.log_status(f"Found existing document: {doc_name}")
        
        # First upload all images to Google Drive
        uploaded_visuals = []
        visuals = db_session.query(Visual).filter(Visual.article_id == article.id).all()
        
        if visuals:
            self.log_status(f"Processing {len(visuals)} visuals for article")
            for visual in visuals:
                # Check if file_path is a Google Drive ID or a local file path
                if visual.file_path and not visual.file_path.startswith('http'):
                    # If this is a local file that exists, upload it
                    if os.path.exists(visual.file_path):
                        visual_name = f"{visual.type}_{visual.id}"
                        self.log_status(f"Uploading visual from local path: {visual.file_path}")
                        
                        # Upload the file to Google Drive
                        try:
                            with open(visual.file_path, 'rb') as file:
                                file_data = file.read()
                                file_id = await self.drive_client.upload_image(file_data, visual_name)
                                
                                if file_id:
                                    # Update the visual with the Google Drive file ID
                                    visual.file_path = file_id
                                    # Also update file_id to maintain compatibility with the rest of the codebase
                                    visual.file_id = file_id
                                    db_session.commit()
                                    uploaded_visuals.append(visual)
                                    self.log_status(f"Successfully uploaded visual to Drive with ID: {file_id}")
                                else:
                                    self.log_status(f"Failed to upload visual: {visual_name}")
                        except Exception as e:
                            self.log_status(f"Error uploading visual: {str(e)}")
                    else:
                        self.log_status(f"Visual file not found at path: {visual.file_path}")
                else:
                    # This is already a Drive ID or URL, make sure file_id is also set
                    if not visual.file_id:
                        visual.file_id = visual.file_path
                        db_session.commit()
                    uploaded_visuals.append(visual)
                    self.log_status(f"Visual already has Drive ID: {visual.file_path}")
        
        # Now write the article content to the doc
        self.docs_client.write_content(doc_id, article.content)
        
        # After content is written, add the visuals to the document
        if uploaded_visuals:
            # Get the document to find appropriate insertion points
            document = await self.docs_client.get_document(doc_id)
            
            # Insert header image first if present
            header_images = [v for v in uploaded_visuals if v.type == 'header_image']
            if header_images:
                for header_image in header_images:
                    try:
                        self.log_status(f"Inserting header image at beginning of document")
                        # Use file_id instead of file_path for consistency
                        image_id = header_image.file_id if header_image.file_id else header_image.file_path
                        await self.docs_client.insert_image(
                            document_id=doc_id,
                            image_id=image_id,
                            position=1  # Top of document, after title
                        )
                    except Exception as e:
                        self.log_status(f"Failed to insert header image: {str(e)}")
            
            # Calculate positions for other visuals
            other_visuals = [v for v in uploaded_visuals if v.type != 'header_image']
            if other_visuals and document:
                content = document.get('body', {}).get('content', [])
                doc_length = content[-1].get('endIndex', 1) if content else 1
                
                # Distribute visuals throughout document
                positions = self._calculate_visual_positions(doc_length, len(other_visuals))
                
                for i, visual in enumerate(other_visuals):
                    if i < len(positions):
                        try:
                            self.log_status(f"Inserting {visual.type} at position {positions[i]}")
                            # Use file_id instead of file_path for consistency
                            image_id = visual.file_id if visual.file_id else visual.file_path
                            await self.docs_client.insert_image(
                                document_id=doc_id,
                                image_id=image_id,
                                position=positions[i]
                            )
                        except Exception as e:
                            self.log_status(f"Failed to insert visual: {str(e)}")
        
        # Create or find a doc for social posts
        social_posts = db_session.query(SocialPost).filter(SocialPost.article_id == article.id).all()
        if social_posts:
            social_doc_name = f"{article.title} - Social Posts"
            social_doc_id, social_doc_url = await self.drive_client.find_doc_by_name(social_doc_name, folder_id)
            
            if not social_doc_id:
                # Document doesn't exist, create it
                social_doc_id, social_doc_url = await self.drive_client.create_doc(social_doc_name, folder_id)
                self.log_status(f"Created new social posts document: {social_doc_name}")
            else:
                self.log_status(f"Found existing social posts document: {social_doc_name}")
            
            # Prepare social post content with professional formatting
            social_content = f"# Social Media Posts for '{article.title}'\n\n"
            for post in social_posts:
                social_content += f"## {post.platform.upper()}\n\n"
                
                # Format content differently based on platform
                if post.platform == "linkedin":
                    # LinkedIn posts typically have formatting like bold, bullet points
                    formatted_content = post.content.replace('*', '**')  # Ensure proper bold formatting
                    social_content += formatted_content + "\n\n"
                elif post.platform == "twitter":
                    social_content += post.content + "\n\n"
                
                social_content += f"**Status:** {post.status}\n\n"
                if post.scheduled_time:
                    social_content += f"**Scheduled for:** {post.scheduled_time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                social_content += "---\n\n"
            
            # Write social content to the doc (replacing existing content)
            self.docs_client.write_content(social_doc_id, social_content)
        
        # Check if an export record already exists
        existing_export = db_session.query(ArticleExport).filter(
            ArticleExport.article_id == article.id,
            ArticleExport.doc_id == doc_id
        ).first()
        
        if existing_export:
            # Update existing export record
            existing_export.doc_url = doc_url
            existing_export.folder_id = folder_id
            existing_export.export_date = datetime.now()
            existing_export.status = "pending_review"
            db_session.commit()
            export = existing_export
            self.log_status(f"Updated existing export record: {export.id}")
        else:
            # Create new export record
            export = await self.process({
                "article": article,
                "doc_id": doc_id,
                "doc_url": doc_url,
                "folder_id": folder_id,
                "folder_url": folder_url
            })
            self.log_status(f"Created new export record: {export.id}")
        
        # Share with reviewer if email provided
        if reviewer_email:
            await self.drive_client.share_file(folder_id, reviewer_email)
            self.log_status(f"Shared export with reviewer: {reviewer_email}")
        
        # Update article status
        article.status = "review"
        db_session.commit()
        
        self.log_status(f"Completed export for article: {article_id}")
        return export
    
    async def _get_or_create_root_folder(self):
        """Get or create the root folder for all content."""
        # In a real implementation, you might store this ID in a database or settings
        # For simplicity, we'll create a new folder each time
        return await self.drive_client.create_folder("AI Content Automation")
    
    async def process(self, data):
        """Process and store the export record."""
        article = data["article"]
        doc_id = data["doc_id"]
        doc_url = data["doc_url"]
        folder_id = data["folder_id"]
        folder_url = data["folder_url"]
        
        # Create export record
        export = ArticleExport(
            article_id=article.id,
            doc_id=doc_id,
            doc_url=doc_url,
            folder_id=folder_id,
            export_date=datetime.now(),
            status="pending_review"
        )
        
        db_session.add(export)
        db_session.commit()
        
        return export

    async def _create_document(self, article: Article, visuals: List[Visual] = None) -> str:
        """
        Create a Google Doc with content from the article and visuals.
        
        Args:
            article: The article object containing content
            visuals: List of visual objects to include in the document
            
        Returns:
            The document ID
        """
        try:
            if not article:
                logger.error("No article provided for document creation")
                return None
                
            title = article.title or "Untitled Document"
            logger.info(f"Creating document with title: {title}")
            
            # Create document with title
            google_client = GoogleDocsClient()
            document_id = await google_client.create_document(title)
            
            if not document_id:
                logger.error("Failed to create document")
                return None
                
            # Write article content to document
            content_sections = self._prepare_content_sections(article)
            await google_client.write_content(document_id, content_sections)
            
            # Add visuals to the document
            if visuals:
                await self._insert_visuals(google_client, document_id, article, visuals)
            
            logger.info(f"Document created successfully with ID: {document_id}")
            return document_id
            
        except Exception as e:
            logger.error(f"Error creating document: {str(e)}")
            return None
            
    def _prepare_content_sections(self, article: Article) -> List[Dict[str, Any]]:
        """
        Prepare content sections for document creation.
        
        Args:
            article: The article object
            
        Returns:
            List of content sections with text and type
        """
        sections = []
        
        # Add title
        if article.title:
            sections.append({
                "text": article.title,
                "type": "title"
            })
            
        # Add subtitle/description if available
        if article.description:
            sections.append({
                "text": article.description,
                "type": "subtitle"
            })
            
        # Add content sections
        if article.content:
            try:
                # Try to parse content if it's stored as JSON
                content_sections = json.loads(article.content) if isinstance(article.content, str) else article.content
                
                for section in content_sections:
                    if isinstance(section, dict):
                        section_type = section.get("type", "paragraph")
                        section_text = section.get("text", "")
                        
                        if section_text:
                            sections.append({
                                "text": section_text,
                                "type": section_type
                            })
            except (json.JSONDecodeError, TypeError):
                # If content is plain text, add as paragraphs
                paragraphs = article.content.split("\n\n") if isinstance(article.content, str) else [article.content]
                for paragraph in paragraphs:
                    if paragraph.strip():
                        sections.append({
                            "text": paragraph.strip(),
                            "type": "paragraph"
                        })
                        
        return sections
        
    async def _insert_visuals(self, google_client: GoogleDocsClient, document_id: str, article: Article, visuals: List[Visual]) -> None:
        """
        Insert visuals into the document at appropriate positions.
        
        Args:
            google_client: The GoogleDocsClient instance
            document_id: The document ID
            article: The article object
            visuals: List of visuals to insert
        """
        try:
            # Get the document to determine appropriate positions
            document = await google_client.get_document(document_id)
            content = document.get('body', {}).get('content', [])
            
            # Find potential insertion points based on content
            insertion_points = self._determine_insertion_points(content)
            
            # Organize visuals by type
            visual_types = {
                "header_image": [],
                "chart": [],
                "infographic": [],
                "quote_card": []
            }
            
            for visual in visuals:
                if visual.file_id and visual.visual_type in visual_types:
                    visual_types[visual.visual_type].append(visual)
            
            # Insert header image at the top (after title)
            if visual_types["header_image"]:
                header_image = visual_types["header_image"][0]
                position = insertion_points.get("header", None)
                caption = f"Featured image: {header_image.description}" if header_image.description else "Featured image"
                await google_client.insert_image_with_caption(document_id, header_image.file_id, caption, position)
            
            # Insert charts after relevant paragraphs
            charts_inserted = 0
            for chart in visual_types["chart"]:
                if charts_inserted < len(insertion_points.get("body", [])):
                    position = insertion_points["body"][charts_inserted]
                    caption = chart.description or "Data visualization"
                    await google_client.insert_image_with_caption(document_id, chart.file_id, caption, position)
                    charts_inserted += 1
            
            # Insert infographics in remaining body positions
            infographics_inserted = 0
            remaining_positions = insertion_points.get("body", [])[charts_inserted:]
            for infographic in visual_types["infographic"]:
                if infographics_inserted < len(remaining_positions):
                    position = remaining_positions[infographics_inserted]
                    caption = infographic.description or "Infographic"
                    await google_client.insert_image_with_caption(document_id, infographic.file_id, caption, position)
                    infographics_inserted += 1
            
            # Insert quote cards near the end
            if visual_types["quote_card"] and "conclusion" in insertion_points:
                quote_card = visual_types["quote_card"][0]
                position = insertion_points["conclusion"]
                caption = quote_card.description or "Quote"
                await google_client.insert_image_with_caption(document_id, quote_card.file_id, caption, position)
                
            logger.info(f"Successfully inserted {len(visuals)} visuals into document {document_id}")
            
        except Exception as e:
            logger.error(f"Error inserting visuals into document: {str(e)}")
    
    def _determine_insertion_points(self, content: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Determine appropriate insertion points for visuals in the document.
        
        Args:
            content: Document content
            
        Returns:
            Dictionary of insertion points by section type
        """
        insertion_points = {
            "header": None,
            "body": [],
            "conclusion": None
        }
        
        # Find title/header section
        title_index = None
        for i, item in enumerate(content):
            if item.get("paragraph", {}).get("paragraphStyle", {}).get("namedStyleType") == "TITLE":
                title_index = i
                break
        
        if title_index is not None:
            # Header image goes after title and subtitle (if present)
            subtitle_index = title_index + 1 if title_index + 1 < len(content) else None
            if subtitle_index and content[subtitle_index].get("paragraph", {}).get("paragraphStyle", {}).get("namedStyleType") == "SUBTITLE":
                insertion_points["header"] = content[subtitle_index].get("endIndex", 1)
            else:
                insertion_points["header"] = content[title_index].get("endIndex", 1)
        
        # Find body paragraphs for charts and infographics
        # Look for paragraph breaks as good insertion points
        paragraph_count = 0
        for i, item in enumerate(content):
            if "paragraph" in item and item.get("paragraph", {}).get("elements"):
                paragraph_count += 1
                
                # Every 3-4 paragraphs is a good spot for visuals
                if paragraph_count % 3 == 0 and i > title_index + 1 if title_index is not None else i > 0:
                    insertion_points["body"].append(item.get("endIndex", 1))
        
        # If no body insertion points, add one at end
        if not insertion_points["body"] and content:
            insertion_points["body"].append(content[-1].get("endIndex", 1))
        
        # Conclusion is near the end of the document
        if len(content) > 2:
            # Use the second to last paragraph as conclusion point
            insertion_points["conclusion"] = content[-2].get("endIndex", 1)
        
        return insertion_points

    def _calculate_visual_positions(self, doc_length: int, num_visuals: int) -> list:
        """
        Calculate positions in the document to insert visuals for even distribution.
        
        Args:
            doc_length: Total length of the document
            num_visuals: Number of visuals to insert
            
        Returns:
            List of position indices for inserting visuals
        """
        positions = []
        
        # Skip the first 10% of content (usually intro)
        start_pos = int(doc_length * 0.1)
        
        # Use the middle 80% of the document
        usable_length = int(doc_length * 0.8)
        
        if num_visuals <= 0:
            return positions
            
        # For a single visual, place it at the 1/3 point
        if num_visuals == 1:
            positions.append(start_pos + int(usable_length * 0.33))
            return positions
            
        # For multiple visuals, distribute evenly
        segment = usable_length / (num_visuals + 1)
        for i in range(1, num_visuals + 1):
            positions.append(start_pos + int(segment * i))
            
        self.log_status(f"Calculated {num_visuals} visual positions at: {positions}")
        return positions

    async def create_professional_document(self, article: Article) -> str:
        """
        Create a professionally formatted Google Document from an article.
        
        Args:
            article: The Article object containing content and metadata
            
        Returns:
            Document ID if successful, empty string otherwise
        """
        try:
            logger.info(f"Creating professional document for article: {article.title}")
            
            # Create a new Google Doc with the article title
            doc = await self.docs_client.create_document(article.title)
            if not doc:
                logger.error("Failed to create Google Doc")
                return ""
                
            document_id = doc.get('documentId', '')
            
            # Determine content based on article structure
            content = self._prepare_content(article)
            
            # Write content to the document
            success = await self.docs_client.write_content(
                document_id=document_id,
                content=content
            )
            
            if not success:
                logger.error("Failed to write content to Google Doc")
                return ""
            
            # Place visuals in the document
            if article.visuals and len(article.visuals) > 0:
                logger.info(f"Placing {len(article.visuals)} visuals in document")
                await self.docs_client.place_visuals_in_document(
                    document_id=document_id, 
                    article=article,
                    visuals=article.visuals
                )
            
            # Apply final formatting
            await self.docs_client.add_headers_and_formatting(document_id)
            
            logger.info(f"Successfully created professional document: {document_id}")
            return document_id
            
        except Exception as e:
            logger.error(f"Error creating professional document: {str(e)}")
            return ""