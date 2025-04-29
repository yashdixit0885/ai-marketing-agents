# services/api_clients/google_docs_client.py

import logging
import re
import json
from googleapiclient.discovery import build
from google.oauth2 import service_account
from config.settings import settings

logger = logging.getLogger(__name__)

class GoogleDocsClient:
    """Client for interacting with Google Docs API."""
    
    def __init__(self):
        """Initialize the Google Docs client."""
        try:
            self.credentials = service_account.Credentials.from_service_account_file(
                settings.GOOGLE_APPLICATION_CREDENTIALS,
                scopes=['https://www.googleapis.com/auth/documents']
            )
            self.service = build('docs', 'v1', credentials=self.credentials)
            logger.info("Successfully initialized Google Docs client")
        except Exception as e:
            logger.error(f"Failed to initialize Google Docs client: {str(e)}")
            raise
    
    async def write_content(self, doc_id, content):
        """Write content to a Google Doc."""
        try:
            # Get the current document to check its length
            document = self.service.documents().get(documentId=doc_id).execute()
            
            # Insert content at index 1 (beginning of document)
            requests = self._clear_document(document)
            requests.append({
                'insertText': {
                    'location': {'index': 1},
                    'text': content + "\n\n--- REVIEW SECTION ---\n\nReviewer: \n\nStatus: [  ] Approved   [  ] Rejected   [  ] Needs Revision\n\nComments:\n\n"
                }
            })
            
            result = self.service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()
            
            logger.info(f"Updated document: {doc_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to write content to document {doc_id}: {str(e)}")
            raise
    
    async def append_content(self, doc_id, content):
        """Append content to the end of a Google Doc."""
        try:
            # Get the current document
            document = self.service.documents().get(documentId=doc_id).execute()
            
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
            
            result = self.service.documents().batchUpdate(
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
            document = self.service.documents().get(documentId=doc_id).execute()
            
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
                        'width': {
                            'magnitude': width,
                            'unit': 'PT'
                        },
                        'height': {
                            'magnitude': height,
                            'unit': 'PT'
                        }
                    }
                }
            }]
            
            result = self.service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()
            
            logger.info(f"Inserted image into document: {doc_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to insert image into document {doc_id}: {str(e)}")
            raise
    
    async def create_professional_document(self, doc_id, content, visuals):
        """Create a professionally formatted document with integrated visuals."""
        try:
            # Get the current document
            document = self.service.documents().get(documentId=doc_id).execute()
            
            # Start with a clean document
            requests = self._clear_document(document)
            
            # Parse the content to identify logical sections for image placement
            sections = self._parse_content_sections(content)
            
            # Create document with strategically placed visuals
            current_index = 1
            visual_index = 0
            
            for section in sections:
                # Add section content
                requests.append({
                    'insertText': {
                        'location': {'index': current_index},
                        'text': section['content']
                    }
                })
                
                # Apply formatting to headings
                if section['type'] == 'heading1':
                    requests.append({
                        'updateParagraphStyle': {
                            'range': {
                                'startIndex': current_index,
                                'endIndex': current_index + len(section['content']) - 1
                            },
                            'paragraphStyle': {'namedStyleType': 'HEADING_1'},
                            'fields': 'namedStyleType'
                        }
                    })
                elif section['type'] == 'heading2':
                    requests.append({
                        'updateParagraphStyle': {
                            'range': {
                                'startIndex': current_index,
                                'endIndex': current_index + len(section['content']) - 1
                            },
                            'paragraphStyle': {'namedStyleType': 'HEADING_2'},
                            'fields': 'namedStyleType'
                        }
                    })
                
                current_index += len(section['content'])
                
                # If this is a good spot for an image and we have visuals left
                if section['visual_opportunity'] and visual_index < len(visuals):
                    visual = visuals[visual_index]
                    
                    # Add a bit of spacing
                    requests.append({
                        'insertText': {
                            'location': {'index': current_index},
                            'text': '\n\n'
                        }
                    })
                    current_index += 2
                    
                    # Insert the image
                    image_url = f"https://drive.google.com/uc?export=view&id={visual['file_id']}"
                    requests.append({
                        'insertInlineImage': {
                            'location': {'index': current_index},
                            'uri': image_url,
                            'objectSize': {
                                'width': {'magnitude': 500, 'unit': 'PT'},
                                'height': {'magnitude': 350, 'unit': 'PT'}
                            }
                        }
                    })
                    
                    # Add caption
                    requests.append({
                        'insertText': {
                            'location': {'index': current_index + 1},
                            'text': f"\n\nFigure: {visual['title']}\n\n"
                        }
                    })
                    
                    # Style the caption (centered, italic)
                    requests.append({
                        'updateParagraphStyle': {
                            'range': {
                                'startIndex': current_index + 3,
                                'endIndex': current_index + 3 + len(f"Figure: {visual['title']}")
                            },
                            'paragraphStyle': {'alignment': 'CENTER'},
                            'fields': 'alignment'
                        }
                    })
                    
                    requests.append({
                        'updateTextStyle': {
                            'range': {
                                'startIndex': current_index + 3,
                                'endIndex': current_index + 3 + len(f"Figure: {visual['title']}")
                            },
                            'textStyle': {'italic': True},
                            'fields': 'italic'
                        }
                    })
                    
                    current_index += 7 + len(f"Figure: {visual['title']}")
                    visual_index += 1
            
            # Add review section at the end
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': "\n\n" + "-" * 30 + "\n\n## REVIEW SECTION\n\n" +
                           "Reviewer: \n\n" +
                           "Status: [ ] Approved   [ ] Rejected   [ ] Needs Revision\n\n" +
                           "Comments:\n\n"
                }
            })
            
            # Execute all requests
            result = self.service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()
            
            logger.info(f"Created professional document: {doc_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to create professional document {doc_id}: {str(e)}")
            raise
    
    def _clear_document(self, document):
        """Create request to clear the document content."""
        requests = []
        if document.get('body', {}).get('content', []):
            content_items = document.get('body', {}).get('content', [])
            if len(content_items) > 1:
                end_index = content_items[-1].get('endIndex', 1)
                if end_index > 2:
                    requests.append({
                        'deleteContentRange': {
                            'range': {
                                'startIndex': 1,
                                'endIndex': end_index - 1
                            }
                        }
                    })
        return requests
    
    def _parse_content_sections(self, content):
        """Parse content into logical sections with image placement opportunities."""
        lines = content.split('\n')
        sections = []
        current_section = {'content': '', 'type': 'paragraph', 'visual_opportunity': False}
        
        for line in lines:
            # Check for headings
            heading1_match = re.match(r'^#\s+(.*)', line)
            heading2_match = re.match(r'^##\s+(.*)', line)
            
            if heading1_match or heading2_match:
                # Save previous section if not empty
                if current_section['content']:
                    sections.append(current_section)
                
                # Start new section
                if heading1_match:
                    current_section = {
                        'content': f"{line}\n\n",
                        'type': 'heading1',
                        'visual_opportunity': False
                    }
                else:
                    current_section = {
                        'content': f"{line}\n\n",
                        'type': 'heading2',
                        'visual_opportunity': False
                    }
            else:
                # Add to current section
                current_section['content'] += f"{line}\n"
                
                # Mark as visual opportunity if this section is getting longer
                if len(current_section['content']) > 500:
                    current_section['visual_opportunity'] = True
                    sections.append(current_section)
                    current_section = {'content': '', 'type': 'paragraph', 'visual_opportunity': False}
        
        # Add the last section
        if current_section['content']:
            sections.append(current_section)
        
        return sections
    
    async def add_comment(self, doc_id, text, start_index, end_index):
        """Add a comment to the document."""
        try:
            result = self.service.documents().batchUpdate(
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