#!/usr/bin/env python3
"""
Test script for weather agent functionality
"""
import asyncio
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from weather_agent import WeatherAgent
from planner import AgenticPlanner

async def test_weather_agent():
    """Test the weather agent directly"""
    print("🌤️ Testing Weather Agent...")
    print("=" * 50)

    try:
        weather_agent = WeatherAgent()

        # Test 1: Current weather for KL
        print("\n1. Testing current weather for Kuala Lumpur:")
        result = await weather_agent.get_current_weather("Kuala Lumpur, Malaysia")
        if result.get("success"):
            print(result["formatted_response"])
        else:
            print(f"❌ Error: {result.get('error')}")

        # Test 2: 3-day forecast
        print("\n2. Testing 3-day forecast for KL:")
        result = await weather_agent.get_weather_forecast(3, "Kuala Lumpur, Malaysia")
        if result.get("success"):
            print(result["formatted_response"])
        else:
            print(f"❌ Error: {result.get('error')}")

        # Test 3: Search locations
        print("\n3. Testing location search for 'Penang':")
        result = await weather_agent.search_weather_locations("Penang")
        if result.get("success"):
            print(result["formatted_response"])
        else:
            print(f"❌ Error: {result.get('error')}")

    except Exception as e:
        print(f"❌ Weather agent test failed: {str(e)}")

async def test_agentic_planner():
    """Test the integrated agentic planner with weather"""
    print("\n\n🤖 Testing Agentic Planner with Weather...")
    print("=" * 50)

    try:
        # Mock outlets data
        outlets_data = '[{"name": "SS2 Branch", "area": "petaling_jaya"}]'
        planner = AgenticPlanner(outlets_data)

        test_messages = [
            "What's the weather like today?",
            "Give me the forecast for tomorrow in KL",
            "Weather forecast for 5 days",
            "What's the temperature in Penang?",
            "Will it rain tomorrow?"
        ]

        for i, message in enumerate(test_messages, 1):
            print(f"\n{i}. Testing message: '{message}'")
            try:
                result = await planner.process_message(message, {})
                print(f"   Intent: {result.intent.intent.value}")
                print(f"   Action: {result.action.action_type.value}")
                print(f"   Confidence: {result.intent.confidence}")
                print(f"   Tools: {result.action.required_tools}")

                if 'message' in result.action.parameters:
                    response = result.action.parameters['message']
                    # Truncate long responses for testing
                    if len(response) > 200:
                        response = response[:200] + "..."
                    print(f"   Response: {response}")
                else:
                    print(f"   Response: {result.action.parameters}")

            except Exception as e:
                print(f"   ❌ Error: {str(e)}")

    except Exception as e:
        print(f"❌ Planner test failed: {str(e)}")

async def main():
    """Run all tests"""
    print("🚀 Starting Weather Integration Tests")
    print("=" * 60)

    # Test weather agent directly
    await test_weather_agent()

    # Test agentic planner integration
    await test_agentic_planner()

    print("\n✅ Testing completed!")
    print("\n📝 To test via API:")
    print("   1. Start server: uvicorn main:app --reload")
    print("   2. Test current weather:")
    print("      curl -X POST 'http://localhost:8000/chat/agentic' \\")
    print("           -H 'Content-Type: application/json' \\")
    print("           -d '{\"message\": \"What is the weather like today?\"}'")
    print("   3. Test forecast:")
    print("      curl -X POST 'http://localhost:8000/chat/agentic' \\")
    print("           -H 'Content-Type: application/json' \\")
    print("           -d '{\"message\": \"Give me a 3-day forecast\"}'")

if __name__ == "__main__":
    asyncio.run(main())