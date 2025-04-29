# services/api_clients/google_docs_client.py

import logging
import re
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
            
            # Insert content at the beginning of the document
            requests = self._content_to_requests(content, document)
            
            result = self.service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()
            
            logger.info(f"Updated document: {doc_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to write content to document {doc_id}: {str(e)}")
            raise
    
    def _content_to_requests(self, content, document):
        """Convert markdown content to Google Docs API requests."""
        # Start with a clean document
        requests = []
        
        # If the document is not empty, delete all content
        if document.get('body').get('content'):
            end_index = document.get('body').get('content')[-1].get('endIndex', 1)
            if end_index > 1:
                requests.append({
                    'deleteContentRange': {
                        'range': {
                            'startIndex': 1,
                            'endIndex': end_index
                        }
                    }
                })
        
        # Process content sections
        lines = content.split('\n')
        current_index = 1
        
        for line in lines:
            # Check for headers
            header_match = re.match(r'^(#+)\s+(.*)', line)
            if header_match:
                level = len(header_match.group(1))
                text = header_match.group(2)
                
                # Insert the text
                requests.append({
                    'insertText': {
                        'location': {
                            'index': current_index
                        },
                        'text': text + "\n"
                    }
                })
                
                # Set the appropriate heading style
                style_range = {
                    'range': {
                        'startIndex': current_index,
                        'endIndex': current_index + len(text)
                    }
                }
                
                if level == 1:
                    requests.append({
                        'updateParagraphStyle': {
                            'paragraphStyle': {
                                'namedStyleType': 'HEADING_1'
                            },
                            'range': style_range['range'],
                            'fields': 'namedStyleType'
                        }
                    })
                elif level == 2:
                    requests.append({
                        'updateParagraphStyle': {
                            'paragraphStyle': {
                                'namedStyleType': 'HEADING_2'
                            },
                            'range': style_range['range'],
                            'fields': 'namedStyleType'
                        }
                    })
                elif level == 3:
                    requests.append({
                        'updateParagraphStyle': {
                            'paragraphStyle': {
                                'namedStyleType': 'HEADING_3'
                            },
                            'range': style_range['range'],
                            'fields': 'namedStyleType'
                        }
                    })
                
                current_index += len(text) + 1
            else:
                # Regular text
                requests.append({
                    'insertText': {
                        'location': {
                            'index': current_index
                        },
                        'text': line + "\n"
                    }
                })
                current_index += len(line) + 1
        
        # Add a section at the end for review comments
        requests.append({
            'insertText': {
                'location': {
                    'index': current_index
                },
                'text': "\n\n--- REVIEW SECTION ---\n\nReviewer: \n\nStatus: [  ] Approved   [  ] Rejected   [  ] Needs Revision\n\nComments:\n\n"
            }
        })
        
        return requests
    
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