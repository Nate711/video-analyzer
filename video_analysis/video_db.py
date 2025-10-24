#!/usr/bin/env python3
"""Video database for tracking uploaded videos"""

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from google import genai

logger = logging.getLogger(__name__)

# Gemini Files API expiry time (48 hours)
EXPIRY_HOURS = 48


class VideoDatabase:
    """Manages a JSON database of uploaded videos"""

    def __init__(self, db_path: str = "videos.json"):
        self.db_path = Path(db_path)
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        """Create database file if it doesn't exist"""
        if not self.db_path.exists():
            self._save_db({"videos": []})
            logger.info(f"Created new video database at {self.db_path}")

    def _load_db(self) -> Dict:
        """Load database from JSON file"""
        with open(self.db_path, "r") as f:
            return json.load(f)

    def _save_db(self, data: Dict):
        """Save database to JSON file"""
        with open(self.db_path, "w") as f:
            json.dump(data, f, indent=2)

    def add_video(
        self,
        local_path: str,
        file_id: str,
        file_name: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Add a video to the database

        Args:
            local_path: Local path to the video file
            file_id: Gemini file ID
            file_name: Gemini file name (e.g., files/xyz)
            display_name: Optional display name for the video
            description: Optional description
            metadata: Optional additional metadata

        Returns:
            The created video entry
        """
        db = self._load_db()

        # Generate display name if not provided
        if not display_name:
            display_name = Path(local_path).stem

        video_entry = {
            "id": len(db["videos"]) + 1,
            "display_name": display_name,
            "local_path": str(Path(local_path).absolute()),
            "file_id": file_id,
            "file_name": file_name,
            "description": description or "",
            "uploaded_at": datetime.now().isoformat(),
            "metadata": metadata or {},
        }

        db["videos"].append(video_entry)
        self._save_db(db)

        logger.info(f"Added video to database: {display_name} (ID: {video_entry['id']})")
        return video_entry

    def get_video(self, video_id: int) -> Optional[Dict]:
        """Get a video by ID

        Args:
            video_id: Video ID

        Returns:
            Video entry or None if not found
        """
        db = self._load_db()
        for video in db["videos"]:
            if video["id"] == video_id:
                return video
        return None

    def get_video_by_name(self, display_name: str) -> Optional[Dict]:
        """Get a video by display name

        Args:
            display_name: Display name to search for

        Returns:
            Video entry or None if not found
        """
        db = self._load_db()
        for video in db["videos"]:
            if video["display_name"] == display_name:
                return video
        return None

    def list_videos(self) -> List[Dict]:
        """List all videos in the database

        Returns:
            List of video entries
        """
        db = self._load_db()
        return db["videos"]

    def delete_video(self, video_id: int) -> bool:
        """Delete a video from the database

        Args:
            video_id: Video ID to delete

        Returns:
            True if deleted, False if not found
        """
        db = self._load_db()
        original_count = len(db["videos"])
        db["videos"] = [v for v in db["videos"] if v["id"] != video_id]

        if len(db["videos"]) < original_count:
            self._save_db(db)
            logger.info(f"Deleted video ID {video_id} from database")
            return True

        return False

    def update_video(self, video_id: int, **kwargs) -> bool:
        """Update video metadata

        Args:
            video_id: Video ID to update
            **kwargs: Fields to update (display_name, description, metadata)

        Returns:
            True if updated, False if not found
        """
        db = self._load_db()

        for video in db["videos"]:
            if video["id"] == video_id:
                if "display_name" in kwargs:
                    video["display_name"] = kwargs["display_name"]
                if "description" in kwargs:
                    video["description"] = kwargs["description"]
                if "metadata" in kwargs:
                    video["metadata"].update(kwargs["metadata"])

                self._save_db(db)
                logger.info(f"Updated video ID {video_id}")
                return True

        return False

    def get_expiry_time(self, video: Dict) -> datetime:
        """Calculate expiry time for a video

        Args:
            video: Video entry from database

        Returns:
            DateTime when the video expires
        """
        uploaded_at = datetime.fromisoformat(video["uploaded_at"])
        return uploaded_at + timedelta(hours=EXPIRY_HOURS)

    def is_expired(self, video: Dict) -> bool:
        """Check if a video has expired

        Args:
            video: Video entry from database

        Returns:
            True if expired, False otherwise
        """
        expiry_time = self.get_expiry_time(video)
        return datetime.now() > expiry_time

    def get_time_until_expiry(self, video: Dict) -> timedelta:
        """Get time remaining until expiry

        Args:
            video: Video entry from database

        Returns:
            timedelta representing time until expiry (negative if already expired)
        """
        expiry_time = self.get_expiry_time(video)
        return expiry_time - datetime.now()

    def check_file_exists(self, video: Dict, client: genai.Client) -> bool:
        """Check if video file still exists in Gemini Files API

        Args:
            video: Video entry from database
            client: Gemini client instance

        Returns:
            True if file exists, False otherwise
        """
        try:
            file = client.files.get(name=video["file_name"])
            return file.state.name == "ACTIVE"
        except Exception as e:
            logger.debug(f"File check failed for {video['file_name']}: {e}")
            return False

    def mark_as_expired(self, video_id: int) -> bool:
        """Mark a video as expired in metadata

        Args:
            video_id: Video ID to mark as expired

        Returns:
            True if updated, False if not found
        """
        db = self._load_db()

        for video in db["videos"]:
            if video["id"] == video_id:
                video["metadata"]["expired"] = True
                video["metadata"]["expired_at"] = datetime.now().isoformat()
                self._save_db(db)
                logger.info(f"Marked video ID {video_id} as expired")
                return True

        return False

    def cleanup_expired(self, client: Optional[genai.Client] = None) -> Dict[str, List[int]]:
        """Remove expired videos from database

        Args:
            client: Optional Gemini client to verify file existence before deletion

        Returns:
            Dictionary with 'deleted' and 'kept' lists of video IDs
        """
        db = self._load_db()
        to_delete = []
        kept = []

        for video in db["videos"]:
            should_delete = False

            # Check if expired by time
            if self.is_expired(video):
                # If client provided, verify file is actually gone
                if client:
                    if not self.check_file_exists(video, client):
                        should_delete = True
                    else:
                        # File still exists despite being past expiry time
                        logger.info(f"Video ID {video['id']} is past expiry but file still exists")
                        kept.append(video["id"])
                else:
                    # No client, trust expiry time calculation
                    should_delete = True

            if should_delete:
                to_delete.append(video["id"])
            elif video["id"] not in kept:
                kept.append(video["id"])

        # Delete expired videos
        if to_delete:
            db["videos"] = [v for v in db["videos"] if v["id"] not in to_delete]
            self._save_db(db)
            logger.info(f"Cleaned up {len(to_delete)} expired videos")

        return {"deleted": to_delete, "kept": kept}
