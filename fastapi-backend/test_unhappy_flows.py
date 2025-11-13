"""
Test suite for unhappy flows in the agentic chat system
Tests missing parameters, API downtime, and malicious payloads
"""
import pytest
import httpx
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
import json
from main import app

client = TestClient(app)

class TestMissingParameters:
    """Test cases for missing or invalid parameters"""

    def test_empty_message(self):
        """Test bot response to empty message"""
        response = client.post("/chat/agentic", json={
            "message": "",
            "session_id": "test_session"
        })
        assert response.status_code == 200
        data = response.json()
        assert "please provide" in data["response"].lower() or "what would you like" in data["response"].lower()
        assert data["intent"] in ["unclear", "greeting"]

    def test_whitespace_only_message(self):
        """Test bot response to whitespace-only message"""
        response = client.post("/chat/agentic", json={
            "message": "   \n\t   ",
            "session_id": "test_session"
        })
        assert response.status_code == 200
        data = response.json()
        assert "please provide" in data["response"].lower() or "what would you like" in data["response"].lower()

    def test_vague_calculate_request(self):
        """Test response to 'Calculate' without parameters"""
        response = client.post("/chat/agentic", json={
            "message": "Calculate",
            "session_id": "test_session"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["action_type"] == "ask_clarification"
        assert "calculation" in data["response"].lower() and "example" in data["response"].lower()

    def test_vague_outlet_request(self):
        """Test response to 'Show outlets' without location"""
        response = client.post("/chat/agentic", json={
            "message": "Show outlets",
            "session_id": "test_session"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["action_type"] == "ask_clarification"
        assert ("which area" in data["response"].lower() or
                "where would you like" in data["response"].lower() or
                "specify a location" in data["response"].lower())

    def test_vague_weather_request(self):
        """Test response to 'Weather' without location"""
        response = client.post("/chat/agentic", json={
            "message": "Weather",
            "session_id": "test_session"
        })
        assert response.status_code == 200
        data = response.json()
        # Should ask for clarification or provide default location weather
        assert data["action_type"] in ["ask_clarification", "get_weather"]

    def test_missing_session_id(self):
        """Test handling when session_id is missing"""
        response = client.post("/chat/agentic", json={
            "message": "Hello"
        })
        assert response.status_code == 200
        data = response.json()
        # Should auto-generate session_id
        assert data["session_id"] is not None
        assert len(data["session_id"]) > 0


class TestAPIDowntime:
    """Test cases for API downtime simulation"""

    @patch('weather_agent.WeatherAgent.get_current_weather')
    async def test_weather_api_downtime(self, mock_weather):
        """Test weather request when WeatherAPI is down"""
        # Simulate HTTP 500 from weather API
        mock_weather.side_effect = httpx.HTTPStatusError(
            "Internal Server Error",
            request=Mock(),
            response=Mock(status_code=500)
        )

        response = client.post("/chat/agentic", json={
            "message": "What's the weather in Kuala Lumpur?",
            "session_id": "test_session"
        })

        assert response.status_code == 200
        data = response.json()
        assert "weather service is currently unavailable" in data["response"].lower()
        assert "try again later" in data["response"].lower()

    @patch('outlets.OutletService.find_outlets_by_area')
    def test_outlet_service_failure(self, mock_outlets):
        """Test outlet request when service fails"""
        # Simulate service failure
        mock_outlets.side_effect = Exception("Database connection failed")

        response = client.post("/chat/agentic", json={
            "message": "Find outlets in Klang Valley",
            "session_id": "test_session"
        })

        assert response.status_code == 200
        data = response.json()
        assert "unable to retrieve outlet information" in data["response"].lower()

    @patch('openai.OpenAI')
    def test_openai_api_failure(self, mock_openai):
        """Test when OpenAI API is down"""
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("OpenAI API Error")
        mock_openai.return_value = mock_client

        response = client.post("/chat/agentic", json={
            "message": "Hello, how are you?",
            "session_id": "test_session"
        })

        assert response.status_code == 200
        data = response.json()
        assert "experiencing technical difficulties" in data["response"].lower()

    def test_network_timeout_simulation(self):
        """Test handling of network timeouts"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = httpx.TimeoutException("Request timeout")

            response = client.post("/chat/agentic", json={
                "message": "Get weather for Penang",
                "session_id": "test_session"
            })

            assert response.status_code == 200
            data = response.json()
            assert "service is taking longer than expected" in data["response"].lower()


class TestMaliciousPayloads:
    """Test cases for malicious payload handling"""

    def test_sql_injection_attempt(self):
        """Test SQL injection attempt in outlet search"""
        response = client.get("/outlets/'; DROP TABLE outlets; --")

        # Should not crash and should handle safely
        assert response.status_code in [404, 500]  # Either not found or safely handled

        # Test in chat message
        response = client.post("/chat/agentic", json={
            "message": "Find outlets in '; DROP TABLE outlets; --",
            "session_id": "test_session"
        })

        assert response.status_code == 200
        data = response.json()
        # Should sanitize and respond appropriately
        assert "no outlets found" in data["response"].lower() or "unable to find" in data["response"].lower()

    def test_xss_attempt(self):
        """Test XSS payload in message"""
        malicious_message = "<script>alert('xss')</script>Find outlets"

        response = client.post("/chat/agentic", json={
            "message": malicious_message,
            "session_id": "test_session"
        })

        assert response.status_code == 200
        data = response.json()
        # Response should not contain unescaped script tags
        assert "<script>" not in data["response"]
        assert "alert(" not in data["response"]

    def test_extremely_long_message(self):
        """Test handling of extremely long messages"""
        long_message = "A" * 100000  # 100KB message

        response = client.post("/chat/agentic", json={
            "message": long_message,
            "session_id": "test_session"
        })

        # Should either truncate or reject gracefully
        assert response.status_code in [200, 400, 413]
        if response.status_code == 200:
            data = response.json()
            assert len(data["response"]) > 0

    def test_json_injection(self):
        """Test JSON injection attempts"""
        response = client.post("/chat/agentic", json={
            "message": '{"malicious": "payload", "override": true}',
            "session_id": "test_session"
        })

        assert response.status_code == 200
        data = response.json()
        # Should treat as normal text, not as JSON
        assert "malicious" not in str(data).lower() or "find" in data["response"].lower()

    def test_unicode_attacks(self):
        """Test Unicode-based attacks"""
        # Test various Unicode attack vectors
        unicode_attacks = [
            "Find outlets in \u202e\u0644\u0627",  # Right-to-left override
            "Find outlets\u0000in Klang",  # Null byte injection
            "Find outlets\uffef",  # Zero-width character
        ]

        for attack_message in unicode_attacks:
            response = client.post("/chat/agentic", json={
                "message": attack_message,
                "session_id": "test_session"
            })

            assert response.status_code == 200
            data = response.json()
            assert len(data["response"]) > 0

    def test_command_injection_attempt(self):
        """Test command injection in location parameter"""
        response = client.post("/chat/agentic", json={
            "message": "Weather in Kuala Lumpur; rm -rf /",
            "session_id": "test_session"
        })

        assert response.status_code == 200
        data = response.json()
        # Should sanitize location and not execute commands
        assert "rm" not in data["response"].lower()


class TestErrorRecovery:
    """Test error recovery and graceful degradation"""

    def test_partial_service_failure(self):
        """Test when some services fail but others work"""
        with patch('weather_agent.WeatherAgent.get_current_weather', side_effect=Exception("Weather API down")):
            response = client.post("/chat/agentic", json={
                "message": "What's the weather and find outlets in KL?",
                "session_id": "test_session"
            })

            assert response.status_code == 200
            data = response.json()
            # Should handle weather failure but still provide outlet info if possible
            assert len(data["response"]) > 0

    def test_context_corruption_recovery(self):
        """Test recovery from corrupted session context"""
        # First establish normal context
        response1 = client.post("/chat/agentic", json={
            "message": "I'm in Klang Valley",
            "session_id": "test_corrupt_session"
        })
        assert response1.status_code == 200

        # Simulate context corruption by injecting bad data
        with patch('main.memory_manager.get_context', return_value={"malformed": "data"}):
            response2 = client.post("/chat/agentic", json={
                "message": "Find outlets nearby",
                "session_id": "test_corrupt_session"
            })

            assert response2.status_code == 200
            data = response2.json()
            # Should recover gracefully and ask for clarification
            assert len(data["response"]) > 0

    def test_memory_overflow_protection(self):
        """Test protection against memory overflow from long conversations"""
        session_id = "memory_test_session"

        # Simulate a very long conversation
        for i in range(100):
            response = client.post("/chat/agentic", json={
                "message": f"Message number {i}",
                "session_id": session_id
            })
            assert response.status_code == 200

        # System should still respond normally
        final_response = client.post("/chat/agentic", json={
            "message": "Are you still working?",
            "session_id": session_id
        })

        assert final_response.status_code == 200
        data = final_response.json()
        assert len(data["response"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])