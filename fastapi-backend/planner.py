from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel
from enum import Enum
import re
import json
from datetime import datetime, time
from openai import OpenAI
import os

class IntentType(Enum):
    GREETING = "greeting"
    OUTLET_SEARCH = "outlet_search"
    HOURS_INQUIRY = "hours_inquiry"
    LOCATION_INQUIRY = "location_inquiry"
    PHONE_INQUIRY = "phone_inquiry"
    CALCULATION = "calculation"
    WEATHER_CURRENT = "weather_current"
    WEATHER_FORECAST = "weather_forecast"
    WEATHER_LOCATION = "weather_location"
    PRODUCT_SEARCH = "product_search"
    OUTLET_SEARCH_NL = "outlet_search_nl"
    GENERAL_QUESTION = "general_question"
    GOODBYE = "goodbye"
    UNCLEAR = "unclear"

class ActionType(Enum):
    ASK_CLARIFICATION = "ask_clarification"
    SEARCH_OUTLETS = "search_outlets"
    CALCULATE = "calculate"
    GET_WEATHER = "get_weather"
    GET_FORECAST = "get_forecast"
    SEARCH_WEATHER_LOCATION = "search_weather_location"
    SEARCH_PRODUCTS = "search_products"
    SEARCH_OUTLETS_NL = "search_outlets_nl"
    PROVIDE_INFO = "provide_info"
    RAG_SEARCH = "rag_search"
    FINISH = "finish"

class ParsedIntent(BaseModel):
    intent: IntentType
    entities: Dict[str, Any]
    missing_info: List[str]
    confidence: float

class PlannedAction(BaseModel):
    action_type: ActionType
    parameters: Dict[str, Any]
    reasoning: str
    required_tools: List[str]

class PlannerResult(BaseModel):
    intent: ParsedIntent
    action: PlannedAction
    context_updates: Dict[str, Any]

