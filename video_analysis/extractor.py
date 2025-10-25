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

    def convert_to_gif(
        self,
        input_video: str,
        output_gif: str,
        max_size_mb: float = 4.0,
        fps: int = 10,
        width: int = 480,
    ) -> bool:
        """Convert a video to an optimized GIF

        Args:
            input_video: Path to input video file
            output_gif: Path for output GIF file
            max_size_mb: Target max size in MB (will reduce quality if needed)
            fps: Frames per second for GIF (default: 10)
            width: Width in pixels (height auto-scaled, default: 480)

        Returns:
            True if conversion succeeded, False otherwise
        """
        try:
            # Two-pass ffmpeg for optimized GIF with palette
            palette_path = output_gif.replace('.gif', '_palette.png')

            # First pass: generate palette
            palette_cmd = [
                "ffmpeg",
                "-i",
                input_video,
                "-vf",
                f"fps={fps},scale={width}:-1:flags=lanczos,palettegen",
                "-y",
                palette_path,
            ]

            logger.info(f"Generating palette for GIF optimization...")
            subprocess.run(palette_cmd, capture_output=True, text=True, check=True)

            # Second pass: create GIF using palette
            gif_cmd = [
                "ffmpeg",
                "-i",
                input_video,
                "-i",
                palette_path,
                "-lavfi",
                f"fps={fps},scale={width}:-1:flags=lanczos[x];[x][1:v]paletteuse",
                "-y",
                output_gif,
            ]

            logger.info(f"Converting to GIF: {output_gif}")
            subprocess.run(gif_cmd, capture_output=True, text=True, check=True)

            # Clean up palette
            if os.path.exists(palette_path):
                os.remove(palette_path)

            # Check file size and reduce quality if needed
            file_size_mb = os.path.getsize(output_gif) / (1024 * 1024)

            if file_size_mb > max_size_mb:
                logger.warning(f"GIF size {file_size_mb:.2f}MB exceeds {max_size_mb}MB, reducing quality...")

                # Reduce width and try again
                new_width = int(width * 0.75)
                temp_gif = output_gif.replace('.gif', '_temp.gif')

                # Regenerate palette with smaller size
                palette_cmd[3] = f"fps={fps},scale={new_width}:-1:flags=lanczos,palettegen"
                subprocess.run(palette_cmd, capture_output=True, text=True, check=True)

                # Regenerate GIF with smaller size
                gif_cmd[5] = f"fps={fps},scale={new_width}:-1:flags=lanczos[x];[x][1:v]paletteuse"
                gif_cmd[-1] = temp_gif
                subprocess.run(gif_cmd, capture_output=True, text=True, check=True)

                # Replace original
                os.replace(temp_gif, output_gif)

                # Clean up palette
                if os.path.exists(palette_path):
                    os.remove(palette_path)

                file_size_mb = os.path.getsize(output_gif) / (1024 * 1024)
                logger.info(f"Reduced GIF size to {file_size_mb:.2f}MB")

            logger.info(f"Successfully created GIF: {output_gif} ({file_size_mb:.2f}MB)")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"ffmpeg error during GIF conversion: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Error converting to GIF: {e}")
            return False

    def extract_all_segments_as_gifs(
        self,
        input_video: str,
        segments: List[VideoSegment],
        output_dir: str,
        prefix: str = "segment",
        padding_seconds: float = 1.0,
        max_size_mb: float = 4.0,
        fps: int = 10,
        width: int = 480,
    ) -> List[str]:
        """Extract all video segments as GIFs

        Args:
            input_video: Path to input video file
            segments: List of VideoSegment objects
            output_dir: Directory to save extracted GIFs
            prefix: Prefix for output filenames
            padding_seconds: Seconds to add before/after each segment (default: 1.0)
            max_size_mb: Target max size in MB per GIF (default: 4.0)
            fps: Frames per second for GIF (default: 10)
            width: Width in pixels (default: 480)

        Returns:
            List of paths to successfully created GIFs
        """
        # First extract video segments
        temp_dir = Path(output_dir) / "_temp_videos"
        temp_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Extracting video segments for GIF conversion...")
        video_segments = self.extract_all_segments(
            input_video,
            segments,
            str(temp_dir),
            prefix=prefix,
            overwrite=True,
            padding_seconds=padding_seconds,
        )

        # Convert each to GIF
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        gif_files = []

        for video_path in video_segments:
            gif_path = str(Path(output_dir) / Path(video_path).stem) + ".gif"

            if self.convert_to_gif(video_path, gif_path, max_size_mb, fps, width):
                gif_files.append(gif_path)

        # Clean up temp videos
        import shutil

        shutil.rmtree(temp_dir)

        logger.info(f"Created {len(gif_files)}/{len(segments)} GIFs in {output_dir}")
        return gif_files
