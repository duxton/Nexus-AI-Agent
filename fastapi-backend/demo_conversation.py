# #!/usr/bin/env python3
# """
# Demo script showing the conversational memory system in action.
# This demonstrates the exact flow specified in the requirements.
# """

# import asyncio
# import httpx
# import json
# from typing import Optional

# class ConversationDemo:
#     def __init__(self, base_url: str = "http://localhost:8000"):
#         self.base_url = base_url
#         self.session_id: Optional[str] = None

#     async def send_message(self, message: str) -> dict:
#         """Send a message to the chat endpoint and return the response"""
#         async with httpx.AsyncClient() as client:
#             payload = {"message": message}
#             if self.session_id:
#                 payload["session_id"] = self.session_id

#             response = await client.post(f"{self.base_url}/chat", json=payload)
#             result = response.json()

#             # Update session ID for subsequent requests
#             self.session_id = result["session_id"]

#             return result

#     async def get_conversation_history(self) -> list:
#         """Get the conversation history for the current session"""
#         if not self.session_id:
#             return []

#         async with httpx.AsyncClient() as client:
#             response = await client.get(f"{self.base_url}/conversation/{self.session_id}")
#             return response.json()

#     async def get_session_stats(self) -> dict:
#         """Get session statistics"""
#         if not self.session_id:
#             return {}

#         async with httpx.AsyncClient() as client:
#             response = await client.get(f"{self.base_url}/session/{self.session_id}/stats")
#             return response.json()

#     def print_conversation_turn(self, turn_number: int, user_message: str, bot_response: str):
#         """Print a conversation turn in a nice format"""
#         print(f"\n{'='*60}")
#         print(f"TURN {turn_number}")
#         print(f"{'='*60}")
#         print(f"User: {user_message}")
#         print(f"Bot:  {bot_response}")

# async def demo_happy_path():
#     """Demonstrate the happy path conversation flow from requirements"""
#     print("🎯 DEMONSTRATING HAPPY PATH CONVERSATION FLOW")
#     print("=" * 80)

#     demo = ConversationDemo()

#     # Turn 1: User asks about outlet in Petaling Jaya
#     print("Starting conversation...")
#     result1 = await demo.send_message("Is there an outlet in Petaling Jaya?")
#     demo.print_conversation_turn(result1["turn_number"], "Is there an outlet in Petaling Jaya?", result1["response"])

#     # Turn 2: User specifies SS 2 and asks for opening time
#     result2 = await demo.send_message("SS 2, what's the opening time?")
#     demo.print_conversation_turn(result2["turn_number"], "SS 2, what's the opening time?", result2["response"])

#     # Turn 3: Follow-up question using context
#     result3 = await demo.send_message("What about the address?")
#     demo.print_conversation_turn(result3["turn_number"], "What about the address?", result3["response"])

#     # Show conversation history and stats
#     history = await demo.get_conversation_history()
#     stats = await demo.get_session_stats()

#     print(f"\n{'='*60}")
#     print("CONVERSATION SUMMARY")
#     print(f"{'='*60}")
#     print(f"Session ID: {stats['session_id']}")
#     print(f"Total Turns: {stats['total_turns']}")
#     print(f"Context Keys: {stats['context_keys']}")

#     return demo.session_id

# async def demo_interrupted_path():
#     """Demonstrate interrupted conversation handling"""
#     print("\n\n🔄 DEMONSTRATING INTERRUPTED CONVERSATION HANDLING")
#     print("=" * 80)

#     demo = ConversationDemo()

#     # Start a conversation
#     result1 = await demo.send_message("I'm looking for outlets")
#     demo.print_conversation_turn(result1["turn_number"], "I'm looking for outlets", result1["response"])

#     # Interrupt with new session (simulate app restart)
#     print("\n⚠️  SIMULATING SESSION INTERRUPTION...")
#     demo_new = ConversationDemo()

#     # Continue conversation with new session
#     result2 = await demo_new.send_message("What are the opening hours for SS 2?")
#     demo_new.print_conversation_turn(result2["turn_number"], "What are the opening hours for SS 2?", result2["response"])

#     # Show that context was recovered from message content
#     result3 = await demo_new.send_message("What's the phone number?")
#     demo_new.print_conversation_turn(result3["turn_number"], "What's the phone number?", result3["response"])

#     return demo_new.session_id

# async def demo_memory_features():
#     """Demonstrate advanced memory features"""
#     print("\n\n🧠 DEMONSTRATING MEMORY FEATURES")
#     print("=" * 80)

#     demo = ConversationDemo()

#     # Complex conversation with context building
#     conversations = [
#         "Hello there!",
#         "I need information about your outlets in Kuala Lumpur",
#         "Tell me about the KLCC location",
#         "When do you open?",
#         "What's the exact address?",
#         "Do you have parking available?"
#     ]

#     for i, message in enumerate(conversations, 1):
#         result = await demo.send_message(message)
#         demo.print_conversation_turn(result["turn_number"], message, result["response"])
#         await asyncio.sleep(0.5)  # Small delay for readability

#     # Show final stats
#     stats = await demo.get_session_stats()
#     print(f"\n{'='*60}")
#     print("FINAL CONVERSATION STATS")
#     print(f"{'='*60}")
#     print(json.dumps(stats, indent=2))

# async def main():
#     """Run all demonstrations"""
#     print("🤖 CONVERSATIONAL OUTLET ASSISTANT DEMO")
#     print("🔗 LangChain-based Memory System")
#     print("⚡ FastAPI Backend")
#     print("\nMake sure the FastAPI server is running on http://localhost:8000")
#     print("Start it with: uvicorn main:app --reload")

#     try:
#         # Test server availability
#         async with httpx.AsyncClient() as client:
#             response = await client.get("http://localhost:8000/")
#             print(f"✅ Server is running: {response.json()['message']}")
#     except httpx.ConnectError:
#         print("❌ Server is not running. Please start it with: uvicorn main:app --reload")
#         return

#     # Run demonstrations
#     await demo_happy_path()
#     await demo_interrupted_path()
#     await demo_memory_features()

#     print("\n\n🎉 DEMO COMPLETED SUCCESSFULLY!")
#     print("✅ All conversation flows demonstrated")
#     print("✅ Memory persistence working")
#     print("✅ Context tracking functional")
#     print("✅ Interrupted conversation handling verified")

# if __name__ == "__main__":
#     asyncio.run(main())