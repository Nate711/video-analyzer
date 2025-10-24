#!/usr/bin/env python3
"""Core video analysis functionality using Gemini 2.5 Flash API"""

import json
import logging
from typing import List

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


def parse_segments_response(response_text: str) -> List[VideoSegment]:
    """Parse Gemini API response into VideoSegment objects

    Args:
        response_text: Raw response text from Gemini API

    Returns:
        List of VideoSegment objects
    """
    # Remove markdown code blocks if present
    response_text = response_text.strip()
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

    logger.info(f"Parsed {len(segments)} segments from response")
    return segments
