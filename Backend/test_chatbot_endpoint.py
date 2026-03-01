#!/usr/bin/env python3
"""
Test script to verify chatbot endpoint is accessible
"""
import requests
import json

def test_chatbot_endpoint():
    url = "http://localhost:5000/api/chatbot"
    
    payload = {
        "message": "Hello, can you help me?",
        "context": {
            "currentQuestion": None,
            "skill": None,
            "role": None,
            "interviewType": None
        },
        "conversationHistory": []
    }
    
    try:
        print("Testing chatbot endpoint...")
        print(f"URL: {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(url, json=payload, timeout=10)
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("\n[SUCCESS] Chatbot endpoint is working!")
                return True
            else:
                print(f"\n[ERROR] Error: {data.get('message')}")
                return False
        else:
            print(f"\n[ERROR] HTTP Error: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("\n[ERROR] Connection Error: Backend server is not running on port 5000")
        print("Please start the server using: python start_server.py")
        return False
    except Exception as e:
        print(f"\n[ERROR] Error: {str(e)}")
        return False

if __name__ == "__main__":
    test_chatbot_endpoint()

