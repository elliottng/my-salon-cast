#!/usr/bin/env python3
"""
Export OpenAPI schema from MySalonCast FastAPI application.

This script generates machine-readable OpenAPI documentation in JSON format
and saves it to a file for external use, documentation generation, or API client generation.
"""

import json
import requests
import argparse
from pathlib import Path


def export_openapi_schema(server_url: str = "http://127.0.0.1:8002", output_file: str = "openapi.json"):
    """
    Export OpenAPI schema from running FastAPI server.
    
    Args:
        server_url: Base URL of the running FastAPI server
        output_file: Path to save the OpenAPI schema JSON file
    """
    try:
        # Fetch OpenAPI schema from the server
        response = requests.get(f"{server_url}/openapi.json", timeout=10)
        response.raise_for_status()
        
        # Parse and format the JSON
        openapi_schema = response.json()
        
        # Save to file with pretty formatting
        output_path = Path(output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(openapi_schema, f, indent=2, ensure_ascii=False)
        
        print(f"✅ OpenAPI schema exported successfully!")
        print(f"📁 File saved: {output_path.absolute()}")
        print(f"📊 Schema version: {openapi_schema.get('openapi', 'unknown')}")
        print(f"🏷️  API title: {openapi_schema.get('info', {}).get('title', 'unknown')}")
        print(f"🔢 API version: {openapi_schema.get('info', {}).get('version', 'unknown')}")
        
        # Count endpoints
        paths = openapi_schema.get('paths', {})
        endpoint_count = sum(len(methods) for methods in paths.values())
        print(f"🔗 Total endpoints: {endpoint_count}")
        
        return True
        
    except requests.RequestException as e:
        print(f"❌ Error connecting to server: {e}")
        print(f"💡 Make sure the FastAPI server is running at {server_url}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON response: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Export OpenAPI schema from MySalonCast FastAPI server")
    parser.add_argument(
        "--url", 
        default="http://127.0.0.1:8002",
        help="FastAPI server URL (default: http://127.0.0.1:8002)"
    )
    parser.add_argument(
        "--output",
        default="openapi.json", 
        help="Output file path (default: openapi.json)"
    )
    
    args = parser.parse_args()
    
    print("🚀 MySalonCast OpenAPI Schema Exporter")
    print("=" * 50)
    print(f"Server URL: {args.url}")
    print(f"Output file: {args.output}")
    print()
    
    success = export_openapi_schema(args.url, args.output)
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
