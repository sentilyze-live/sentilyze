"""Agent OS Core - Main FastAPI Application."""

import asyncio
import random
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.agents import AGENT_REGISTRY, get_agent, list_agents
from src.config import settings
from src.data_bridge import BigQueryDataClient, FirestoreDataClient, PubSubDataClient
from src.routes.telegram_v2 import router as telegram_router  # Using new unified router
from src.routes.autonomous import router as autonomous_router  # Brainstorming, content, actions
from src.utils.telegram_manager import get_telegram_manager

logger = structlog.get_logger(__name__)


async def setup_telegram_webhook():
    """Set up Telegram webhook on startup.

    Uses the new unified TelegramManager for clean webhook setup.

    This function:
    - Validates configuration
    - Verifies HTTPS requirement (security)
    - Sets webhook with Telegram API
    - Logs success/failure
    """
    # Security checks
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("telegram.webhook_skipped", reason="no_bot_token")
        return

    if not settings.DOMAIN:
        logger.warning("telegram.webhook_skipped", reason="no_domain_configured")
        return

    # Validate HTTPS (Telegram requires HTTPS for webhooks)
    domain = settings.DOMAIN
    webhook_url = f"https://{domain}/telegram/webhook"

    # Only allow production domains (not localhost)
    if "localhost" in domain or "127.0.0.1" in domain:
        logger.info(
            "telegram.webhook_skipped",
            reason="localhost_not_supported",
            message="Telegram webhooks require HTTPS. Use ngrok for local testing."
        )
        return

    try:
        # Get unified telegram manager
        telegram = get_telegram_manager()

        # Check if enabled
        if not telegram.enabled:
            logger.warning("telegram.webhook_skipped", reason="manager_disabled")
            return

        # Set webhook
        result = await telegram.set_webhook(webhook_url)

        if result.get("ok"):
            logger.info(
                "telegram.webhook_configured",
                url=webhook_url,
                description="Telegram bot ready to receive messages (v2.0)"
            )
        else:
            logger.error(
                "telegram.webhook_failed",
                error=result.get("description", "Unknown error"),
                url=webhook_url
            )

    except Exception as e:
        logger.error("telegram.webhook_error", error=str(e))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("agent_os.startup", version=settings.APP_VERSION)
    
    # Initialize data clients (singleton pattern)
    app.state.bigquery = BigQueryDataClient()
    app.state.firestore = FirestoreDataClient()
    app.state.pubsub = PubSubDataClient()
    
    # KimiClient instances are created per-agent on demand
    logger.info("agent_os.api_clients_ready")
    
    # Create Pub/Sub topics
    try:
        await app.state.pubsub.create_topics()
        logger.info("agent_os.topics_created")
    except Exception as e:
        logger.error("agent_os.topics_error", error=str(e))
    
    # Initialize MARIA background monitoring
    maria_task = None
    if settings.ENABLE_MARIA:
        try:
            from src.agents.maria_agent import MariaAgent
            maria = MariaAgent()
            
            # Send immediate startup notification
            logger.info("maria.sending_startup_notification")
            startup_success = await maria._notify(
                "🚀 <b>MARIA Başlatıldı!</b>\n\n"
                "🤖 Sistem izlemeye başladım.\n"
                f"⏱️ Her {settings.MARIA_INTERVAL_MIN}-{settings.MARIA_INTERVAL_MAX} dakikada bir kontrol edeceğim.\n"
                "🔧 Otomatik düzeltmeler aktif.\n\n"
                "<i>Sentilyze Dream Team'in guardian'ı hazır! 😊</i>\n\n"
                f"🕐 Başlangıç: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
            )
            
            if startup_success:
                logger.info("maria.startup_notification_sent")
            else:
                logger.warning("maria.startup_notification_failed")
            
            # Start MARIA's continuous monitoring loop
            async def maria_monitoring_loop():
                """MARIA's background monitoring loop with random intervals."""
                logger.info("maria.monitoring_loop_started")
                
                while True:
                    try:
                        # Run check
                        await maria._execute(context={})
                        
                        # Calculate random interval for next check
                        next_interval = random.randint(
                            settings.MARIA_INTERVAL_MIN * 60,  # Convert to seconds
                            settings.MARIA_INTERVAL_MAX * 60
                        )
                        
                        logger.info("maria.next_check_scheduled", minutes=next_interval//60)
                        await asyncio.sleep(next_interval)
                        
                    except Exception as e:
                        logger.error("maria.loop_error", error=str(e))
                        await asyncio.sleep(300)  # Wait 5 minutes on error
            
            # Start MARIA in background
            maria_task = asyncio.create_task(maria_monitoring_loop())
            logger.info("maria.background_task_started")
            
        except Exception as e:
            logger.error("maria.init_error", error=str(e))
    else:
        logger.info("maria.disabled")
    
    # Setup Telegram webhook securely
    await setup_telegram_webhook()
    
    yield
    
    # Shutdown
    logger.info("agent_os.shutdown")

    # Cancel MARIA task if running
    if maria_task:
        maria_task.cancel()
        try:
            await maria_task
        except asyncio.CancelledError:
            pass
        logger.info("maria.monitoring_stopped")

    # Close Telegram manager
    try:
        telegram = get_telegram_manager()
        await telegram.close()
        logger.info("telegram_manager.closed")
    except Exception as e:
        logger.warning("telegram_manager.close_error", error=str(e))

    # Close shared httpx client
    try:
        await KimiClient.close_shared_client()
        logger.info("agent_os.shared_client_closed")
    except Exception as e:
        logger.warning("agent_os.client_close_error", error=str(e))


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Sentilyze Agent OS - AI Agent Orchestration System",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Telegram routes
app.include_router(telegram_router)

# Include Autonomous system routes (brainstorming, content pipeline, actions)
app.include_router(autonomous_router)


@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "agents": list_agents(),
        "enabled_agents": settings.enabled_agents,
    }


