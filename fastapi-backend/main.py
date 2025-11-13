from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from typing import Optional, List
import re
import os
import json
import html
import logging
from openai import OpenAI
from dotenv import load_dotenv
import httpx

from memory import memory_manager, ConversationTurn
from outlets import outlet_service
from planner import AgenticPlanner, ActionType
from product_kb import product_kb
from outlets_db import text2sql, initialize_outlets_db

load_dotenv()

app = FastAPI(title="Conversational Outlet Assistant", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3002", "http://127.0.0.1:3000", "http://127.0.0.1:3002"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

    @field_validator('message')
    @classmethod
    def validate_message(cls, v):
        if len(str(v)) > 10000:  # 10KB limit
            raise ValueError('Message too long')
        # Allow empty messages to be handled by the application logic
        if v is None:
            v = ""
        # Sanitize HTML/XSS
        return html.escape(str(v))

    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v):
        if v and len(v) > 100:
            raise ValueError('Session ID too long')
        return v

class ChatResponse(BaseModel):
    response: str
    session_id: str
    turn_number: int
    context_updated: bool = False

class AgenticChatResponse(BaseModel):
    response: str
    session_id: str
    turn_number: int
    context_updated: bool = False
    intent: str
    action_type: str
    reasoning: str
    confidence: float
    tools_used: List[str]

