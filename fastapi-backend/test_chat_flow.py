import pytest
import httpx
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

class TestChatFlowHappyPath:
    def test_complete_conversation_flow(self):
        """Test the complete conversation flow as described in requirements"""

        # Turn 1: User asks about outlet in Petaling Jaya
        response1 = client.post("/chat", json={
            "message": "Is there an outlet in Petaling Jaya?"
        })
        assert response1.status_code == 200
        data1 = response1.json()
        session_id = data1["session_id"]
        assert "Yes!" in data1["response"]
        assert "Petaling Jaya" in data1["response"]
        assert data1["turn_number"] == 1

        # Turn 2: Bot asks which outlet, user specifies SS 2
        response2 = client.post("/chat", json={
            "message": "SS 2, what's the opening time?",
            "session_id": session_id
        })
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["session_id"] == session_id
        assert "SS 2" in data2["response"]
        assert "9:00 AM" in data2["response"]
        assert data2["turn_number"] == 2

        # Turn 3: Follow-up question about the same outlet
        response3 = client.post("/chat", json={
            "message": "What's the address?",
            "session_id": session_id
        })
        assert response3.status_code == 200
        data3 = response3.json()
        assert data3["session_id"] == session_id
        assert "SS 2" in data3["response"] or "Jalan SS 2/24" in data3["response"]
        assert data3["turn_number"] == 3

    def test_conversation_memory_persistence(self):
        """Test that conversation context is maintained across turns"""

        # Start a conversation about Petaling Jaya
        response1 = client.post("/chat", json={
            "message": "Do you have any outlets in Petaling Jaya?"
        })
        session_id = response1.json()["session_id"]

        # Ask about opening hours without specifying location again
        response2 = client.post("/chat", json={
            "message": "What are the opening hours?",
            "session_id": session_id
        })
        assert response2.status_code == 200
        data2 = response2.json()
        # Should provide opening hours for Petaling Jaya outlets
        assert "9:00 AM" in data2["response"] or "8:30 AM" in data2["response"] or "10:00 AM" in data2["response"]

    def test_context_extraction_and_memory(self):
        """Test context extraction and memory management"""

        # Start conversation mentioning specific location
        response1 = client.post("/chat", json={
            "message": "I'm looking for the SS 15 outlet"
        })
        session_id = response1.json()["session_id"]

        # Ask follow-up without mentioning location
        response2 = client.post("/chat", json={
            "message": "When do you open?",
            "session_id": session_id
        })
        assert response2.status_code == 200
        data2 = response2.json()
        assert "8:30 AM" in data2["response"]  # SS 15 specific opening time

    def test_greeting_and_natural_flow(self):
        """Test natural conversation flow starting with greeting"""

        # Start with greeting
        response1 = client.post("/chat", json={
            "message": "Hello"
        })
        session_id = response1.json()["session_id"]
        assert "Hello" in response1.json()["response"]

        # Ask about outlets
        response2 = client.post("/chat", json={
            "message": "Do you have stores in KL?",
            "session_id": session_id
        })
        assert response2.status_code == 200
        data2 = response2.json()
        assert "Kuala Lumpur" in data2["response"]
        assert "KLCC" in data2["response"] or "Bukit Bintang" in data2["response"]

