"""Autonomous System Routes - Brainstorming, Content Pipeline, Actions.

API endpoints for managing the autonomous agent system:
- Brainstorming sessions (trigger, status, history)
- Content pipeline (generate, queue, publish)
- Autonomous actions (approve, reject, pending, history)
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
import structlog

from src.managers.brainstorming_manager import get_brainstorming_manager
from src.managers.content_pipeline import get_content_pipeline
from src.managers.autonomous_actions import get_action_manager

router = APIRouter(prefix="/autonomous", tags=["autonomous"])
logger = structlog.get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Brainstorming Endpoints
# ═══════════════════════════════════════════════════════════════════


@router.post("/brainstorming/trigger")
async def trigger_brainstorming() -> Dict[str, Any]:
    """Manually trigger a brainstorming session.

    Runs the full brainstorming pipeline immediately,
    regardless of the regular schedule.

    Returns:
        Session results with proposals and dispatched actions
    """
    try:
        brainstorming = get_brainstorming_manager()
        result = await brainstorming.run_session()
        return {
            "ok": True,
            "session_id": result.get("session_id"),
            "total_proposals": result.get("total_proposals", 0),
            "dispatched_actions": result.get("dispatched_actions", 0),
        }
    except Exception as e:
        logger.error("route.brainstorming_trigger_error", error=str(e))
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": str(e)},
        )


@router.get("/brainstorming/status")
async def brainstorming_status() -> Dict[str, Any]:
    """Get brainstorming system status.

    Returns:
        Current status including next scheduled run
    """
    try:
        brainstorming = get_brainstorming_manager()
        should_run = await brainstorming.should_run()
        return {
            "ok": True,
            "should_run_now": should_run,
            "last_session": brainstorming.last_session.isoformat() if brainstorming.last_session else None,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════════════
# Content Pipeline Endpoints
# ═══════════════════════════════════════════════════════════════════


@router.post("/content/generate")
async def generate_content(
    topic: str,
    platform: str = "blog",
) -> Dict[str, Any]:
    """Generate content for a specific platform.

    Args:
        topic: Content topic
        platform: Target platform (blog, linkedin, twitter, reddit, discord)

    Returns:
        Generated content with metadata
    """
    try:
        pipeline = get_content_pipeline()
        content = await pipeline.generate_content(
            topic=topic,
            platform=platform,
            source_agent="manual",
        )
        if content:
            return {"ok": True, "content": content}
        return {"ok": False, "error": "Content generation failed"}
    except Exception as e:
        logger.error("route.content_generate_error", error=str(e))
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": str(e)},
        )


@router.post("/content/generate-all")
async def generate_multi_platform(
    topic: str,
    platforms: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate content for multiple platforms from a single topic.

    Args:
        topic: Content topic
        platforms: Comma-separated platforms (default: all)

    Returns:
        Dict of platform -> generated content
    """
    try:
        pipeline = get_content_pipeline()
        platform_list = platforms.split(",") if platforms else None
        results = await pipeline.generate_multi_platform(
            topic=topic,
            platforms=platform_list,
            source_agent="manual",
        )
        return {
            "ok": True,
            "platforms_generated": list(results.keys()),
            "content": results,
        }
    except Exception as e:
        logger.error("route.content_multi_error", error=str(e))
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": str(e)},
        )


@router.get("/content/queue")
async def content_queue(
    platform: Optional[str] = None,
    status: str = "ready_to_publish",
    limit: int = Query(default=20, le=100),
) -> Dict[str, Any]:
    """Get content queue for publishing.

    Args:
        platform: Filter by platform
        status: Filter by status
        limit: Maximum results

    Returns:
        List of queued content items
    """
    try:
        pipeline = get_content_pipeline()
        items = await pipeline.get_content_queue(
            platform=platform,
            status=status,
            limit=limit,
        )
        return {"ok": True, "count": len(items), "items": items}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/content/{content_id}/publish")
async def mark_content_published(content_id: str) -> Dict[str, Any]:
    """Mark content as published.

    Args:
        content_id: Content document ID

    Returns:
        Success status
    """
    try:
        pipeline = get_content_pipeline()
        success = await pipeline.mark_published(content_id)
        return {"ok": success}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════════════
# Autonomous Action Endpoints
# ═══════════════════════════════════════════════════════════════════


@router.get("/actions/pending")
async def get_pending_actions(
    limit: int = Query(default=20, le=100),
) -> Dict[str, Any]:
    """Get all pending approval actions.

    Returns:
        List of actions awaiting approval
    """
    try:
        action_mgr = get_action_manager()
        actions = await action_mgr.get_pending_actions(limit=limit)
        return {"ok": True, "count": len(actions), "actions": actions}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/actions/{action_id}/approve")
async def approve_action(action_id: str) -> Dict[str, Any]:
    """Approve and execute a pending action.

    Args:
        action_id: Action ID to approve

    Returns:
        Updated action with execution result
    """
    try:
        action_mgr = get_action_manager()
        result = await action_mgr.approve_action(action_id)
        return {"ok": "error" not in result, "action": result}
    except Exception as e:
        logger.error("route.approve_error", action_id=action_id, error=str(e))
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": str(e)},
        )


@router.post("/actions/{action_id}/reject")
async def reject_action(
    action_id: str,
    reason: str = "",
) -> Dict[str, Any]:
    """Reject a pending action.

    Args:
        action_id: Action ID to reject
        reason: Rejection reason

    Returns:
        Updated action
    """
    try:
        action_mgr = get_action_manager()
        result = await action_mgr.reject_action(action_id, reason=reason)
        return {"ok": "error" not in result, "action": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/actions/history")
async def get_action_history(
    agent_name: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=50, le=200),
) -> Dict[str, Any]:
    """Get action history with optional filters.

    Args:
        agent_name: Filter by agent
        status: Filter by status
        limit: Maximum results

    Returns:
        List of historical actions
    """
    try:
        action_mgr = get_action_manager()
        actions = await action_mgr.get_action_history(
            agent_name=agent_name,
            status=status,
            limit=limit,
        )
        return {"ok": True, "count": len(actions), "actions": actions}
    except Exception as e:
        return {"ok": False, "error": str(e)}
