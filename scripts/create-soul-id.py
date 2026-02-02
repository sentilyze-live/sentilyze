"""Higgsfield AI Soul ID Creation Script.

This script creates a Soul ID (custom reference) for Ece character
using the Higgsfield Cloud API.

Usage:
    python scripts/create-soul-id.py

API Reference:
    POST /v1/custom-references
    
Required Headers:
    - hf-api-key: Your API Key ID
    - hf-secret: Your API Secret
    - Content-Type: application/json

Request Body:
    - name: Name for the Soul ID (max 100 chars)
    - input_images: List of image objects with 'type' and 'image_url' fields
    
Response:
    - id: UUID of the created Soul ID
    - name: Name of the Soul ID
    - status: Current status (not_ready, queued, in_progress, completed, failed)
    - created_at: Creation timestamp
    - in_progress_at: When processing started (nullable)
    - thumbnail_url: Thumbnail URL (nullable)
"""

import asyncio
import json
import os
import sys
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
HIGGSFIELD_API_KEY_ID = os.getenv("HIGGSFIELD_API_KEY_ID")
HIGGSFIELD_API_KEY_SECRET = os.getenv("HIGGSFIELD_API_KEY_SECRET")
HIGGSFIELD_BASE_URL = os.getenv("HIGGSFIELD_BASE_URL", "https://platform.higgsfield.ai")

# Ece face images from previous generation
# Using the best generated face images for training the Soul ID
# Format: Each image needs 'type' and 'image_url' fields
ECE_FACE_IMAGES = [
    {
        "type": "face",
        "image_url": "https://d3u0tzju9qaucj.cloudfront.net/ffaba52b-f71d-48df-bfe6-360264498ff5/38450e46-2fa1-43df-b911-4acdc64b4051.png"
    },
    {
        "type": "face", 
        "image_url": "https://d3u0tzju9qaucj.cloudfront.net/ffaba52b-f71d-48df-bfe6-360264498ff5/16c8d2ff-f621-4351-b363-e4613a26522e.png"
    },
    {
        "type": "face",
        "image_url": "https://d3u0tzju9qaucj.cloudfront.net/ffaba52b-f71d-48df-bfe6-360264498ff5/61e1572e-f233-4233-8b52-d9a09c15f6a7.png"
    },
    {
        "type": "face",
        "image_url": "https://d3u0tzju9qaucj.cloudfront.net/ffaba52b-f71d-48df-bfe6-360264498ff5/27322fe8-dec8-40c7-b45f-bc7e96555db9.png"
    },
    {
        "type": "face",
        "image_url": "https://d3u0tzju9qaucj.cloudfront.net/ffaba52b-f71d-48df-bfe6-360264498ff5/63d4395b-3d29-457e-8d1c-a83e4928a317.png"
    },
]


def validate_credentials() -> bool:
    """Validate that required credentials are present."""
    if not HIGGSFIELD_API_KEY_ID:
        print("[ERROR] HIGGSFIELD_API_KEY_ID not found in environment")
        return False
    if not HIGGSFIELD_API_KEY_SECRET:
        print("[ERROR] HIGGSFIELD_API_KEY_SECRET not found in environment")
        return False
    return True


