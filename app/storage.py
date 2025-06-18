"""Cloud Storage integration for MySalonCast MCP server."""

import os
import logging
import time
from typing import Optional, List, BinaryIO, Dict, Any
from pathlib import Path
from app.config import get_config
from app.storage_utils import (
    parse_gs_url, 
    ensure_directory_exists, 
    log_storage_error,
    validate_storage_available
)

# Import Google Cloud Storage client (optional for local development)
try:
    from google.cloud import storage
    STORAGE_AVAILABLE = True
except ImportError:
    STORAGE_AVAILABLE = False
    logging.warning("Google Cloud Storage not available. Using local file system.")

class StorageManager:
    """Manages file storage with Cloud Storage integration."""
    
    def __init__(self):
        self.config = get_config()
        self.client = None
        
        # Initialize storage client if available and credentials are configured
        # This supports both cloud environments and local environments with cloud credentials
        if STORAGE_AVAILABLE and (
            self.config.is_cloud_environment or 
            (self.config.project_id and self.config.audio_bucket and os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
        ):
            try:
                self.client = storage.Client(project=self.config.project_id)
                logging.info("Google Cloud Storage client initialized")
            except Exception as e:
                logging.warning(f"Failed to initialize Storage client: {e}")
    
    @property
    def is_cloud_storage_available(self) -> bool:
        """Check if Cloud Storage is available and configured."""
        return self.client is not None and self.config.audio_bucket is not None
    
    def get_audio_file_path(self, podcast_id: str, filename: str) -> str:
        """
        Get the path for an audio file based on environment.
        
        Args:
            podcast_id: The podcast identifier
            filename: The audio filename
            
        Returns:
            Local file path or Cloud Storage URL
        """
        if self.config.is_local_environment:
            return f"./outputs/audio/{podcast_id}/{filename}"
        else:
            # Return Cloud Storage URL for cloud environments
            return f"gs://{self.config.audio_bucket}/podcasts/{podcast_id}/audio/{filename}"
    
    def upload_audio_file(self, local_path: str, podcast_id: str, filename: str) -> str:
        """
        Upload an audio file to appropriate storage.
        
        Args:
            local_path: Path to the local file
            podcast_id: The podcast identifier
            filename: The target filename
            
        Returns:
            The final storage path/URL
        """
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Local file not found: {local_path}")
        
        if self.is_cloud_storage_available:
            try:
                bucket = self.client.bucket(self.config.audio_bucket)
                blob_path = f"podcasts/{podcast_id}/audio/{filename}"
                blob = bucket.blob(blob_path)
                
                # Upload with appropriate content type
                content_type = "audio/mpeg" if filename.endswith(".mp3") else "audio/wav"
                blob.upload_from_filename(local_path, content_type=content_type)
                
                # Make blob publicly readable for both cloud and local environments
                blob.make_public()
                public_url = blob.public_url
                
                if not self.config.is_local_environment:
                    logging.info(f"Uploaded audio file to Cloud Storage: {blob_path}")
                    return public_url
                else:
                    # For local development, return the public URL for browser compatibility
                    logging.info(f"Uploaded audio file to Cloud Storage (local dev): {blob_path}")
                    return public_url
                
            except Exception as e:
                logging.error(f"Failed to upload to Cloud Storage: {e}")
                # Fall back to local storage
                pass
        
        # Local storage fallback
        target_dir = f"./outputs/audio/{podcast_id}"
        ensure_directory_exists(target_dir)
        target_path = f"{target_dir}/{filename}"
        
        if local_path != target_path:
            import shutil
            shutil.copy2(local_path, target_path)
        
        logging.info(f"Stored audio file locally: {target_path}")
        return target_path
    
    def download_audio_file(self, storage_path: str, local_path: str) -> bool:
        """
        Download an audio file from storage to local path.
        
        Args:
            storage_path: Storage path (GS URL or local path)
            local_path: Target local path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if storage_path.startswith("gs://"):
                if not validate_storage_available(self, "download"):
                    return False
                
                # Parse GS URL
                parsed = parse_gs_url(storage_path)
                if not parsed:
                    logging.error(f"Invalid GS URL format: {storage_path}")
                    return False
                    
                bucket_name, blob_path = parsed
                
                bucket = self.client.bucket(bucket_name)
                blob = bucket.blob(blob_path)
                
                # Create target directory
                ensure_directory_exists(os.path.dirname(local_path))
                
                blob.download_to_filename(local_path)
                logging.info(f"Downloaded from Cloud Storage: {storage_path}")
                return True
            else:
                # Local file copy
                if os.path.exists(storage_path):
                    ensure_directory_exists(os.path.dirname(local_path))
                    import shutil
                    shutil.copy2(storage_path, local_path)
                    logging.info(f"Copied local file: {storage_path}")
                    return True
                else:
                    logging.warning(f"Local file not found: {storage_path}")
                    return False
                    
        except Exception as e:
            log_storage_error("download audio file", e, storage_path)
            return False
    
    def delete_audio_file(self, storage_path: str) -> bool:
        """
        Delete an audio file from storage.
        
        Args:
            storage_path: Storage path (GS URL or local path)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if storage_path.startswith("gs://"):
                if not validate_storage_available(self, "delete"):
                    return False
                
                parsed = parse_gs_url(storage_path)
                if not parsed:
                    logging.error(f"Invalid GS URL format: {storage_path}")
                    return False
                    
                bucket_name, blob_path = parsed
                
                bucket = self.client.bucket(bucket_name)
                blob = bucket.blob(blob_path)
                blob.delete()
                
                logging.info(f"Deleted from Cloud Storage: {storage_path}")
                return True
            else:
                # Local file deletion
                if os.path.exists(storage_path):
                    os.remove(storage_path)
                    logging.info(f"Deleted local file: {storage_path}")
                    return True
                    
        except Exception as e:
            log_storage_error("delete audio file", e, storage_path)
            return False
    
    def list_podcast_files(self, podcast_id: str) -> List[str]:
        """
        List all files for a podcast.
        
        Args:
            podcast_id: The podcast identifier
            
        Returns:
            List of file paths/URLs
        """
        files = []
        
        try:
            if self.is_cloud_storage_available:
                bucket = self.client.bucket(self.config.audio_bucket)
                prefix = f"podcasts/{podcast_id}/audio/"
                blobs = bucket.list_blobs(prefix=prefix)
                
                for blob in blobs:
                    files.append(f"gs://{self.config.audio_bucket}/{blob.name}")
            else:
                # Local directory listing
                local_dir = f"./outputs/audio/{podcast_id}"
                if os.path.exists(local_dir):
                    for filename in os.listdir(local_dir):
                        files.append(f"{local_dir}/{filename}")
                        
        except Exception as e:
            logging.error(f"Failed to list podcast files: {e}")
        
        return files
    
    def cleanup_old_files(self, days_old: int = 7) -> int:
        """
        Clean up old audio files based on age.
        
        Args:
            days_old: Files older than this many days will be deleted
            
        Returns:
            Number of files deleted
        """
        deleted_count = 0
        
        try:
            from datetime import datetime, timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            if self.is_cloud_storage_available:
                bucket = self.client.bucket(self.config.audio_bucket)
                blobs = bucket.list_blobs(prefix="podcasts/")
                
                for blob in blobs:
                    if blob.time_created < cutoff_date:
                        blob.delete()
                        deleted_count += 1
                        logging.info(f"Deleted old file: {blob.name}")
            else:
                # Local cleanup
                audio_dir = "./outputs/audio"
                if os.path.exists(audio_dir):
                    for root, dirs, files in os.walk(audio_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            file_age = datetime.fromtimestamp(os.path.getmtime(file_path))
                            if file_age < cutoff_date:
                                os.remove(file_path)
                                deleted_count += 1
                                logging.info(f"Deleted old local file: {file_path}")
                                
        except Exception as e:
            logging.error(f"Failed to cleanup old files: {e}")
        
        logging.info(f"Cleanup completed: {deleted_count} files deleted")
        return deleted_count


class CloudStorageManager(StorageManager):
    """Extended storage manager with async methods for podcast workflow integration."""
    
    def __init__(self):
        super().__init__()
        # Simple in-memory cache for text files
        self._text_cache = {}
        self._cache_max_size = 50  # Maximum number of cached items
        self._cache_ttl = 300  # Cache TTL in seconds (5 minutes)
    
    def _get_cache_key(self, url: str) -> str:
        """Generate cache key for URL."""
        import hashlib
        return hashlib.md5(url.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """Check if cache entry is still valid."""
        import time
        return time.time() - cache_entry['timestamp'] < self._cache_ttl
    
    def _clean_cache(self):
        """Remove expired entries and enforce size limit."""
        import time
        current_time = time.time()
        
        # Remove expired entries
        expired_keys = [
            key for key, entry in self._text_cache.items()
            if current_time - entry['timestamp'] > self._cache_ttl
        ]
        for key in expired_keys:
            del self._text_cache[key]
        
        # Enforce size limit (remove oldest entries)
        if len(self._text_cache) > self._cache_max_size:
            sorted_items = sorted(
                self._text_cache.items(),
                key=lambda x: x[1]['timestamp']
            )
            # Remove oldest entries to get back to max size
            excess_count = len(self._text_cache) - self._cache_max_size
            for key, _ in sorted_items[:excess_count]:
                del self._text_cache[key]
    
    async def upload_audio_file_async(self, local_path: str, cloud_path: str) -> Optional[str]:
        """
        Upload an audio file to cloud storage asynchronously.
        
        Args:
            local_path: Path to the local file
            cloud_path: Target cloud storage path (e.g., "episodes/task_id/final_podcast.mp3")
            
        Returns:
            Cloud storage URL if successful, None otherwise
        """
        if not os.path.exists(local_path):
            logging.error(f"Local file not found: {local_path}")
            return None
            
        if self.is_cloud_storage_available:
            try:
                bucket = self.client.bucket(self.config.audio_bucket)
                blob = bucket.blob(cloud_path)
                
                # Upload with appropriate content type
                content_type = "audio/mpeg" if local_path.endswith(".mp3") else "audio/wav"
                blob.upload_from_filename(local_path, content_type=content_type)
                
                # Make blob publicly readable for both cloud and local environments
                blob.make_public()
                public_url = blob.public_url
                
                if not self.config.is_local_environment:
                    logging.info(f"Uploaded audio file to Cloud Storage: {cloud_path}")
                    return public_url
                else:
                    # For local development, return the public URL for browser compatibility
                    logging.info(f"Uploaded audio file to Cloud Storage (local dev): {cloud_path}")
                    return public_url
                    
            except Exception as e:
                logging.error(f"Failed to upload audio file to Cloud Storage: {e}")
                return None
        else:
            # In local development without cloud storage, just return the local path
            logging.info(f"Cloud storage not available, keeping local path: {local_path}")
            return local_path
    
    async def upload_audio_segment_async(self, local_path: str) -> Optional[str]:
        """
        Upload an individual audio segment to cloud storage.
        
        Args:
            local_path: Path to the local audio segment file
            
        Returns:
            Cloud storage URL if successful, None otherwise
        """
        if not os.path.exists(local_path):
            logging.error(f"Audio segment file not found: {local_path}")
            return None
            
        # Extract filename and create cloud path
        filename = os.path.basename(local_path)
        # Extract task ID from the path or use timestamp
        import time
        timestamp = int(time.time())
        cloud_path = f"segments/{timestamp}/{filename}"
        
        return await self.upload_audio_file_async(local_path, cloud_path)
    
    async def upload_podcast_episode_async(self, podcast_episode) -> bool:
        """
        Upload podcast episode assets to cloud storage.
        
        Args:
            podcast_episode: PodcastEpisode object with file paths
            
        Returns:
            True if successful, False otherwise
        """
        try:
            success = True
            
            # Upload main audio file if it exists and is a local path
            if (podcast_episode.audio_filepath and 
                os.path.exists(podcast_episode.audio_filepath) and 
                not podcast_episode.audio_filepath.startswith(('http://', 'https://', 'gs://'))):
                
                cloud_url = await self.upload_audio_file_async(
                    podcast_episode.audio_filepath,
                    f"episodes/final/{os.path.basename(podcast_episode.audio_filepath)}"
                )
                if cloud_url:
                    # Update the episode with the cloud URL
                    podcast_episode.audio_filepath = cloud_url
                else:
                    success = False
            
            # Upload individual dialogue turn audio files if they exist
            if hasattr(podcast_episode, 'dialogue_turn_audio_paths') and podcast_episode.dialogue_turn_audio_paths:
                updated_paths = []
                for audio_path in podcast_episode.dialogue_turn_audio_paths:
                    if (os.path.exists(audio_path) and 
                        not audio_path.startswith(('http://', 'https://', 'gs://'))):
                        
                        cloud_url = await self.upload_audio_file_async(
                            audio_path,
                            f"episodes/segments/{os.path.basename(audio_path)}"
                        )
                        updated_paths.append(cloud_url if cloud_url else audio_path)
                    else:
                        updated_paths.append(audio_path)
                
                podcast_episode.dialogue_turn_audio_paths = updated_paths
            
            return success
            
        except Exception as e:
            logging.error(f"Failed to upload podcast episode assets: {e}")
            return False

    async def upload_text_file_async(self, content: str, cloud_path: str, content_type: str = "text/plain") -> Optional[str]:
        """
        Upload text content to cloud storage asynchronously.
        
        Args:
            content: Text content to upload
            cloud_path: Target cloud storage path (e.g., "text/task_id/outline.json")
            content_type: MIME content type (default: "text/plain")
            
        Returns:
            Cloud storage URL if successful, None otherwise
        """
        if not content or not content.strip():
            logging.error("Empty content provided for text file upload")
            return None
            
        if self.is_cloud_storage_available:
            try:
                bucket = self.client.bucket(self.config.audio_bucket)  # Reuse audio bucket for simplicity
                blob = bucket.blob(cloud_path)
                
                # Upload text content with appropriate content type
                blob.upload_from_string(content, content_type=content_type)
                
                # Make blob publicly readable for cloud environments
                if not self.config.is_local_environment:
                    blob.make_public()
                    public_url = blob.public_url
                    logging.info(f"Uploaded text file to Cloud Storage: {cloud_path}")
                    return public_url
                else:
                    # For local development, return the GS URL for consistency
                    gs_url = f"gs://{self.config.audio_bucket}/{cloud_path}"
                    logging.info(f"Uploaded text file to Cloud Storage (local dev): {cloud_path}")
                    return gs_url
                    
            except Exception as e:
                logging.error(f"Failed to upload text file to Cloud Storage: {e}")
                return None
        else:
            # In local development without cloud storage, we need to save locally
            # Create a temporary local file for compatibility
            import tempfile
            import hashlib
            
            # Create a deterministic local path based on cloud_path
            safe_filename = cloud_path.replace("/", "_").replace("\\", "_")
            local_dir = os.path.join(tempfile.gettempdir(), "mysaloncast_text_files")
            ensure_directory_exists(local_dir)
            local_path = os.path.join(local_dir, safe_filename)
            
            try:
                with open(local_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logging.info(f"Cloud storage not available, saved text file locally: {local_path}")
                return local_path
            except Exception as e:
                logging.error(f"Failed to save text file locally: {e}")
                return None

    async def _upload_json_data_async(
        self, 
        data: Dict[str, Any], 
        cloud_path: str, 
        data_type: str
    ) -> Optional[str]:
        """
        Generic method to upload JSON data to cloud storage.
        
        Args:
            data: Data dictionary to serialize as JSON
            cloud_path: Target cloud storage path
            data_type: Type of data for error messages (e.g., "outline", "persona research")
            
        Returns:
            Cloud storage URL if successful, None otherwise
        """
        if not data:
            logging.error(f"Empty {data_type} data provided")
            return None
            
        try:
            import json
            json_content = json.dumps(data, indent=2, ensure_ascii=False)
            
            return await self.upload_text_file_async(
                json_content, 
                cloud_path, 
                content_type="application/json"
            )
            
        except Exception as e:
            logging.error(f"Failed to serialize {data_type} data: {e}")
            return None

    async def upload_outline_async(self, outline_data: Dict[str, Any], task_id: str) -> Optional[str]:
        """
        Upload podcast outline JSON to cloud storage.
        
        Args:
            outline_data: Outline data dictionary
            task_id: Task identifier for organizing files
            
        Returns:
            Cloud storage URL if successful, None otherwise
        """
        cloud_path = f"text/{task_id}/podcast_outline.json"
        return await self._upload_json_data_async(outline_data, cloud_path, "outline")

    async def upload_persona_research_async(self, research_data: Dict[str, Any], task_id: str, person_id: str) -> Optional[str]:
        """
        Upload persona research JSON to cloud storage.
        
        Args:
            research_data: Persona research data dictionary
            task_id: Task identifier for organizing files
            person_id: Person identifier for the research
            
        Returns:
            Cloud storage URL if successful, None otherwise
        """
        cloud_path = f"text/{task_id}/persona_research_{person_id}.json"
        return await self._upload_json_data_async(research_data, cloud_path, "persona research")

    async def download_text_file_async(self, cloud_url: str) -> Optional[str]:
        """
        Download text content from cloud storage or local file.
        
        Args:
            cloud_url: Cloud storage URL or local file path
            
        Returns:
            Text content if successful, None otherwise
        """
        cache_key = self._get_cache_key(cloud_url)
        if cache_key in self._text_cache:
            cache_entry = self._text_cache[cache_key]
            if self._is_cache_valid(cache_entry):
                return cache_entry['content']
        
        try:
            # Handle local file paths
            if not cloud_url.startswith(('http://', 'https://', 'gs://')):
                if os.path.exists(cloud_url):
                    with open(cloud_url, 'r', encoding='utf-8') as f:
                        content = f.read()
                    self._text_cache[cache_key] = {'content': content, 'timestamp': int(time.time())}
                    self._clean_cache()
                    return content
                else:
                    logging.warning(f"Local text file not found: {cloud_url}")
                    return None
            
            # Handle GCS URLs
            if self.is_cloud_storage_available and cloud_url.startswith('gs://'):
                # Extract bucket and blob path from gs:// URL
                gs_path = cloud_url.replace('gs://', '')
                bucket_name, blob_path = gs_path.split('/', 1)
                
                bucket = self.client.bucket(bucket_name)
                blob = bucket.blob(blob_path)
                
                if blob.exists():
                    content = blob.download_as_text(encoding='utf-8')
                    self._text_cache[cache_key] = {'content': content, 'timestamp': int(time.time())}
                    self._clean_cache()
                    logging.info(f"Downloaded text file from Cloud Storage: {blob_path}")
                    return content
                else:
                    logging.warning(f"Text file not found in Cloud Storage: {blob_path}")
                    return None
            
            # Handle HTTP/HTTPS URLs (public URLs)
            if cloud_url.startswith(('http://', 'https://')):
                import urllib.request
                try:
                    with urllib.request.urlopen(cloud_url) as response:
                        content = response.read().decode('utf-8')
                        self._text_cache[cache_key] = {'content': content, 'timestamp': int(time.time())}
                        self._clean_cache()
                        logging.info(f"Downloaded text file from public URL: {cloud_url}")
                        return content
                except Exception as e:
                    logging.error(f"Failed to download from public URL {cloud_url}: {e}")
                    return None
            
            logging.error(f"Unsupported URL format: {cloud_url}")
            return None
            
        except Exception as e:
            logging.error(f"Failed to download text file from {cloud_url}: {e}")
            return None


# Global storage manager instance
_storage_manager = None

def get_storage_manager() -> StorageManager:
    """Get the global storage manager instance."""
    global _storage_manager
    if _storage_manager is None:
        _storage_manager = StorageManager()
    return _storage_manager
