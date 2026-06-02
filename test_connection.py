"""
test_connection.py
------------------
Phase 1: Test that your Gemini API key is working correctly.

How to run:
    python test_connection.py

Expected output:
    ✅ Gemini connection successful!
    Response: Hello! I am OctoBot...
"""

import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load .env file
load_dotenv()

# Get Gemini API key
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ ERROR: GEMINI_API_KEY not found in your .env file.")
    print("   Make sure your .env file contains:")
    print("   GEMINI_API_KEY=your_api_key_here")
    exit(1)

print("🔑 Gemini API key loaded successfully.")
print("🤖 Testing connection to Gemini...")

try:
    # Configure Gemini
    genai.configure(api_key=api_key)

    # Create model
    model = genai.GenerativeModel("gemini-2.5-flash")

    # Send test prompt
    response = model.generate_content(
        "Say exactly this: 'Hello! I am OctoBot, your Pharos documentation assistant.'"
    )

    print("\n✅ Gemini connection successful!")
    print(f"Response: {response.text}")

except Exception as e:
    print(f"\n❌ Connection failed: {e}")

    print("\nCommon fixes:")
    print("  1. Check your GEMINI_API_KEY in .env")
    print("  2. Verify the API key in Google AI Studio")
    print("  3. Make sure you're connected to the internet")