@app.get("/health")
async def health() -> Dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.APP_VERSION,
    }


@app.get("/agents")
async def get_agents() -> List[Dict[str, Any]]:
    """Get all available agents."""
    agents = []
    for agent_name in list_agents():
        agent = get_agent(agent_name)
        agents.append(agent.get_info())
    return agents


@app.get("/agents/{agent_name}")
async def get_agent_info(agent_name: str) -> Dict[str, Any]:
    """Get specific agent information."""
    try:
        agent = get_agent(agent_name)
        return agent.get_info()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/agents/{agent_name}/run")
async def run_agent(agent_name: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Run a specific agent."""
    try:
        agent = get_agent(agent_name)
        result = await agent.run(context)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("agent_run_error", agent=agent_name, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/run-all")
async def run_all_agents() -> Dict[str, Any]:
    """Run all enabled agents."""
    results = {}
    
    for agent_name in settings.enabled_agents:
        try:
            agent = get_agent(agent_name)
            result = await agent.run()
            results[agent_name] = result
        except Exception as e:
            logger.error("agent_run_error", agent=agent_name, error=str(e))
            results[agent_name] = {"success": False, "error": str(e)}
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "results": results,
    }


@app.post("/agents/test-telegram")
async def test_telegram_message(
    agent_name: str = "all",
    message: str = "🤖 Test mesajı from Sentilyze Agent OS!",
) -> Dict[str, Any]:
    """Send a test message to Telegram from an agent.
    
    Args:
        agent_name: Name of the agent sending the message (default: "all")
        message: Message to send (default: test message)
    
    Returns:
        API response with success status and Telegram API response
    """
    from src.utils.telegram import TelegramNotifier
    
    try:
        if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
            return {
                "success": False,
                "error": "Telegram credentials not configured",
                "configured": False
            }
        
        # Format message with agent name
        formatted_message = f"📢 <b>{agent_name.upper()} Test Mesajı</b>\n\n{message}"
        
        # Send via Telegram
        notifier = TelegramNotifier()
        response = await notifier.send_message(formatted_message)
        
        return {
            "success": response.get("ok", False),
            "agent_name": agent_name,
            "telegram_response": response,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error("telegram_test_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/trends")
async def get_trends(status: str = "active", limit: int = 50) -> List[Dict[str, Any]]:
    """Get trends from Firestore."""
    firestore = FirestoreDataClient()
    return await firestore.get_trends(status=status, limit=limit)


@app.get("/content")
async def get_content(
    content_type: str = None,
    status: str = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Get content from Firestore."""
    firestore = FirestoreDataClient()
    return await firestore.get_content(
        content_type=content_type,
        status=status,
        limit=limit,
    )


@app.get("/experiments")
async def get_experiments(status: str = None, limit: int = 50) -> List[Dict[str, Any]]:
    """Get experiments from Firestore."""
    firestore = FirestoreDataClient()
    return await firestore.get_experiments(status=status, limit=limit)


@app.get("/sentiment/{asset}")
async def get_sentiment(asset: str, hours: int = 24) -> Dict[str, Any]:
    """Get sentiment data for an asset."""
    bigquery = BigQueryDataClient()
    data = await bigquery.get_sentiment_data(asset=asset, hours=hours)
    return {
        "asset": asset,
        "hours": hours,
        "data": data,
        "count": len(data),
    }


@app.get("/metrics")
async def get_metrics(days: int = 30) -> Dict[str, Any]:
    """Get user analytics metrics."""
    bigquery = BigQueryDataClient()
    return await bigquery.get_user_analytics(days=days)


# Memory endpoints (Structured Memory System)
@app.get("/agents/{agent_name}/memory")
async def get_agent_memory(agent_name: str) -> Dict[str, Any]:
    """Get full memory context for an agent (WORKING.md style)."""
    from src.memory import StructuredMemory
    
    memory = StructuredMemory(agent_name)
    return await memory.get_full_context()


# Parallel agent execution endpoint
@app.post("/run-all-parallel")
async def run_all_agents_parallel() -> Dict[str, Any]:
    """Run all enabled agents in parallel (optimized)."""
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    
    start_time = datetime.utcnow()
    results = {}
    errors = {}
    
    async def run_single_agent(agent_name: str) -> tuple:
        """Run a single agent and return result."""
        try:
            agent = get_agent(agent_name)
            result = await agent.run()
            return agent_name, result, None
        except Exception as e:
            logger.error("agent_parallel_run_error", agent=agent_name, error=str(e))
            return agent_name, None, str(e)
    
    # Run all agents in parallel
    tasks = [
        run_single_agent(agent_name) 
        for agent_name in settings.enabled_agents
    ]
    
    # Execute all tasks concurrently
    completed_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    for result in completed_results:
        if isinstance(result, tuple):
            agent_name, success_result, error = result
            if error:
                errors[agent_name] = error
                results[agent_name] = {"success": False, "error": error}
            else:
                results[agent_name] = success_result
    
    duration = (datetime.utcnow() - start_time).total_seconds()
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "duration_seconds": duration,
        "parallel_execution": True,
        "agents_run": len(results),
        "success_count": sum(1 for r in results.values() if r.get("success", False)),
        "error_count": len(errors),
        "results": results,
    }


