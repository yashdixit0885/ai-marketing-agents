# services/api_clients/google_docs_client.py

import logging
import re
import json
from googleapiclient.discovery import build
from google.oauth2 import service_account
from config.settings import settings
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from typing import List, Dict, Any, Union, Optional, Tuple
from googleapiclient.errors import HttpError
import asyncio
import base64
from datetime import datetime

from models.content_models import Article, Visual
from utils.helpers import clean_text

logger = logging.getLogger(__name__)

class GoogleDocsClient:
    """Client for interacting with Google Docs API."""
    
    def __init__(self):
        """Initialize the Google Docs client."""
        # Check if credentials file exists
        credentials_file = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if not credentials_file or not os.path.exists(credentials_file):
            logger.error(f"Google credentials file not found at {credentials_file}")
            raise FileNotFoundError(f"Google credentials file not found at {credentials_file}")
            
        try:
            # Initialize the service
            credentials = service_account.Credentials.from_service_account_file(
                credentials_file,
                scopes=['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive']
            )
            self.docs_service = build('docs', 'v1', credentials=credentials)
            logger.info("Google Docs client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Google Docs client: {e}")
            raise
    
    def _clean_content(self, content: str) -> str:
        """Clean content for compatibility with Google Docs API.
        
        Args:
            content: The content to clean
            
        Returns:
            str: The cleaned content
        """
        if not content:
            return "No content available."
            
        # Remove trailing newlines
        content = content.strip()
        
        # Replace multiple consecutive newlines with just two
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        if not content:
            return "No content available."
            
        return content

    def _split_content(self, content: str, max_length: int = 50000) -> List[str]:
        """Split content into chunks that respect paragraph boundaries."""
        paragraphs = content.split('\n\n')
        chunks = []
        current_chunk = []
        current_length = 0
        
        for para in paragraphs:
            para_length = len(para)
            if current_length + para_length > max_length and current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = []
                current_length = 0
            current_chunk.append(para)
            current_length += para_length
            
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
            
        return chunks

    def create_document(self, title: str) -> Optional[str]:
        """Create a new Google Doc.
        
        Args:
            title: The title of the document
            
        Returns:
            str: The document ID if successful, None otherwise
        """
        try:
            body = {
                'title': title
            }
            doc = self.docs_service.documents().create(body=body).execute()
            doc_id = doc.get('documentId')
            logger.info(f"Created new Google Doc with ID: {doc_id}")
            return doc_id
        except Exception as e:
            logger.error(f"Error creating Google Doc: {e}")
            return None

    def _parse_markdown_to_requests(self, content: str, start_index: int = 1) -> tuple[str, List[Dict]]:
        """Parse markdown content and generate Google Docs API requests.
        
        Args:
            content: The markdown content to parse
            start_index: The starting index in the document
            
        Returns:
            tuple: (cleaned_text, formatting_requests)
        """
        # Process the content in stages to avoid index calculation errors
        plain_text = content
        requests = []
        
        # Track all positions that will need formatting
        formatting_positions = []
        
        # 1. First find all the headers
        header_matches = list(re.finditer(r'^(#{1,3})\s+(.+)$', content, re.MULTILINE))
        for match in header_matches:
            level = len(match.group(1))
            header_text = match.group(2)
            start = match.start()
            end = match.end()
            
            formatting_positions.append({
                'type': 'header',
                'level': level,
                'text': header_text,
                'start': start,
                'end': end,
                'original': match.group(0)
            })
        
        # 2. Find all bold text
        bold_matches = list(re.finditer(r'\*\*(.*?)\*\*', content))
        for match in bold_matches:
            formatting_positions.append({
                'type': 'bold',
                'text': match.group(1),
                'start': match.start(),
                'end': match.end(),
                'original': match.group(0)
            })
            
        # 3. Find all italic text
        italic_matches = list(re.finditer(r'\*([^*]+)\*', content))
        for match in italic_matches:
            # Check if this is already part of a bold match
            is_part_of_bold = False
            for bold_match in bold_matches:
                if match.start() >= bold_match.start() and match.end() <= bold_match.end():
                    is_part_of_bold = True
                    break
                    
            if not is_part_of_bold:
                formatting_positions.append({
                    'type': 'italic',
                    'text': match.group(1),
                    'start': match.start(),
                    'end': match.end(),
                    'original': match.group(0)
                })
        
        # 4. Find all bullet points and checkboxes
        bullet_matches = list(re.finditer(r'^(\s*)(?:[*-])\s+(.+)$', content, re.MULTILINE))
        for match in bullet_matches:
            formatting_positions.append({
                'type': 'bullet',
                'indent': len(match.group(1)),
                'text': match.group(2),
                'start': match.start(),
                'end': match.end(),
                'original': match.group(0)
            })
            
        # Sort all formatting positions by their end position in reverse order
        # This ensures we replace from the end to avoid messing up positions
        formatting_positions.sort(key=lambda x: x['end'], reverse=True)
            
        # First pass: replace all markdown syntax with plain text
        for pos in formatting_positions:
            if pos['type'] == 'header':
                # Replace header with just the text
                plain_text = plain_text[:pos['start']] + pos['text'] + plain_text[pos['end']:]
            elif pos['type'] == 'bold':
                # Replace **text** with just text
                plain_text = plain_text[:pos['start']] + pos['text'] + plain_text[pos['end']:]
            elif pos['type'] == 'italic':
                # Replace *text* with just text
                plain_text = plain_text[:pos['start']] + pos['text'] + plain_text[pos['end']:]
            elif pos['type'] == 'bullet':
                # Replace bullet with just the text
                plain_text = plain_text[:pos['start']] + pos['text'] + plain_text[pos['end']:]
                
        # Second pass: recalculate all positions based on the plain text
        # This is a simplified approach that will rebuild formatting requests based on the clean text
        
        # Reset indices for each markdown element
        current_pos = 0
        lines = plain_text.split('\n')
        header_index = 0
        
        # Process line by line to handle headers and bullets
        for i, line in enumerate(lines):
            line_length = len(line) + (1 if i < len(lines) - 1 else 0)  # +1 for newline
            
            # Check if this line was a header
            header_match = None
            for pos in formatting_positions:
                if pos['type'] == 'header' and header_index < len(header_matches):
                    # Original header line matched the pattern
                    if pos['text'] == line:
                        # This is a header line
                        requests.append({
                            'updateParagraphStyle': {
                                'range': {
                                    'startIndex': start_index + current_pos,
                                    'endIndex': start_index + current_pos + len(line)
                                },
                                'paragraphStyle': {
                                    'namedStyleType': f'HEADING_{pos["level"]}'
                                },
                                'fields': 'namedStyleType'
                            }
                        })
                        header_index += 1
                        break
            
            # Check if this line was a bullet point
            for pos in formatting_positions:
                if pos['type'] == 'bullet' and pos['text'] == line:
                    # This is a bullet line
                    requests.append({
                        'createParagraphBullets': {
                            'range': {
                                'startIndex': start_index + current_pos,
                                'endIndex': start_index + current_pos + len(line) + (1 if i < len(lines) - 1 else 0)
                            },
                            'bulletPreset': 'BULLET_DISC_CIRCLE_SQUARE'
                        }
                    })
                    break
                    
            # Move position forward
            current_pos += line_length
        
        # Process inline formatting (bold, italic)
        for i, char in enumerate(plain_text):
            # Check if this character starts bold text
            for pos in formatting_positions:
                if pos['type'] == 'bold':
                    # Find where this bold text appears in plain_text
                    bold_text = pos['text']
                    bold_start = plain_text.find(bold_text, max(0, i - len(bold_text)))
                    
                    if bold_start == i:
                        # Found the start of bold text
                        requests.append({
                            'updateTextStyle': {
                                'range': {
                                    'startIndex': start_index + i,
                                    'endIndex': start_index + i + len(bold_text)
                                },
                                'textStyle': {
                                    'bold': True
                                },
                                'fields': 'bold'
                            }
                        })
                        
            # Check if this character starts italic text
            for pos in formatting_positions:
                if pos['type'] == 'italic':
                    # Find where this italic text appears in plain_text
                    italic_text = pos['text']
                    italic_start = plain_text.find(italic_text, max(0, i - len(italic_text)))
                    
                    if italic_start == i:
                        # Found the start of italic text
                        requests.append({
                            'updateTextStyle': {
                                'range': {
                                    'startIndex': start_index + i,
                                    'endIndex': start_index + i + len(italic_text)
                                },
                                'textStyle': {
                                    'italic': True
                                },
                                'fields': 'italic'
                            }
                        })
                                
        return plain_text, requests

    def write_content(self, doc_id: str, content: str) -> bool:
        """Write content to a Google Doc with proper markdown formatting.
        
        Args:
            doc_id: The ID of the Google Doc
            content: The content to write (with markdown formatting)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not content:
            logger.warning("No content provided to write to Google Doc")
            return False
            
        if not doc_id:
            logger.error("No document ID provided to write content to Google Doc")
            return False
            
        try:
            # Clean the content before parsing markdown
            cleaned_content = self._clean_content(content)
            
            # Get the document to ensure it exists
            doc = self.docs_service.documents().get(documentId=doc_id).execute()
            
            # Get current end index of the document
            end_index = doc.get('body', {}).get('content', [])[-1].get('endIndex', 1)
            insertion_index = max(1, end_index - 1)  # Start at least at index 1 to preserve title
            
            # Split content into chunks if it's too large
            content_chunks = self._split_content(cleaned_content)
            
            for chunk in content_chunks:
                # Parse markdown and get formatting requests
                clean_text, formatting_requests = self._parse_markdown_to_requests(
                    chunk, 
                    start_index=insertion_index
                )
                
                # Create a request to insert the clean text
                requests = [
                    {
                        'insertText': {
                            'location': {
                                'index': insertion_index
                            },
                            'text': clean_text
                        }
                    }
                ]
                
                # Add all formatting requests
                requests.extend(formatting_requests)
                
                # Execute the batch update
                result = self.docs_service.documents().batchUpdate(
                    documentId=doc_id,
                    body={'requests': requests}
                ).execute()
                
                # Update insertion index for next chunk if there are multiple chunks
                if len(content_chunks) > 1:
                    # Re-fetch document to get updated end index
                    doc = self.docs_service.documents().get(documentId=doc_id).execute()
                    end_index = doc.get('body', {}).get('content', [])[-1].get('endIndex', 1)
                    insertion_index = max(1, end_index - 1)
            
            # Add a review section at the end
            review_section = "\n\n## For Review\nPlease add any feedback or comments below:\n- \n- \n- \n"
            self.docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={
                    'requests': [
                        {
                            'insertText': {
                                'location': {
                                    'index': insertion_index
                                },
                                'text': review_section
                            }
                        }
                    ]
                }
            ).execute()
            
            logger.info(f"Successfully wrote content to Google Doc: {doc_id}")
            return True
                
        except Exception as e:
            logger.error(f"Error writing content to Google Doc: {e}")
            return False
    
    async def append_content(self, doc_id, content):
        """Append content to the end of a Google Doc."""
        try:
            # Get the current document
            document = self.docs_service.documents().get(documentId=doc_id).execute()
            
            # Determine the end index
            end_index = document.get('body').get('content')[-1].get('endIndex', 1)
            
            # Insert at the end
            requests = [{
                'insertText': {
                    'location': {
                        'index': end_index - 1
                    },
                    'text': content
                }
            }]
            
            result = self.docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()
            
            logger.info(f"Appended content to document: {doc_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to append content to document {doc_id}: {str(e)}")
            raise
    
    async def insert_image(self, document_id: str, image_id: str, position: int = None) -> bool:
        """
        Insert an image from Google Drive into a document.
        
        Args:
            document_id: The ID of the document
            image_id: The ID of the image in Google Drive
            position: The position to insert at, or None for end of document
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not document_id or not image_id:
                logger.error("Missing document ID or image ID for image insertion")
                return False
                
            logger.info(f"Inserting image {image_id} into document {document_id}")
            
            # Get the document to determine insert position if not specified
            if position is None:
                document = await self.get_document(document_id)
                content = document.get('body', {}).get('content', [])
                if content:
                    position = content[-1].get("endIndex", 1)
                else:
                    position = 1
            
            # Initialize the Docs API service
            creds = await self._get_credentials()
            service = build('docs', 'v1', credentials=creds)
            
            # Create a request to insert the image
            request = {
                'insertInlineImage': {
                    'location': {
                        'index': position
                    },
                    'uri': f'https://drive.google.com/uc?id={image_id}',
                    'objectSize': {
                        'width': {
                            'magnitude': 600,
                            'unit': 'PT'
                        },
                        'height': {
                            'magnitude': 350,
                            'unit': 'PT'
                        }
                    }
                }
            }
            
            # Add a new line after the image for spacing
            requests = [
                request,
                {
                    'insertText': {
                        'location': {
                            'index': position + 1  # +1 because the image takes up 1 index
                        },
                        'text': '\n\n'
                    }
                }
            ]
            
            # Execute the requests
            service.documents().batchUpdate(
                documentId=document_id,
                body={'requests': requests}
            ).execute()
            
            logger.info(f"Successfully inserted image {image_id} into document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error inserting image: {str(e)}")
            return False

    async def insert_image_with_caption(self, document_id: str, image_id: str, caption: str, position: int = None) -> bool:
        """
        Insert an image from Google Drive into a document with a caption below it.
        
        Args:
            document_id: The ID of the document
            image_id: The ID of the image in Google Drive
            caption: The caption text to display below the image
            position: The position in the document to insert at, or None for end of document
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # First insert the image
            image_inserted = await self.insert_image(document_id, image_id, position)
            if not image_inserted:
                logger.error(f"Failed to insert image {image_id} into document {document_id}")
                return False
                
            # Get updated document to find the position after the image
            document = await self.get_document(document_id)
            content = document.get('body', {}).get('content', [])
            
            # Find the position for the caption (after the newly inserted image)
            caption_position = None
            for i, item in enumerate(content):
                if "paragraph" in item and i > 0 and "image" in content[i-1].get("paragraph", {}).get("elements", [{}])[0].get("inlineObjectElement", {}):
                    caption_position = item.get("startIndex", None)
                    break
                    
            if not caption_position and content:
                # If we couldn't find a position, use the end of the document
                caption_position = content[-1].get("endIndex", 1)
                
            # Insert the caption text
            if caption_position:
                await self._insert_caption(document_id, caption, caption_position)
                logger.info(f"Successfully inserted image with caption in document {document_id}")
                return True
            else:
                logger.warning(f"Could not determine position for caption in document {document_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error inserting image with caption: {str(e)}")
            return False
            
    async def _insert_caption(self, document_id: str, caption: str, position: int) -> None:
        """
        Insert a formatted caption at the specified position.
        
        Args:
            document_id: The document ID
            caption: The caption text
            position: The position to insert at
        """
        try:
            creds = await self._get_credentials()
            service = build('docs', 'v1', credentials=creds)
            
            # Create requests to insert the caption with center alignment and italic formatting
            requests = [
                {
                    'insertText': {
                        'location': {
                            'index': position
                        },
                        'text': caption + '\n'
                    }
                },
                {
                    'updateParagraphStyle': {
                        'range': {
                            'startIndex': position,
                            'endIndex': position + len(caption)
                        },
                        'paragraphStyle': {
                            'alignment': 'CENTER'
                        },
                        'fields': 'alignment'
                    }
                },
                {
                    'updateTextStyle': {
                        'range': {
                            'startIndex': position,
                            'endIndex': position + len(caption)
                        },
                        'textStyle': {
                            'italic': True
                        },
                        'fields': 'italic'
                    }
                }
            ]
            
            # Execute the requests
            service.documents().batchUpdate(
                documentId=document_id,
                body={'requests': requests}
            ).execute()
            
        except Exception as e:
            logger.error(f"Error inserting caption: {str(e)}")

    async def create_professional_document(self, article: Article, visuals: List[Visual] = None) -> Dict[str, Any]:
        """Create a professionally formatted document with content and integrated visuals.
        
        Args:
            article: Article object containing content
            visuals: List of Visual objects to include in the document
            
        Returns:
            Document metadata including ID
        """
        try:
            # Create new document
            doc_id = self.create_document(article.title)
            
            if not doc_id:
                logger.error("Failed to create document")
                return {"documentId": None}
                
            # Write the main article content first
            content_written = self.write_content(doc_id, article.content)
            if not content_written:
                logger.error("Failed to write content to document")
                return {"documentId": doc_id}  # Return ID even if content writing failed
                
            # If we have visuals, try to insert them
            if visuals and len(visuals) > 0:
                try:
                    logger.info(f"Inserting {len(visuals)} visuals into document {doc_id}")
                    # Insert header image first if present
                    header_images = [v for v in visuals if v.type == 'header_image']
                    if header_images:
                        # Insert at the beginning of the document
                        for visual in header_images:
                            # The Visual model stores the Google Drive file ID in file_path
                            placement_successful = await self.insert_image(
                                document_id=doc_id, 
                                image_id=visual.file_path,
                                position=1  # Top of document
                            )
                            if placement_successful:
                                logger.info(f"Inserted header image {visual.title} at beginning of document")
                            else:
                                logger.warning(f"Failed to insert header image {visual.title}")
                    
                    # Insert remaining visuals distributed throughout the document
                    other_visuals = [v for v in visuals if v.type != 'header_image']
                    if other_visuals:
                        # Get document to find appropriate positions
                        document = self.docs_service.documents().get(documentId=doc_id).execute()
                        content = document.get('body', {}).get('content', [])
                        
                        if content:
                            doc_length = content[-1].get('endIndex', 1)
                            
                            # Calculate positions to distribute visuals evenly
                            num_visuals = len(other_visuals)
                            
                            # Start after the first 15% of content
                            start_pos = max(int(doc_length * 0.15), 1)
                            
                            # Distribute throughout the remaining 75% of the document
                            remaining_space = int(doc_length * 0.75)
                            
                            if num_visuals == 1:
                                # Single visual goes at 1/3 point
                                positions = [start_pos + int(remaining_space * 0.33)]
                            else:
                                # Multiple visuals distributed evenly
                                positions = []
                                for i in range(num_visuals):
                                    pos = start_pos + int((i + 1) * remaining_space / (num_visuals + 1))
                                    positions.append(pos)
                                
                            # Insert visuals at calculated positions
                            for i, visual in enumerate(other_visuals):
                                if i < len(positions):
                                    placement_successful = await self.insert_image(
                                        document_id=doc_id,
                                        image_id=visual.file_path,
                                        position=positions[i]
                                    )
                                    if placement_successful:
                                        logger.info(f"Inserted {visual.type} visual {visual.title} at position {positions[i]}")
                                    else:
                                        logger.warning(f"Failed to insert {visual.type} visual {visual.title}")
                                        
                except Exception as e:
                    logger.error(f"Error placing visuals in document: {str(e)}")
                    # Continue with document creation even if visual placement fails
            
            logger.info(f"Professional document created with ID: {doc_id}")
            return {"documentId": doc_id, "title": article.title}
            
        except Exception as e:
            logger.error(f"Failed to create professional document: {str(e)}")
            return {"documentId": None}
    
    def _parse_content_into_sections(self, content: str) -> list:
        """Parse content into sections with type identification."""
        sections = []
        lines = content.split('\n')
        
        current_section = {'type': 'paragraph', 'content': '', 'visual_opportunity': False}
        section_count = 0
        
        for line in lines:
            # Check for headings
            if line.startswith('# '):
                # If the current section has content, add it to sections
                if current_section['content'].strip():
                    # Enable visual opportunity for longer paragraphs
                    if current_section['type'] == 'paragraph' and len(current_section['content']) > 100:
                        current_section['visual_opportunity'] = True
                    sections.append(current_section)
                
                # Start a new heading1 section
                current_section = {
                    'type': 'heading1',
                    'content': line[2:],  # Remove the '# ' prefix
                    'visual_opportunity': False  # Don't put visuals right after headings
                }
                sections.append(current_section)
                current_section = {'type': 'paragraph', 'content': '', 'visual_opportunity': False}
                section_count += 1
                
            elif line.startswith('## '):
                # If the current section has content, add it to sections
                if current_section['content'].strip():
                    # Enable visual opportunity for longer paragraphs
                    if current_section['type'] == 'paragraph' and len(current_section['content']) > 100:
                        current_section['visual_opportunity'] = True
                    sections.append(current_section)
                
                # Start a new heading2 section
                current_section = {
                    'type': 'heading2',
                    'content': line[3:],  # Remove the '## ' prefix
                    'visual_opportunity': False  # Don't put visuals right after headings
                }
                sections.append(current_section)
                current_section = {'type': 'paragraph', 'content': '', 'visual_opportunity': False}
                section_count += 1
                
            # Check for empty lines (paragraph breaks)
            elif not line.strip() and current_section['content'].strip():
                # Enable visual opportunity for longer paragraphs
                if current_section['type'] == 'paragraph' and len(current_section['content']) > 100:
                    current_section['visual_opportunity'] = True
                sections.append(current_section)
                current_section = {'type': 'paragraph', 'content': '', 'visual_opportunity': False}
                
            # Add to current section
            else:
                if current_section['content'] and not current_section['content'].endswith('\n'):
                    current_section['content'] += '\n'
                current_section['content'] += line
        
        # Add the last section if it has content
        if current_section['content'].strip():
            # Enable visual opportunity for longer paragraphs
            if current_section['type'] == 'paragraph' and len(current_section['content']) > 100:
                current_section['visual_opportunity'] = True
            sections.append(current_section)
        
        # If we have multiple sections but no visual opportunities yet,
        # mark every third paragraph section as a visual opportunity
        visual_ops = sum(1 for s in sections if s.get('visual_opportunity', False))
        if len(sections) > 3 and visual_ops == 0:
            paragraph_count = 0
            for i, section in enumerate(sections):
                if section['type'] == 'paragraph':
                    paragraph_count += 1
                    if paragraph_count % 3 == 0:
                        sections[i]['visual_opportunity'] = True
            
        return sections

    def _process_text_with_markdown(self, text: str) -> dict:
        """Process text with markdown formatting and generate style requests."""
        style_requests = []
        
        # Handle bold text (**text**)
        bold_matches = list(re.finditer(r'\*\*(.*?)\*\*', text))
        for match in reversed(bold_matches):
            start, end = match.span()
            matched_text = match.group(1)
            
            # Create style request for bold text
            style_requests.append({
                'updateTextStyle': {
                    'range': {
                        'startIndex': start,
                        'endIndex': start + len(matched_text)
                    },
                    'textStyle': {
                        'bold': True
                    },
                    'fields': 'bold'
                }
            })
            
            # Replace the markdown syntax with just the text
            text = text[:start] + matched_text + text[end:]
        
        # Handle italic text (*text*)
        italic_matches = list(re.finditer(r'\*(.*?)\*', text))
        for match in reversed(italic_matches):
            start, end = match.span()
            matched_text = match.group(1)
            
            # Create style request for italic text
            style_requests.append({
                'updateTextStyle': {
                    'range': {
                        'startIndex': start,
                        'endIndex': start + len(matched_text)
                    },
                    'textStyle': {
                        'italic': True
                    },
                    'fields': 'italic'
                }
            })
            
            # Replace the markdown syntax with just the text
            text = text[:start] + matched_text + text[end:]
        
        # Handle code blocks and inline code
        code_matches = list(re.finditer(r'`(.*?)`', text))
        for match in reversed(code_matches):
            start, end = match.span()
            matched_text = match.group(1)
            
            # Create style request for code text
            style_requests.append({
                'updateTextStyle': {
                    'range': {
                        'startIndex': start,
                        'endIndex': start + len(matched_text)
                    },
                    'textStyle': {
                        'fontFamily': 'Consolas'
                    },
                    'fields': 'fontFamily'
                }
            })
            
            # Replace the markdown syntax with just the text
            text = text[:start] + matched_text + text[end:]
        
        # Handle bullet points - we won't replace these, just identify them for later processing
        
        # Handle links [text](url)
        link_matches = list(re.finditer(r'\[(.*?)\]\((.*?)\)', text))
        for match in reversed(link_matches):
            start, end = match.span()
            link_text = match.group(1)
            url = match.group(2)
            
            # Create style request for link
            style_requests.append({
                'updateTextStyle': {
                    'range': {
                        'startIndex': start,
                        'endIndex': start + len(link_text)
                    },
                    'textStyle': {
                        'link': {
                            'url': url
                        }
                    },
                    'fields': 'link'
                }
            })
            
            # Replace the markdown syntax with just the text
            text = text[:start] + link_text + text[end:]
            
        return {
            'text': text,
            'style_requests': style_requests
        }
    
    async def add_comment(self, doc_id, text, start_index, end_index):
        """Add a comment to the document."""
        try:
            result = self.docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={
                    'requests': [
                        {
                            'createComment': {
                                'text': text,
                                'range': {
                                    'startIndex': start_index,
                                    'endIndex': end_index
                                }
                            }
                        }
                    ]
                }
            ).execute()
            
            logger.info(f"Added comment to document: {doc_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to add comment to document {doc_id}: {str(e)}")
            raise

    def _categorize_visuals(self, visuals_data: List[Dict[str, Any]]) -> Dict[str, List]:
        """Categorize visuals by type for better integration."""
        categorized = {}
        
        for visual in visuals_data:
            visual_type = visual.get('type', 'other')
            if visual_type not in categorized:
                categorized[visual_type] = []
            categorized[visual_type].append(visual)
        
        return categorized

    async def _get_image_url(self, file_path: str) -> str:
        """Get publicly accessible URL for an image.
        
        In a real implementation, this would get a sharing URL from Google Drive.
        For now, we'll assume file_path is already a public URL or Drive ID.
        """
        # Check if we need to create a public URL from a Drive ID
        if file_path and not file_path.startswith('http'):
            # For this simplified version, we'll just return a drive viewer URL
            # In a real app, you would use the Drive API to get or create a public URL
            return f"https://drive.google.com/uc?id={file_path}"
        
        return file_path or ""
    
    async def get_document(self, document_id: str) -> Dict[str, Any]:
        """
        Get a Google Doc by ID.
        
        Args:
            document_id: The ID of the document to retrieve
            
        Returns:
            The document data
        """
        try:
            if not document_id:
                logger.error("No document ID provided for retrieval")
                return {}
                
            logger.info(f"Retrieving document: {document_id}")
            # Initialize the Drive API service
            creds = await self._get_credentials()
            service = build('docs', 'v1', credentials=creds)
            
            # Get the document
            document = service.documents().get(documentId=document_id).execute()
            return document
            
        except Exception as e:
            logger.error(f"Error retrieving document: {str(e)}")
            return {}

    async def place_visuals_in_document(self, document_id: str, article: Article, 
                                   visuals: List[Visual]) -> bool:
        """
        Intelligently place visuals throughout a document based on their placement attribute.
        
        Args:
            document_id: The ID of the document
            article: The article object
            visuals: List of Visual objects to place in the document
            
        Returns:
            True if successful, False otherwise
        """
        if not self.docs_service:
            logger.error("Google Docs service not initialized")
            return False
            
        if not document_id or not visuals:
            logger.warning(f"Missing document_id or no visuals to place")
            return False
            
        try:
            # Get document content to determine section positions
            document = await self.get_document(document_id)
            if not document:
                logger.error(f"Document {document_id} not found")
                return False
            
            # First, create a map of section names to positions in the document
            section_positions = await self._identify_section_positions(document, article)
            
            # Group visuals by their placement
            visual_groups = {}
            for visual in visuals:
                placement = visual.placement if hasattr(visual, 'placement') else "body"
                if placement not in visual_groups:
                    visual_groups[placement] = []
                visual_groups[placement].append(visual)
            
            # Insert header image first if exists
            if "header" in visual_groups:
                for visual in visual_groups["header"]:
                    # Header images go at the very top
                    await self.insert_image_with_caption(
                        document_id=document_id,
                        image_id=visual.file_id,
                        caption=visual.description,
                        position=1  # Start of document after title
                    )
                    logger.info(f"Placed header image {visual.title} at document start")
            
            # Then place all other visuals according to their section placement
            for section, position in section_positions.items():
                if section in visual_groups:
                    for visual in visual_groups[section]:
                        # Place visual at the end of its designated section
                        await self.insert_image_with_caption(
                            document_id=document_id,
                            image_id=visual.file_id,
                            caption=visual.description,
                            position=position
                        )
                        logger.info(f"Placed {visual.type} visual in section '{section}'")
            
            # Place any remaining visuals in the body
            if "body" in visual_groups:
                # Distribute body visuals throughout the document at sensible intervals
                body_positions = await self._calculate_body_positions(document, len(visual_groups["body"]))
                
                for i, visual in enumerate(visual_groups["body"]):
                    if i < len(body_positions):
                        position = body_positions[i]
                        await self.insert_image_with_caption(
                            document_id=document_id,
                            image_id=visual.file_id,
                            caption=visual.description,
                            position=position
                        )
                        logger.info(f"Placed {visual.type} visual in document body position {i+1}/{len(body_positions)}")
            
            logger.info(f"Successfully placed {len(visuals)} visuals in document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error placing visuals in document: {str(e)}")
            return False
    
    async def _identify_section_positions(self, document: Dict[str, Any], 
                                     article: Article) -> Dict[str, int]:
        """
        Identify the end position of each section in the document.
        
        Args:
            document: The document resource
            article: The article object
            
        Returns:
            Dictionary mapping section names to end positions
        """
        section_positions = {}
        
        try:
            content = document.get('body', {}).get('content', [])
            
            # Extract content structure from article if available
            article_sections = []
            if isinstance(article.content, dict):
                # Check for structured content
                if "introduction" in article.content:
                    article_sections.append(("introduction", article.content["introduction"]))
                
                if "sections" in article.content and isinstance(article.content["sections"], list):
                    for section in article.content["sections"]:
                        if isinstance(section, dict) and "heading" in section:
                            article_sections.append((section["heading"], section.get("content", "")))
                
                if "conclusion" in article.content:
                    article_sections.append(("conclusion", article.content["conclusion"]))
            
            # Look for heading elements and map to sections
            current_section = "header"  # Default section at start
            current_end = 1  # Start at beginning of document
            
            for item in content:
                # Track the current end position
                current_end = item.get('endIndex', current_end)
                
                # Check if this is a paragraph that might be a heading
                if 'paragraph' in item:
                    paragraph = item.get('paragraph', {})
                    elements = paragraph.get('elements', [])
                    
                    for element in elements:
                        if 'textRun' in element:
                            text = element.get('textRun', {}).get('content', '').strip()
                            
                            # Check if this is a heading (either by style or by markdown)
                            is_heading = False
                            if 'paragraphStyle' in paragraph:
                                style = paragraph.get('paragraphStyle', {}).get('namedStyleType', '')
                                is_heading = style.startswith('HEADING_')
                                
                            if is_heading or re.match(r'^#{1,3}\s+', text):
                                # Save the end position of the current section
                                section_positions[current_section] = current_end
                                
                                # Extract the heading text (removing any markdown)
                                heading_text = re.sub(r'^#{1,3}\s+', '', text).lower()
                                
                                # Find matching section from article content
                                matched = False
                                for section_name, _ in article_sections:
                                    if (section_name.lower() in heading_text or 
                                        heading_text in section_name.lower()):
                                        current_section = section_name
                                        matched = True
                                        break
                                
                                if not matched:
                                    # Use the heading text itself as section name
                                    current_section = heading_text
            
            # Add the final section position at the end of the document
            section_positions[current_section] = current_end
            
            # Add position for "body" if not already present (middle of document)
            if "body" not in section_positions:
                section_positions["body"] = current_end // 2
                
            # Add position for "conclusion" if not already present (end of document)
            if "conclusion" not in section_positions:
                section_positions["conclusion"] = current_end
                
            return section_positions
            
        except Exception as e:
            logger.error(f"Error identifying section positions: {str(e)}")
            return {"body": document.get('body', {}).get('content', [])[-1].get('endIndex', 1)}
    
    async def _calculate_body_positions(self, document: Dict[str, Any], 
                                   num_visuals: int) -> List[int]:
        """
        Calculate appropriate positions to place visuals in the document body.
        
        Args:
            document: The document resource
            num_visuals: Number of visuals to place
            
        Returns:
            List of position indices for placing visuals
        """
        positions = []
        
        try:
            # Get document length
            content = document.get('body', {}).get('content', [])
            if not content:
                return positions
                
            doc_length = content[-1].get('endIndex', 1)
            
            # Skip the first 10% of the document (usually intro)
            start_pos = int(doc_length * 0.1)
            # Use only the middle 80% of the document
            usable_length = int(doc_length * 0.8)
            
            if num_visuals <= 0:
                return positions
                
            # Distribute evenly
            if num_visuals == 1:
                # Single visual goes at the 1/3 point
                positions.append(start_pos + int(usable_length * 0.33))
            else:
                # Multiple visuals are distributed evenly
                segment = usable_length / (num_visuals + 1)
                for i in range(1, num_visuals + 1):
                    positions.append(start_pos + int(segment * i))
            
            return positions
            
        except Exception as e:
            logger.error(f"Error calculating body positions: {str(e)}")
            return positions
    
    def share_document(self, doc_id: str, email: str, role: str = 'reader') -> bool:
        """Share a document with a specific user.
        
        Args:
            doc_id (str): The ID of the document to share
            email (str): The email address of the user to share with
            role (str): The role to grant (reader, writer, commenter)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not doc_id:
                logger.error("No document ID provided to share")
                return False
                
            # Initialize the Drive API service with the same credentials
            credentials_file = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            credentials = service_account.Credentials.from_service_account_file(
                credentials_file,
                scopes=['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive']
            )
            drive_service = build('drive', 'v3', credentials=credentials)
            
            # Create the permission
            user_permission = {
                'type': 'user',
                'role': role,
                'emailAddress': email
            }
            
            # Share the document
            drive_service.permissions().create(
                fileId=doc_id,
                body=user_permission,
                fields='id',
                sendNotificationEmail=True
            ).execute()
            
            logger.info(f"Successfully shared document {doc_id} with {email} as {role}")
            return True
            
        except Exception as e:
            logger.error(f"Error sharing document: {e}")
            return False
        
    async def _get_credentials(self):
        """Get credentials for API calls.
        
        Returns:
            The credentials object
        """
        try:
            # We already have credentials initialized in the constructor
            return self.docs_service._credentials
        except Exception as e:
            logger.error(f"Error getting credentials: {str(e)}")
            # Recreate credentials if needed
            credentials_file = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            return service_account.Credentials.from_service_account_file(
                credentials_file,
                scopes=['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive']
            )