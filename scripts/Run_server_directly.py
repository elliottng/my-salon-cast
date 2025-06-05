#!/usr/bin/env python
"""
Simple script to run the MySalonCast FastAPI server directly.
Use this to quickly serve and listen to podcasts in a web browser.
"""
import os
import subprocess
import signal
import sys
import uvicorn
import psutil

def kill_existing_servers():
    """Kill any existing uvicorn server processes on port 8080."""
    try:
        # Use psutil to find and kill processes using port 8080
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if proc.info['cmdline'] and len(proc.info['cmdline']) > 1:
                cmdline = ' '.join(proc.info['cmdline'])
                if ('uvicorn' in cmdline or 'python' in proc.info['name']) and '8080' in cmdline:
                    print(f"Killing existing server process: {proc.info['pid']} {cmdline}")
                    psutil.Process(proc.info['pid']).terminate()
    except Exception as e:
        print(f"Error killing existing servers: {e}")

if __name__ == "__main__":
    # Ensure we're in the project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)
    
    # Kill existing servers
    kill_existing_servers()
    
    # Make sure the outputs directory exists
    os.makedirs("./outputs/audio", exist_ok=True)
    
    # List available podcasts
    podcast_dirs = [d for d in os.listdir("./outputs/audio") 
                   if os.path.isdir(os.path.join("./outputs/audio", d))]
    
    if podcast_dirs:
        print("\nAvailable podcasts:")
        for i, podcast_id in enumerate(podcast_dirs, 1):
            final_path = os.path.join("./outputs/audio", podcast_id, "final.mp3")
            status = "✓" if os.path.exists(final_path) else "×"
            print(f"{i}. {podcast_id} {status}")
        
        port = int(os.getenv("PORT", 8000))
        print(f"\nTo listen to a podcast, visit: http://localhost:{port}/listen/<podcast_id>")
        print(f"For example: http://localhost:{port}/listen/{podcast_dirs[0]}")
    else:
        print("\nNo podcasts found in the outputs/audio directory.")

    # Start the server
    print("\nStarting MySalonCast server...")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