# Cost monitoring endpoint (GROWTH package)
@app.get("/costs")
async def get_cost_summary() -> Dict[str, Any]:
    """Get AI cost monitoring summary."""
    from src.utils.cost_monitor import cost_monitor
    
    return cost_monitor.get_summary()


@app.get("/costs/agents/{agent_name}")
async def get_agent_costs(agent_name: str) -> Dict[str, Any]:
    """Get cost details for a specific agent."""
    from src.utils.cost_monitor import cost_monitor
    
    metrics = cost_monitor.get_agent_stats(agent_name)
    if not metrics:
        return {
            "error": f"No cost data for agent: {agent_name}",
            "available_agents": list(cost_monitor._agent_metrics.keys()),
        }
    
    return {
        "agent": agent_name,
        "runs_today": metrics.runs_today,
        "runs_this_month": metrics.runs_this_month,
        "tokens_input": metrics.tokens_input,
        "tokens_output": metrics.tokens_output,
        "estimated_cost_usd": round(metrics.estimated_cost_usd, 4),
        "last_run": metrics.last_run.isoformat() if metrics.last_run else None,
        "avg_cost_per_run": round(metrics.estimated_cost_usd / max(metrics.runs_this_month, 1), 6),
    }


@app.get("/agents/{agent_name}/memory/working")
async def get_agent_working_memory(agent_name: str) -> Dict[str, Any]:
    """Get agent's WORKING.md (current task state)."""
    from src.memory import StructuredMemory
    
    memory = StructuredMemory(agent_name)
    working = await memory.get_working_memory()
    return {
        "agent_name": agent_name,
        "working_memory": working.to_dict(),
        "working_md": memory._generate_working_md(working),
    }


