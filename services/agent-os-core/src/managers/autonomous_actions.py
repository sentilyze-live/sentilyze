"""Autonomous Action Manager - Agent Self-Execution with Approval Gateway.

Manages the execution of autonomous agent actions:
- Auto-executable actions run immediately (content, analysis, monitoring)
- Approval-required actions wait for user confirmation (deploy, financial, code changes)
- Tracks all actions and their outcomes
- Integrates with Telegram for approval workflow

Approval flow:
1. Agent proposes action → stored as pending
2. Telegram notification sent with approve/reject prompt
3. User responds → action executed or cancelled
4. Result logged and reported
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog

from src.config import settings
from src.data_bridge import FirestoreDataClient
from src.utils.telegram_manager import get_telegram_manager

logger = structlog.get_logger(__name__)


# Actions that ALWAYS require approval
APPROVAL_REQUIRED_ACTIONS = {
    "deploy",           # Deploying code to production
    "financial",        # Financial decisions
    "code_write",       # Writing code to files (CODER agent)
    "infrastructure",   # Infrastructure changes
    "delete",           # Deleting data or resources
    "api_key",          # API key management
    "user_data",        # User data modifications
    "pricing",          # Pricing changes
}

# Actions that can run autonomously
AUTO_EXECUTABLE_ACTIONS = {
    "content",          # Content generation
    "analysis",         # Data analysis
    "monitoring",       # System monitoring
    "community",        # Community engagement content
    "experiment",       # Experiment proposals
    "report",           # Report generation
    "alert",            # Alert processing
    "brainstorming",    # Brainstorming proposals
}


class AutonomousActionManager:
    """Manages autonomous agent actions with approval gateway."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self.firestore = FirestoreDataClient()
        self.telegram = get_telegram_manager()
        self._initialized = True

    async def propose_action(
        self,
        agent_name: str,
        action_type: str,
        title: str,
        description: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Propose an autonomous action.

        If the action type is auto-executable, it will be executed immediately.
        If it requires approval, a notification is sent to Telegram.

        Args:
            agent_name: Name of the proposing agent
            action_type: Type of action (from APPROVAL_REQUIRED or AUTO_EXECUTABLE)
            title: Short action title
            description: Detailed description
            payload: Additional action data

        Returns:
            Action record with status
        """
        action_id = f"action_{agent_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        requires_approval = action_type in APPROVAL_REQUIRED_ACTIONS

        action = {
            "action_id": action_id,
            "agent_name": agent_name,
            "action_type": action_type,
            "title": title,
            "description": description,
            "payload": payload or {},
            "requires_approval": requires_approval,
            "status": "pending_approval" if requires_approval else "approved",
            "proposed_at": datetime.utcnow().isoformat(),
            "decided_at": None,
            "executed_at": None,
            "result": None,
        }

        # Store the action
        await self.firestore.set_document(
            "agent_os_autonomous_actions",
            action_id,
            {**action, "timestamp": datetime.utcnow()},
        )

        if requires_approval:
            # Send approval request to Telegram
            await self._send_approval_request(action)
            logger.info(
                "autonomous_actions.approval_requested",
                action_id=action_id,
                agent=agent_name,
                action_type=action_type,
            )
        else:
            # Execute immediately
            result = await self._execute_action(action)
            action["status"] = "completed" if result.get("success") else "failed"
            action["executed_at"] = datetime.utcnow().isoformat()
            action["result"] = result

            # Update in Firestore
            await self.firestore.set_document(
                "agent_os_autonomous_actions",
                action_id,
                action,
            )

            logger.info(
                "autonomous_actions.auto_executed",
                action_id=action_id,
                agent=agent_name,
                success=result.get("success"),
            )

        return action

    async def approve_action(self, action_id: str) -> Dict[str, Any]:
        """Approve and execute a pending action.

        Args:
            action_id: ID of the action to approve

        Returns:
            Updated action record
        """
        try:
            doc = self.firestore.client.collection("agent_os_autonomous_actions").document(action_id).get()
            if not doc.exists:
                return {"error": f"Action {action_id} not found"}

            action = doc.to_dict()

            if action.get("status") != "pending_approval":
                return {"error": f"Action {action_id} is not pending approval (status: {action.get('status')})"}

            # Execute the action
            action["status"] = "approved"
            action["decided_at"] = datetime.utcnow().isoformat()

            result = await self._execute_action(action)
            action["status"] = "completed" if result.get("success") else "failed"
            action["executed_at"] = datetime.utcnow().isoformat()
            action["result"] = result

            # Update in Firestore
            await self.firestore.set_document(
                "agent_os_autonomous_actions",
                action_id,
                action,
            )

            # Notify via Telegram
            status_icon = "✅" if result.get("success") else "❌"
            await self.telegram.send_message(
                f"{status_icon} <b>Aksiyon tamamlandi:</b> {action.get('title', action_id)}\n"
                f"Agent: {action.get('agent_name', '?').upper()}\n"
                f"Sonuc: {json.dumps(result, default=str)[:200]}",
            )

            return action

        except Exception as e:
            logger.error("autonomous_actions.approve_error", action_id=action_id, error=str(e))
            return {"error": str(e)}

    async def reject_action(self, action_id: str, reason: str = "") -> Dict[str, Any]:
        """Reject a pending action.

        Args:
            action_id: ID of the action to reject
            reason: Rejection reason

        Returns:
            Updated action record
        """
        try:
            doc = self.firestore.client.collection("agent_os_autonomous_actions").document(action_id).get()
            if not doc.exists:
                return {"error": f"Action {action_id} not found"}

            action = doc.to_dict()
            action["status"] = "rejected"
            action["decided_at"] = datetime.utcnow().isoformat()
            action["rejection_reason"] = reason

            await self.firestore.set_document(
                "agent_os_autonomous_actions",
                action_id,
                action,
            )

            await self.telegram.send_message(
                f"🚫 <b>Aksiyon reddedildi:</b> {action.get('title', action_id)}\n"
                f"Sebep: {reason or 'Belirtilmedi'}",
            )

            return action

        except Exception as e:
            logger.error("autonomous_actions.reject_error", action_id=action_id, error=str(e))
            return {"error": str(e)}

    async def _execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an approved action.

        Routes to the appropriate agent for execution.

        Args:
            action: Action record

        Returns:
            Execution result
        """
        from src.agents import get_agent

        agent_name = action.get("agent_name", "")
        action_type = action.get("action_type", "")

        try:
            agent = get_agent(agent_name)

            context = {
                "task": action.get("description", action.get("title", "")),
                "action_id": action.get("action_id"),
                "action_type": action_type,
                "autonomous_run": True,
                "brainstorming_proposal": action.get("payload", {}).get("brainstorming_proposal", False),
                **action.get("payload", {}),
            }

            result = await agent.run(context)

            return {
                "success": result.get("success", False),
                "run_id": result.get("run_id"),
                "summary": result.get("result", {}).get("response", "")[:500] if isinstance(result.get("result"), dict) else str(result.get("result", ""))[:500],
            }

        except Exception as e:
            logger.error(
                "autonomous_actions.execution_error",
                agent=agent_name,
                error=str(e),
            )
            return {"success": False, "error": str(e)}

    async def _send_approval_request(self, action: Dict[str, Any]) -> None:
        """Send approval request via Telegram.

        Args:
            action: Action requiring approval
        """
        agent = action.get("agent_name", "?").upper()
        title = action.get("title", "?")
        description = action.get("description", "")[:300]
        action_type = action.get("action_type", "?")
        action_id = action.get("action_id", "?")

        message = (
            f"🔔 <b>Onay Gerekli</b>\n\n"
            f"👤 Agent: <b>{agent}</b>\n"
            f"📋 Tip: <code>{action_type}</code>\n"
            f"📝 Baslik: {title}\n"
            f"📄 Aciklama: {description}\n\n"
            f"ID: <code>{action_id}</code>\n\n"
            f"Onaylamak icin: <code>/approve {action_id}</code>\n"
            f"Reddetmek icin: <code>/reject {action_id}</code>"
        )

        await self.telegram.send_message(message)

    async def get_pending_actions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get all pending approval actions.

        Args:
            limit: Maximum results

        Returns:
            List of pending actions
        """
        try:
            docs = (
                self.firestore.client.collection("agent_os_autonomous_actions")
                .where("status", "==", "pending_approval")
                .order_by("proposed_at", direction="DESCENDING")
                .limit(limit)
                .stream()
            )
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            logger.error("autonomous_actions.pending_error", error=str(e))
            return []

    async def get_action_history(
        self,
        agent_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get action history with optional filters.

        Args:
            agent_name: Filter by agent
            status: Filter by status
            limit: Maximum results

        Returns:
            List of actions
        """
        try:
            query = self.firestore.client.collection("agent_os_autonomous_actions")
            if agent_name:
                query = query.where("agent_name", "==", agent_name)
            if status:
                query = query.where("status", "==", status)
            query = query.order_by("proposed_at", direction="DESCENDING").limit(limit)

            return [doc.to_dict() for doc in query.stream()]
        except Exception as e:
            logger.error("autonomous_actions.history_error", error=str(e))
            return []

    async def cleanup_expired(self, hours: int = 48) -> int:
        """Clean up expired pending actions.

        Actions pending for more than `hours` are auto-rejected.

        Args:
            hours: Hours before expiry

        Returns:
            Number of expired actions cleaned up
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        cleaned = 0

        try:
            docs = (
                self.firestore.client.collection("agent_os_autonomous_actions")
                .where("status", "==", "pending_approval")
                .stream()
            )

            for doc in docs:
                data = doc.to_dict()
                proposed_at = data.get("proposed_at", "")
                if proposed_at:
                    try:
                        proposed_time = datetime.fromisoformat(proposed_at.replace("Z", "+00:00").replace("+00:00", ""))
                        if proposed_time < cutoff:
                            await self.reject_action(
                                doc.id,
                                reason=f"Otomatik suresi doldu ({hours} saat)"
                            )
                            cleaned += 1
                    except (ValueError, TypeError):
                        pass

        except Exception as e:
            logger.error("autonomous_actions.cleanup_error", error=str(e))

        if cleaned > 0:
            logger.info("autonomous_actions.cleanup_completed", cleaned=cleaned)

        return cleaned


# Singleton accessor
_action_manager = None


def get_action_manager() -> AutonomousActionManager:
    """Get or create AutonomousActionManager singleton."""
    global _action_manager
    if _action_manager is None:
        _action_manager = AutonomousActionManager()
    return _action_manager