class TestChatFlowInterruptedPaths:
    def test_session_interruption_and_recovery(self):
        """Test conversation recovery after session interruption"""

        # Start conversation
        response1 = client.post("/chat", json={
            "message": "Is there an outlet in Petaling Jaya?"
        })
        original_session_id = response1.json()["session_id"]

        # Simulate session interruption - start new conversation
        response2 = client.post("/chat", json={
            "message": "What outlets do you have?"
        })
        new_session_id = response2.json()["session_id"]

        # Verify new session was created
        assert new_session_id != original_session_id

        # Continue with new session
        response3 = client.post("/chat", json={
            "message": "In SS 2 area",
            "session_id": new_session_id
        })
        assert response3.status_code == 200

    def test_invalid_session_handling(self):
        """Test handling of invalid session IDs"""

        response = client.post("/chat", json={
            "message": "Hello",
            "session_id": "invalid-session-id"
        })
        assert response.status_code == 200
        # Should create new session for invalid ID
        assert response.json()["session_id"] != "invalid-session-id"

    def test_context_loss_and_recovery(self):
        """Test handling when context is lost mid-conversation"""

        # Start conversation with specific context
        response1 = client.post("/chat", json={
            "message": "I need info about SS 2 outlet"
        })
        session_id = response1.json()["session_id"]

        # Clear session to simulate context loss
        client.delete(f"/session/{session_id}")

        # Try to continue conversation
        response2 = client.post("/chat", json={
            "message": "What are the opening hours?",
            "session_id": session_id
        })
        assert response2.status_code == 200
        # Should ask for clarification since context is lost
        assert "which" in response2.json()["response"].lower() or "area" in response2.json()["response"].lower()

    def test_ambiguous_queries(self):
        """Test handling of ambiguous queries that might interrupt flow"""

        # Start with ambiguous query
        response1 = client.post("/chat", json={
            "message": "Do you have outlets?"
        })
        session_id = response1.json()["session_id"]
        assert "which area" in response1.json()["response"].lower() or "where" in response1.json()["response"].lower()

        # Provide partial information
        response2 = client.post("/chat", json={
            "message": "Near shopping mall",
            "session_id": session_id
        })
        assert response2.status_code == 200
        # Should still ask for more specific information

    def test_multiple_location_mentions(self):
        """Test handling when user mentions multiple locations"""

        response = client.post("/chat", json={
            "message": "Do you have outlets in both Petaling Jaya and Kuala Lumpur?"
        })
        assert response.status_code == 200
        data = response.json()
        # Should handle multiple locations appropriately
        assert "Petaling Jaya" in data["response"] and "Kuala Lumpur" in data["response"]

class TestAPIEndpoints:
    def test_conversation_history_endpoint(self):
        """Test conversation history retrieval"""

        # Create a conversation
        response1 = client.post("/chat", json={
            "message": "Hello"
        })
        session_id = response1.json()["session_id"]

        client.post("/chat", json={
            "message": "Is there an outlet in PJ?",
            "session_id": session_id
        })

        # Get conversation history
        history_response = client.get(f"/conversation/{session_id}")
        assert history_response.status_code == 200
        history = history_response.json()
        assert len(history) == 2
        assert history[0]["user_message"] == "Hello"
        assert history[1]["user_message"] == "Is there an outlet in PJ?"

    def test_session_stats_endpoint(self):
        """Test session statistics endpoint"""

        response = client.post("/chat", json={
            "message": "Hello"
        })
        session_id = response.json()["session_id"]

        stats_response = client.get(f"/session/{session_id}/stats")
        assert stats_response.status_code == 200
        stats = stats_response.json()
        assert stats["session_id"] == session_id
        assert stats["total_turns"] == 1

    def test_clear_session_endpoint(self):
        """Test session clearing functionality"""

        response = client.post("/chat", json={
            "message": "Hello"
        })
        session_id = response.json()["session_id"]

        # Clear session
        clear_response = client.delete(f"/session/{session_id}")
        assert clear_response.status_code == 200

        # Verify session is cleared
        stats_response = client.get(f"/session/{session_id}/stats")
        assert stats_response.status_code == 404

    def test_outlets_endpoints(self):
        """Test outlet information endpoints"""

        # Test get all outlets
        response = client.get("/outlets")
        assert response.status_code == 200
        outlets = response.json()
        assert len(outlets) > 0

        # Test get outlets by area
        response = client.get("/outlets/petaling_jaya")
        assert response.status_code == 200
        pj_outlets = response.json()
        assert len(pj_outlets) == 3  # Should have 3 PJ outlets

        # Test non-existent area
        response = client.get("/outlets/non_existent")
        assert response.status_code == 404

if __name__ == "__main__":
    pytest.main([__file__, "-v"])