@app.get("/agents/{agent_name}/memory/daily")
async def get_agent_daily_notes(
    agent_name: str,
    date: Optional[str] = None,
) -> Dict[str, Any]:
    """Get agent's daily notes (YYYY-MM-DD.md style)."""
    from src.memory import StructuredMemory
    from datetime import datetime
    
    memory = StructuredMemory(agent_name)
    if date is None:
        date = datetime.utcnow().strftime("%Y-%m-%d")
    
    activities = await memory.get_daily_notes(date)
    return {
        "agent_name": agent_name,
        "date": date,
        "activities": activities,
        "daily_md": memory._generate_daily_md(date, activities),
    }


# Cache monitoring endpoint (Full Power package)
@app.get("/cache/stats")
async def get_cache_stats() -> Dict[str, Any]:
    """Get context cache statistics for cost optimization monitoring."""
    from src.api.kimi_client import KimiClient
    
    stats = KimiClient.get_cache_stats()
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "package": "FULL POWER",
        "cache_optimization": {
            "target_hit_ratio": "80%",
            "current_hit_ratio": f"{stats.get('hit_ratio', 0):.1%}",
            "status": "OPTIMAL" if stats.get('hit_ratio', 0) >= 0.75 else "NEEDS_OPTIMIZATION",
        },
        "statistics": stats,
        "cost_impact": {
            "with_current_cache": f"Input cost reduced by ~{stats.get('hit_ratio', 0) * 83:.0f}%",
            "estimated_monthly_savings": f"${stats.get('hits', 0) * 0.0005:.2f}",
        },
    }


@app.get("/agents/{agent_name}/memory/long-term")
async def get_agent_long_term_memory(
    agent_name: str,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """Get agent's long-term memory (MEMORY.md style)."""
    from src.memory import StructuredMemory
    
    memory = StructuredMemory(agent_name)
    memories = await memory.get_long_term_memory(category)
    return {
        "agent_name": agent_name,
        "category_filter": category,
        "memories": memories,
        "memory_md": memory._generate_memory_md(memories),
    }


# ═══════════════════════════════════════════════════════════════════
# MARIA Endpoints - DevOps Guardian
# ═══════════════════════════════════════════════════════════════════

@app.get("/maria/status")
async def get_maria_status() -> Dict[str, Any]:
    """Get MARIA's current monitoring status."""
    if not settings.ENABLE_MARIA:
        return {"error": "MARIA is disabled", "enabled": False}
    
    # Check Telegram configuration
    telegram_configured = bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID)
    
    return {
        "enabled": True,
        "timestamp": datetime.utcnow().isoformat(),
        "telegram": {
            "configured": telegram_configured,
            "bot_token_prefix": settings.TELEGRAM_BOT_TOKEN[:15] + "..." if settings.TELEGRAM_BOT_TOKEN else "Not set",
            "chat_id": settings.TELEGRAM_CHAT_ID if settings.TELEGRAM_CHAT_ID else "Not set",
            "status": "Ready" if telegram_configured else "Not configured",
        },
        "configuration": {
            "auto_fix_enabled": settings.MARIA_AUTO_FIX_ENABLED,
            "can_restart_services": settings.MARIA_CAN_RESTART_SERVICES,
            "check_interval": f"{settings.MARIA_INTERVAL_MIN}-{settings.MARIA_INTERVAL_MAX} minutes (random)",
            "daily_cost_threshold": settings.MARIA_DAILY_COST_THRESHOLD,
            "monthly_cost_threshold": settings.MARIA_MONTHLY_COST_THRESHOLD,
        },
        "message": "🤖 MARIA is watching over the system!",
    }


