# Agentic Planning System - Technical Documentation

## Overview

This document describes the implementation of an agentic planning system for the conversational outlet assistant. The system analyzes user intent, determines missing information, and plans appropriate actions using a structured decision-making process.

## Architecture

The agentic planning system consists of four main components:

### 1. Intent Classification System (`IntentClassifier`)

**Purpose**: Parse user messages and classify intentions while extracting relevant entities.

**Decision Points**:
- **Pattern Matching vs. ML**: Uses regex patterns for speed and reliability over ML models for this domain-specific use case
- **Intent Categories**: Defined 9 specific intent types covering the outlet assistant domain:
  - `GREETING` - Welcome interactions
  - `OUTLET_SEARCH` - Finding store locations
  - `HOURS_INQUIRY` - Opening/closing times
  - `LOCATION_INQUIRY` - Address information
  - `PHONE_INQUIRY` - Contact details
  - `CALCULATION` - Math operations
  - `GENERAL_QUESTION` - Fallback category
  - `GOODBYE` - Conversation termination
  - `UNCLEAR` - Ambiguous inputs

**Entity Extraction**:
- **Location entities**: Extracts geographic references (PJ, KL, SS2, etc.)
- **Mathematical expressions**: Identifies operands and operators for calculations
- **Missing information tracking**: Determines what additional data is needed

### 2. Action Planning System (`ActionPlanner`)

**Purpose**: Decide the next action based on parsed intent and current context.

**Decision Logic**:

```
IF intent == GREETING:
    → ACTION: PROVIDE_INFO (welcome message)

IF intent == CALCULATION:
    IF missing calculation expression:
        → ACTION: ASK_CLARIFICATION
    ELSE:
        → ACTION: CALCULATE

IF intent == OUTLET_SEARCH:
    IF missing location AND no session context:
        → ACTION: ASK_CLARIFICATION
    ELSE:
        → ACTION: SEARCH_OUTLETS

IF intent == UNCLEAR:
    → ACTION: ASK_CLARIFICATION

ELSE:
    → Fallback to LLM processing
```

**Key Decision Points**:
- **Context Awareness**: Leverages session memory to avoid re-asking for known information
- **Progressive Disclosure**: Only asks for missing critical information
- **Fallback Strategy**: Routes complex queries to LLM when rule-based logic insufficient

### 3. Tool Execution System (`ToolExecutor`)

**Purpose**: Execute specific tools based on planned actions.

**Available Tools**:

| Tool | Purpose | Input | Output |
|------|---------|-------|--------|
| `execute_calculation` | Math operations | operand1, operator, operand2 | Calculation result |
| `search_outlets` | Find stores | location/area | List of matching outlets |
| `get_hours_info` | Opening times | location/area | Hours information |

**Design Decisions**:
- **Tool Isolation**: Each tool is self-contained with clear interfaces
- **Error Handling**: Graceful degradation with informative error messages
- **Data Integration**: Uses existing outlet service data structure

### 4. Orchestration Layer (`AgenticPlanner`)

**Purpose**: Coordinate the entire planning workflow.

**Process Flow**:

```
1. MESSAGE INPUT
   ↓
2. INTENT CLASSIFICATION
   ├── Extract entities
   ├── Determine intent type
   └── Identify missing information
   ↓
3. ACTION PLANNING
   ├── Analyze context
   ├── Plan next action
   └── Determine required tools
   ↓
4. TOOL EXECUTION (if needed)
   ├── Execute calculations
   ├── Search outlets
   └── Format responses
   ↓
5. CONTEXT UPDATES
   ├── Update session memory
   └── Return structured result
```

## Key Decision Points & Rationale

### 1. Rule-Based vs. ML Approach

**Decision**: Implemented rule-based intent classification with regex patterns
**Rationale**:
- Domain is well-defined with limited intent types
- Faster execution and predictable behavior
- Easier to debug and maintain
- No training data requirements

### 2. Hierarchical Action Planning

**Decision**: Multi-level decision tree (intent → action → tool)
**Rationale**:
- Clear separation of concerns
- Easy to extend with new intents/actions
- Transparent decision process for debugging

### 3. Session Context Integration

**Decision**: Leverage existing session memory for context awareness
**Rationale**:
- Prevents repetitive questions
- Improves user experience
- Maintains conversation coherence

### 4. Graceful Degradation

**Decision**: Fallback to LLM for complex/unhandled cases
**Rationale**:
- Ensures system robustness
- Handles edge cases gracefully
- Maintains conversational quality

### 5. Structured Response Format

**Decision**: Return detailed planning metadata alongside responses
**Rationale**:
- Enables debugging and monitoring
- Provides transparency into decision process
- Supports future optimization efforts

## API Endpoints

### New Agentic Chat Endpoint

```
POST /chat/agentic
```

**Response Format**:
```json
{
  "response": "Generated response text",
  "session_id": "unique_session_id",
  "turn_number": 1,
  "context_updated": true,
  "intent": "outlet_search",
  "action_type": "search_outlets",
  "reasoning": "User wants outlet information and location is available",
  "confidence": 0.8,
  "tools_used": ["outlet_search"]
}
```

## Testing Examples

### Example 1: Location Search
```
Input: "Is there an outlet in PJ?"
Intent: outlet_search
Action: search_outlets
Tools: [outlet_search]
Response: "Found 3 outlet(s): SS2 Branch - SS 2..."
```

### Example 2: Calculation
```
Input: "What's 15 + 7?"
Intent: calculation
Action: calculate
Tools: [calculator]
Response: "15 + 7 = 22"
```

### Example 3: Missing Information
```
Input: "What time do you open?"
Intent: hours_inquiry
Action: ask_clarification
Tools: []
Response: "Which outlet would you like the opening hours for?"
```

## Usage

Start the enhanced API server:
```bash
uvicorn main:app --reload
```

Test the agentic endpoint:
```bash
curl -X POST "http://localhost:8000/chat/agentic" \
  -H "Content-Type: application/json" \
  -d '{"message": "Calculate 5 + 3"}'
```

## Future Enhancements

1. **ML-Based Intent Classification**: Upgrade to transformer-based models for better accuracy
2. **Multi-Step Planning**: Support complex workflows requiring multiple tool calls
3. **Learning from Feedback**: Incorporate user feedback to improve planning decisions
4. **Tool Composition**: Enable chaining multiple tools for complex tasks
5. **Confidence Thresholds**: Dynamic routing based on confidence scores