class ConversationAgent:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.outlets_data = self._get_outlets_data()
        self.planner = AgenticPlanner(self.outlets_data)

    def _get_outlets_data(self) -> str:
        """Get formatted outlet data for the LLM"""
        all_outlets = []
        for area, outlets in outlet_service.outlets.items():
            for outlet in outlets:
                all_outlets.append({
                    "name": outlet.name,
                    "location": outlet.location,
                    "area": outlet.area,
                    "opening_time": outlet.opening_time,
                    "closing_time": outlet.closing_time,
                    "phone": outlet.phone,
                    "address": outlet.address
                })
        return json.dumps(all_outlets, indent=2)

    def extract_location_context(self, message: str, session_id: str) -> None:
        """Extract and store location context from message"""
        message_lower = message.lower()

        # Check for specific locations mentioned and update context
        if "petaling jaya" in message_lower or "pj" in message_lower:
            memory_manager.update_context(session_id, "area", "petaling_jaya")
        elif "kuala lumpur" in message_lower or "kl" in message_lower:
            memory_manager.update_context(session_id, "area", "kuala_lumpur")

        # Specific locations
        if "ss 2" in message_lower or "ss2" in message_lower:
            memory_manager.update_context(session_id, "area", "petaling_jaya")
            memory_manager.update_context(session_id, "specific_location", "ss 2")
        elif "ss 15" in message_lower or "ss15" in message_lower:
            memory_manager.update_context(session_id, "area", "petaling_jaya")
            memory_manager.update_context(session_id, "specific_location", "ss 15")
        elif "damansara utama" in message_lower:
            memory_manager.update_context(session_id, "area", "petaling_jaya")
            memory_manager.update_context(session_id, "specific_location", "damansara utama")
        elif "klcc" in message_lower:
            memory_manager.update_context(session_id, "area", "kuala_lumpur")
            memory_manager.update_context(session_id, "specific_location", "klcc")
        elif "bukit bintang" in message_lower:
            memory_manager.update_context(session_id, "area", "kuala_lumpur")
            memory_manager.update_context(session_id, "specific_location", "bukit bintang")

    def get_system_prompt(self, session_id: str) -> str:
        """Generate system prompt with context and outlet data"""

        # Get conversation context
        conversation_history = memory_manager.get_conversation_context(session_id)

        # Get current context
        area = memory_manager.get_context(session_id, "area")
        specific_location = memory_manager.get_context(session_id, "specific_location")

        context_info = ""
        if area:
            context_info += f"Current area context: {area}\n"
        if specific_location:
            context_info += f"Current specific location context: {specific_location}\n"

        return f"""You are a helpful assistant for a chain of outlets/stores. Your job is to help customers find information about outlet locations, opening hours, addresses, and phone numbers.

OUTLET DATA:
{self.outlets_data}

CONVERSATION CONTEXT:
{context_info}

CONVERSATION HISTORY:
{conversation_history}

INSTRUCTIONS:
1. Be helpful and friendly
2. Use the outlet data above to answer questions about locations, hours, addresses, and phone numbers
3. Pay attention to the conversation context - if a user mentioned a specific area or location earlier, remember that context
4. If a user asks about opening hours or address without specifying which outlet, and you have context about a specific location, use that context
5. If the user's question is unclear, ask for clarification
6. Keep responses concise but informative
7. If a user asks about an outlet that doesn't exist in our data, politely let them know we don't have that location

Remember: You have access to outlets in Petaling Jaya (SS 2, SS 15, Damansara Utama) and Kuala Lumpur (KLCC, Bukit Bintang)."""

    async def process_message(self, message: str, session_id: str) -> str:
        """Process message using OpenAI GPT-4o-mini"""
        try:
            # Extract location context from current message
            self.extract_location_context(message, session_id)

            # Get system prompt with context
            system_prompt = self.get_system_prompt(session_id)

            # Call OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                max_tokens=500,
                temperature=0.7
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            # Fallback response if OpenAI fails
            return f"I'm sorry, I'm having trouble processing your request right now. Please try again. (Error: {str(e)})"

    async def process_message_with_planner(self, message: str, session_id: str) -> str:
        """Process message using the agentic planner system"""
        try:
            # Get current session context
            session_context = {
                'area': memory_manager.get_context(session_id, "area"),
                'specific_location': memory_manager.get_context(session_id, "specific_location")
            }

            # Use planner to analyze intent and plan action
            planner_result = await self.planner.process_message(message, session_context)

            # Apply context updates from planner
            for key, value in planner_result.context_updates.items():
                memory_manager.update_context(session_id, key, value)

            # Execute the planned action
            action = planner_result.action

            if action.action_type == ActionType.ASK_CLARIFICATION:
                return action.parameters['question']

            elif action.action_type == ActionType.PROVIDE_INFO:
                return action.parameters['message']

            elif action.action_type == ActionType.SEARCH_OUTLETS:
                return action.parameters['message']

            elif action.action_type == ActionType.CALCULATE:
                return action.parameters['message']

            elif action.action_type == ActionType.FINISH:
                return action.parameters['message']

            else:
                # Fallback to LLM for complex queries
                return await self.process_message(message, session_id)

        except Exception as e:
            # Fallback to original LLM processing
            return await self.process_message(message, session_id)

    async def process_message_with_planner_detailed(self, message: str, session_id: str) -> tuple:
        """Process message with detailed planner information for debugging"""
        try:
            # Get current session context
            session_context = {
                'area': memory_manager.get_context(session_id, "area"),
                'specific_location': memory_manager.get_context(session_id, "specific_location")
            }

            # Use planner to analyze intent and plan action
            planner_result = await self.planner.process_message(message, session_context)

            # Apply context updates from planner
            for key, value in planner_result.context_updates.items():
                memory_manager.update_context(session_id, key, value)

            # Execute the planned action
            action = planner_result.action
            response_text = ""

            if action.action_type == ActionType.ASK_CLARIFICATION:
                response_text = action.parameters['question']
            elif action.action_type == ActionType.PROVIDE_INFO:
                response_text = action.parameters['message']
            elif action.action_type == ActionType.SEARCH_OUTLETS:
                response_text = action.parameters['message']
            elif action.action_type == ActionType.CALCULATE:
                response_text = action.parameters['message']
            elif action.action_type == ActionType.FINISH:
                response_text = action.parameters['message']
            elif action.action_type == ActionType.GET_WEATHER:
                response_text = action.parameters['message']
            elif action.action_type == ActionType.GET_FORECAST:
                response_text = action.parameters['message']
            else:
                response_text = await self.process_message(message, session_id)

            return (
                response_text,
                planner_result.intent.intent.value,
                planner_result.action.action_type.value,
                planner_result.action.reasoning,
                planner_result.intent.confidence,
                planner_result.action.required_tools
            )

        except Exception as e:
            logging.error(f"ERROR in process_message_with_planner_detailed: {str(e)}")
            # Fallback to basic LLM response
            fallback_response = await self.process_message(message, session_id)
            return (
                fallback_response,
                "general_question",
                "provide_info",
                "Fallback due to planner error",
                0.5,
                []
            )

    async def get_fallback_response(self, message: str) -> str:
        """Generate a safe fallback response when main processing fails"""
        message_lower = message.lower()

        # Simple keyword-based fallback responses
        if any(word in message_lower for word in ['outlet', 'shop', 'store', 'mall']):
            return "I can help you find outlet information. Could you specify which area you're interested in? For example, Kuala Lumpur or Petaling Jaya."
        elif any(word in message_lower for word in ['weather', 'temperature', 'rain', 'sunny']):
            return "I can provide weather information. Could you specify which city you'd like the weather for?"
        elif any(word in message_lower for word in ['calculate', 'math', 'compute', 'number']):
            return "I can help with calculations. Could you provide the specific calculation you need?"
        elif any(word in message_lower for word in ['hello', 'hi', 'hey']):
            return "Hello! I'm here to help you find outlets, get weather information, or perform calculations. What would you like to know?"
        else:
            return "I'm here to help with outlet information, weather updates, and calculations. Could you please rephrase your question?"
            # fallback_response = await self.process_message(message, session_id)
            # return (
            #     fallback_response,
            #     "error_fallback",
            #     "llm_fallback",
            #     f"Planner failed, using LLM fallback: {str(e)}",
            #     0.0,
            #     ["openai_llm"]
            # )