class IntentClassifier:
    """Classifies user intents and extracts entities"""

    def __init__(self):
        self.location_patterns = [
            r'\b(?:petaling jaya|pj)\b',
            r'\b(?:kuala lumpur|kl)\b',
            r'\b(?:ss\s*2|ss2)\b',
            r'\b(?:ss\s*15|ss15)\b',
            r'\bdamansara utama\b',
            r'\bklcc\b',
            r'\bbukit bintang\b'
        ]

        self.malaysia_cities = [
            r'\b(?:kuala lumpur|kl|johor|penang|selangor|sabah|sarawak)\b',
            r'\b(?:ipoh|malacca|melaka|kuching|kota kinabalu|shah alam)\b',
            r'\b(?:petaling jaya|pj|subang jaya|klang|ampang)\b'
        ]

        self.calculation_patterns = [
            r'\d+\s*[\+\-\*\/]\s*\d+',
            r'calculate|compute|math|plus|minus|times|divided|sum|total'
        ]

        self.weather_current_patterns = [
            r'\b(?:weather|temperature|temp|climate|conditions?)\b',
            r'\b(?:hot|cold|warm|cool|humid|dry)\b',
            r'\b(?:current|now|today|right now)\b.*\b(?:weather|temperature)\b',
            r'\b(?:what\'?s the weather|how\'?s the weather|weather like)\b'
        ]

        self.weather_forecast_patterns = [
            r'\b(?:forecast|tomorrow|next|week|days?|future)\b.*\b(?:weather|rain|storm)\b',
            r'\b(?:will it rain|going to rain|rain today|rain tomorrow)\b',
            r'\b(?:weather for|forecast for)\b',
            r'\b(?:3[\s-]?day|weekly|weekend) (?:weather|forecast)\b'
        ]

        self.greeting_patterns = [
            r'\b(?:hi|hello|hey|good morning|good afternoon|good evening)\b'
        ]

        self.goodbye_patterns = [
            r'\b(?:bye|goodbye|thank you|thanks|see you)\b'
        ]

        self.product_patterns = [
            r'\b(?:product|products|drinkware|mug|mugs|cup|cups|tumbler|tumblers|bottle|bottles)\b',
            r'\b(?:travel mug|coffee mug|espresso cup|french press|cold brew|thermal|carafe)\b',
            r'\b(?:ceramic|stainless steel|bamboo|glass|eco-friendly)\b',
            r'\b(?:buy|purchase|shop|store|merchandise|buy online)\b'
        ]

        self.advanced_outlet_patterns = [
            r'\b(?:find|search|locate|discover)\b.*\b(?:outlet|store|branch|location)\b',
            r'\b(?:drive.?thru|drive.?through)\b',
            r'\b(?:24.?hour|24.?hours|overnight|late night)\b',
            r'\b(?:parking|wifi|meeting|family.?friendly|student.?friendly)\b',
            r'\b(?:near|nearby|close to|around)\b'
        ]

    def classify_intent(self, message: str, session_context: Dict[str, Any] = None) -> ParsedIntent:
        """Classify user intent and extract entities"""
        message_lower = message.lower().strip()
        entities = {}
        missing_info = []

        # Handle empty or whitespace-only messages
        if not message_lower:
            return ParsedIntent(
                intent=IntentType.UNCLEAR,
                entities={},
                missing_info=['message'],
                confidence=0.0
            )

        # Extract locations (outlets)
        for pattern in self.location_patterns:
            if re.search(pattern, message_lower):
                entities['location'] = re.search(pattern, message_lower).group()
                break

        # Extract weather locations (Malaysian cities)
        for pattern in self.malaysia_cities:
            if re.search(pattern, message_lower):
                entities['weather_location'] = re.search(pattern, message_lower).group()
                break

        # Extract forecast duration
        forecast_match = re.search(r'(\d+)[\s-]?day', message_lower)
        if forecast_match:
            entities['forecast_days'] = int(forecast_match.group(1))

        # Determine intent
        if re.search('|'.join(self.greeting_patterns), message_lower):
            intent = IntentType.GREETING
            confidence = 0.9

        elif re.search('|'.join(self.goodbye_patterns), message_lower):
            intent = IntentType.GOODBYE
            confidence = 0.9

        elif re.search('|'.join(self.calculation_patterns), message_lower):
            intent = IntentType.CALCULATION
            confidence = 0.8
            # Extract numbers and operators
            math_match = re.search(r'(\d+)\s*([\+\-\*\/])\s*(\d+)', message)
            if math_match:
                entities['operand1'] = int(math_match.group(1))
                entities['operator'] = math_match.group(2)
                entities['operand2'] = int(math_match.group(3))
            else:
                missing_info.append('calculation_expression')
                confidence = 0.6  # Lower confidence for vague calculation request

        elif re.search('|'.join(self.weather_forecast_patterns), message_lower):
            intent = IntentType.WEATHER_FORECAST
            confidence = 0.8
            if 'forecast_days' not in entities:
                entities['forecast_days'] = 3  # Default to 3-day forecast

        elif re.search('|'.join(self.weather_current_patterns), message_lower):
            intent = IntentType.WEATHER_CURRENT
            confidence = 0.8
            # Check if location is missing for weather requests
            if 'weather_location' not in entities:
                # Check for very vague weather requests
                vague_weather_terms = ['weather', 'temperature', 'temp', 'climate']
                if any(term == message_lower.strip() for term in vague_weather_terms):
                    missing_info.append('location')
                    confidence = 0.6

        elif re.search('|'.join(self.product_patterns), message_lower):
            intent = IntentType.PRODUCT_SEARCH
            confidence = 0.8
            # Extract product-related entities
            entities['product_query'] = message_lower

        elif re.search('|'.join(self.advanced_outlet_patterns), message_lower):
            # Advanced outlet search with natural language
            intent = IntentType.OUTLET_SEARCH_NL
            confidence = 0.8
            entities['outlet_query'] = message_lower

        elif 'outlet' in message_lower or 'store' in message_lower or 'shop' in message_lower or 'mall' in message_lower:
            intent = IntentType.OUTLET_SEARCH
            confidence = 0.8
            if 'location' not in entities:
                missing_info.append('location')
                # Very vague outlet requests
                vague_outlet_terms = ['outlet', 'outlets', 'store', 'stores', 'shop', 'shops', 'show outlets', 'find outlets']
                if any(term == message_lower.strip() for term in vague_outlet_terms):
                    confidence = 0.6

        elif any(word in message_lower for word in ['hour', 'time', 'open', 'close', 'when']):
            intent = IntentType.HOURS_INQUIRY
            confidence = 0.8
            if 'location' not in entities and not session_context.get('area'):
                missing_info.append('location')

        elif any(word in message_lower for word in ['address', 'where', 'located']):
            intent = IntentType.LOCATION_INQUIRY
            confidence = 0.8
            if 'location' not in entities and not session_context.get('area'):
                missing_info.append('location')

        elif any(word in message_lower for word in ['phone', 'number', 'contact', 'call']):
            intent = IntentType.PHONE_INQUIRY
            confidence = 0.8
            if 'location' not in entities and not session_context.get('area'):
                missing_info.append('location')

        # Handle single-word vague requests
        elif message_lower.strip() in ['calculate', 'computation', 'math']:
            intent = IntentType.CALCULATION
            confidence = 0.5
            missing_info.append('calculation_expression')

        else:
            intent = IntentType.UNCLEAR
            confidence = 0.3
            missing_info.append('clarification')

        return ParsedIntent(
            intent=intent,
            entities=entities,
            missing_info=missing_info,
            confidence=confidence
        )

