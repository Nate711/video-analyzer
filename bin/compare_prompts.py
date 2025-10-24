#!/usr/bin/env python3
"""Compare different prompts for video analysis and extract segments"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from google import genai

# Add parent directory to path for local imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from video_analysis.core import VideoSegment, parse_segments_response
from video_analysis.extractor import VideoExtractor
from video_analysis.prompts import PROMPTS, list_prompts
from video_analysis.video_db import VideoDatabase

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def save_analysis_results(prompt_name: str, segments: list, output_dir: str, video_info: dict = None):
    """Save analysis results to JSON file

    Args:
        prompt_name: Name of the prompt used
        segments: List of VideoSegment objects
        output_dir: Directory to save results
        video_info: Optional video information from database
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    results = {
        "prompt_name": prompt_name,
        "timestamp": datetime.now().isoformat(),
        "segment_count": len(segments),
        "segments": [seg.to_dict() for seg in segments],
    }

    if video_info:
        results["video_info"] = {
            "id": video_info.get("id"),
            "display_name": video_info.get("display_name"),
            "local_path": video_info.get("local_path"),
        }

    output_file = Path(output_dir) / f"{prompt_name}_analysis.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    logger.info(f"Saved analysis results to {output_file}")


def format_time_remaining(td):
    """Format timedelta for display"""
    if td.total_seconds() < 0:
        return "EXPIRED"

    hours = int(td.total_seconds() // 3600)
    minutes = int((td.total_seconds() % 3600) // 60)

    if hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"


def select_video_interactive(db: VideoDatabase, client: genai.Client) -> dict:
    """Interactive video selection from database

    Args:
        db: VideoDatabase instance
        client: Gemini client for checking file status

    Returns:
        Selected video entry
    """
    videos = db.list_videos()

    if not videos:
        logger.error("No videos in database. Upload a video first using: python bin/manage_videos.py upload <path>")
        sys.exit(1)

    print("\nAvailable videos:")
    print("=" * 120)

    active_videos = []
    for video in videos:
        is_expired = db.is_expired(video)
        time_remaining = db.get_time_until_expiry(video)

        # Check if file exists
        exists = db.check_file_exists(video, client)

        if not is_expired and exists:
            status = f"✓ Active ({format_time_remaining(time_remaining)})"
            active_videos.append(video)
        elif is_expired:
            status = "✗ EXPIRED"
        elif not exists:
            status = "✗ File not found in API"
        else:
            status = "?"

        print(f"\n[{video['id']}] {video['display_name']} - {status}")
        print(f"    Path: {video['local_path']}")
        print(f"    Uploaded: {video['uploaded_at']}")
        if video['description']:
            print(f"    Description: {video['description']}")

    print("=" * 120)

    if not active_videos:
        logger.error("No active videos available. Upload a new video or check status.")
        sys.exit(1)

    while True:
        try:
            choice = input("\nEnter video ID to use: ").strip()
            video_id = int(choice)
            video = db.get_video(video_id)

            if not video:
                print(f"Video ID {video_id} not found. Please try again.")
                continue

            # Validate video is usable
            if db.is_expired(video):
                print(f"Video ID {video_id} has expired. Please choose an active video.")
                continue

            if not db.check_file_exists(video, client):
                print(f"Video ID {video_id} file not found in Gemini API. Please choose another video.")
                continue

            return video

        except ValueError:
            print("Invalid input. Please enter a numeric ID.")
        except KeyboardInterrupt:
            print("\nCancelled.")
            sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        description="Compare different prompts for video analysis and extract segments"
    )
    parser.add_argument(
        "video_source",
        nargs="?",
        help="Video ID from database or path to video file. Omit for interactive selection.",
    )
    parser.add_argument(
        "--db", default="videos.json", help="Path to video database JSON file (default: videos.json)"
    )
    parser.add_argument(
        "--prompts",
        nargs="+",
        choices=list_prompts(),
        help=f"Specific prompts to test (default: all). Available: {', '.join(list_prompts())}",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Base output directory for results and video segments (default: output)",
    )
    parser.add_argument(
        "--extract-videos",
        action="store_true",
        help="Extract video segments to separate files using ffmpeg",
    )
    parser.add_argument(
        "--skip-analysis",
        action="store_true",
        help="Skip analysis and only extract videos from existing JSON results",
    )

    args = parser.parse_args()

    # Initialize database
    db = VideoDatabase(args.db)

    # Determine video source
    video_info = None
    video_path = None
    gemini_file = None

    # Get API key early for validation
    api_key = None
    client = None
    if not args.skip_analysis:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY not set in .env file")
            logger.info("Get your API key from: https://aistudio.google.com/app/apikey")
            sys.exit(1)
        client = genai.Client(api_key=api_key)

    if args.video_source:
        # Parse as video ID
        try:
            video_id = int(args.video_source)
            video_info = db.get_video(video_id)
            if not video_info:
                logger.error(f"Video ID {video_id} not found in database")
                sys.exit(1)

            # Validate video is not expired and file exists
            if not args.skip_analysis:
                if db.is_expired(video_info):
                    logger.error(f"Video ID {video_id} has expired. Please upload a new video or use a different one.")
                    sys.exit(1)

                if not db.check_file_exists(video_info, client):
                    logger.error(f"Video ID {video_id} file not found in Gemini API. The file may have been deleted.")
                    logger.info("Try re-uploading the video with: python bin/manage_videos.py upload <path>")
                    sys.exit(1)

            video_path = video_info["local_path"]
            gemini_file = video_info["file_name"]
            time_remaining = db.get_time_until_expiry(video_info)
            logger.info(
                f"Using uploaded video: {video_info['display_name']} (ID: {video_id}) - {format_time_remaining(time_remaining)} remaining"
            )
        except ValueError:
            logger.error(f"Invalid video ID: {args.video_source}. Must be a numeric ID from the database.")
            logger.info("Upload a video first with: python bin/manage_videos.py upload <path>")
            sys.exit(1)
    else:
        # Interactive selection (requires client for validation)
        if not client:
            logger.error("Interactive selection requires API key for validation")
            sys.exit(1)
        video_info = select_video_interactive(db, client)
        video_path = video_info["local_path"]
        gemini_file = video_info["file_name"]
        logger.info(f"Selected video: {video_info['display_name']} (ID: {video_info['id']})")

    # Determine which prompts to test
    prompts_to_test = args.prompts if args.prompts else list_prompts()

    logger.info(f"Testing {len(prompts_to_test)} prompts: {', '.join(prompts_to_test)}")

    # Initialize extractor
    extractor = VideoExtractor() if args.extract_videos else None

    for prompt_name in prompts_to_test:
        logger.info(f"\n{'=' * 80}")
        logger.info(f"Testing prompt: {prompt_name}")
        logger.info(f"{'=' * 80}")

        # Create output directory with video name if available
        if video_info:
            prompt_output_dir = Path(args.output_dir) / video_info["display_name"] / prompt_name
        else:
            prompt_output_dir = Path(args.output_dir) / Path(video_path).stem / prompt_name

        try:
            # Analyze or load existing results
            if args.skip_analysis:
                # Load existing analysis results
                analysis_file = prompt_output_dir / f"{prompt_name}_analysis.json"
                if not analysis_file.exists():
                    logger.error(f"Analysis file not found: {analysis_file}")
                    continue

                with open(analysis_file, "r") as f:
                    results = json.load(f)
                    segments = [VideoSegment(**seg) for seg in results["segments"]]
                    logger.info(f"Loaded {len(segments)} segments from {analysis_file}")
            else:
                # Analyze video with current prompt
                prompt = PROMPTS[prompt_name]

                # Use pre-uploaded file
                logger.info(f"Using pre-uploaded Gemini file: {gemini_file} (sampling at 2 FPS)")
                from google.genai import types

                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=types.Content(
                        parts=[
                            types.Part(
                                file_data=types.FileData(file_uri=f"https://generativelanguage.googleapis.com/v1beta/{gemini_file}"),
                                video_metadata=types.VideoMetadata(fps=2),
                            ),
                            types.Part(text=prompt),
                        ]
                    ),
                )

                # Parse response using shared utility
                segments = parse_segments_response(response.text)

                # Save analysis results
                save_analysis_results(prompt_name, segments, prompt_output_dir, video_info)

                # Display segments
                print(f"\nResults for prompt '{prompt_name}':")
                print("-" * 80)
                for i, seg in enumerate(segments, 1):
                    print(f"\n{i}. {seg.activity}")
                    print(f"   Timestamp: {seg.start_time} - {seg.end_time}")
                    if seg.description:
                        print(f"   {seg.description}")

            # Extract video segments if requested
            if args.extract_videos and segments:
                videos_dir = prompt_output_dir / "videos"
                logger.info(f"\nExtracting video segments to {videos_dir}")

                extracted = extractor.extract_all_segments(
                    video_path,
                    segments,
                    str(videos_dir),
                    prefix=prompt_name,
                    overwrite=True,
                )

                logger.info(f"Extracted {len(extracted)} video segments")

        except Exception as e:
            logger.exception(f"Error processing prompt '{prompt_name}': {e}")
            continue

    # Summary
    logger.info(f"\n{'=' * 80}")
    logger.info("COMPARISON COMPLETE")
    logger.info(f"{'=' * 80}")
    logger.info(f"Results saved to: {args.output_dir}")
    logger.info(f"Tested prompts: {', '.join(prompts_to_test)}")

    if args.extract_videos:
        logger.info("\nVideo segments extracted to subdirectories for each prompt")
        logger.info("Compare the extracted clips to evaluate which prompt works best")


if __name__ == "__main__":
    main()
