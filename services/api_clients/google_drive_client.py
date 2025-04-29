# services/api_clients/google_drive_client.py

import logging
from googleapiclient.discovery import build
from google.oauth2 import service_account
from config.settings import settings

logger = logging.getLogger(__name__)

class GoogleDriveClient:
    """Client for interacting with Google Drive API."""
    
    def __init__(self):
        """Initialize the Google Drive client."""
        try:
            self.credentials = service_account.Credentials.from_service_account_file(
                settings.GOOGLE_APPLICATION_CREDENTIALS,
                scopes=['https://www.googleapis.com/auth/drive.file']
            )
            self.service = build('drive', 'v3', credentials=self.credentials)
            logger.info("Successfully initialized Google Drive client")
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive client: {str(e)}")
            raise
    
    async def create_folder(self, name, parent_id=None):
        """Create a folder in Google Drive."""
        try:
            file_metadata = {
                'name': name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_id:
                file_metadata['parents'] = [parent_id]
            
            folder = self.service.files().create(
                body=file_metadata,
                fields='id, webViewLink'
            ).execute()
            
            logger.info(f"Created folder: {name} with ID: {folder.get('id')}")
            return folder.get('id'), folder.get('webViewLink')
        except Exception as e:
            logger.error(f"Failed to create folder {name}: {str(e)}")
            raise
    
    async def create_doc(self, name, folder_id=None):
        """Create a Google Doc in the specified folder."""
        try:
            file_metadata = {
                'name': name,
                'mimeType': 'application/vnd.google-apps.document'
            }
            
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            file = self.service.files().create(
                body=file_metadata,
                fields='id, webViewLink'
            ).execute()
            
            logger.info(f"Created document: {name} with ID: {file.get('id')}")
            return file.get('id'), file.get('webViewLink')
        except Exception as e:
            logger.error(f"Failed to create document {name}: {str(e)}")
            raise
    
    async def share_file(self, file_id, email, role='writer'):
        """Share a file with a specific user."""
        try:
            permission = {
                'type': 'user',
                'role': role,
                'emailAddress': email
            }
            
            result = self.service.permissions().create(
                fileId=file_id,
                body=permission,
                fields='id',
                sendNotificationEmail=True
            ).execute()
            
            logger.info(f"Shared file {file_id} with {email}")
            return result.get('id')
        except Exception as e:
            logger.error(f"Failed to share file {file_id} with {email}: {str(e)}")
            raise