#!/usr/bin/env python3
"""
Test script for MySalonCast API local Docker deployment.
Tests podcast generation, status polling, and audio retrieval.
"""

import argparse
import json
import requests
import time
import webbrowser
from typing import List

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Test MySalonCast API locally')
    parser.add_argument('--source-urls', required=True, 
                       help='Comma-separated list of source URLs')
    parser.add_argument('--prominent-people', required=True,
                       help='Comma-separated list of prominent people')
    parser.add_argument('--length', required=True,
                       help='Desired podcast length (e.g., "15 minutes")')
    parser.add_argument('--base-url', default='http://localhost:8000',
                       help='Base URL for the API (default: http://localhost:8000)')
    parser.add_argument('--open-browser', action='store_true',
                       help='Open the audio player in browser when complete')
    
    return parser.parse_args()

def create_podcast(base_url: str, source_urls: List[str], prominent_people: List[str], length: str):
    """Create a new podcast via POST request."""
    url = f"{base_url}/generate/podcast_async/"
    payload = {
        "source_urls": source_urls,
        "prominent_persons": prominent_people,
        "desired_podcast_length_str": length
    }
    
    print(f"🚀 Creating podcast with payload:")
    print(json.dumps(payload, indent=2))
    print(f"\nPOST {url}")
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        print(f"✅ Podcast creation started successfully!")
        print(f"Response: {json.dumps(result, indent=2)}")
        
        return result.get('task_id')
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to create podcast: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return None

def poll_status(base_url: str, task_id: str):
    """Poll the status endpoint until completion. Returns task_id when complete."""
    url = f"{base_url}/status/{task_id}"
    print(f"\n🔄 Polling status every 60 seconds...")
    print(f"GET {url}")
    
    while True:
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            status_data = response.json()
            
            current_status = status_data.get('status', 'unknown')
            progress = status_data.get('progress_percentage', 0)
            description = status_data.get('status_description', '')
            
            print(f"\n📊 Status: {current_status} ({progress:.1f}%)")
            if description:
                print(f"Description: {description}")
            
            # Print any logs if available
            logs = status_data.get('logs', [])
            if logs:
                print("Latest logs:")
                for log in logs[-3:]:  # Show last 3 logs
                    print(f"  - {log}")
            
            # Check if completed
            if current_status == 'completed':
                print(f"✅ Podcast generation completed!")
                result_episode = status_data.get('result_episode')
                if result_episode:
                    print(f"Episode title: {result_episode.get('title', 'N/A')}")
                    print(f"Audio filepath: {result_episode.get('audio_filepath', 'N/A')}")
                
                # task_id is used consistently across all endpoints
                return task_id
            
            elif current_status == 'failed':
                print(f"❌ Podcast generation failed!")
                error_msg = status_data.get('error_message', 'Unknown error')
                print(f"Error: {error_msg}")
                return None
            
            elif current_status == 'cancelled':
                print(f"⚠️ Podcast generation was cancelled!")
                return None
            
            # Wait 60 seconds before next poll
            print(f"⏳ Waiting 60 seconds before next status check...")
            time.sleep(60)
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to get status: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            print(f"⏳ Retrying in 60 seconds...")
            time.sleep(60)

def get_audio_player(base_url: str, task_id: str, open_browser: bool = False):
    """Get the audio player page."""
    url = f"{base_url}/podcast/{task_id}/audio"
    print(f"\n🎵 Getting audio player page...")
    print(f"GET {url}")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        print(f"✅ Audio player page retrieved successfully!")
        print(f"Content-Type: {response.headers.get('content-type', 'N/A')}")
        print(f"Content-Length: {len(response.text)} characters")
        print(f"🌐 Audio player URL: {url}")
        
        if open_browser:
            print(f"🚀 Opening audio player in browser...")
            webbrowser.open(url)
        else:
            print(f"💡 You can open this URL in your browser to play the podcast: {url}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to get audio player: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return False

def main():
    """Main test function."""
    args = parse_arguments()
    
    # Parse comma-separated lists
    source_urls = [url.strip() for url in args.source_urls.split(',')]
    prominent_people = [person.strip() for person in args.prominent_people.split(',')]
    
    print(f"🧪 MySalonCast API Local Test")
    print(f"Base URL: {args.base_url}")
    print(f"Source URLs: {source_urls}")
    print(f"Prominent People: {prominent_people}")
    print(f"Podcast Length: {args.length}")
    
    # Step 1: Create podcast
    task_id = create_podcast(args.base_url, source_urls, prominent_people, args.length)
    if not task_id:
        print("❌ Failed to create podcast. Exiting.")
        return
    
    print(f"\n📝 Task ID stored: {task_id}")
    
    # Step 2: Poll status until completion
    completed_task_id = poll_status(args.base_url, task_id)
    if not completed_task_id:
        print("❌ Failed to complete podcast generation. Exiting.")
        return
    
    # Step 3: Get audio player (API now consistently uses task_id)
    success = get_audio_player(args.base_url, completed_task_id, args.open_browser)
    if success:
        print(f"🌐 Audio player URL: {args.base_url}/podcast/{completed_task_id}/audio")
        print(f"💡 You can open this URL in your browser to play the podcast: {args.base_url}/podcast/{completed_task_id}/audio")
        print(f"\n🎉 Test completed successfully!")
    else:
        print(f"\n⚠️ Test completed with audio retrieval issues.")

if __name__ == "__main__":
    main()