agent = ConversationAgent()

# Initialize databases
@app.on_event("startup")
async def startup_event():
    """Initialize databases and services on startup"""
    try:
        print("🚀 Starting up application...")

        # Initialize outlets database
        print("📊 Initializing outlets database...")
        initialize_outlets_db()

        # Initialize product knowledge base
        print("🔍 Initializing product knowledge base...")
        if product_kb.initialize():
            product_kb._initialized = True
            print("✅ Product KB initialized")
        else:
            print("⚠️  Product KB initialization failed, will retry on first request")

        print("✅ Application startup complete")

    except Exception as e:
        print(f"❌ Startup error: {e}")
        # Don't prevent startup, just log the error

@app.get("/")
async def root():
    return {"message": "Conversational Outlet Assistant API", "version": "1.0.0"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Get or create session
        session_id = memory_manager.get_or_create_session(request.session_id)

        # Process the message with agentic planner first, fallback to LLM
        response = await agent.process_message_with_planner(request.message, session_id)

        # Add the turn to memory
        memory_manager.add_turn(session_id, request.message, response)

        # Get conversation history to determine turn number
        history = memory_manager.get_conversation_history(session_id)
        turn_number = len(history)

        return ChatResponse(
            response=response,
            session_id=session_id,
            turn_number=turn_number,
            context_updated=True
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")

@app.post("/chat/agentic", response_model=AgenticChatResponse)
async def agentic_chat(request: ChatRequest):
    """Chat endpoint using the agentic planner system with detailed response"""
    session_id = None
    fallback_response = "I'm experiencing technical difficulties. Please try again later."

    try:
        # Validate and sanitize input
        if not request.message or len(request.message.strip()) == 0:
            return AgenticChatResponse(
                response="I'm here to help! What would you like to know about outlets, weather, or calculations?",
                session_id=memory_manager.get_or_create_session(request.session_id),
                turn_number=1,
                context_updated=False,
                intent="unclear",
                action_type="ask_clarification",
                reasoning="Empty or whitespace-only message received",
                confidence=1.0,
                tools_used=[]
            )

        # Get or create session with error handling
        try:
            session_id = memory_manager.get_or_create_session(request.session_id)
        except Exception as e:
            logging.error(f"Session management error: {e}")
            session_id = memory_manager.get_or_create_session(None)  # Create new session

        # Process the message with enhanced error handling
        try:
            response_data = await agent.process_message_with_planner_detailed(request.message, session_id)
            response_text, intent, action_type, reasoning, confidence, tools_used = response_data
        except httpx.TimeoutException:
            return AgenticChatResponse(
                response="The service is taking longer than expected. Please try again in a moment.",
                session_id=session_id,
                turn_number=1,
                context_updated=False,
                intent="error",
                action_type="provide_info",
                reasoning="Network timeout occurred",
                confidence=1.0,
                tools_used=[]
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code >= 500:
                error_response = "One of our services is currently unavailable. Please try again later."
            else:
                error_response = "I encountered an issue processing your request. Could you please rephrase?"

            return AgenticChatResponse(
                response=error_response,
                session_id=session_id,
                turn_number=1,
                context_updated=False,
                intent="error",
                action_type="provide_info",
                reasoning=f"HTTP error {e.response.status_code}",
                confidence=1.0,
                tools_used=[]
            )
        except Exception as e:
            logging.error(f"Planner processing error: {e}")
            # Fallback to simple response
            return AgenticChatResponse(
                response=await agent.get_fallback_response(request.message),
                session_id=session_id,
                turn_number=1,
                context_updated=False,
                intent="general_question",
                action_type="provide_info",
                reasoning="Fallback due to processing error",
                confidence=0.5,
                tools_used=[]
            )

        # Add the turn to memory with error handling
        try:
            memory_manager.add_turn(session_id, request.message, response_text)
        except Exception as e:
            logging.error(f"Memory storage error: {e}")
            # Continue without storing - not critical for response

        # Get conversation history to determine turn number
        try:
            history = memory_manager.get_conversation_history(session_id)
            turn_number = len(history)
        except Exception:
            turn_number = 1  # Default if history retrieval fails

        return AgenticChatResponse(
            response=response_text,
            session_id=session_id,
            turn_number=turn_number,
            context_updated=True,
            intent=intent,
            action_type=action_type,
            reasoning=reasoning,
            confidence=confidence,
            tools_used=tools_used
        )

    except ValueError as e:
        # Validation errors (bad input)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Unexpected error in agentic_chat: {e}")
        # Last resort fallback
        fallback_session = session_id if session_id else "error_session"
        raise HTTPException(
            status_code=500,
            detail="I apologize, but I'm experiencing technical difficulties. Please try again later."
        )

@app.get("/conversation/{session_id}", response_model=List[ConversationTurn])
async def get_conversation_history(session_id: str):
    try:
        history = memory_manager.get_conversation_history(session_id)
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving conversation: {str(e)}")

@app.get("/session/{session_id}/stats")
async def get_session_stats(session_id: str):
    try:
        stats = memory_manager.get_session_stats(session_id)
        if not stats:
            raise HTTPException(status_code=404, detail="Session not found")
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving session stats: {str(e)}")

@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    try:
        success = memory_manager.clear_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"message": "Session cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing session: {str(e)}")

@app.get("/outlets")
async def get_all_outlets():
    try:
        all_outlets = []
        for area, outlets in outlet_service.outlets.items():
            all_outlets.extend(outlets)
        return all_outlets
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving outlets: {str(e)}")

@app.get("/outlets/{area}")
async def get_outlets_by_area(area: str):
    try:
        outlets = outlet_service.find_outlets_by_area(area)
        if not outlets:
            raise HTTPException(status_code=404, detail=f"No outlets found in {area}")
        return outlets
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving outlets: {str(e)}")

class ProductQuery(BaseModel):
    query: str
    max_results: Optional[int] = 5

class OutletQuery(BaseModel):
    query: str

@app.get("/products")
async def search_products(query: str, max_results: int = 5):
    """
    Search ZUS Coffee drinkware products using RAG

    - **query**: Natural language query about products (e.g., "travel mugs for commuting")
    - **max_results**: Maximum number of results to return (default: 5)
    """
    try:
        if not query or query.strip() == "":
            raise HTTPException(status_code=400, detail="Query parameter cannot be empty")

        # Initialize product KB if not already done
        if not hasattr(product_kb, '_initialized'):
            print("Initializing product knowledge base...")
            if not product_kb.initialize():
                raise HTTPException(status_code=503, detail="Product knowledge base unavailable")
            product_kb._initialized = True

        result = product_kb.query(query, max_results)
        print(result["answer"])
        return {
            "query": query,
            "answer": result["answer"],
            "products": result["products"],
            "sources": result["sources"],
            "total_found": result.get("total_found", 0),
            "success": True
        }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Product search error: {e}")
        raise HTTPException(status_code=500, detail=f"Error searching products: {str(e)}")

@app.post("/products")
async def search_products_post(request: ProductQuery):
    """
    Search ZUS Coffee drinkware products using RAG (POST method)

    Request body:
    - **query**: Natural language query about products
    - **max_results**: Maximum number of results to return (optional)
    """
    return await search_products(request.query, request.max_results)

@app.get("/outlets/search")
async def search_outlets_nl(query: str):
    """
    Search outlets using natural language with Text2SQL

    - **query**: Natural language query (e.g., "outlets with drive-thru in KL")
    """
    try:
        if not query or query.strip() == "":
            raise HTTPException(status_code=400, detail="Query parameter cannot be empty")

        result = text2sql.query(query)

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])

        return {
            "query": query,
            "sql_query": result["sql_query"],
            "results": result["results"],
            "count": result["count"],
            "success": True
        }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Outlet search error: {e}")
        raise HTTPException(status_code=500, detail=f"Error searching outlets: {str(e)}")

@app.post("/outlets/search")
async def search_outlets_nl_post(request: OutletQuery):
    """
    Search outlets using natural language with Text2SQL (POST method)

    Request body:
    - **query**: Natural language query about outlets
    """
    return await search_outlets_nl(request.query)