async def create_soul_id(name: str, input_images: List[Dict[str, str]]) -> Dict[str, Any]:
    """Create a new Soul ID (custom reference).
    
    Args:
        name: Name for the Soul ID (max 100 characters)
        input_images: List of image objects with 'type' and 'image_url' fields
        
    Returns:
        API response containing Soul ID details
    """
    endpoint = f"{HIGGSFIELD_BASE_URL}/v1/custom-references"
    
    headers = {
        "hf-api-key": HIGGSFIELD_API_KEY_ID,
        "hf-secret": HIGGSFIELD_API_KEY_SECRET,
        "Content-Type": "application/json",
    }
    
    payload = {
        "name": name,
        "input_images": input_images,
    }
    
    print(f"\n>> Creating Soul ID: '{name}'")
    print(f"   Endpoint: {endpoint}")
    print(f"   API Key ID: {HIGGSFIELD_API_KEY_ID[:8]}...")
    print(f"   Input Images: {len(input_images)} images")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                endpoint,
                headers=headers,
                json=payload,
            )
            
            print(f"\n   Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("\n   [SUCCESS] Soul ID created successfully!")
                print(f"\n   Response Details:")
                print(f"      ID: {data.get('id')}")
                print(f"      Name: {data.get('name')}")
                print(f"      Status: {data.get('status')}")
                print(f"      Created At: {data.get('created_at')}")
                if data.get('thumbnail_url'):
                    print(f"      Thumbnail: {data.get('thumbnail_url')}")
                return data
            elif response.status_code == 422:
                error_data = response.json()
                print(f"\n   [ERROR] Validation Error (422):")
                print(json.dumps(error_data, indent=2))
                return {"error": error_data, "status_code": 422}
            else:
                print(f"\n   [ERROR] HTTP {response.status_code}")
                print(f"   Response: {response.text}")
                return {"error": response.text, "status_code": response.status_code}
                
        except httpx.RequestError as e:
            print(f"\n   [ERROR] Request Error: {e}")
            return {"error": str(e)}
        except Exception as e:
            print(f"\n   [ERROR] Unexpected Error: {e}")
            return {"error": str(e)}


async def list_soul_ids() -> Dict[str, Any]:
    """List all existing Soul IDs.
    
    Returns:
        API response containing list of Soul IDs
    """
    endpoint = f"{HIGGSFIELD_BASE_URL}/v1/custom-references/list"
    
    headers = {
        "hf-api-key": HIGGSFIELD_API_KEY_ID,
        "hf-secret": HIGGSFIELD_API_KEY_SECRET,
        "Content-Type": "application/json",
    }
    
    print(f"\n>> Listing existing Soul IDs...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(endpoint, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                soul_ids = data.get("items", [])
                
                if soul_ids:
                    print(f"\n   Found {len(soul_ids)} Soul ID(s):")
                    for soul in soul_ids:
                        print(f"\n   [Soul] {soul.get('name')}")
                        print(f"      ID: {soul.get('id')}")
                        print(f"      Status: {soul.get('status')}")
                else:
                    print("\n   No Soul IDs found")
                    
                return data
            else:
                print(f"\n   [ERROR] HTTP {response.status_code}")
                print(f"   Response: {response.text}")
                return {"error": response.text, "status_code": response.status_code}
                
        except Exception as e:
            print(f"\n   [ERROR] {e}")
            return {"error": str(e)}


async def main():
    """Main function."""
    print("=" * 60)
    print("Higgsfield AI - Soul ID Creator")
    print("=" * 60)
    
    # Validate credentials
    if not validate_credentials():
        print("\n[!] Please set the following environment variables:")
        print("    - HIGGSFIELD_API_KEY_ID")
        print("    - HIGGSFIELD_API_KEY_SECRET")
        sys.exit(1)
    
    print("\n   Credentials validated")
    print(f"   Base URL: {HIGGSFIELD_BASE_URL}")
    
    # First, list existing Soul IDs
    await list_soul_ids()
    
    # Create a new Soul ID for Ece
    print("\n" + "-" * 60)
    print("Creating new Soul ID for Ece character...")
    print("-" * 60)
    
    # Soul ID name for Ece
    soul_name = "Ece - Turkish Female Character"
    
    result = await create_soul_id(soul_name, ECE_FACE_IMAGES)
    
    # Save result to file
    if "error" not in result:
        output_file = "soul-id-result.json"
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\n   Result saved to: {output_file}")
        
        print("\n" + "=" * 60)
        print("Next Steps:")
        print("=" * 60)
        print("1. Soul ID status will change from 'not_ready' to 'completed'")
        print("2. You can check status using the List Soul IDs API")
        print("3. Once completed, you can use this Soul ID for image generation")
        print("4. Add the Soul ID to your .env file:")
        print(f"   ECE_SOUL_ID={result.get('id')}")
        print("=" * 60)
    else:
        print("\n   [FAILED] Failed to create Soul ID")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
