"""Agent OS Core - Main FastAPI Application."""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.agents import AGENT_REGISTRY, get_agent, list_agents
from src.config import settings
from src.data_bridge import BigQueryDataClient, FirestoreDataClient, PubSubDataClient

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("agent_os.startup", version=settings.APP_VERSION)
    
    # Initialize data clients
    app.state.bigquery = BigQueryDataClient()
    app.state.firestore = FirestoreDataClient()
    app.state.pubsub = PubSubDataClient()
    
    # Create Pub/Sub topics
    try:
        await app.state.pubsub.create_topics()
        logger.info("agent_os.topics_created")
    except Exception as e:
        logger.error("agent_os.topics_error", error=str(e))
    
    yield
    
    # Shutdown
    logger.info("agent_os.shutdown")


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
