#!/usr/bin/env python3
"""Video analysis CLI tool - original single-prompt version"""

import os
import sys
import logging
import argparse
from dotenv import load_dotenv
from video_analysis.core import VideoAnalyzer

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Default prompt
DEFAULT_PROMPT = """
Analyze this first person view video of someone doing a chore and break it down into distinct parts/segments.

The goal is to use the parts to extract clips showing key moments of the chore being done.

Key points of interest:
- User has difficulty using the tool
- User makes progress e.g. opening a door, picking a piece of clothing, opening a lid, etc

For each segment, provide:
- Start time (MM:SS format)
- End time (MM:SS format)
- Brief activity name (2-5 words)
- Short description (1 sentence)

Return ONLY a JSON array with this structure:
[
  {
    "start_time": "00:00",
    "end_time": "00:15",
    "activity": "Activity Name",
    "description": "What happens in this segment"
  }
]

No text before or after the JSON.
"""


def main():
    parser = argparse.ArgumentParser(
        description="Analyze videos and summarize key parts with timestamps using Gemini AI"
    )
    parser.add_argument("video_path", help="Path to the video file to analyze")

    args = parser.parse_args()

    # Validate video file exists
    if not os.path.exists(args.video_path):
        logger.error(f"Video file not found: {args.video_path}")
        sys.exit(1)

    # Get API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not set in .env file")
        logger.info("Get your API key from: https://aistudio.google.com/app/apikey")
        sys.exit(1)

    # Initialize analyzer
    analyzer = VideoAnalyzer(api_key)

    try:
        # Analyze video
        segments = analyzer.analyze_video_segments(args.video_path, DEFAULT_PROMPT)

        # Display segments
        print("\n" + "=" * 80)
        print("VIDEO SUMMARY - KEY PARTS")
        print("=" * 80)
        for i, seg in enumerate(segments, 1):
            print(f"\n{i}. {seg.activity}")
            print(f"   Timestamp: {seg.start_time} - {seg.end_time}")
            if seg.description:
                print(f"   {seg.description}")
        print("\n" + "=" * 80)

    except Exception as e:
        logger.exception(f"Error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
