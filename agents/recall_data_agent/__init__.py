# agents/recall_data_agent/__init__.py
"""RecallDataAgent - Multi-Agency Recall Database Management
Handles ingestion from 39+ international regulatory agencies and live queries.
"""

from .agent_logic import RecallDataAgentLogic
from .models import Recall

__all__ = ["RecallDataAgentLogic", "Recall"]
