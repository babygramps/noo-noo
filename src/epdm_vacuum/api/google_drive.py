"""
Google Drive Uploader - Automatic upload of test data to Google Drive

Uses a service account for headless operation on Raspberry Pi.
Includes a retry queue for handling network failures.
"""

from typing import Optional, Dict, Any, List, Callable
import logging
import threading
import time
import json
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class GoogleDriveUploader:
    """
    Handles uploading test data files to Google Drive.
    
    Features:
    - Service account authentication (no user interaction)
    - Background retry queue for failed uploads
    - Persistent queue that survives restarts
    - Callbacks for upload events (success/failure)
    """
    
    def __init__(
        self,
        credentials_file: str,
        folder_id: str,
        retry_interval_seconds: int = 60,
        max_retries: int = 10,
        data_dir: str = "data",
    ):
        """
        Initialize the Google Drive uploader.
        
        Args:
            credentials_file: Path to service account JSON key file
            folder_id: Google Drive folder ID to upload to
            retry_interval_seconds: Time between retry attempts
            max_retries: Maximum retry attempts before giving up
            data_dir: Directory where test data is stored
        """
        self.credentials_file = Path(credentials_file)
        self.folder_id = folder_id
        self.retry_interval = retry_interval_seconds
        self.max_retries = max_retries
        self.data_dir = Path(data_dir)
        
        # Queue file for persistence
        self._queue_file = self.data_dir / ".upload_queue.json"
        
        # Upload queue: list of {file_path, retries, added_time, last_error}
        self._queue: List[Dict[str, Any]] = []
        self._queue_lock = threading.Lock()
        
        # Google Drive service (lazy initialized)
        self._service = None
        self._service_lock = threading.Lock()
        
        # Background retry thread
        self._retry_thread: Optional[threading.Thread] = None
        self._retry_thread_running = False
        
        # Callbacks
        self._upload_success_callbacks: List[Callable[[str, str], None]] = []
        self._upload_failure_callbacks: List[Callable[[str, str, bool], None]] = []
        
        # Load any pending uploads from disk
        self._load_queue()
        
        logger.info(f"GoogleDriveUploader initialized for folder: {folder_id}")
    
    def _get_service(self):
        """Get or create the Google Drive API service."""
        with self._service_lock:
            if self._service is not None:
                return self._service
            
            try:
                from google.oauth2 import service_account
                from googleapiclient.discovery import build
                
                if not self.credentials_file.exists():
                    logger.error(f"Credentials file not found: {self.credentials_file}")
                    return None
                
                # Load credentials
                # Use full drive scope to allow uploading to shared folders
                credentials = service_account.Credentials.from_service_account_file(
                    str(self.credentials_file),
                    scopes=['https://www.googleapis.com/auth/drive']
                )
                
                # Build service
                self._service = build('drive', 'v3', credentials=credentials)
                logger.info("Google Drive API service initialized")
                return self._service
                
            except ImportError as e:
                logger.error(f"Google API libraries not installed: {e}")
                return None
            except Exception as e:
                logger.error(f"Failed to initialize Google Drive service: {e}")
                return None
    
    def start_retry_loop(self) -> None:
        """Start the background retry loop."""
        if self._retry_thread_running:
            return
        
        self._retry_thread_running = True
        self._retry_thread = threading.Thread(target=self._retry_loop, daemon=True)
        self._retry_thread.start()
        logger.info("Upload retry loop started")
    
    def stop_retry_loop(self) -> None:
        """Stop the background retry loop."""
        self._retry_thread_running = False
        if self._retry_thread:
            self._retry_thread.join(timeout=5.0)
            self._retry_thread = None
        logger.info("Upload retry loop stopped")
    
    def _retry_loop(self) -> None:
        """Background thread that retries failed uploads."""
        while self._retry_thread_running:
            try:
                self._process_queue()
            except Exception as e:
                logger.error(f"Error in retry loop: {e}")
            
            # Wait before next retry cycle
            for _ in range(self.retry_interval):
                if not self._retry_thread_running:
                    break
                time.sleep(1)
    
    def _process_queue(self) -> None:
        """Process pending uploads in the queue."""
        with self._queue_lock:
            if not self._queue:
                return
            
            # Make a copy to iterate
            queue_copy = list(self._queue)
        
        for item in queue_copy:
            if not self._retry_thread_running:
                break
            
            file_path = item["file_path"]
            retries = item.get("retries", 0)
            
            if retries >= self.max_retries:
                logger.warning(f"Max retries reached for {file_path}, removing from queue")
                self._remove_from_queue(file_path)
                self._notify_failure(file_path, "Max retries exceeded", will_retry=False)
                continue
            
            # Try upload
            logger.info(f"Retrying upload: {file_path} (attempt {retries + 1}/{self.max_retries})")
            success, error = self._upload_single_file(file_path)
            
            if success:
                self._remove_from_queue(file_path)
            else:
                self._update_queue_item(file_path, retries + 1, error)
    
    def upload_file(self, file_path: str, folder_id: Optional[str] = None) -> tuple[bool, str]:
        """
        Upload a single file to Google Drive.
        
        Args:
            file_path: Path to file to upload
            folder_id: Optional folder ID (uses default if None)
        
        Returns:
            tuple: (success, file_id_or_error)
        """
        target_folder = folder_id or self.folder_id
        path = Path(file_path)
        
        if not path.exists():
            return False, f"File not found: {file_path}"
        
        service = self._get_service()
        if not service:
            return False, "Google Drive service not available"
        
        try:
            from googleapiclient.http import MediaFileUpload
            
            # Prepare file metadata
            file_metadata = {
                'name': path.name,
                'parents': [target_folder]
            }
            
            # Determine mime type
            mime_type = 'text/csv' if path.suffix == '.csv' else 'application/json'
            
            # Create media upload
            media = MediaFileUpload(
                str(path),
                mimetype=mime_type,
                resumable=True
            )
            
            # Execute upload
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()
            
            file_id = file.get('id')
            web_link = file.get('webViewLink', '')
            
            logger.info(f"Uploaded {path.name} to Google Drive: {file_id}")
            return True, web_link or file_id
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Upload failed for {path.name}: {error_msg}")
            return False, error_msg
    
    def _upload_single_file(self, file_path: str) -> tuple[bool, str]:
        """Internal upload method for retry queue processing."""
        return self.upload_file(file_path)
    
    def upload_test_data(self, csv_path: str) -> tuple[bool, str]:
        """
        Upload test data files (CSV and companion JSON) to Google Drive.
        
        Args:
            csv_path: Path to CSV file (JSON will be found automatically)
        
        Returns:
            tuple: (success, message)
        """
        csv_file = Path(csv_path)
        json_file = csv_file.with_suffix('.json')
        
        results = []
        all_success = True
        
        # Upload CSV
        if csv_file.exists():
            success, result = self.upload_file(str(csv_file))
            if success:
                logger.info(f"CSV uploaded: {csv_file.name}")
                self._notify_success(str(csv_file), result)
            else:
                logger.error(f"CSV upload failed: {result}")
                self._add_to_queue(str(csv_file))
                self._notify_failure(str(csv_file), result, will_retry=True)
                all_success = False
            results.append(f"CSV: {'OK' if success else 'QUEUED'}")
        else:
            logger.warning(f"CSV file not found: {csv_file}")
            results.append("CSV: NOT FOUND")
        
        # Upload JSON
        if json_file.exists():
            success, result = self.upload_file(str(json_file))
            if success:
                logger.info(f"JSON uploaded: {json_file.name}")
                self._notify_success(str(json_file), result)
            else:
                logger.error(f"JSON upload failed: {result}")
                self._add_to_queue(str(json_file))
                self._notify_failure(str(json_file), result, will_retry=True)
                all_success = False
            results.append(f"JSON: {'OK' if success else 'QUEUED'}")
        else:
            logger.warning(f"JSON file not found: {json_file}")
            results.append("JSON: NOT FOUND")
        
        message = ", ".join(results)
        return all_success, message
    
    def _add_to_queue(self, file_path: str) -> None:
        """Add a file to the retry queue."""
        with self._queue_lock:
            # Check if already in queue
            for item in self._queue:
                if item["file_path"] == file_path:
                    return
            
            self._queue.append({
                "file_path": file_path,
                "retries": 0,
                "added_time": datetime.now().isoformat(),
                "last_error": None,
            })
            self._save_queue()
        
        logger.info(f"Added to upload queue: {file_path}")
    
    def _remove_from_queue(self, file_path: str) -> None:
        """Remove a file from the retry queue."""
        with self._queue_lock:
            self._queue = [item for item in self._queue if item["file_path"] != file_path]
            self._save_queue()
        
        logger.info(f"Removed from upload queue: {file_path}")
    
    def _update_queue_item(self, file_path: str, retries: int, error: str) -> None:
        """Update retry count and error for a queue item."""
        with self._queue_lock:
            for item in self._queue:
                if item["file_path"] == file_path:
                    item["retries"] = retries
                    item["last_error"] = error
                    item["last_attempt"] = datetime.now().isoformat()
                    break
            self._save_queue()
    
    def _save_queue(self) -> None:
        """Persist queue to disk."""
        try:
            self._queue_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._queue_file, 'w') as f:
                json.dump(self._queue, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save upload queue: {e}")
    
    def _load_queue(self) -> None:
        """Load queue from disk."""
        try:
            if self._queue_file.exists():
                with open(self._queue_file, 'r') as f:
                    self._queue = json.load(f)
                logger.info(f"Loaded {len(self._queue)} pending uploads from queue")
        except Exception as e:
            logger.error(f"Failed to load upload queue: {e}")
            self._queue = []
    
    def get_pending_uploads(self) -> List[Dict[str, Any]]:
        """Get list of pending uploads."""
        with self._queue_lock:
            return list(self._queue)
    
    def get_status(self) -> Dict[str, Any]:
        """Get uploader status."""
        with self._queue_lock:
            pending = len(self._queue)
        
        return {
            "enabled": True,
            "folder_id": self.folder_id,
            "retry_thread_running": self._retry_thread_running,
            "pending_uploads": pending,
            "service_initialized": self._service is not None,
            "credentials_file_exists": self.credentials_file.exists(),
        }
    
    def force_retry(self) -> tuple[bool, str]:
        """Force immediate retry of all pending uploads."""
        with self._queue_lock:
            count = len(self._queue)
        
        if count == 0:
            return True, "No pending uploads"
        
        # Process queue immediately in a new thread
        thread = threading.Thread(target=self._process_queue, daemon=True)
        thread.start()
        
        return True, f"Retrying {count} pending uploads"
    
    def manual_upload(self, filename: str) -> tuple[bool, str]:
        """
        Manually upload a file from the data directory.
        
        Args:
            filename: Name of file in data directory
        
        Returns:
            tuple: (success, message)
        """
        file_path = self.data_dir / filename
        if not file_path.exists():
            return False, f"File not found: {filename}"
        
        # Upload with companion JSON if CSV
        if file_path.suffix == '.csv':
            return self.upload_test_data(str(file_path))
        else:
            success, result = self.upload_file(str(file_path))
            if success:
                self._notify_success(str(file_path), result)
            else:
                self._notify_failure(str(file_path), result, will_retry=False)
            return success, result
    
    # === Callback Management ===
    
    def add_success_callback(self, callback: Callable[[str, str], None]) -> None:
        """Add callback for successful uploads. Args: (filename, drive_url)"""
        self._upload_success_callbacks.append(callback)
    
    def add_failure_callback(self, callback: Callable[[str, str, bool], None]) -> None:
        """Add callback for failed uploads. Args: (filename, error, will_retry)"""
        self._upload_failure_callbacks.append(callback)
    
    def _notify_success(self, file_path: str, drive_url: str) -> None:
        """Notify callbacks of successful upload."""
        filename = Path(file_path).name
        for callback in self._upload_success_callbacks:
            try:
                callback(filename, drive_url)
            except Exception as e:
                logger.error(f"Upload success callback error: {e}")
    
    def _notify_failure(self, file_path: str, error: str, will_retry: bool) -> None:
        """Notify callbacks of failed upload."""
        filename = Path(file_path).name
        for callback in self._upload_failure_callbacks:
            try:
                callback(filename, error, will_retry)
            except Exception as e:
                logger.error(f"Upload failure callback error: {e}")


def create_uploader_from_config(config: Dict[str, Any]) -> Optional[GoogleDriveUploader]:
    """
    Create a GoogleDriveUploader from configuration dictionary.
    
    Args:
        config: Configuration dict with google_drive section
    
    Returns:
        GoogleDriveUploader or None if disabled/invalid config
    """
    drive_config = config.get("google_drive", {})
    
    if not drive_config.get("enabled", False):
        logger.info("Google Drive upload disabled in config")
        return None
    
    folder_id = drive_config.get("folder_id")
    credentials_file = drive_config.get("credentials_file")
    
    if not folder_id or not credentials_file:
        logger.error("Google Drive config missing folder_id or credentials_file")
        return None
    
    return GoogleDriveUploader(
        credentials_file=credentials_file,
        folder_id=folder_id,
        retry_interval_seconds=drive_config.get("retry_interval_seconds", 60),
        max_retries=drive_config.get("max_retries", 10),
        data_dir=drive_config.get("data_dir", "data"),
    )

