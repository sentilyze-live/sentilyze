"""Team Standup Manager - Coordinated agent status sharing.

Runs daily (integrated with MARIA's daily summary).
Each agent provides:
- What they did since last standup
- Current status
- Requests to other agents
"""

from datetime import datetime
from typing import Any, Dict, List

import structlog

from src.data_bridge import FirestoreDataClient
from src.utils.telegram_manager import get_telegram_manager

logger = structlog.get_logger(__name__)


class TeamStandupManager:
    """Orchestrates daily team standup across all agents."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self.firestore = FirestoreDataClient()
        self._initialized = True

    async def run_standup(self) -> Dict[str, Any]:
        """Orchestrate a team standup.

        Collects status from all agents and sends a compiled
        report to Telegram.

        Returns:
            Standup report data
        """
        from src.agents import list_agents, get_agent

        agent_names = list_agents()
        standup_reports = {}

        for agent_name in agent_names:
            try:
                agent = get_agent(agent_name)
                memory_context = await agent.get_memory_context()
                agent_state = await self.firestore.get_agent_state(agent_name)

                standup_reports[agent_name] = {
                    "name": agent.name,
                    "last_run": agent_state.get("last_run_at", "N/A") if agent_state else "N/A",
                    "last_success": agent_state.get("last_run_success", False) if agent_state else False,
                    "run_count": agent_state.get("run_count", 0) if agent_state else 0,
                    "working_memory": memory_context.get("working", {}),
                }
            except Exception as e:
                standup_reports[agent_name] = {
                    "name": agent_name.upper(),
                    "error": str(e),
                }
                logger.warning("standup.agent_error", agent=agent_name, error=str(e))

        # Compile report
        compiled = self._compile_standup(standup_reports)

        # Send to Telegram
        telegram = get_telegram_manager()
        if telegram.enabled:
            await telegram.send_message(compiled)

        # Store standup in Firestore
        standup_id = f"standup_{datetime.utcnow().strftime('%Y-%m-%d')}"
        await self.firestore.set_document(
            "agent_os_standups",
            standup_id,
            {
                "reports": {k: str(v) for k, v in standup_reports.items()},
                "compiled": compiled,
                "timestamp": datetime.utcnow(),
            },
        )

        logger.info("standup.completed", agent_count=len(standup_reports))
        return standup_reports

    def _compile_standup(self, reports: Dict[str, Any]) -> str:
        """Compile individual reports into a formatted Telegram message.

        Args:
            reports: Dict of agent_name -> report data

        Returns:
            Formatted HTML message
        """
        now = datetime.utcnow()
        parts = [
            f"📋 <b>Takim Standup - {now.strftime('%Y-%m-%d %H:%M')} UTC</b>",
            "",
        ]

        for agent_name, report in reports.items():
            name = report.get("name", agent_name.upper())
            if "error" in report:
                parts.append(f"❌ <b>{name}</b>: Durum alinamadi")
                continue

            last_success = report.get("last_success", False)
            run_count = report.get("run_count", 0)
            status_icon = "✅" if last_success else "⚠️"

            parts.append(f"{status_icon} <b>{name}</b> | {run_count} calistirma")

            # Add working memory summary if available
            working = report.get("working_memory", {})
            if isinstance(working, dict) and working.get("title"):
                parts.append(f"   └ {working['title']}")

        parts.extend([
            "",
            f"<i>Sonraki standup: yarin {now.strftime('%H:%M')} UTC</i>",
        ])

        return "\n".join(parts)


# Singleton accessor
_standup_manager = None


def get_standup_manager() -> TeamStandupManager:
    """Get or create TeamStandupManager singleton."""
    global _standup_manager
    if _standup_manager is None:
        _standup_manager = TeamStandupManager()
    return _standup_manager
