"""Agent implementations for Agent OS."""

from .base import BaseAgent
from .scout_agent import ScoutAgent
from .elon_agent import ElonAgent
from .seth_agent import SethAgent
from .zara_agent import ZaraAgent
from .oracle_agent import OracleAgent
from .coder_agent import CoderAgent
from .maria_agent import MariaAgent
from .sentinel_agent import SentinelAgent
from .atlas_agent import AtlasAgent

__all__ = [
    "BaseAgent",
    "ScoutAgent",
    "ElonAgent",
    "SethAgent",
    "ZaraAgent",
    "OracleAgent",
    "CoderAgent",
    "MariaAgent",
    "SentinelAgent",
    "AtlasAgent",
]

# Agent registry
AGENT_REGISTRY = {
    "scout": ScoutAgent,
    "elon": ElonAgent,
    "seth": SethAgent,
    "zara": ZaraAgent,
    "oracle": OracleAgent,
    "coder": CoderAgent,
    "maria": MariaAgent,
    "sentinel": SentinelAgent,
    "atlas": AtlasAgent,
}


def get_agent(agent_name: str) -> BaseAgent:
    """Get agent instance by name.

    Args:
        agent_name: Name of the agent

    Returns:
        Agent instance

    Raises:
        ValueError: If agent not found
    """
    agent_class = AGENT_REGISTRY.get(agent_name.lower())
    if not agent_class:
        raise ValueError(f"Unknown agent: {agent_name}")
    return agent_class()


def list_agents() -> list[str]:
    """List all available agent names.

    Returns:
        List of agent names
    """
    return list(AGENT_REGISTRY.keys())
