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
    
    async def upload_file(self, file_path, name, folder_id=None):
        """Upload a file to Google Drive."""
        try:
            from googleapiclient.http import MediaFileUpload
            
            file_metadata = {
                'name': name,
            }
            
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            media = MediaFileUpload(
                file_path,
                mimetype='application/octet-stream',
                resumable=True
            )
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink, webContentLink'
            ).execute()
            
            # Set file to be publicly accessible for embedding
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }
            
            self.service.permissions().create(
                fileId=file.get('id'),
                body=permission,
                fields='id'
            ).execute()
            
            logger.info(f"Uploaded file: {name} with ID: {file.get('id')}")
            return file.get('id'), file.get('webViewLink'), file.get('webContentLink')
        except Exception as e:
            logger.error(f"Failed to upload file {name}: {str(e)}")
            raise
        
    async def search_files(self, query, folder_id=None):
        """Search for files in Google Drive."""
        try:
            q = query
            if folder_id:
                q = f"{q} and '{folder_id}' in parents"
                
            results = self.service.files().list(
                q=q,
                spaces='drive',
                fields='files(id, name, webViewLink, webContentLink)'
            ).execute()
            
            return results.get('files', [])
        except Exception as e:
            logger.error(f"Failed to search files: {str(e)}")
            raise

    async def find_folder_by_name(self, name, parent_id=None):
        """Find a folder by name."""
        query = f"mimeType='application/vnd.google-apps.folder' and name='{name}'"
        files = await self.search_files(query, parent_id)
        
        if files:
            return files[0].get('id'), files[0].get('webViewLink')
        return None, None

    async def find_doc_by_name(self, name, folder_id=None):
        """Find a document by name."""
        query = f"mimeType='application/vnd.google-apps.document' and name='{name}'"
        files = await self.search_files(query, folder_id)
        
        if files:
            return files[0].get('id'), files[0].get('webViewLink')
        return None, None
    
    async def upload_image(self, image_data, filename, folder_id=None):
        """
        Upload image data to Google Drive.
        
        Args:
            image_data: The binary data of the image
            filename: The name to give the uploaded file
            folder_id: Optional folder ID to place the file in
            
        Returns:
            The file ID of the uploaded image
        """
        try:
            from googleapiclient.http import MediaInMemoryUpload
            import mimetypes
            
            # Determine mimetype from filename
            mime_type, _ = mimetypes.guess_type(filename)
            if not mime_type or not mime_type.startswith('image/'):
                mime_type = 'image/png'  # Default to PNG if can't determine type
            
            file_metadata = {
                'name': filename
            }
            
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            # Create a media upload object from the binary data
            media = MediaInMemoryUpload(
                image_data,
                mimetype=mime_type,
                resumable=True
            )
            
            # Upload the file
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink, webContentLink'
            ).execute()
            
            # Set file to be publicly accessible for embedding
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }
            
            self.service.permissions().create(
                fileId=file.get('id'),
                body=permission,
                fields='id'
            ).execute()
            
            logger.info(f"Uploaded image: {filename} with ID: {file.get('id')}")
            return file.get('id')
            
        except Exception as e:
            logger.error(f"Failed to upload image {filename}: {str(e)}")
            return None