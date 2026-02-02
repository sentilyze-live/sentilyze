"""Structured Memory System for Agent OS.

Implements WORKING.md style memory management similar to Clawdbot.
Each agent maintains:
- WORKING.md: Current task state
- YYYY-MM-DD.md: Daily activity logs
- MEMORY.md: Long-term curated knowledge
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
import structlog

from src.config import settings
from src.data_bridge.firestore_client import FirestoreDataClient

logger = structlog.get_logger(__name__)


class MemoryType(Enum):
    """Types of structured memory."""
    WORKING = "working"
    DAILY = "daily"
    LONG_TERM = "long_term"


@dataclass
class TaskState:
    """Current task state for WORKING.md."""
    title: str = ""
    description: str = ""
    status: str = "idle"  # idle, in_progress, blocked, review, done
    progress_percent: int = 0
    started_at: Optional[str] = None
    last_updated: Optional[str] = None
    next_steps: List[str] = field(default_factory=list)
    blockers: List[str] = field(default_factory=list)
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskState":
        return cls(**data)


@dataclass
class DailyActivity:
    """Activity entry for daily notes."""
    timestamp: str
    action: str
    details: str
    result: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LongTermMemory:
    """Long-term curated memory entry."""
    category: str
    key: str
    value: str
    importance: str = "medium"  # low, medium, high, critical
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class StructuredMemory:
    """Structured memory manager for agents."""
    
    def __init__(self, agent_name: str):
        """Initialize structured memory for an agent.
        
        Args:
            agent_name: Name of the agent (e.g., "scout", "oracle")
        """
        self.agent_name = agent_name
        self.firestore = FirestoreDataClient()
        self.collection_name = "agent_memory"
        
    def _get_document_id(self, memory_type: MemoryType, date: Optional[str] = None) -> str:
        """Generate Firestore document ID.
        
        Args:
            memory_type: Type of memory
            date: Optional date for daily notes
            
        Returns:
            Document ID string
        """
        if memory_type == MemoryType.DAILY and date:
            return f"{self.agent_name}_{memory_type.value}_{date}"
        return f"{self.agent_name}_{memory_type.value}"
    
    async def get_working_memory(self) -> TaskState:
        """Get current working memory (WORKING.md equivalent).
        
        Returns:
            TaskState object with current task information
        """
        doc_id = self._get_document_id(MemoryType.WORKING)
        
        try:
            doc = await self.firestore.get_document(self.collection_name, doc_id)
            if doc and "task_state" in doc:
                return TaskState.from_dict(doc["task_state"])
        except Exception as e:
            logger.warning("memory.get_working_failed", agent=self.agent_name, error=str(e))
        
        # Return default if not found
        return TaskState(
            title="No active task",
            status="idle",
            last_updated=datetime.utcnow().isoformat()
        )
    
    async def update_working_memory(self, task_state: TaskState) -> None:
        """Update working memory.
        
        Args:
            task_state: New task state to save
        """
        doc_id = self._get_document_id(MemoryType.WORKING)
        task_state.last_updated = datetime.utcnow().isoformat()
        
        data = {
            "agent_name": self.agent_name,
            "memory_type": MemoryType.WORKING.value,
            "task_state": task_state.to_dict(),
            "updated_at": datetime.utcnow().isoformat(),
            "working_md": self._generate_working_md(task_state)
        }
        
        await self.firestore.set_document(self.collection_name, doc_id, data)
        logger.info("memory.working_updated", agent=self.agent_name, task=task_state.title)
    
    async def add_daily_activity(self, action: str, details: str, result: Optional[str] = None) -> None:
        """Add activity to daily notes.
        
        Args:
            action: What was done
            details: Description of the activity
            result: Optional result/outcome
        """
        today = datetime.utcnow().strftime("%Y-%m-%d")
        doc_id = self._get_document_id(MemoryType.DAILY, today)
        
        activity = DailyActivity(
            timestamp=datetime.utcnow().isoformat(),
            action=action,
            details=details,
            result=result
        )
        
        # Get existing daily notes or create new
        try:
            doc = await self.firestore.get_document(self.collection_name, doc_id)
            activities = doc.get("activities", []) if doc else []
        except:
            activities = []
        
        activities.append(activity.to_dict())
        
        data = {
            "agent_name": self.agent_name,
            "memory_type": MemoryType.DAILY.value,
            "date": today,
            "activities": activities,
            "updated_at": datetime.utcnow().isoformat(),
            "daily_md": self._generate_daily_md(today, activities)
        }
        
        await self.firestore.set_document(self.collection_name, doc_id, data)
        logger.debug("memory.daily_activity_added", agent=self.agent_name, action=action)
    
    async def get_daily_notes(self, date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get daily notes for a specific date.
        
        Args:
            date: Date string (YYYY-MM-DD), defaults to today
            
        Returns:
            List of daily activities
        """
        if date is None:
            date = datetime.utcnow().strftime("%Y-%m-%d")
            
        doc_id = self._get_document_id(MemoryType.DAILY, date)
        
        try:
            doc = await self.firestore.get_document(self.collection_name, doc_id)
            if doc:
                return doc.get("activities", [])
        except Exception as e:
            logger.warning("memory.get_daily_failed", agent=self.agent_name, date=date, error=str(e))
        
        return []
    
    async def add_long_term_memory(self, category: str, key: str, value: str, importance: str = "medium") -> None:
        """Add long-term memory entry.
        
        Args:
            category: Category of memory (e.g., "lessons", "decisions", "facts")
            key: Unique key for this memory
            value: The memory content
            importance: Importance level (low, medium, high, critical)
        """
        doc_id = self._get_document_id(MemoryType.LONG_TERM)
        
        memory = LongTermMemory(
            category=category,
            key=key,
            value=value,
            importance=importance
        )
        
        # Get existing memories or create new
        try:
            doc = await self.firestore.get_document(self.collection_name, doc_id)
            memories = doc.get("memories", []) if doc else []
        except:
            memories = []
        
        # Check if key already exists, update if so
        updated = False
        for i, mem in enumerate(memories):
            if mem.get("key") == key and mem.get("category") == category:
                memories[i] = memory.to_dict()
                updated = True
                break
        
        if not updated:
            memories.append(memory.to_dict())
        
        # Sort by importance
        importance_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        memories.sort(key=lambda x: importance_order.get(x.get("importance", "medium"), 2))
        
        data = {
            "agent_name": self.agent_name,
            "memory_type": MemoryType.LONG_TERM.value,
            "memories": memories,
            "updated_at": datetime.utcnow().isoformat(),
            "memory_md": self._generate_memory_md(memories)
        }
        
        await self.firestore.set_document(self.collection_name, doc_id, data)
        logger.info("memory.long_term_added", agent=self.agent_name, category=category, key=key)
    
    async def get_long_term_memory(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get long-term memory entries.
        
        Args:
            category: Optional category filter
            
        Returns:
            List of memory entries
        """
        doc_id = self._get_document_id(MemoryType.LONG_TERM)
        
        try:
            doc = await self.firestore.get_document(self.collection_name, doc_id)
            if doc:
                memories = doc.get("memories", [])
                if category:
                    memories = [m for m in memories if m.get("category") == category]
                return memories
        except Exception as e:
            logger.warning("memory.get_long_term_failed", agent=self.agent_name, error=str(e))
        
        return []
    
    def _generate_working_md(self, task_state: TaskState) -> str:
        """Generate markdown representation of WORKING.md.
        
        Args:
            task_state: Current task state
            
        Returns:
            Markdown string
        """
        md = f"""# WORKING.md — {self.agent_name.upper()} Current Task

## Current Task
**{task_state.title}**

{task_state.description}

## Status
- **State:** {task_state.status}
- **Progress:** {task_state.progress_percent}%
- **Started:** {task_state.started_at or 'N/A'}
- **Last Updated:** {task_state.last_updated or 'N/A'}

"""
        
        if task_state.next_steps:
            md += "## Next Steps\n"
            for i, step in enumerate(task_state.next_steps, 1):
                md += f"{i}. {step}\n"
            md += "\n"
        
        if task_state.blockers:
            md += "## Blockers\n"
            for blocker in task_state.blockers:
                md += f"- ⚠️ {blocker}\n"
            md += "\n"
        
        if task_state.notes:
            md += f"## Notes\n{task_state.notes}\n"
        
        return md
    
    def _generate_daily_md(self, date: str, activities: List[Dict[str, Any]]) -> str:
        """Generate markdown representation of daily notes.
        
        Args:
            date: Date string
            activities: List of activities
            
        Returns:
            Markdown string
        """
        md = f"""# {date} — {self.agent_name.upper()} Daily Notes

"""
        
        for activity in activities:
            timestamp = activity.get("timestamp", "")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                    time_str = dt.strftime("%H:%M")
                except:
                    time_str = timestamp
            else:
                time_str = "--:--"
            
            md += f"## {time_str} UTC\n"
            md += f"**{activity.get('action', 'Unknown')}**\n\n"
            md += f"{activity.get('details', '')}\n\n"
            
            if activity.get('result'):
                md += f"**Result:** {activity['result']}\n\n"
        
        return md
    
    def _generate_memory_md(self, memories: List[Dict[str, Any]]) -> str:
        """Generate markdown representation of MEMORY.md.
        
        Args:
            memories: List of memory entries
            
        Returns:
            Markdown string
        """
        md = f"""# MEMORY.md — {self.agent_name.upper()} Long-term Memory

## Important Learnings & Decisions

"""
        
        # Group by category
        categories = {}
        for memory in memories:
            cat = memory.get("category", "uncategorized")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(memory)
        
        for category, mems in sorted(categories.items()):
            md += f"\n### {category.upper()}\n\n"
            for memory in mems:
                importance = memory.get("importance", "medium")
                icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(importance, "⚪")
                md += f"{icon} **{memory.get('key', 'Unknown')}**\n"
                md += f"{memory.get('value', '')}\n\n"
        
        return md
    
    async def get_full_context(self) -> Dict[str, Any]:
        """Get full memory context for agent.
        
        Returns:
            Dictionary with all memory types
        """
        working = await self.get_working_memory()
        today = datetime.utcnow().strftime("%Y-%m-%d")
        daily = await self.get_daily_notes(today)
        long_term = await self.get_long_term_memory()
        
        return {
            "agent_name": self.agent_name,
            "working": working.to_dict(),
            "daily_notes": daily,
            "long_term_memory": long_term,
            "working_md": self._generate_working_md(working),
            "daily_md": self._generate_daily_md(today, daily),
            "memory_md": self._generate_memory_md(long_term)
        }
    
    async def clear_memory(self, memory_type: Optional[MemoryType] = None) -> None:
        """Clear memory for agent.
        
        Args:
            memory_type: Specific type to clear, or None for all
        """
        if memory_type:
            doc_id = self._get_document_id(memory_type)
            await self.firestore.delete_document(self.collection_name, doc_id)
            logger.info("memory.cleared", agent=self.agent_name, type=memory_type.value)
        else:
            # Clear all memory types
            for mt in MemoryType:
                doc_id = self._get_document_id(mt)
                try:
                    await self.firestore.delete_document(self.collection_name, doc_id)
                except:
                    pass
            logger.info("memory.all_cleared", agent=self.agent_name)
