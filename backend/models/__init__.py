"""
This module centralizes the imports for all models to ensure that
relationships between them are properly registered and work seamlessly.
It serves as an entry point for the application's ORM to recognize and manage
table relationships effectively.
"""

# Import all models here

from src.user.models import User as User
from src.user.models import LoginEvent as LoginEvent
from src.chat.models import ChatSession as ChatSession
from src.chat.models import ChatMessage as ChatMessage
