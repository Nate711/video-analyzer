#!/usr/bin/env python3
"""Core video analysis functionality using Gemini 2.5 Flash API"""

import json
import time
import logging
from typing import List
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class VideoSegment:
    """Represents a video segment with timing and description"""

    def __init__(self, start_time: str, end_time: str, activity: str, description: str = ""):
        self.start_time = start_time
        self.end_time = end_time
        self.activity = activity
        self.description = description

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "activity": self.activity,
            "description": self.description,
        }


class VideoAnalyzer:
    """Handles video analysis using Gemini API"""

    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model_id = "gemini-2.5-flash"

    def analyze_video_segments(self, video_path: str, prompt: str) -> List[VideoSegment]:
        """Analyze video and return activity segments with timestamps

        Args:
            video_path: Path to the video file
            prompt: Analysis prompt to send to Gemini

        Returns:
            List of VideoSegment objects
        """

        logger.info(f"Uploading video: {video_path}")
        video_file = self.client.files.upload(file=video_path)

        while video_file.state.name == "PROCESSING":
            logger.info("Waiting for video processing...")
            time.sleep(2)
            video_file = self.client.files.get(name=video_file.name)

        logger.info(f"Video uploaded successfully (File ID: {video_file.name})")
        logger.info("Analyzing video to identify key parts...")

        response = self.client.models.generate_content(model=self.model_id, contents=[video_file, prompt])

        # Parse JSON response
        response_text = response.text.strip()

        # Remove markdown code blocks if present
        if response_text.startswith("```json"):
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif response_text.startswith("```"):
            response_text = response_text.split("```")[1].split("```")[0].strip()

        segments_data = json.loads(response_text)
        segments = [
            VideoSegment(
                start_time=seg["start_time"],
                end_time=seg["end_time"],
                activity=seg["activity"],
                description=seg.get("description", ""),
            )
            for seg in segments_data
        ]

        logger.info(f"Found {len(segments)} segments")
        return segments
