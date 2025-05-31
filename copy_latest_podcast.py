#!/usr/bin/env python
import os
import shutil
import sys
import glob
import logging
import tempfile
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def find_latest_podcast_temp_dir():
    """Find the most recent podcast job temporary directory"""
    temp_dirs = glob.glob(os.path.join(tempfile.gettempdir(), "podcast_job_*"))
    if not temp_dirs:
        logger.error("No podcast temporary directories found")
        return None
    
    # Sort by creation time (newest first)
    temp_dirs.sort(key=os.path.getctime, reverse=True)
    return temp_dirs[0]

def ensure_output_dirs(podcast_id):
    """Create the necessary output directories for a podcast"""
    base_dir = "./outputs/audio"
    podcast_dir = os.path.join(base_dir, podcast_id)
    segments_dir = os.path.join(podcast_dir, "segments")
    
    os.makedirs(podcast_dir, exist_ok=True)
    os.makedirs(segments_dir, exist_ok=True)
    
    return podcast_dir, segments_dir

def copy_podcast_files(temp_dir, podcast_id=None):
    """Copy podcast files from temporary directory to outputs directory"""
    if not os.path.exists(temp_dir):
        logger.error(f"Temp directory not found: {temp_dir}")
        return False
    
    # Generate podcast ID if not provided
    if not podcast_id:
        podcast_id = str(uuid.uuid4())[:8]
    
    logger.info(f"Copying podcast files from {temp_dir} to outputs/audio/{podcast_id}")
    
    # Create output directories
    podcast_dir, segments_dir = ensure_output_dirs(podcast_id)
    
    # Copy final podcast file
    final_podcast_path = os.path.join(temp_dir, "final_podcast.mp3")
    if os.path.exists(final_podcast_path):
        final_dest = os.path.join(podcast_dir, "final.mp3")
        shutil.copy2(final_podcast_path, final_dest)
        logger.info(f"Copied final podcast to {final_dest}")
    else:
        logger.warning(f"Final podcast not found at {final_podcast_path}")
    
    # Copy segments
    segments_src_dir = os.path.join(temp_dir, "audio_segments")
    if os.path.exists(segments_src_dir) and os.path.isdir(segments_src_dir):
        for filename in os.listdir(segments_src_dir):
            if filename.endswith(".mp3"):
                src_path = os.path.join(segments_src_dir, filename)
                dest_path = os.path.join(segments_dir, filename)
                shutil.copy2(src_path, dest_path)
                logger.info(f"Copied segment {filename}")
    else:
        logger.warning(f"Segments directory not found at {segments_src_dir}")
    
    return podcast_id

def main():
    # Find the latest podcast temp directory
    temp_dir = find_latest_podcast_temp_dir()
    if not temp_dir:
        sys.exit(1)
    
    logger.info(f"Found latest podcast temp directory: {temp_dir}")
    
    # Copy files
    podcast_id = copy_podcast_files(temp_dir)
    if podcast_id:
        logger.info(f"Successfully copied podcast files to outputs/audio/{podcast_id}")
        logger.info(f"You can now access the podcast at: http://localhost:8000/listen/{podcast_id}")
    else:
        logger.error("Failed to copy podcast files")
        sys.exit(1)

if __name__ == "__main__":
    main()
