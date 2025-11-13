#!/usr/bin/env python3
"""
Comprehensive demonstration of Custom APIs and RAG Integration
Shows success and failure modes with example transcripts
"""

import asyncio
import json
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def demo_scenario(title: str, endpoint: str, method: str = "GET", data: dict = None, params: dict = None):
    """Demo a scenario with formatted output"""
    print(f"\n{'='*60}")
    print(f"SCENARIO: {title}")
    print(f"{'='*60}")

    try:
        if method == "GET":
            print(f"📡 GET {endpoint}")
            if params:
                print(f"📋 Params: {json.dumps(params, indent=2)}")
            response = client.get(endpoint, params=params)
        else:
            print(f"📡 POST {endpoint}")
            if data:
                print(f"📋 Data: {json.dumps(data, indent=2)}")
            response = client.post(endpoint, json=data)

        print(f"📊 Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success Response:")

            if "answer" in result:  # Products API
                print(f"💬 Answer: {result['answer'][:200]}...")
                if result.get("products"):
                    print(f"📦 Products Found: {len(result['products'])}")
                    for i, product in enumerate(result['products'][:2], 1):
                        print(f"   {i}. {product.get('name', 'Unknown')} - {product.get('price', 'N/A')}")

            elif "results" in result:  # Outlets API
                print(f"🔍 SQL Query: {result['sql_query']}")
                print(f"📍 Outlets Found: {result['count']}")
                for i, outlet in enumerate(result['results'][:2], 1):
                    print(f"   {i}. {outlet.get('name', 'Unknown')} - {outlet.get('city', 'Unknown')}")

            elif "response" in result:  # Chat API
                print(f"💬 Response: {result['response'][:200]}...")
                print(f"🎯 Intent: {result.get('intent', 'N/A')}")
                print(f"🔧 Action: {result.get('action_type', 'N/A')}")

        else:
            print(f"❌ Error Response: {response.text}")

    except Exception as e:
        print(f"💥 Exception: {e}")

    print(f"{'='*60}")