@app.post("/maria/test-telegram")
async def test_telegram_connection() -> Dict[str, Any]:
    """Test Telegram bot connection and send a test message."""
    if not settings.ENABLE_MARIA:
        return {"error": "MARIA is disabled", "enabled": False}
    
    try:
        from src.agents.maria_agent import MariaAgent
        maria = MariaAgent()
        
        if not maria.telegram:
            return {
                "success": False,
                "error": "Telegram not configured",
                "details": {
                    "token_exists": bool(settings.TELEGRAM_BOT_TOKEN),
                    "chat_id_exists": bool(settings.TELEGRAM_CHAT_ID),
                }
            }
        
        # Send test message
        test_message = """🧪 <b>Telegram Test Mesajı</b>

Merhaba! Bu bir test mesajıdır.

✅ Bot bağlantısı başarılı!
✅ MARIA aktif ve çalışıyor.

Sistem şu anda izleniyor.
Her 45-75 dakikada bir kontrol yapılacak.

<i>~ MARIA 🤖</i>"""
        
        success = await maria._notify(test_message)
        
        return {
            "success": success,
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Test message sent successfully" if success else "Failed to send message",
            "telegram_config": {
                "bot_token_prefix": settings.TELEGRAM_BOT_TOKEN[:10] + "..." if settings.TELEGRAM_BOT_TOKEN else None,
                "chat_id": settings.TELEGRAM_CHAT_ID,
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@app.post("/maria/run-check")
async def run_maria_check() -> Dict[str, Any]:
    """Manually trigger a MARIA monitoring check."""
    if not settings.ENABLE_MARIA:
        raise HTTPException(status_code=400, detail="MARIA is disabled")
    
    try:
        from src.agents.maria_agent import MariaAgent
        maria = MariaAgent()
        result = await maria._execute(context={})
        return {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "result": result,
        }
    except Exception as e:
        logger.error("maria_manual_check_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/maria/telegram/command")
async def handle_telegram_command(
    command: str,
    args: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Handle a command from Telegram (for testing/debugging)."""
    if not settings.ENABLE_MARIA:
        raise HTTPException(status_code=400, detail="MARIA is disabled")
    
    try:
        from src.agents.maria_agent import MariaAgent
        maria = MariaAgent()
        response = await maria.handle_command(command, args or [])
        return {
            "success": True,
            "command": command,
            "args": args,
            "response": response,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error("maria_command_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/maria/health-summary")
async def get_health_summary() -> Dict[str, Any]:
    """Get a quick health summary from MARIA's perspective."""
    if not settings.ENABLE_MARIA:
        return {"error": "MARIA is disabled", "enabled": False}
    
    try:
        from src.agents.maria_agent import MariaAgent
        maria = MariaAgent()
        
        # Quick health check
        health = await maria._check_system_health()
        costs = await maria._check_costs()
        
        healthy_count = sum(1 for h in health.values() if h["healthy"])
        total_count = len(health)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "enabled": True,
            "system_health": {
                "healthy_services": healthy_count,
                "total_services": total_count,
                "status": "✅ All healthy" if healthy_count == total_count else f"⚠️ {total_count - healthy_count} issues",
                "services": health,
            },
            "costs": costs,
            "message": f"🤖 MARIA: {healthy_count}/{total_count} servis çalışıyor. Günlük maliyet: ${costs['daily']:.2f}",
        }
    except Exception as e:
        logger.error("maria_health_summary_error", error=str(e))
        return {
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


def main():
    """Main entry point."""
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.is_development,
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
