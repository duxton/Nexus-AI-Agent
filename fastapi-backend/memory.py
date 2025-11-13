from typing import Dict, List, Optional
from pydantic import BaseModel
import uuid
from datetime import datetime

class ConversationTurn(BaseModel):
    user_message: str
    bot_response: str
    timestamp: datetime
    turn_number: int

class ConversationSession(BaseModel):
    session_id: str
    turns: List[ConversationTurn] = []
    context: Dict = {}
    created_at: datetime
    last_updated: datetime

class ConversationMemoryManager:
    def __init__(self, window_size: int = 10):
        self.sessions: Dict[str, ConversationSession] = {}
        self.window_size = window_size

    def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        now = datetime.now()
        self.sessions[session_id] = ConversationSession(
            session_id=session_id,
            created_at=now,
            last_updated=now
        )
        return session_id

    def get_or_create_session(self, session_id: Optional[str] = None) -> str:
        if session_id and session_id in self.sessions:
            return session_id
        return self.create_session()

    def add_turn(self, session_id: str, user_message: str, bot_response: str) -> None:
        if session_id not in self.sessions:
            session_id = self.create_session()

        session = self.sessions[session_id]
        turn_number = len(session.turns) + 1

        turn = ConversationTurn(
            user_message=user_message,
            bot_response=bot_response,
            timestamp=datetime.now(),
            turn_number=turn_number
        )

        session.turns.append(turn)
        session.last_updated = datetime.now()

        # Keep only the last N turns based on window size
        if len(session.turns) > self.window_size:
            session.turns = session.turns[-self.window_size:]

    def get_conversation_history(self, session_id: str) -> List[ConversationTurn]:
        if session_id not in self.sessions:
            return []
        return self.sessions[session_id].turns

    def get_conversation_context(self, session_id: str) -> str:
        """Get conversation context as a formatted string for LLM input"""
        if session_id not in self.sessions:
            return ""

        turns = self.sessions[session_id].turns
        if not turns:
            return ""

        context_lines = []
        for turn in turns[-self.window_size:]:  # Keep only recent turns
            context_lines.append(f"User: {turn.user_message}")
            context_lines.append(f"Assistant: {turn.bot_response}")

        return "\n".join(context_lines)

    def update_context(self, session_id: str, key: str, value: any) -> None:
        if session_id in self.sessions:
            self.sessions[session_id].context[key] = value
            self.sessions[session_id].last_updated = datetime.now()

    def get_context(self, session_id: str, key: str) -> any:
        if session_id in self.sessions:
            return self.sessions[session_id].context.get(key)
        return None

    def clear_session(self, session_id: str) -> bool:
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    def get_session_stats(self, session_id: str) -> Dict:
        if session_id not in self.sessions:
            return {}

        session = self.sessions[session_id]
        return {
            "session_id": session_id,
            "total_turns": len(session.turns),
            "created_at": session.created_at.isoformat(),
            "last_updated": session.last_updated.isoformat(),
            "context_keys": list(session.context.keys())
        }

# Global memory manager instance
memory_manager = ConversationMemoryManager()