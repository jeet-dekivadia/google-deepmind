#!/usr/bin/env python3
"""
Test script to verify Gemini Vision API functionality for frame description.
"""

import asyncio
import tempfile
import os
from PIL import Image
import google.generativeai as genai
from config import GEMINI_API_KEY

async def test_describe_image():
    try:
        # Configure Gemini for vision
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Create a simple test image
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            # Create a simple colored rectangle for testing
            img = Image.new('RGB', (640, 480), color='red')
            img.save(tmp_file.name)
            
            prompt = """Describe this image in detail. Include:
            - Colors present
            - Objects or shapes visible
            - Any text if present
            - Overall composition
            """
            
            # Test the vision API
            response = model.generate_content([prompt, img])
            description = response.text.strip()
            
            print(f"✅ Vision API test successful!")
            print(f"Description: {description}")
            
            # Clean up
            os.unlink(tmp_file.name)
            return True
            
    except Exception as e:
        print(f"❌ Vision API test failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_describe_image())
