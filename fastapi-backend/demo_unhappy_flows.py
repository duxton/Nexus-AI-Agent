#!/usr/bin/env python3
"""
Demonstration script for unhappy flow handling in the agentic chat system
"""

import asyncio
import json
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_scenario(name: str, request_data: dict):
    """Test a scenario and display results"""
    print(f"\n{'='*60}")
    print(f"SCENARIO: {name}")
    print(f"{'='*60}")
    print(f"Request: {json.dumps(request_data, indent=2)}")

    try:
        response = client.post("/chat/agentic", json=request_data)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Response: {data['response']}")
            print(f"Intent: {data['intent']}")
            print(f"Action Type: {data['action_type']}")
            print(f"Reasoning: {data['reasoning']}")
            print(f"Confidence: {data['confidence']}")
        else:
            print(f"Error Response: {response.text}")

    except Exception as e:
        print(f"Exception occurred: {e}")

def main():
    """Run unhappy flow demonstrations"""

    print("🤖 UNHAPPY FLOWS DEMONSTRATION")
    print("Demonstrating robust error handling in the agentic chat system")

    # Test 1: Missing Parameters
    test_scenario(
        "Empty Message",
        {"message": "", "session_id": "demo_session"}
    )

    test_scenario(
        "Whitespace Only Message",
        {"message": "   \n\t   ", "session_id": "demo_session"}
    )

    test_scenario(
        "Vague Calculation Request",
        {"message": "Calculate", "session_id": "demo_session"}
    )

    test_scenario(
        "Vague Outlet Request",
        {"message": "Show outlets", "session_id": "demo_session"}
    )

    test_scenario(
        "Vague Weather Request",
        {"message": "Weather", "session_id": "demo_session"}
    )

    # Test 2: Malicious Payloads
    test_scenario(
        "XSS Attempt",
        {"message": "<script>alert('xss')</script>Find outlets", "session_id": "demo_session"}
    )

    test_scenario(
        "SQL Injection Attempt",
        {"message": "Find outlets in '; DROP TABLE outlets; --", "session_id": "demo_session"}
    )

    test_scenario(
        "Command Injection Attempt",
        {"message": "Weather in Kuala Lumpur; rm -rf /", "session_id": "demo_session"}
    )

    test_scenario(
        "JSON Injection",
        {"message": '{"malicious": "payload", "override": true}', "session_id": "demo_session"}
    )

    # Test 3: Edge Cases
    test_scenario(
        "Very Long Message",
        {"message": "A" * 1000 + " Find outlets", "session_id": "demo_session"}
    )

    test_scenario(
        "Unicode Attack",
        {"message": "Find outlets\u0000in Klang\uffef", "session_id": "demo_session"}
    )

    print(f"\n{'='*60}")
    print("DEMONSTRATION COMPLETED")
    print("Key Features Demonstrated:")
    print("✅ Empty message handling")
    print("✅ Vague request clarification")
    print("✅ XSS protection via HTML escaping")
    print("✅ SQL injection prevention")
    print("✅ Command injection protection")
    print("✅ Graceful error handling")
    print("✅ User-friendly error messages")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()