class ToolExecutor:
    """Executes various tools based on planned actions"""

    def __init__(self, outlets_data: str):
        self.outlets_data = outlets_data
        # Import weather agent here to avoid circular imports
        try:
            from weather_agent import weather_agent
            self.weather_agent = weather_agent
        except ImportError:
            self.weather_agent = None

    def execute_calculation(self, operand1: int, operator: str, operand2: int) -> str:
        """Execute mathematical calculations"""
        try:
            if operator == '+':
                result = operand1 + operand2
            elif operator == '-':
                result = operand1 - operand2
            elif operator == '*':
                result = operand1 * operand2
            elif operator == '/':
                if operand2 == 0:
                    return "Error: Cannot divide by zero"
                result = operand1 / operand2
            else:
                return "Error: Unsupported operator"

            return f"{operand1} {operator} {operand2} = {result}"
        except Exception as e:
            return f"Calculation error: {str(e)}"

    def search_outlets(self, location: str = None, area: str = None) -> str:
        """Search for outlets based on location/area"""
        outlets_data = json.loads(self.outlets_data)

        if location:
            location_lower = location.lower()
            filtered_outlets = [
                outlet for outlet in outlets_data
                if location_lower in outlet['location'].lower() or
                   location_lower in outlet['area'].lower()
            ]
        elif area:
            area_lower = area.lower()
            filtered_outlets = [
                outlet for outlet in outlets_data
                if area_lower in outlet['area'].lower()
            ]
        else:
            filtered_outlets = outlets_data

        if not filtered_outlets:
            return "No outlets found matching your criteria."

        result = f"Found {len(filtered_outlets)} outlet(s):\n"
        for outlet in filtered_outlets:
            result += f"• {outlet['name']} - {outlet['location']}\n"

        return result

    def get_hours_info(self, location: str = None, area: str = None) -> str:
        """Get opening hours for outlets"""
        outlets_data = json.loads(self.outlets_data)

        if location:
            location_lower = location.lower()
            filtered_outlets = [
                outlet for outlet in outlets_data
                if location_lower in outlet['location'].lower() or
                   location_lower in outlet['area'].lower()
            ]
        elif area:
            area_lower = area.lower()
            filtered_outlets = [
                outlet for outlet in outlets_data
                if area_lower in outlet['area'].lower()
            ]
        else:
            return "Please specify which outlet you'd like hours for."

        if not filtered_outlets:
            return "No outlets found matching your criteria."

        result = "Opening hours:\n"
        for outlet in filtered_outlets:
            result += f"• {outlet['name']}: {outlet['opening_time']} - {outlet['closing_time']}\n"

        return result

    async def get_current_weather(self, location: str = None) -> str:
        """Get current weather information"""
        if not self.weather_agent:
            return "I'm sorry, but the weather service is currently unavailable. Please try again later or contact support."

        try:
            result = await self.weather_agent.get_current_weather(location)
            if result.get("success"):
                return result["formatted_response"]
            elif result.get("error"):
                error_msg = result.get("error", "Unknown error")
                if "timeout" in error_msg.lower():
                    return "The weather service is taking longer than expected to respond. Please try again in a moment."
                elif "api" in error_msg.lower() and "error" in error_msg.lower():
                    return "The weather service is currently experiencing issues. Please try again later."
                else:
                    return f"I'm unable to fetch weather information at the moment. {error_msg}"
            else:
                return "I couldn't retrieve weather information right now. Please try again later."
        except Exception as e:
            return "The weather service is currently unavailable. Please try again later."

    async def get_weather_forecast(self, days: int = 3, location: str = None) -> str:
        """Get weather forecast information"""
        if not self.weather_agent:
            return "I'm sorry, but the weather service is currently unavailable. Please try again later or contact support."

        try:
            result = await self.weather_agent.get_weather_forecast(days, location)
            if result.get("success"):
                return result["formatted_response"]
            elif result.get("error"):
                error_msg = result.get("error", "Unknown error")
                if "timeout" in error_msg.lower():
                    return "The weather service is taking longer than expected to respond. Please try again in a moment."
                elif "api" in error_msg.lower() and "error" in error_msg.lower():
                    return "The weather service is currently experiencing issues. Please try again later."
                else:
                    return f"I'm unable to fetch weather forecast at the moment. {error_msg}"
            else:
                return "I couldn't retrieve weather forecast right now. Please try again later."
        except Exception:
            return "The weather service is currently unavailable. Please try again later."

    async def search_products(self, query: str) -> str:
        """Search for ZUS Coffee drinkware products using RAG"""
        try:
            # Import here to avoid circular imports
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "http://localhost:8000/products",
                    params={"query": query, "max_results": 3}
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("answer", "No products found.")
                else:
                    return "I'm unable to search products at the moment. Please try again later."

        except Exception as e:
            return f"Product search is currently unavailable: {str(e)}"

    async def search_outlets_nl(self, query: str) -> str:
        """Search outlets using natural language Text2SQL"""
        try:
            # Import here to avoid circular imports
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "http://localhost:8000/outlets/search",
                    params={"query": query}
                )

                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])

                    if not results:
                        return "No outlets found matching your criteria."

                    # Format results
                    result_text = f"Found {len(results)} outlet(s):\n\n"
                    for outlet in results[:5]:  # Limit to 5 results
                        result_text += f"📍 **{outlet.get('name', 'Unknown')}**\n"
                        result_text += f"   📧 {outlet.get('address', 'Address not available')}\n"

                        if outlet.get('phone'):
                            result_text += f"   📞 {outlet['phone']}\n"

                        if outlet.get('opening_time') and outlet.get('closing_time'):
                            result_text += f"   🕐 {outlet['opening_time']} - {outlet['closing_time']}\n"

                        # Show special features
                        features = []
                        if outlet.get('has_drive_thru'):
                            features.append("Drive-thru")
                        if outlet.get('is_24_hours'):
                            features.append("24-hours")
                        if outlet.get('has_wifi'):
                            features.append("WiFi")

                        if features:
                            result_text += f"   ✨ {', '.join(features)}\n"

                        result_text += "\n"

                    return result_text

                else:
                    return "I'm unable to search outlets at the moment. Please try again later."

        except Exception as e:
            return f"Outlet search is currently unavailable: {str(e)}"

    async def search_weather_locations(self, query: str) -> str:
        """Search for weather locations"""
        if not self.weather_agent:
            return "Weather service is currently unavailable. Please ensure WEATHER_API_KEY is configured."

        try:
            result = await self.weather_agent.search_weather_locations(query)
            if result.get("success"):
                return result["formatted_response"]
            else:
                return f"Location Search Error: {result.get('error', 'Unknown error occurred')}"
        except Exception as e:
            return f"Failed to search locations: {str(e)}"

