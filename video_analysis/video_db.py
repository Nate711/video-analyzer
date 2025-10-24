#!/usr/bin/env python3
"""Video database for tracking uploaded videos"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


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
