"""
In-memory session management for interview sessions.
"""
from typing import Dict, List, Optional
import uuid
from datetime import datetime


class Session:
    """Represents a single interview session."""
    def __init__(self, name: str, job_role: str, interview_type: str):
        self.session_id = str(uuid.uuid4())
        self.name = name
        self.job_role = job_role
        self.interview_type = interview_type
        self.created_at = datetime.now()
        self.questions: List[str] = []
        self.current_question_index = 0
        self.answers: List[Dict] = []  # Store answer, feedback, follow-ups
        self.follow_up_questions: List[str] = []  # Current follow-ups queue
        self.current_follow_up_index = 0
        self.detailed_evaluations: List[Dict] = []  # Detailed rubric scores
        self.last_question = ""
        self.completed = False
        # Ask a follow-up after the first question, then after every 5–6 questions
        # This stores the 1-based question number at which the next follow-up should be asked
        self.next_followup_after = 1


class SessionManager:
    """Manages interview sessions in memory."""
    def __init__(self):
        self.sessions: Dict[str, Session] = {}

    def create_session(self, name: str, job_role: str, interview_type: str) -> Session:
        """Create a new interview session."""
        session = Session(name, job_role, interview_type)
        self.sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Retrieve a session by ID."""
        return self.sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False


# Global session manager instance
session_manager = SessionManager()
