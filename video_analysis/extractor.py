#!/usr/bin/env python3
"""Video extraction functionality using ffmpeg"""

import os
import subprocess
import logging
from pathlib import Path
from typing import List
from .core import VideoSegment

logger = logging.getLogger(__name__)


class VideoExtractor:
    """Handles extraction of video segments using ffmpeg"""

    @staticmethod
    def time_to_seconds(time_str: str) -> float:
        """Convert MM:SS or HH:MM:SS format to seconds

        Args:
            time_str: Time string in MM:SS or HH:MM:SS format

        Returns:
            Time in seconds as float
        """
        parts = time_str.split(":")
        if len(parts) == 2:  # MM:SS
            minutes, seconds = parts
            return int(minutes) * 60 + float(seconds)
        elif len(parts) == 3:  # HH:MM:SS
            hours, minutes, seconds = parts
            return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        else:
            raise ValueError(f"Invalid time format: {time_str}")

    def extract_segment(
        self,
        input_video: str,
        segment: VideoSegment,
        output_path: str,
        overwrite: bool = False,
        padding_seconds: float = 1.0,
    ) -> bool:
        """Extract a single video segment using ffmpeg

        Args:
            input_video: Path to input video file
            segment: VideoSegment with start_time and end_time
            output_path: Path for output video file
            overwrite: Whether to overwrite existing files
            padding_seconds: Seconds to add before/after segment (default: 1.0)

        Returns:
            True if extraction succeeded, False otherwise
        """
        try:
            start_seconds = self.time_to_seconds(segment.start_time)
            end_seconds = self.time_to_seconds(segment.end_time)

            # Apply padding (ensure start doesn't go negative)
            start_seconds = max(0, start_seconds - padding_seconds)
            end_seconds = end_seconds + padding_seconds

            duration = end_seconds - start_seconds

            # Build ffmpeg command
            cmd = [
                "ffmpeg",
                "-ss",
                str(start_seconds),
                "-i",
                input_video,
                "-t",
                str(duration),
                "-c",
                "copy",  # Copy codec for fast extraction
            ]

            if overwrite:
                cmd.append("-y")

            cmd.append(output_path)

            if padding_seconds > 0:
                logger.info(
                    f"Extracting segment: {segment.start_time} - {segment.end_time} "
                    f"(+{padding_seconds}s padding) to {output_path}"
                )
            else:
                logger.info(f"Extracting segment: {segment.start_time} - {segment.end_time} to {output_path}")

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            logger.info(f"Successfully extracted segment to {output_path}")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"ffmpeg error: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Error extracting segment: {e}")
            return False

    def extract_all_segments(
        self,
        input_video: str,
        segments: List[VideoSegment],
        output_dir: str,
        prefix: str = "segment",
        overwrite: bool = False,
        padding_seconds: float = 1.0,
    ) -> List[str]:
        """Extract all video segments to separate files

        Args:
            input_video: Path to input video file
            segments: List of VideoSegment objects
            output_dir: Directory to save extracted segments
            prefix: Prefix for output filenames
            overwrite: Whether to overwrite existing files
            padding_seconds: Seconds to add before/after each segment (default: 1.0)

        Returns:
            List of paths to successfully extracted segments
        """
        # Create output directory if it doesn't exist
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Get video file extension
        _, ext = os.path.splitext(input_video)

        extracted_files = []

        for i, segment in enumerate(segments, 1):
            # Create safe filename from activity name
            safe_activity = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in segment.activity)
            safe_activity = safe_activity.replace(" ", "_").lower()

            output_filename = f"{prefix}_{i:03d}_{safe_activity}{ext}"
            output_path = os.path.join(output_dir, output_filename)

            if self.extract_segment(input_video, segment, output_path, overwrite, padding_seconds):
                extracted_files.append(output_path)

        logger.info(f"Extracted {len(extracted_files)}/{len(segments)} segments to {output_dir}")
        return extracted_files
