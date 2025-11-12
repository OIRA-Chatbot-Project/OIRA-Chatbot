"""
Example client script to test the OIRA Chatbot API
This demonstrates how to interact with all endpoints
"""

import requests
import uuid
import json

# Configuration
BASE_URL = "http://localhost:8000"

def test_health():
    """Test the health check endpoint"""
    print("\n" + "="*50)
    print("Testing Health Check")
    print("="*50)
    
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200


def test_chat(session_id, message):
    """Test the chat endpoint"""
    print("\n" + "="*50)
    print("Testing Chat Endpoint")
    print("="*50)
    
    payload = {
        "session_id": session_id,
        "message": message
    }
    
    print(f"Sending: {message}")
    response = requests.post(f"{BASE_URL}/chat", json=payload)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\nAnswer: {data['answer']}")
        print(f"\nMessage ID: {data['message_id']}")
        print(f"\nCitations ({len(data['citations'])}):")
        for i, citation in enumerate(data['citations'], 1):
            print(f"  {i}. Source: {citation['source']}")
            print(f"     Page: {citation.get('page', 'N/A')}")
            print(f"     Content: {citation['content'][:100]}...")
        return data['message_id']
    else:
        print(f"Error: {response.text}")
        return None


def test_feedback(session_id, message_id, rating, note=None):
    """Test the feedback endpoint"""
    print("\n" + "="*50)
    print("Testing Feedback Endpoint")
    print("="*50)
    
    payload = {
        "session_id": session_id,
        "message_id": message_id,
        "rating": rating
    }
    
    if note:
        payload["note"] = note
    
    print(f"Submitting feedback: {'👍' if rating == 1 else '👎'}")
    response = requests.post(f"{BASE_URL}/feedback", json=payload)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        return True
    else:
        print(f"Error: {response.text}")
        return False


def test_get_messages(session_id):
    """Test the messages endpoint"""
    print("\n" + "="*50)
    print("Testing Get Messages Endpoint")
    print("="*50)
    
    response = requests.get(f"{BASE_URL}/messages", params={"session_id": session_id})
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\nSession ID: {data['session_id']}")
        print(f"Total Messages: {len(data['messages'])}")
        print("\nConversation History:")
        print("-" * 50)
        
        for msg in data['messages']:
            role_emoji = "🧑" if msg['role'] == 'user' else "🤖"
            print(f"\n{role_emoji} {msg['role'].upper()} (ID: {msg['id']})")
            print(f"Time: {msg['created_at']}")
            print(f"Content: {msg['content'][:200]}{'...' if len(msg['content']) > 200 else ''}")
            
            if msg.get('citations'):
                print(f"Citations: {len(msg['citations'])}")
        
        return True
    else:
        print(f"Error: {response.text}")
        return False


def run_full_test():
    """Run a complete test scenario"""
    print("\n" + "🤖 " + "="*48)
    print("OIRA Chatbot API - Full Test Suite")
    print("="*50)
    
    # Generate a unique session ID
    session_id = str(uuid.uuid4())
    print(f"\nGenerated Session ID: {session_id}")
    
    # Test 1: Health check
    if not test_health():
        print("\n❌ Health check failed. Is the server running?")
        return
    
    # Test 2: First chat message
    message_id_1 = test_chat(
        session_id,
        "What computer science courses are available?"
    )
    
    if not message_id_1:
        print("\n❌ Chat test failed")
        return
    
    # Test 3: Follow-up message (uses conversation history)
    message_id_2 = test_chat(
        session_id,
        "Tell me more about the first course you mentioned"
    )
    
    # Test 4: Submit positive feedback
    if message_id_1:
        test_feedback(session_id, message_id_1, rating=1, note="Very helpful!")
    
    # Test 5: Submit negative feedback
    if message_id_2:
        test_feedback(session_id, message_id_2, rating=-1)
    
    # Test 6: Get conversation history
    test_get_messages(session_id)
    
    print("\n" + "="*50)
    print("✅ All tests completed!")
    print("="*50)
    print(f"\nYou can view the conversation at:")
    print(f"Session ID: {session_id}")


def interactive_chat():
    """Interactive chat session"""
    print("\n" + "="*50)
    print("Interactive Chat Mode")
    print("="*50)
    print("Type 'quit' to exit, 'new' for new session, 'history' to see messages")
    
    session_id = str(uuid.uuid4())
    print(f"\nSession ID: {session_id}")
    
    while True:
        user_input = input("\n🧑 You: ").strip()
        
        if user_input.lower() == 'quit':
            break
        elif user_input.lower() == 'new':
            session_id = str(uuid.uuid4())
            print(f"New session started: {session_id}")
            continue
        elif user_input.lower() == 'history':
            test_get_messages(session_id)
            continue
        elif not user_input:
            continue
        
        message_id = test_chat(session_id, user_input)
        
        if message_id:
            feedback = input("\nRate this answer (+ for thumbs up, - for thumbs down, Enter to skip): ").strip()
            if feedback == '+':
                test_feedback(session_id, message_id, 1)
            elif feedback == '-':
                note = input("Optional feedback note: ").strip()
                test_feedback(session_id, message_id, -1, note if note else None)


if __name__ == "__main__":
    import sys
    
    print("\n🤖 OIRA Chatbot API Test Client")
    print("\nOptions:")
    print("  1. Run full test suite")
    print("  2. Interactive chat")
    print("  3. Exit")
    
    choice = input("\nSelect option (1-3): ").strip()
    
    if choice == "1":
        run_full_test()
    elif choice == "2":
        interactive_chat()
    else:
        print("Goodbye!")
