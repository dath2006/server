import cloudinary
import cloudinary.uploader
import cloudinary.api
from typing import Optional, Dict, Any, BinaryIO
from fastapi import UploadFile
import os
import uuid
import mimetypes
from pathlib import Path
import tempfile
import aiofiles
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class CloudinaryService:
    def __init__(self):
        self._is_configured = False
        self._configure_cloudinary()
    
    def _configure_cloudinary(self):
        """Configure Cloudinary with environment variables"""
        if (settings.cloudinary_cloud_name and 
            settings.cloudinary_api_key and 
            settings.cloudinary_api_secret):
            
            cloudinary.config(
                cloud_name=settings.cloudinary_cloud_name,
                api_key=settings.cloudinary_api_key,
                api_secret=settings.cloudinary_api_secret,
                secure=True
            )
            self._is_configured = True
            logger.info("Cloudinary configured successfully")
        else:
            logger.warning("Cloudinary not configured - missing environment variables")
    
    def is_available(self) -> bool:
        """Check if Cloudinary is properly configured"""
        return self._is_configured
    
    def get_resource_type(self, file_type: str) -> str:
        """Determine Cloudinary resource type based on MIME type"""
        if file_type.startswith('image/'):
            return 'image'
        elif file_type.startswith('video/'):
            return 'video'
        else:
            return 'raw'  # For audio and other file types
    
    def get_upload_folder(self, file_type: str) -> str:
        """Get appropriate folder name based on file type"""
        if file_type.startswith('image/'):
            return 'images'
        elif file_type.startswith('video/'):
            return 'videos'
        elif file_type.startswith('audio/'):
            return 'audio'
        else:
            return 'files'
    
    async def upload_file(
        self, 
        file: UploadFile, 
        folder_prefix: str = "chyrp_lite"
    ) -> Dict[str, Any]:
        """
        Upload file to Cloudinary
        Returns dict with url, secure_url, public_id, resource_type, format, bytes
        """
        if not self.is_available():
            raise ValueError("Cloudinary is not configured")
        
        try:
            # Get file info
            content_type = file.content_type or mimetypes.guess_type(file.filename)[0] or 'application/octet-stream'
            resource_type = self.get_resource_type(content_type)
            folder = self.get_upload_folder(content_type)
            
            # Generate unique public_id
            file_extension = Path(file.filename).suffix.lower() if file.filename else ''
            unique_id = str(uuid.uuid4())
            public_id = f"{folder_prefix}/{folder}/{unique_id}"
            
            # Reset file pointer to beginning
            await file.seek(0)
            
            # Read file content
            file_content = await file.read()
            
            # Upload to Cloudinary
            upload_options = {
                'public_id': public_id,
                'resource_type': resource_type,
                'folder': f"{folder_prefix}/{folder}",
                'use_filename': False,
                'unique_filename': True,
                'overwrite': False,
            }
            
            # Add specific options for different file types
            if resource_type == 'image':
                upload_options.update({
                    'quality': 'auto',
                    'fetch_format': 'auto',
                })
            elif resource_type == 'video':
                upload_options.update({
                    'quality': 'auto',
                })
            
            result = cloudinary.uploader.upload(file_content, **upload_options)
            
            return {
                'url': result.get('secure_url', result.get('url')),
                'public_id': result['public_id'],
                'resource_type': result.get('resource_type', resource_type),
                'format': result.get('format'),
                'bytes': result.get('bytes', 0),
                'width': result.get('width'),
                'height': result.get('height'),
                'duration': result.get('duration'),  # For videos/audio
                'created_at': result.get('created_at'),
                'version': result.get('version'),
                'original_filename': file.filename,
                'content_type': content_type
            }
            
        except Exception as e:
            logger.error(f"Error uploading to Cloudinary: {str(e)}")
            raise Exception(f"Failed to upload to Cloudinary: {str(e)}")
    
    async def delete_file(self, public_id: str, resource_type: str = 'image') -> bool:
        """Delete file from Cloudinary"""
        if not self.is_available():
            return False
        
        try:
            result = cloudinary.uploader.destroy(
                public_id, 
                resource_type=resource_type
            )
            return result.get('result') == 'ok'
        except Exception as e:
            logger.error(f"Error deleting from Cloudinary: {str(e)}")
            return False
    
    def get_optimized_url(
        self, 
        public_id: str, 
        width: Optional[int] = None,
        height: Optional[int] = None,
        quality: str = 'auto',
        format: str = 'auto'
    ) -> str:
        """Get optimized URL for images"""
        if not self.is_available():
            return ""
        
        try:
            transformations = {
                'quality': quality,
                'fetch_format': format
            }
            
            if width:
                transformations['width'] = width
            if height:
                transformations['height'] = height
            
            return cloudinary.CloudinaryImage(public_id).build_url(**transformations)
        except Exception as e:
            logger.error(f"Error building optimized URL: {str(e)}")
            return ""
    
    def get_video_thumbnail(self, public_id: str, width: int = 300) -> str:
        """Get video thumbnail URL"""
        if not self.is_available():
            return ""
        
        try:
            return cloudinary.CloudinaryVideo(public_id).build_url(
                resource_type='video',
                format='jpg',
                width=width,
                quality='auto'
            )
        except Exception as e:
            logger.error(f"Error building video thumbnail URL: {str(e)}")
            return ""


