#!/usr/bin/env python3
"""CLI tool for managing video uploads to Gemini Files API"""

import os
import sys
import time
import logging
import argparse
from pathlib import Path
from dotenv import load_dotenv
from google import genai

# Add parent directory to path for local imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from video_analysis.video_db import VideoDatabase

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def upload_video(args, client: genai.Client, db: VideoDatabase):
    """Upload a video to Gemini Files API"""

    if not os.path.exists(args.video_path):
        logger.error(f"Video file not found: {args.video_path}")
        sys.exit(1)

    # Check if already uploaded
    existing = db.get_video_by_name(args.name or Path(args.video_path).stem)
    if existing and not args.force:
        logger.warning(
            f"Video '{existing['display_name']}' already exists (ID: {existing['id']}). Use --force to re-upload."
        )
        sys.exit(1)

    logger.info(f"Uploading video: {args.video_path}")
    video_file = client.files.upload(file=args.video_path)

    # Wait for processing
    while video_file.state.name == "PROCESSING":
        logger.info("Waiting for video processing...")
        time.sleep(2)
        video_file = client.files.get(name=video_file.name)

    if video_file.state.name != "ACTIVE":
        logger.error(f"Video processing failed: {video_file.state.name}")
        sys.exit(1)

    logger.info(f"Video uploaded successfully")
    logger.info(f"  File ID: {video_file.name}")
    logger.info(f"  URI: {video_file.uri}")

    # Add to database
    video_entry = db.add_video(
        local_path=args.video_path,
        file_id=video_file.name.split("/")[-1],
        file_name=video_file.name,
        display_name=args.name,
        description=args.description,
        metadata={"uri": video_file.uri, "mime_type": video_file.mime_type},
    )

    print(f"\nVideo added to database:")
    print(f"  ID: {video_entry['id']}")
    print(f"  Name: {video_entry['display_name']}")
    print(f"  Gemini File: {video_entry['file_name']}")


def list_videos(args, db: VideoDatabase):
    """List all uploaded videos"""

    videos = db.list_videos()

    if not videos:
        print("No videos in database.")
        return

    print(f"\nUploaded Videos ({len(videos)}):")
    print("=" * 100)

    for video in videos:
        print(f"\nID: {video['id']}")
        print(f"Name: {video['display_name']}")
        print(f"Local Path: {video['local_path']}")
        print(f"Gemini File: {video['file_name']}")
        print(f"Uploaded: {video['uploaded_at']}")
        if video['description']:
            print(f"Description: {video['description']}")
        if args.verbose and video.get('metadata'):
            print(f"Metadata: {video['metadata']}")

    print("=" * 100)


def show_video(args, db: VideoDatabase):
    """Show details of a specific video"""

    video = db.get_video(args.id)

    if not video:
        logger.error(f"Video ID {args.id} not found")
        sys.exit(1)

    print(f"\nVideo Details:")
    print("=" * 100)
    print(f"ID: {video['id']}")
    print(f"Name: {video['display_name']}")
    print(f"Local Path: {video['local_path']}")
    print(f"Gemini File ID: {video['file_id']}")
    print(f"Gemini File Name: {video['file_name']}")
    print(f"Uploaded: {video['uploaded_at']}")
    print(f"Description: {video['description']}")
    print(f"Metadata: {video.get('metadata', {})}")
    print("=" * 100)


def delete_video(args, client: genai.Client, db: VideoDatabase):
    """Delete a video from database and optionally from Gemini"""

    video = db.get_video(args.id)

    if not video:
        logger.error(f"Video ID {args.id} not found")
        sys.exit(1)

    # Delete from Gemini if requested
    if args.delete_remote:
        try:
            logger.info(f"Deleting from Gemini: {video['file_name']}")
            client.files.delete(name=video['file_name'])
            logger.info("Deleted from Gemini Files API")
        except Exception as e:
            logger.warning(f"Failed to delete from Gemini: {e}")

    # Delete from database
    if db.delete_video(args.id):
        logger.info(f"Deleted video '{video['display_name']}' (ID: {args.id}) from database")
    else:
        logger.error(f"Failed to delete video from database")


def update_video(args, db: VideoDatabase):
    """Update video metadata"""

    updates = {}
    if args.name:
        updates["display_name"] = args.name
    if args.description:
        updates["description"] = args.description

    if not updates:
        logger.error("No updates specified. Use --name or --description")
        sys.exit(1)

    if db.update_video(args.id, **updates):
        logger.info(f"Updated video ID {args.id}")
        show_video(argparse.Namespace(id=args.id), db)
    else:
        logger.error(f"Video ID {args.id} not found")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Manage video uploads to Gemini Files API")
    parser.add_argument("--db", default="videos.json", help="Path to video database JSON file (default: videos.json)")

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Upload command
    upload_parser = subparsers.add_parser("upload", help="Upload a video to Gemini Files API")
    upload_parser.add_argument("video_path", help="Path to the video file to upload")
    upload_parser.add_argument("--name", help="Display name for the video (default: filename)")
    upload_parser.add_argument("--description", help="Description of the video")
    upload_parser.add_argument("--force", action="store_true", help="Force re-upload if video already exists")

    # List command
    list_parser = subparsers.add_parser("list", help="List all uploaded videos")
    list_parser.add_argument("--verbose", "-v", action="store_true", help="Show additional metadata")

    # Show command
    show_parser = subparsers.add_parser("show", help="Show details of a specific video")
    show_parser.add_argument("id", type=int, help="Video ID to show")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a video from database")
    delete_parser.add_argument("id", type=int, help="Video ID to delete")
    delete_parser.add_argument(
        "--delete-remote", action="store_true", help="Also delete from Gemini Files API (not just database)"
    )

    # Update command
    update_parser = subparsers.add_parser("update", help="Update video metadata")
    update_parser.add_argument("id", type=int, help="Video ID to update")
    update_parser.add_argument("--name", help="New display name")
    update_parser.add_argument("--description", help="New description")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Initialize database
    db = VideoDatabase(args.db)

    # Initialize Gemini client for commands that need it
    client = None
    if args.command in ["upload", "delete"]:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY not set in .env file")
            logger.info("Get your API key from: https://aistudio.google.com/app/apikey")
            sys.exit(1)
        client = genai.Client(api_key=api_key)

    # Execute command
    if args.command == "upload":
        upload_video(args, client, db)
    elif args.command == "list":
        list_videos(args, db)
    elif args.command == "show":
        show_video(args, db)
    elif args.command == "delete":
        delete_video(args, client, db)
    elif args.command == "update":
        update_video(args, db)


if __name__ == "__main__":
    main()
