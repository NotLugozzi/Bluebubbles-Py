"""Attachment cache service for storing and retrieving message attachments."""

import os
import hashlib
from typing import Optional, Dict, Any
from pathlib import Path
from ..api.client import BlueBubblesClient


class AttachmentCache:
    """Manages caching of message attachments."""
    
    def __init__(self, cache_dir: str = None):
        """Initialize the attachment cache."""
        if cache_dir is None:
            # Use XDG cache directory or fallback to home
            cache_base = os.environ.get('XDG_CACHE_HOME', 
                                      os.path.expanduser('~/.cache'))
            cache_dir = os.path.join(cache_base, 'bluebubbles', 'attachments')
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache for this session
        self._memory_cache = {}
        self._metadata_cache = {}
    
    def _get_cache_path(self, attachment_guid: str, extension: str = None) -> Path:
        """Get the cache file path for an attachment."""
        # Create a safe filename from the attachment GUID
        safe_name = attachment_guid.replace('/', '_').replace('\\', '_')
        if extension:
            return self.cache_dir / f"{safe_name}.{extension}"
        else:
            return self.cache_dir / safe_name
    
    def get_cached_attachment(self, attachment_guid: str) -> Optional[bytes]:
        """Get cached attachment data if it exists."""
        # Check memory cache first
        if attachment_guid in self._memory_cache:
            return self._memory_cache[attachment_guid]
        
        # Try to find the file with any extension
        base_path = self._get_cache_path(attachment_guid)
        for file_path in self.cache_dir.glob(f"{base_path.name}*"):
            if file_path.is_file():
                try:
                    with open(file_path, 'rb') as f:
                        data = f.read()
                        # Store in memory cache for quick access
                        self._memory_cache[attachment_guid] = data
                        return data
                except Exception:
                    # If file is corrupted, remove it
                    file_path.unlink(missing_ok=True)
        
        return None
    
    def cache_attachment(self, attachment_guid: str, attachment_data: bytes, 
                        metadata: Dict[str, Any] = None):
        """Cache attachment data to disk and memory."""
        if not attachment_data:
            return
        
        # Determine file extension from metadata or MIME type
        extension = None
        if metadata:
            # Try to get extension from filename
            filename = metadata.get('transferName') or metadata.get('name', '')
            if '.' in filename:
                extension = filename.split('.')[-1].lower()
            else:
                # Try to determine from MIME type
                mime_type = metadata.get('mimeType', '')
                if 'image/jpeg' in mime_type:
                    extension = 'jpg'
                elif 'image/png' in mime_type:
                    extension = 'png'
                elif 'image/gif' in mime_type:
                    extension = 'gif'
                elif 'image/webp' in mime_type:
                    extension = 'webp'
                elif 'image/heic' in mime_type:
                    extension = 'heic'
                elif 'video/mp4' in mime_type:
                    extension = 'mp4'
                elif 'video/mov' in mime_type:
                    extension = 'mov'
                elif 'audio/' in mime_type:
                    extension = 'audio'
        
        cache_path = self._get_cache_path(attachment_guid, extension)
        
        try:
            # Save to disk
            with open(cache_path, 'wb') as f:
                f.write(attachment_data)
            
            # Save to memory cache
            self._memory_cache[attachment_guid] = attachment_data
            
            # Cache metadata if provided
            if metadata:
                self._metadata_cache[attachment_guid] = metadata
                
        except Exception as e:
            print(f"Failed to cache attachment {attachment_guid}: {e}")
    
    def get_cached_metadata(self, attachment_guid: str) -> Optional[Dict[str, Any]]:
        """Get cached attachment metadata."""
        return self._metadata_cache.get(attachment_guid)
    
    async def get_attachment(self, client: BlueBubblesClient, attachment_guid: str) -> Optional[bytes]:
        """Get attachment, from cache or by fetching from server."""
        # Try cache first
        cached = self.get_cached_attachment(attachment_guid)
        if cached:
            return cached
        
        # Fetch from server
        try:
            # Get metadata first
            metadata = await client.get_attachment_info(attachment_guid)
            
            # Download the actual attachment
            attachment_data = await client.get_attachment(attachment_guid)
            
            if attachment_data:
                self.cache_attachment(attachment_guid, attachment_data, metadata)
                return attachment_data
        except Exception as e:
            print(f"Failed to fetch attachment {attachment_guid}: {e}")
        
        return None
    
    def clear_cache(self):
        """Clear all cached attachments."""
        # Clear memory cache
        self._memory_cache.clear()
        self._metadata_cache.clear()
        
        # Clear disk cache
        try:
            for file_path in self.cache_dir.glob("*"):
                if file_path.is_file():
                    file_path.unlink()
        except Exception as e:
            print(f"Failed to clear attachment cache: {e}")
    
    def get_attachment_type(self, metadata: Dict[str, Any]) -> str:
        """Determine attachment type from metadata."""
        mime_type = metadata.get('mimeType', '').lower()
        
        if mime_type.startswith('image/'):
            return 'image'
        elif mime_type.startswith('video/'):
            return 'video'
        elif mime_type.startswith('audio/'):
            return 'audio'
        elif 'pdf' in mime_type:
            return 'pdf'
        elif any(doc in mime_type for doc in ['word', 'document', 'text']):
            return 'document'
        else:
            return 'file'
    
    def get_file_size_string(self, size_bytes: int) -> str:
        """Convert file size to human readable string."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