# Global instance
cloudinary_service = CloudinaryService()


async def upload_file_with_fallback(
    file: UploadFile, 
    upload_dir: str = "uploads",
    folder_prefix: str = "chyrp_lite"
) -> tuple[str, Dict[str, Any]]:
    """
    Upload file with Cloudinary as primary and local storage as fallback
    Returns (url, metadata_dict)
    """
    metadata = {
        'is_cloudinary': False,
        'original_filename': file.filename,
        'content_type': file.content_type or 'application/octet-stream',
        'size': 0
    }
    
    # Try Cloudinary first
    if cloudinary_service.is_available():
        try:
            result = await cloudinary_service.upload_file(file, folder_prefix)
            metadata.update({
                'is_cloudinary': True,
                'public_id': result['public_id'],
                'cloudinary_url': result['url'],
                'resource_type': result['resource_type'],
                'format': result.get('format'),
                'size': result.get('bytes', 0),
                'width': result.get('width'),
                'height': result.get('height'),
                'duration': result.get('duration'),
                'version': result.get('version')
            })
            
            logger.info(f"File uploaded to Cloudinary: {result['public_id']}")
            return result['url'], metadata
            
        except Exception as e:
            logger.error(f"Cloudinary upload failed, falling back to local: {str(e)}")
    
    # Fallback to local storage
    try:
        # Reset file pointer
        await file.seek(0)
        
        # Create upload directory
        upload_path = Path(upload_dir)
        upload_path.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        file_extension = Path(file.filename).suffix if file.filename else ''
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = upload_path / unique_filename
        
        # Save file
        content = await file.read()
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        # Build URL (assuming files are served from root)
        file_url = f"/{upload_dir}/{unique_filename}"
        
        metadata.update({
            'local_path': str(file_path),
            'size': len(content)
        })
        
        logger.info(f"File saved locally: {file_path}")
        return file_url, metadata
        
    except Exception as e:
        logger.error(f"Local upload also failed: {str(e)}")
        raise Exception(f"Both Cloudinary and local upload failed: {str(e)}")


async def delete_file_with_fallback(url: str, metadata: Dict[str, Any] = None) -> bool:
    """
    Delete file from Cloudinary or local storage based on metadata
    """
    if not metadata:
        # Try to determine if it's a Cloudinary URL
        if 'cloudinary.com' in url or 'res.cloudinary.com' in url:
            logger.warning("Cannot delete Cloudinary file without public_id")
            return False
        else:
            # Try local deletion
            return await delete_local_file(url)
    
    if metadata.get('is_cloudinary'):
        # Delete from Cloudinary
        public_id = metadata.get('public_id')
        resource_type = metadata.get('resource_type', 'image')
        
        if public_id and cloudinary_service.is_available():
            return await cloudinary_service.delete_file(public_id, resource_type)
        return False
    else:
        # Delete from local storage
        local_path = metadata.get('local_path')
        if local_path and Path(local_path).exists():
            try:
                Path(local_path).unlink()
                return True
            except Exception as e:
                logger.error(f"Error deleting local file {local_path}: {str(e)}")
                return False
        return await delete_local_file(url)


async def delete_local_file(url: str) -> bool:
    """Delete local file from URL"""
    try:
        # Convert URL to local path
        if url.startswith('/'):
            file_path = Path(url[1:])  # Remove leading slash
        else:
            file_path = Path(url)
        
        if file_path.exists():
            file_path.unlink()
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting local file from URL {url}: {str(e)}")
        return False
