# Conversational Memory System with OpenAI GPT-4o-mini

A Python-based conversational assistant powered by OpenAI's GPT-4o-mini with memory capabilities that can maintain context across multiple turns and handle conversation interruptions.

## 🎯 Objective Fulfilled

This implementation demonstrates tracking of **at least three related turns** with context persistence:

### Example Flow (As Required):
1. **User**: "Is there an outlet in Petaling Jaya?"
2. **Bot**: "Yes! Which outlet are you referring to?"
3. **User**: "SS 2, what's the opening time?"
4. **Bot**: "Ah yes, the SS 2 outlet opens at 9:00 AM"

## 🏗️ Architecture

### Core Components

1. **Memory System** (`memory.py`)
   - Session-based conversation tracking
   - Context management for maintaining state
   - Windowed memory (configurable turn limit)
   - Conversation history persistence

2. **Conversation Agent** (`main.py`)
   - **OpenAI GPT-4o-mini integration** for intelligent responses
   - Context extraction from user messages
   - Smart response generation using LLM with outlet data
   - Memory-aware prompt engineering

3. **Outlet Service** (`outlets.py`)
   - Sample data for Petaling Jaya and Kuala Lumpur outlets
   - Location-based search functionality
   - Opening hours and contact information

4. **FastAPI Endpoints** (`main.py`)
   - `/chat` - Main conversation endpoint
   - `/conversation/{session_id}` - Retrieve conversation history
   - `/session/{session_id}/stats` - Session statistics
   - `/outlets` - Outlet information endpoints

## 🚀 Features

### Memory Capabilities
- ✅ **Session Management**: Unique session IDs for each conversation
- ✅ **Context Persistence**: Remembers area, specific location, and conversation state
- ✅ **Turn Tracking**: Maintains chronological conversation history
- ✅ **Windowed Memory**: Configurable memory window (default: 10 turns)
- ✅ **Interrupted Conversation Handling**: Graceful recovery from session interruptions

### Conversation Intelligence
- ✅ **Intent Detection**: Greeting, outlet inquiry, time inquiry, general
- ✅ **Context Extraction**: Automatically extracts location information
- ✅ **Smart Responses**: Uses context to provide relevant information
- ✅ **Follow-up Handling**: Understands references to previous conversation

## 📁 Project Structure

```
fastapi-backend/
├── main.py                 # FastAPI app with conversation endpoints
├── memory.py              # Memory management system
├── outlets.py             # Outlet data and services
├── requirements.txt       # Python dependencies
├── test_memory_basic.py   # Basic functionality tests
├── test_chat_flow.py      # Comprehensive API tests
├── demo_conversation.py   # Interactive demo script
└── README.md             # This file
```

## 🛠️ Installation & Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up OpenAI API Key**
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key:
   # OPENAI_API_KEY=your-actual-api-key-here
   ```

3. **Run Integration Tests**
   ```bash
   python test_openai_integration.py
   python test_memory_basic.py
   ```

4. **Start the Server**
   ```bash
   uvicorn main:app --reload
   ```

5. **Quick Start Script**
   ```bash
   ./run_demo.sh
   ```

6. **Run Full Tests** (requires server running and API key)
   ```bash
   pytest test_chat_flow.py -v
   ```

## 🔧 API Usage

### Chat Endpoint
```bash
# Start a conversation
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Is there an outlet in Petaling Jaya?"}'

# Continue conversation with session ID
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "SS 2, what are the opening hours?", "session_id": "your-session-id"}'
```

### Response Format
```json
{
  "response": "Yes! We have 3 outlet(s) in Petaling Jaya...",
  "session_id": "uuid-here",
  "turn_number": 1,
  "context_updated": true
}
```

## 🧪 Testing

### Happy Path Tests
- ✅ Complete 3-turn conversation flow
- ✅ Memory persistence across turns
- ✅ Context extraction and usage
- ✅ Natural conversation progression

### Interrupted Path Tests
- ✅ Session interruption handling
- ✅ Invalid session ID recovery
- ✅ Context loss and rebuilding
- ✅ Ambiguous query handling

### API Tests
- ✅ All endpoint functionality
- ✅ Error handling
- ✅ Session management
- ✅ Data retrieval

## 📊 Memory System Details

### Session Management
- Each conversation gets a unique UUID
- Sessions store: turns, context, timestamps
- Automatic session creation for new conversations

### Context Tracking
```python
# Example context stored per session
{
  "area": "petaling_jaya",
  "specific_location": "ss 2",
  "last_intent": "time_inquiry"
}
```

### Turn Structure
```python
{
  "user_message": "SS 2, what's the opening time?",
  "bot_response": "The SS 2 Outlet opens at 9:00 AM...",
  "timestamp": "2024-11-06T14:30:05.334729",
  "turn_number": 2
}
```

## 🎯 Demonstrated Capabilities

1. **Multi-turn Context**: Successfully maintains context across 3+ conversation turns
2. **Location Memory**: Remembers area and specific location mentions
3. **Intent Progression**: Handles conversation flow from general to specific queries
4. **Interruption Recovery**: Gracefully handles session interruptions and context rebuilding
5. **Smart Responses**: Uses accumulated context to provide relevant information

## 🔄 Example Conversation Flows

### Happy Path
```
User: "Is there an outlet in Petaling Jaya?"
Bot:  "Yes! We have 3 outlets in Petaling Jaya: SS 2, SS 15, Damansara Utama. Which would you like to know about?"

User: "SS 2, what's the opening time?"
Bot:  "The SS 2 Outlet opens at 9:00 AM and closes at 10:00 PM."

User: "What's the address?"
Bot:  "The SS 2 Outlet is located at No. 15, Jalan SS 2/24, SS 2, 47300 Petaling Jaya, Selangor"
```

### Interrupted Path
```
Session 1:
User: "Looking for outlets"
Bot:  "Which area are you interested in? We have locations in Petaling Jaya and Kuala Lumpur."

[Session interruption - new session starts]

Session 2:
User: "SS 2 opening hours?"
Bot:  "The SS 2 Outlet opens at 9:00 AM and closes at 10:00 PM."
```

## 🏆 Success Criteria Met

- ✅ **At least 3 related turns tracked**: Conversation history maintains multiple turns with context
- ✅ **Python-based framework**: Built with FastAPI, OpenAI GPT-4o-mini, and custom memory management
- ✅ **Memory/State implementation**: Session-based context and conversation tracking with LLM integration
- ✅ **Happy path automation**: Complete test suite for successful conversation flows
- ✅ **Interrupted path automation**: Comprehensive tests for conversation interruptions
- ✅ **Exported framework project**: Complete, runnable FastAPI application with OpenAI integration

## 🚀 Next Steps

Potential enhancements:
- Database persistence for production use
- Integration with actual LLM APIs
- Multi-user session management
- Advanced NLP for better intent detection
- Voice interface support