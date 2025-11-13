#!/usr/bin/env python3
"""
Test suite for custom APIs - Products RAG and Outlets Text2SQL
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

class TestProductsAPI:
    """Test the products RAG endpoint"""

    def test_products_search_get(self):
        """Test GET /products endpoint"""
        response = client.get("/products?query=travel mug for commuting")
        assert response.status_code == 200

        data = response.json()
        assert "answer" in data
        assert "products" in data
        assert "success" in data
        assert data["success"] is True

    def test_products_search_post(self):
        """Test POST /products endpoint"""
        response = client.post("/products", json={
            "query": "ceramic mugs",
            "max_results": 3
        })
        assert response.status_code == 200

        data = response.json()
        assert "answer" in data
        assert "products" in data
        assert len(data["products"]) <= 3

    def test_products_empty_query(self):
        """Test empty query handling"""
        response = client.get("/products?query=")
        assert response.status_code == 400

    def test_products_specific_queries(self):
        """Test specific product queries"""
        test_queries = [
            "eco-friendly options",
            "stainless steel tumbler",
            "French press for brewing",
            "espresso cups",
            "cold brew bottle"
        ]

        for query in test_queries:
            response = client.get(f"/products?query={query}")
            assert response.status_code == 200

            data = response.json()
            assert data["success"] is True
            assert "answer" in data
            print(f"Query: {query} -> Found {data.get('total_found', 0)} products")


class TestOutletsAPI:
    """Test the outlets Text2SQL endpoint"""

    def test_outlets_search_get(self):
        """Test GET /outlets/search endpoint"""
        response = client.get("/outlets/search?query=outlets in Kuala Lumpur")
        assert response.status_code == 200

        data = response.json()
        assert "results" in data
        assert "sql_query" in data
        assert "success" in data
        assert data["success"] is True

    def test_outlets_search_post(self):
        """Test POST /outlets/search endpoint"""
        response = client.post("/outlets/search", json={
            "query": "outlets with drive-thru"
        })
        assert response.status_code == 200

        data = response.json()
        assert "results" in data
        assert "sql_query" in data

    def test_outlets_empty_query(self):
        """Test empty query handling"""
        response = client.get("/outlets/search?query=")
        assert response.status_code == 400

    def test_outlets_specific_queries(self):
        """Test specific outlet queries"""
        test_queries = [
            "24 hour outlets",
            "outlets with parking",
            "outlets in Selangor",
            "drive-thru locations",
            "outlets that serve pastries",
            "outlets with WiFi"
        ]

        for query in test_queries:
            response = client.get(f"/outlets/search?query={query}")
            assert response.status_code == 200

            data = response.json()
            assert data["success"] is True
            print(f"Query: {query} -> SQL: {data['sql_query']} -> Found {data['count']} outlets")


class TestChatbotIntegration:
    """Test chatbot integration with new APIs"""

    def test_product_queries_in_chat(self):
        """Test product-related queries through chatbot"""
        product_queries = [
            "I need a travel mug",
            "What drinkware do you have?",
            "Show me ceramic mugs",
            "Do you have eco-friendly products?",
            "I want to buy a tumbler"
        ]

        for query in product_queries:
            response = client.post("/chat/agentic", json={
                "message": query,
                "session_id": "test_products"
            })
            assert response.status_code == 200

            data = response.json()
            assert data["intent"] in ["product_search", "outlet_search", "general_question"]
            print(f"Product Query: {query} -> Intent: {data['intent']}, Action: {data['action_type']}")

    def test_advanced_outlet_queries_in_chat(self):
        """Test advanced outlet queries through chatbot"""
        outlet_queries = [
            "Find outlets with drive-thru near me",
            "Which outlets are open 24 hours?",
            "Show me outlets with parking",
            "I need outlets in Selangor state",
            "Find outlets that serve pastries and have WiFi"
        ]

        for query in outlet_queries:
            response = client.post("/chat/agentic", json={
                "message": query,
                "session_id": "test_outlets"
            })
            assert response.status_code == 200

            data = response.json()
            assert data["intent"] in ["outlet_search_nl", "outlet_search", "general_question"]
            print(f"Outlet Query: {query} -> Intent: {data['intent']}, Action: {data['action_type']}")


def test_api_endpoints_availability():
    """Test that all API endpoints are accessible"""
    endpoints = [
        ("/", "GET"),
        ("/products?query=test", "GET"),
        ("/outlets/search?query=test", "GET"),
        ("/chat/agentic", "POST")
    ]

    for endpoint, method in endpoints:
        if method == "GET":
            response = client.get(endpoint)
        elif method == "POST":
            response = client.post(endpoint, json={"message": "test", "session_id": "test"})

        # Should not get 404 or 500 errors
        assert response.status_code not in [404, 500], f"Endpoint {endpoint} failed with {response.status_code}"


def test_openapi_spec():
    """Test that OpenAPI spec is generated correctly"""
    response = client.get("/openapi.json")
    assert response.status_code == 200

    openapi_spec = response.json()
    assert "paths" in openapi_spec

    # Check that our new endpoints are documented
    paths = openapi_spec["paths"]
    assert "/products" in paths
    assert "/outlets/search" in paths

    print("✅ OpenAPI spec includes new endpoints")


if __name__ == "__main__":
    print("🧪 Running Custom APIs Test Suite")
    pytest.main([__file__, "-v"])