class ActionPlanner:
    """Plans next actions based on intent and context"""

    def __init__(self, tool_executor: ToolExecutor):
        self.tool_executor = tool_executor

    def plan_action(self, intent: ParsedIntent, session_context: Dict[str, Any]) -> PlannedAction:
        """Plan the next action based on parsed intent"""

        if intent.intent == IntentType.GREETING:
            return PlannedAction(
                action_type=ActionType.PROVIDE_INFO,
                parameters={"message": "Hello! I'm here to help you find information about our outlets. How can I assist you today?"},
                reasoning="User greeted the bot, respond warmly and offer help",
                required_tools=[]
            )

        elif intent.intent == IntentType.GOODBYE:
            return PlannedAction(
                action_type=ActionType.FINISH,
                parameters={"message": "Thank you for using our outlet assistant! Have a great day!"},
                reasoning="User is ending conversation, provide polite farewell",
                required_tools=[]
            )

        elif intent.intent == IntentType.CALCULATION:
            if intent.missing_info:
                return PlannedAction(
                    action_type=ActionType.ASK_CLARIFICATION,
                    parameters={"question": "I'd be happy to help with calculations! Could you please provide a clear math expression? For example: '5 + 3' or '10 * 2'"},
                    reasoning="Missing calculation expression, need clarification",
                    required_tools=[]
                )
            else:
                return PlannedAction(
                    action_type=ActionType.CALCULATE,
                    parameters=intent.entities,
                    reasoning="User wants calculation and all parameters are available",
                    required_tools=["calculator"]
                )

        elif intent.intent == IntentType.WEATHER_CURRENT:
            if 'location' in intent.missing_info:
                return PlannedAction(
                    action_type=ActionType.ASK_CLARIFICATION,
                    parameters={"question": "Which city would you like the weather for? I can provide weather for any Malaysian city. If you don't specify, I'll show weather for Kuala Lumpur."},
                    reasoning="Very vague weather request, asking for clarification",
                    required_tools=[]
                )
            else:
                location = intent.entities.get('weather_location', 'Kuala Lumpur, Malaysia')
                return PlannedAction(
                    action_type=ActionType.GET_WEATHER,
                    parameters={"location": location},
                    reasoning="User wants current weather information",
                    required_tools=["weather_api"]
                )

        elif intent.intent == IntentType.WEATHER_FORECAST:
            if 'location' in intent.missing_info:
                return PlannedAction(
                    action_type=ActionType.ASK_CLARIFICATION,
                    parameters={"question": "Which city would you like the weather forecast for? I can provide forecasts for any Malaysian city."},
                    reasoning="Missing location for weather forecast",
                    required_tools=[]
                )
            else:
                location = intent.entities.get('weather_location', 'Kuala Lumpur, Malaysia')
                days = intent.entities.get('forecast_days', 3)
                return PlannedAction(
                    action_type=ActionType.GET_FORECAST,
                    parameters={"location": location, "days": days},
                    reasoning="User wants weather forecast information",
                    required_tools=["weather_api"]
                )

        elif intent.intent == IntentType.PRODUCT_SEARCH:
            return PlannedAction(
                action_type=ActionType.SEARCH_PRODUCTS,
                parameters={"query": intent.entities.get('product_query', '')},
                reasoning="User wants to search for ZUS Coffee drinkware products",
                required_tools=["product_kb"]
            )

        elif intent.intent == IntentType.OUTLET_SEARCH_NL:
            return PlannedAction(
                action_type=ActionType.SEARCH_OUTLETS_NL,
                parameters={"query": intent.entities.get('outlet_query', '')},
                reasoning="User wants to search outlets using natural language query",
                required_tools=["outlets_db"]
            )

        elif intent.intent == IntentType.OUTLET_SEARCH:
            if 'location' in intent.missing_info and not session_context.get('area'):
                return PlannedAction(
                    action_type=ActionType.ASK_CLARIFICATION,
                    parameters={"question": "Which area are you interested in? We have outlets in Petaling Jaya (SS 2, SS 15, Damansara Utama) and Kuala Lumpur (KLCC, Bukit Bintang)."},
                    reasoning="Missing location information for outlet search",
                    required_tools=[]
                )
            else:
                search_params = {}
                if 'location' in intent.entities:
                    search_params['location'] = intent.entities['location']
                elif session_context.get('area'):
                    search_params['area'] = session_context['area']

                return PlannedAction(
                    action_type=ActionType.SEARCH_OUTLETS,
                    parameters=search_params,
                    reasoning="User wants outlet information and location is available",
                    required_tools=["outlet_search"]
                )

        elif intent.intent == IntentType.HOURS_INQUIRY:
            if 'location' in intent.missing_info and not session_context.get('area') and not session_context.get('last_outlet_mentioned'):
                return PlannedAction(
                    action_type=ActionType.ASK_CLARIFICATION,
                    parameters={"question": "Which outlet would you like the opening hours for? Please specify the location."},
                    reasoning="Missing location information for hours inquiry",
                    required_tools=[]
                )
            else:
                search_params = {}
                if 'location' in intent.entities:
                    search_params['location'] = intent.entities['location']
                elif session_context.get('last_outlet_mentioned'):
                    # Use the last outlet mentioned in conversation
                    search_params['location'] = session_context['last_outlet_mentioned']
                elif session_context.get('specific_location'):
                    search_params['location'] = session_context['specific_location']
                elif session_context.get('area'):
                    search_params['area'] = session_context['area']

                return PlannedAction(
                    action_type=ActionType.PROVIDE_INFO,
                    parameters={"tool_call": "get_hours_info", "tool_params": search_params},
                    reasoning="User wants hours information and location is available from context",
                    required_tools=["outlet_search"]
                )

        elif intent.intent == IntentType.UNCLEAR:
            return PlannedAction(
                action_type=ActionType.ASK_CLARIFICATION,
                parameters={"question": "I'm not sure I understand. Are you looking for outlet locations, opening hours, contact information, or something else? I can also help with simple calculations!"},
                reasoning="User intent is unclear, need clarification",
                required_tools=[]
            )

        else:
            # Default fallback
            return PlannedAction(
                action_type=ActionType.ASK_CLARIFICATION,
                parameters={"question": "How can I help you today? I can provide information about our outlet locations, hours, contact details, current weather conditions, and weather forecasts for Malaysia."},
                reasoning="Fallback action for unhandled intents",
                required_tools=[]
            )

