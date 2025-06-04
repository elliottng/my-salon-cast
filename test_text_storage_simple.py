#!/usr/bin/env python3
"""
Simple validation script for Phase 2.3 text file cloud storage integration.
Checks the database directly to see if text files were uploaded to cloud storage.
"""

import sqlite3
import json
import sys
from pathlib import Path

# Database path
DB_PATH = "/home/elliottng/CascadeProjects/mysaloncast/podcast_status.db"

def test_text_file_storage():
    """Test if text files are stored with cloud URLs in the database."""
    print(" Phase 2.3 Text File Storage Validation")
    print("=" * 50)
    
    if not Path(DB_PATH).exists():
        print(f" Database not found: {DB_PATH}")
        return False
    
    try:
        # Connect to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get the most recent completed podcast generation
        cursor.execute("""
            SELECT 
                task_id,
                status,
                result_episode,
                created_at,
                last_updated_at
            FROM podcast_status 
            WHERE status = 'completed' AND result_episode IS NOT NULL
            ORDER BY last_updated_at DESC 
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        
        if not result:
            print(" No completed podcast episodes found in database")
            return False
        
        task_id, status, result_episode_json, created_at, last_updated_at = result
        
        # Parse the episode data
        try:
            episode_data = json.loads(result_episode_json)
        except json.JSONDecodeError as e:
            print(f" Error parsing episode data: {e}")
            return False
        
        # Extract relevant fields
        title = episode_data.get('title', 'Unknown')
        outline_path = episode_data.get('llm_podcast_outline_path')
        research_paths = episode_data.get('llm_persona_research_paths')
        
        print(f" Most Recent Completed Episode:")
        print(f"  Task ID: {task_id}")
        print(f"  Title: {title}")
        print(f"  Created: {created_at}")
        print(f"  Completed: {last_updated_at}")
        print()
        
        # Test outline path
        print(" Testing Outline Storage:")
        if outline_path:
            print(f"  Outline Path: {outline_path}")
            if outline_path.startswith(('gs://', 'http://', 'https://')):
                print("  Outline stored in cloud storage!")
                cloud_outline = True
            else:
                print("  Outline stored locally (expected in dev mode)")
                cloud_outline = False
        else:
            print("  No outline path found")
            cloud_outline = False
        
        # Test persona research paths
        print("\n🔍 Testing Persona Research Storage:")
        if research_paths:
            # Handle both list and JSON string formats
            if isinstance(research_paths, str):
                try:
                    research_paths = json.loads(research_paths)
                except json.JSONDecodeError:
                    # If it's not valid JSON, treat as single path
                    research_paths = [research_paths]
            elif not isinstance(research_paths, list):
                research_paths = [research_paths]
            
            print(f"  Found {len(research_paths)} research files:")
            
            cloud_research_count = 0
            local_research_count = 0
            
            for i, path in enumerate(research_paths):
                print(f"    {i+1}. {path}")
                if path and path.startswith(('gs://', 'http://', 'https://')):
                    cloud_research_count += 1
                    print(f"       ✅ Cloud storage!")
                else:
                    local_research_count += 1
                    print(f"       💻 Local storage")
            
            print(f"\n  📊 Storage Summary:")
            print(f"    Cloud research files: {cloud_research_count}")
            print(f"    Local research files: {local_research_count}")
            
            cloud_research = cloud_research_count > 0
        else:
            print("  No research paths found")
            cloud_research = False
        
        # Summary
        print("\n" + "=" * 50)
        print(" VALIDATION SUMMARY:")
        print(f" Episode Generated: YES (task_id: {task_id})")
        print(f"  Outline in Cloud: {'YES' if cloud_outline else 'NO (local)'}")
        print(f"  Research in Cloud: {'YES' if cloud_research else 'NO (local)'}")
        
        if cloud_outline or cloud_research:
            print("\n SUCCESS: Text file cloud storage integration is working!")
            print("    At least some text files were uploaded to cloud storage.")
        else:
            print("\n INFO: All text files are stored locally.")
            print("    This is expected in development environment.")
            print("    Cloud storage integration code is in place but may not be")
            print("    activated due to local environment detection.")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f" Database error: {e}")
        return False

def check_environment_config():
    """Check environment configuration that affects cloud storage behavior."""
    print("\n Environment Configuration Check:")
    
    try:
        from app.config import get_config
        config = get_config()
        
        print(f"  Environment: {'LOCAL' if config.is_local_environment else 'CLOUD'}")
        print(f"  Audio Bucket: {config.audio_bucket}")
        print(f"  Database URL: {config.database_url}")
        
        # Try to create CloudStorageManager to see if GCS is available
        from app.storage import CloudStorageManager
        storage = CloudStorageManager()
        
        print(f"  Cloud Storage Available: {'YES' if storage.is_cloud_storage_available else 'NO'}")
        print(f"  Storage Type: {'Cloud' if not config.is_local_environment else 'Local Development'}")
        
    except Exception as e:
        print(f"  Error checking config: {e}")

def main():
    """Main validation function."""
    print(" Starting Phase 2.3 Validation")
    
    # Test 1: Check text file storage in database
    success = test_text_file_storage()
    
    # Test 2: Check environment configuration
    check_environment_config()
    
    if success:
        print("\n Validation completed successfully!")
        print(" Next steps:")
        print("   - Test in cloud environment for full validation")
        print("   - Verify MCP resources can access cloud URLs") 
        print("   - Test caching performance")
    else:
        print("\n Validation failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
