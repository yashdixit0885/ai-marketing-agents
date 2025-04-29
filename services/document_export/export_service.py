import os
import logging
from typing import Dict, List, Optional, Union
from datetime import datetime
from models.content_models import Article, SocialPost, Visual
from services.api_clients.google_docs_client import GoogleDocsClient
from config.settings import settings

logger = logging.getLogger(__name__)

class DocumentExportService:
    """Service for exporting content to Google Docs."""
    
    def __init__(self):
        """Initialize the document export service."""
        self.docs_client = GoogleDocsClient()
    
    async def export_article_to_docs(self, article_id: int, reviewer_email: Optional[str] = None) -> Dict:
        """Export an article and its associated content to Google Docs.
        
        Args:
            article_id: The ID of the article to export
            reviewer_email: Email address of the reviewer to share the document with
            
        Returns:
            Document metadata including the ID and URL
        """
        from models import db_session
        
        # Get the article and associated content
        article = db_session.get(Article, article_id)
        if not article:
            raise ValueError(f"Article with ID {article_id} not found")
        
        # Get social posts
        social_posts = db_session.query(SocialPost).filter_by(article_id=article_id).all()
        
        # Get visuals
        visuals = db_session.query(Visual).filter_by(article_id=article_id).all()
        
        # Create Google Doc
        timestamp = datetime.now().strftime("%Y-%m-%d")
        doc_title = f"[REVIEW] {article.title} - {timestamp}"
        document = self.docs_client.create_document(doc_title)
        doc_id = document.get('documentId')
        
        # Format content for the document
        content_requests = self._format_article_content(article, social_posts, visuals)
        
        # Update document with formatted content
        self.docs_client.update_document(doc_id, content_requests)
        
        # Add approval form
        self.docs_client.add_approval_form(doc_id)
        
        # Share with reviewer if specified
        if reviewer_email:
            self.docs_client.share_document(doc_id, reviewer_email)
        
        # Update article status to indicate it's been sent for review
        article.review_status = "pending"
        article.review_date = None
        article.review_comments = None
        article.reviewed_by = None
        db_session.commit()
        
        # Return document metadata
        return {
            'document_id': doc_id,
            'title': doc_title,
            'url': f"https://docs.google.com/document/d/{doc_id}/edit",
            'review_status': article.review_status
        }
    
    def _format_article_content(self, article, social_posts, visuals) -> List[Dict]:
        """Format article content for Google Docs.
        
        Args:
            article: The article object
            social_posts: List of social posts associated with the article
            visuals: List of visuals associated with the article
            
        Returns:
            List of Google Docs API requests for formatting the document
        """
        requests = []
        
        # Start with a clean document (just keep the title)
        requests.append({
            'insertText': {
                'location': {
                    'index': 1
                },
                'text': article.title
            }
        })
        
        # Format title as heading
        requests.append({
            'updateParagraphStyle': {
                'range': {
                    'startIndex': 1,
                    'endIndex': 1 + len(article.title)
                },
                'paragraphStyle': {
                    'namedStyleType': 'HEADING_1'
                },
                'fields': 'namedStyleType'
            }
        })
        
        # Add metadata section
        metadata_text = f"\n\nArticle ID: {article.id}\n"
        metadata_text += f"Word Count: {article.word_count}\n"
        metadata_text += f"Created: {article.created_at}\n\n"
        
        requests.append({
            'insertText': {
                'location': {
                    'index': 1 + len(article.title)
                },
                'text': metadata_text
            }
        })
        
        # Add horizontal line separator
        current_index = 1 + len(article.title) + len(metadata_text)
        requests.append({
            'insertText': {
                'location': {
                    'index': current_index
                },
                'text': "------------------------------------------------\n\n"
            }
        })
        
        current_index += 50  # Approximate length of separator
        
        # Add main article content
        requests.append({
            'insertText': {
                'location': {
                    'index': current_index
                },
                'text': article.content + "\n\n"
            }
        })
        
        current_index += len(article.content) + 2
        
        # Add section for social media posts
        if social_posts:
            social_header = "=== SOCIAL MEDIA CONTENT ===\n\n"
            requests.append({
                'insertText': {
                    'location': {
                        'index': current_index
                    },
                    'text': social_header
                }
            })
            
            # Format as heading
            requests.append({
                'updateParagraphStyle': {
                    'range': {
                        'startIndex': current_index,
                        'endIndex': current_index + len(social_header)
                    },
                    'paragraphStyle': {
                        'namedStyleType': 'HEADING_2'
                    },
                    'fields': 'namedStyleType'
                }
            })
            
            current_index += len(social_header)
            
            # Add each social post
            for post in social_posts:
                post_text = f"--- {post.platform.upper()} ---\n"
                post_text += post.content + "\n\n"
                
                requests.append({
                    'insertText': {
                        'location': {
                            'index': current_index
                        },
                        'text': post_text
                    }
                })
                
                # Format platform name as bold
                requests.append({
                    'updateTextStyle': {
                        'range': {
                            'startIndex': current_index,
                            'endIndex': current_index + len(f"--- {post.platform.upper()} ---")
                        },
                        'textStyle': {
                            'bold': True
                        },
                        'fields': 'bold'
                    }
                })
                
                current_index += len(post_text)
        
        # Add section for visual references
        if visuals:
            visual_header = "=== VISUAL CONTENT ===\n\n"
            requests.append({
                'insertText': {
                    'location': {
                        'index': current_index
                    },
                    'text': visual_header
                }
            })
            
            # Format as heading
            requests.append({
                'updateParagraphStyle': {
                    'range': {
                        'startIndex': current_index,
                        'endIndex': current_index + len(visual_header)
                    },
                    'paragraphStyle': {
                        'namedStyleType': 'HEADING_2'
                    },
                    'fields': 'namedStyleType'
                }
            })
            
            current_index += len(visual_header)
            
            # Add each visual reference
            for visual in visuals:
                visual_text = f"--- {visual.type.upper()}: {visual.title} ---\n"
                visual_text += f"File: {visual.file_path}\n\n"
                
                requests.append({
                    'insertText': {
                        'location': {
                            'index': current_index
                        },
                        'text': visual_text
                    }
                })
                
                # Format visual type as bold
                requests.append({
                    'updateTextStyle': {
                        'range': {
                            'startIndex': current_index,
                            'endIndex': current_index + len(f"--- {visual.type.upper()}: {visual.title} ---")
                        },
                        'textStyle': {
                            'bold': True
                        },
                        'fields': 'bold'
                    }
                })
                
                current_index += len(visual_text)
        
        return requests