class AgenticPlanner:
    """Main orchestrator that combines intent classification, action planning, and tool execution"""

    def __init__(self, outlets_data: str):
        self.intent_classifier = IntentClassifier()
        self.tool_executor = ToolExecutor(outlets_data)
        self.action_planner = ActionPlanner(self.tool_executor)

    async def process_message(self, message: str, session_context: Dict[str, Any]) -> PlannerResult:
        """Main planning loop: classify intent -> plan action -> execute if needed"""

        # Step 1: Parse intent and extract entities
        intent = self.intent_classifier.classify_intent(message, session_context)

        # Step 2: Plan next action based on intent
        action = self.action_planner.plan_action(intent, session_context)

        # Step 3: Execute tools if required
        if action.action_type == ActionType.CALCULATE:
            result = self.tool_executor.execute_calculation(
                action.parameters['operand1'],
                action.parameters['operator'],
                action.parameters['operand2']
            )
            action.parameters['message'] = result

        elif action.action_type == ActionType.SEARCH_OUTLETS:
            result = self.tool_executor.search_outlets(**action.parameters)
            action.parameters['message'] = result

        elif action.action_type == ActionType.GET_WEATHER:
            result = await self.tool_executor.get_current_weather(action.parameters.get('location'))
            action.parameters['message'] = result

        elif action.action_type == ActionType.GET_FORECAST:
            result = await self.tool_executor.get_weather_forecast(
                action.parameters.get('days', 3),
                action.parameters.get('location')
            )
            action.parameters['message'] = result

        elif action.action_type == ActionType.SEARCH_PRODUCTS:
            result = await self.tool_executor.search_products(action.parameters.get('query', ''))
            action.parameters['message'] = result

        elif action.action_type == ActionType.SEARCH_OUTLETS_NL:
            result = await self.tool_executor.search_outlets_nl(action.parameters.get('query', ''))
            action.parameters['message'] = result

        elif action.parameters.get('tool_call') == 'get_hours_info':
            result = self.tool_executor.get_hours_info(**action.parameters['tool_params'])
            action.parameters['message'] = result

        # Step 4: Determine context updates
        context_updates = {}
        if 'location' in intent.entities:
            location = intent.entities['location'].lower()
            # Store specific outlet location
            context_updates['last_outlet_mentioned'] = intent.entities['location']

            # Also update general area
            if any(area in location for area in ['petaling jaya', 'pj', 'ss 2', 'ss2', 'ss 15', 'ss15', 'damansara']):
                context_updates['area'] = 'petaling_jaya'
                if 'ss 2' in location or 'ss2' in location:
                    context_updates['specific_location'] = 'ss 2'
                elif 'ss 15' in location or 'ss15' in location:
                    context_updates['specific_location'] = 'ss 15'
                elif 'damansara' in location:
                    context_updates['specific_location'] = 'damansara utama'
            elif any(area in location for area in ['kuala lumpur', 'kl', 'klcc', 'bukit bintang']):
                context_updates['area'] = 'kuala_lumpur'
                if 'klcc' in location:
                    context_updates['specific_location'] = 'klcc'
                elif 'bukit bintang' in location:
                    context_updates['specific_location'] = 'bukit bintang'

        return PlannerResult(
            intent=intent,
            action=action,
            context_updates=context_updates
        )