def main():
    """Run comprehensive demonstration"""

    print("🚀 CUSTOM APIs & RAG INTEGRATION DEMONSTRATION")
    print("Part 4: Product KB Retrieval & Outlets Text2SQL")

    # =============================================================================
    # PRODUCTS API DEMONSTRATION
    # =============================================================================

    print("\n🔍 PRODUCTS API - RAG RETRIEVAL DEMONSTRATION")

    # Success Cases
    demo_scenario(
        "Product Search - Travel Mug",
        "/products",
        "GET",
        params={"query": "travel mug for commuting", "max_results": 3}
    )

    demo_scenario(
        "Product Search - Eco-Friendly Options",
        "/products",
        "POST",
        data={"query": "eco-friendly bamboo products", "max_results": 2}
    )

    demo_scenario(
        "Product Search - Ceramic Mugs",
        "/products",
        "GET",
        params={"query": "ceramic coffee mugs for office"}
    )

    demo_scenario(
        "Product Search - Cold Brew Equipment",
        "/products",
        "GET",
        params={"query": "cold brew bottle summer refreshment"}
    )

    # Edge Cases
    demo_scenario(
        "Product Search - Vague Query",
        "/products",
        "GET",
        params={"query": "something for drinking coffee"}
    )

    # Failure Cases
    demo_scenario(
        "Product Search - Empty Query (400 Error)",
        "/products",
        "GET",
        params={"query": ""}
    )

    # =============================================================================
    # OUTLETS API DEMONSTRATION
    # =============================================================================

    print("\n🏪 OUTLETS API - TEXT2SQL DEMONSTRATION")

    # Success Cases
    demo_scenario(
        "Outlets Search - Location-based",
        "/outlets/search",
        "GET",
        params={"query": "outlets in Kuala Lumpur"}
    )

    demo_scenario(
        "Outlets Search - Feature-based",
        "/outlets/search",
        "POST",
        data={"query": "outlets with drive-thru service"}
    )

    demo_scenario(
        "Outlets Search - 24-Hour Operations",
        "/outlets/search",
        "GET",
        params={"query": "24 hour outlets for late night coffee"}
    )

    demo_scenario(
        "Outlets Search - Complex Query",
        "/outlets/search",
        "GET",
        params={"query": "outlets in Selangor with parking and WiFi"}
    )

    demo_scenario(
        "Outlets Search - Service-based",
        "/outlets/search",
        "GET",
        params={"query": "outlets that serve pastries and sandwiches"}
    )

    # Failure Cases
    demo_scenario(
        "Outlets Search - Empty Query (400 Error)",
        "/outlets/search",
        "GET",
        params={"query": ""}
    )

    # =============================================================================
    # CHATBOT INTEGRATION DEMONSTRATION
    # =============================================================================

    print("\n💬 CHATBOT INTEGRATION DEMONSTRATION")

    # Product-related conversations
    demo_scenario(
        "Chat - Product Inquiry",
        "/chat/agentic",
        "POST",
        data={"message": "I need a good travel mug for my daily commute", "session_id": "demo_products"}
    )

    demo_scenario(
        "Chat - Product Materials",
        "/chat/agentic",
        "POST",
        data={"message": "Do you have any ceramic mugs?", "session_id": "demo_products"}
    )

    demo_scenario(
        "Chat - Eco-friendly Products",
        "/chat/agentic",
        "POST",
        data={"message": "Show me eco-friendly drinkware options", "session_id": "demo_products"}
    )

    # Advanced outlet searches
    demo_scenario(
        "Chat - Advanced Outlet Search",
        "/chat/agentic",
        "POST",
        data={"message": "Find me outlets with drive-thru in Selangor", "session_id": "demo_outlets"}
    )

    demo_scenario(
        "Chat - 24-Hour Outlets",
        "/chat/agentic",
        "POST",
        data={"message": "Which outlets are open 24 hours?", "session_id": "demo_outlets"}
    )

    demo_scenario(
        "Chat - Complex Query",
        "/chat/agentic",
        "POST",
        data={"message": "I need outlets near Kuala Lumpur with parking and WiFi for meetings", "session_id": "demo_outlets"}
    )

    # Mixed queries
    demo_scenario(
        "Chat - Mixed Request",
        "/chat/agentic",
        "POST",
        data={"message": "Can you help me find a French press and also tell me about outlets in PJ?", "session_id": "demo_mixed"}
    )

    # =============================================================================
    # FAILURE MODES DEMONSTRATION
    # =============================================================================

    print("\n❌ FAILURE MODES DEMONSTRATION")

    demo_scenario(
        "Chat - Nonsensical Query",
        "/chat/agentic",
        "POST",
        data={"message": "xyzabc123!@#", "session_id": "demo_fail"}
    )

    demo_scenario(
        "Chat - Ambiguous Query",
        "/chat/agentic",
        "POST",
        data={"message": "stuff", "session_id": "demo_fail"}
    )

    # =============================================================================
    # SUMMARY
    # =============================================================================

    print(f"\n{'='*60}")
    print("🎯 DEMONSTRATION SUMMARY")
    print(f"{'='*60}")
    print("✅ Products API (RAG) Features Demonstrated:")
    print("   - Vector similarity search with FAISS")
    print("   - OpenAI-powered answer generation")
    print("   - Product recommendation with details")
    print("   - Error handling and validation")
    print("")
    print("✅ Outlets API (Text2SQL) Features Demonstrated:")
    print("   - Natural language to SQL conversion")
    print("   - Complex query handling")
    print("   - Database search with multiple criteria")
    print("   - Structured result formatting")
    print("")
    print("✅ Chatbot Integration Features Demonstrated:")
    print("   - Intelligent intent detection")
    print("   - API routing based on query type")
    print("   - Conversational context maintenance")
    print("   - Graceful error handling")
    print("")
    print("✅ Error Handling & Recovery:")
    print("   - Empty query validation")
    print("   - Service unavailable scenarios")
    print("   - Invalid input handling")
    print("   - User-friendly error messages")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()