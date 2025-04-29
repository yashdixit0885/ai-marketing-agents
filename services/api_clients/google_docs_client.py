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
from typing import List, Dict, Any, Union, Optional
from googleapiclient.errors import HttpError

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
                scopes=['https://www.googleapis.com/auth/documents']
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
            
            # Parse markdown and get formatting requests
            clean_text, formatting_requests = self._parse_markdown_to_requests(
                cleaned_content, 
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
    
    async def insert_image(self, doc_id, image_url, width=400, height=300):
        """Insert an image into a Google Doc."""
        try:
            # Get the current document
            document = self.docs_service.documents().get(documentId=doc_id).execute()
            
            # Determine the end index
            end_index = document.get('body').get('content')[-1].get('endIndex', 1)
            
            # Insert the image
            requests = [{
                'insertInlineImage': {
                    'location': {
                        'index': end_index - 1
                    },
                    'uri': image_url,
                    'objectSize': {
                        'width': {'magnitude': width, 'unit': 'PT'},
                        'height': {'magnitude': height, 'unit': 'PT'}
                    }
                }
            }]
            
            result = self.docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()
            
            logger.info(f"Inserted image into document: {doc_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to insert image into document {doc_id}: {str(e)}")
            raise
    
    async def create_professional_document(self, doc_id: str, content: str, visuals_data: List[Dict[str, Any]]) -> None:
        """Create a professional document with content and visuals integrated throughout the text.
        
        This creates a publication-ready document with:
        - Proper header formatting
        - Strategic visual placement throughout content
        - Professional styling
        - Review section at the end
        """
        try:
            # Clean content and identify sections
            content = self._clean_content(content)
            sections = self._parse_content_into_sections(content)
            
            # Clear document
            doc = self.docs_service.documents().get(documentId=doc_id).execute()
            
            # Initialize requests
            requests = []
            
            # Start with a clean document if not empty
            if len(doc['body']['content']) > 1:
                end_index = doc['body']['content'][-1]['endIndex']
                if end_index > 1:
                    requests.append({
                        'deleteContentRange': {
                            'range': {
                                'startIndex': 1,
                                'endIndex': end_index - 1
                            }
                        }
                    })
            
            # Set current index for insertion
            current_index = 1
            
            # Set document title if found
            if sections and sections[0]['type'] == 'title':
                # Insert title text
                requests.append({
                    'insertText': {
                        'location': {'index': current_index},
                        'text': sections[0]['content'] + '\n\n'
                    }
                })
                
                # Format title
                requests.append({
                    'updateParagraphStyle': {
                        'range': {
                            'startIndex': current_index,
                            'endIndex': current_index + len(sections[0]['content'])
                        },
                        'paragraphStyle': {
                            'namedStyleType': 'TITLE',
                            'alignment': 'CENTER'
                        },
                        'fields': 'namedStyleType,alignment'
                    }
                })
                
                # Update index
                current_index += len(sections[0]['content']) + 2
                
                # Remove title from sections
                sections.pop(0)
            
            # Add author and date if available
            if sections and sections[0]['type'] == 'metadata':
                # Insert metadata text
                requests.append({
                    'insertText': {
                        'location': {'index': current_index},
                        'text': sections[0]['content'] + '\n\n'
                    }
                })
                
                # Format metadata
                requests.append({
                    'updateParagraphStyle': {
                        'range': {
                            'startIndex': current_index,
                            'endIndex': current_index + len(sections[0]['content'])
                        },
                        'paragraphStyle': {
                            'alignment': 'CENTER'
                        },
                        'fields': 'alignment'
                    }
                })
                
                # Update index
                current_index += len(sections[0]['content']) + 2
                
                # Remove metadata from sections
                sections.pop(0)
            
            # Add executive summary/intro if it exists
            if sections and sections[0]['type'] == 'intro':
                # Process the intro text to handle markdown formatting
                intro_text = self._process_text_with_markdown(sections[0]['content'])
                processed_text = intro_text['text']
                text_style_requests = intro_text['style_requests']
                
                # Insert intro text
                requests.append({
                    'insertText': {
                        'location': {'index': current_index},
                        'text': processed_text + '\n\n'
                    }
                })
                
                # Apply text styling from markdown parsing
                for style_req in text_style_requests:
                    # Make a deep copy of the style request to avoid modifying the original
                    updated_req = style_req.copy()
                    
                    # Create a new copy of the range dict
                    if 'range' in updated_req:
                        updated_req['range'] = updated_req['range'].copy()
                        updated_req['range']['startIndex'] += current_index
                        updated_req['range']['endIndex'] += current_index
                        requests.append(updated_req)
                
                # Format intro (italics for the whole intro)
                requests.append({
                    'updateTextStyle': {
                        'range': {
                            'startIndex': current_index,
                            'endIndex': current_index + len(processed_text)
                        },
                        'textStyle': {
                            'italic': True
                        },
                        'fields': 'italic'
                    }
                })
                
                # Update index
                current_index += len(processed_text) + 2
                
                # Remove intro from sections
                sections.pop(0)
            
            # Insert a visual for the header section if available
            if visuals_data and len(visuals_data) > 0:
                header_visual = visuals_data[0]
                
                # Insert image
                requests.append({
                    'insertInlineImage': {
                        'location': {'index': current_index},
                        'uri': header_visual.get('url', header_visual.get('web_content_link', '')),
                        'objectSize': {
                            'width': {'magnitude': 500, 'unit': 'PT'},
                            'height': {'magnitude': 300, 'unit': 'PT'}
                        }
                    }
                })
                
                # Add caption
                caption = f"\n\n{header_visual.get('title', 'Figure 1')}\n\n"
                requests.append({
                    'insertText': {
                        'location': {'index': current_index + 1},
                        'text': caption
                    }
                })
                
                # Format caption
                requests.append({
                    'updateParagraphStyle': {
                        'range': {
                            'startIndex': current_index + 3,
                            'endIndex': current_index + 3 + len(header_visual.get('title', 'Figure 1'))
                        },
                        'paragraphStyle': {
                            'alignment': 'CENTER'
                        },
                        'fields': 'alignment'
                    }
                })
                
                # Update index and remove the used visual
                current_index += len(caption) + 1
                visuals_data.pop(0)
            
            # Process remaining sections and strategically place visuals
            visual_index = 0
            section_count = 0
            
            for section in sections:
                section_count += 1
                
                # Process the section content for markdown formatting
                if section['type'] in ('paragraph', 'heading1', 'heading2'):
                    processed_content = self._process_text_with_markdown(section['content'])
                    text = processed_content['text']
                    style_requests = processed_content['style_requests']
                else:
                    text = section['content']
                    style_requests = []
                
                # Insert section content
                requests.append({
                    'insertText': {
                        'location': {'index': current_index},
                        'text': text + '\n\n'
                    }
                })
                
                # Apply any text styling from markdown parsing
                for style_req in style_requests:
                    # Make a deep copy of the style request to avoid modifying the original
                    updated_req = style_req.copy()
                    
                    # Create a new copy of the range dict
                    if 'range' in updated_req:
                        updated_req['range'] = updated_req['range'].copy()
                        updated_req['range']['startIndex'] += current_index
                        updated_req['range']['endIndex'] += current_index
                        requests.append(updated_req)
                
                # Format headings
                if section['type'] == 'heading1':
                    requests.append({
                        'updateParagraphStyle': {
                            'range': {
                                'startIndex': current_index,
                                'endIndex': current_index + len(text.split('\n')[0])
                            },
                            'paragraphStyle': {
                                'namedStyleType': 'HEADING_1'
                            },
                            'fields': 'namedStyleType'
                        }
                    })
                elif section['type'] == 'heading2':
                    requests.append({
                        'updateParagraphStyle': {
                            'range': {
                                'startIndex': current_index,
                                'endIndex': current_index + len(text.split('\n')[0])
                            },
                            'paragraphStyle': {
                                'namedStyleType': 'HEADING_2'
                            },
                            'fields': 'namedStyleType'
                        }
                    })
                
                # Convert bulleted lists
                if '* ' in text or '- ' in text:
                    list_items = text.split('\n')
                    for i, item in enumerate(list_items):
                        if item.strip().startswith('* ') or item.strip().startswith('- '):
                            item_start = current_index + text[:text.find(item.strip())].count('\n')
                            item_end = item_start + len(item.strip())
                            
                            # Remove the bullet marker from styling calculation
                            content_start = item_start + 2
                            
                            requests.append({
                                'createParagraphBullets': {
                                    'range': {
                                        'startIndex': item_start,
                                        'endIndex': item_end
                                    },
                                    'bulletPreset': 'BULLET_DISC_CIRCLE_SQUARE'
                                }
                            })
                
                # Update current index
                current_index += len(text) + 2
                
                # Add a visual after this section if it's a good spot and we have visuals left
                if 'visual_opportunity' in section and section['visual_opportunity'] and visual_index < len(visuals_data):
                    visual = visuals_data[visual_index]
                    
                    # Insert image
                    requests.append({
                        'insertInlineImage': {
                            'location': {'index': current_index - 1},
                            'uri': visual.get('url', visual.get('web_content_link', '')),
                            'objectSize': {
                                'width': {'magnitude': 450, 'unit': 'PT'},
                                'height': {'magnitude': 280, 'unit': 'PT'}
                            }
                        }
                    })
                    
                    # Add caption
                    figure_num = visual_index + 2  # +1 for header visual, +1 for 1-indexed
                    caption = f"\n\n{visual.get('title', f'Figure {figure_num}')}\n\n"
                    requests.append({
                        'insertText': {
                            'location': {'index': current_index},
                            'text': caption
                        }
                    })
                    
                    # Format caption
                    requests.append({
                        'updateParagraphStyle': {
                            'range': {
                                'startIndex': current_index + 2,
                                'endIndex': current_index + 2 + len(visual.get('title', f'Figure {figure_num}'))
                            },
                            'paragraphStyle': {
                                'alignment': 'CENTER'
                            },
                            'fields': 'alignment'
                        }
                    })
                    
                    # Update index
                    current_index += len(caption) + 1
                    visual_index += 1
            
            # Add a review section at the end
            review_section = "\n\n" + "-" * 30 + "\n\n" + \
                            "REVIEW SECTION\n\n" + \
                            "Status: [ ] Approved   [ ] Rejected   [ ] Needs Revision\n\n" + \
                            "Reviewer: \n\n" + \
                            "Comments:\n\n"
            
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': review_section
                }
            })
            
            # Format review section header
            requests.append({
                'updateParagraphStyle': {
                    'range': {
                        'startIndex': current_index + 32 + 2,  # After divider
                        'endIndex': current_index + 32 + 2 + 13  # REVIEW SECTION length
                    },
                    'paragraphStyle': {
                        'namedStyleType': 'HEADING_2'
                    },
                    'fields': 'namedStyleType'
                }
            })
            
            # Execute all requests
            if requests:
                self.docs_service.documents().batchUpdate(
                    documentId=doc_id,
                    body={'requests': requests}
                ).execute()
                
                logger.info(f"Successfully created professional document {doc_id}")
            
        except Exception as e:
            logger.error(f"Failed to create professional document {doc_id}: {str(e)}")
            raise
    
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