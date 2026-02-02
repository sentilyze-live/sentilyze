#!/usr/bin/env python3
"""
Agent OS - Agent Testing Script

This script tests all agents in the Agent OS system.

Usage:
    python scripts/test-agents.py --agent scout
    python scripts/test-agents.py --all
    python scripts/test-agents.py --list
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from typing import Any, Dict

# Add the agent-os-core src to path
sys.path.insert(0, "services/agent-os-core")

from src.agents import get_agent, list_agents
from src.config import settings


def print_header(text: str):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f" {text}")
    print("=" * 60)


def print_section(text: str):
    """Print a section header."""
    print(f"\n📌 {text}")
    print("-" * 40)


def print_success(text: str):
    """Print a success message."""
    print(f"✅ {text}")


def print_error(text: str):
    """Print an error message."""
    print(f"❌ {text}")


def print_info(text: str):
    """Print an info message."""
    print(f"ℹ️  {text}")


async def test_agent(agent_name: str) -> Dict[str, Any]:
    """Test a specific agent.
    
    Args:
        agent_name: Name of the agent to test
        
    Returns:
        Test results
    """
    print_section(f"Testing {agent_name.upper()} Agent")
    
    try:
        # Get agent instance
        agent = get_agent(agent_name)
        print_success(f"Agent initialized: {agent.name}")
        print_info(f"Description: {agent.description}")
        print_info(f"Capabilities: {', '.join(agent.capabilities[:3])}...")
        
        # Run agent
        print(f"\n🚀 Running {agent_name} agent...")
        start_time = datetime.now()
        
        result = await agent.run()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        # Print results
        print(f"\n📊 Results:")
        print(f"  - Success: {result.get('success', False)}")
        print(f"  - Duration: {duration:.2f}s")
        print(f"  - Run ID: {result.get('run_id', 'N/A')}")
        
        if result.get('success'):
            result_data = result.get('result', {})
            
            # Agent-specific output
            if agent_name == 'scout':
                trends = result_data.get('trends_detected', [])
                print(f"  - Trends detected: {len(trends)}")
                for trend in trends[:3]:
                    print(f"    • {trend.get('topic', 'Unknown')}: "
                          f"Viral Score {trend.get('viral_score', 0)}")
                    
            elif agent_name == 'elon':
                experiments = result_data.get('experiments_proposed', [])
                print(f"  - Experiments proposed: {len(experiments)}")
                for exp in experiments[:3]:
                    ice = exp.get('ice_scores', {})
                    print(f"    • {exp.get('experiment_name', 'Unknown')}: "
                          f"ICE {ice.get('total', 0)}")
                    
            elif agent_name == 'seth':
                content = result_data.get('content_created', [])
                print(f"  - Content created: {len(content)}")
                for c in content[:3]:
                    print(f"    • {c.get('title', 'Unknown')[:50]}...")
                    
            elif agent_name == 'zara':
                engagements = result_data.get('engagements_processed', [])
                print(f"  - Engagements processed: {len(engagements)}")
                
            elif agent_name == 'ece':
                content = result_data.get('content_created', [])
                visuals = result_data.get('visuals_generated', [])
                print(f"  - Content created: {len(content)}")
                print(f"  - Visuals generated: {len(visuals)}")
        else:
            print_error(f"Agent failed: {result.get('error', 'Unknown error')}")
        
        return {
            'agent': agent_name,
            'success': result.get('success', False),
            'duration': duration,
            'error': result.get('error') if not result.get('success') else None
        }
        
    except Exception as e:
        print_error(f"Test failed: {str(e)}")
        return {
            'agent': agent_name,
            'success': False,
            'error': str(e)
        }


async def test_all_agents():
    """Test all enabled agents."""
    print_header("AGENT OS - FULL SYSTEM TEST")
    
    print_info(f"Environment: {settings.ENVIRONMENT}")
    print_info(f"Enabled agents: {', '.join(settings.enabled_agents)}")
    
    results = []
    
    for agent_name in settings.enabled_agents:
        result = await test_agent(agent_name)
        results.append(result)
        print()  # Empty line between agents
    
    # Summary
    print_header("TEST SUMMARY")
    
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    print(f"Total agents tested: {len(results)}")
    print_success(f"Successful: {len(successful)}")
    
    if failed:
        print_error(f"Failed: {len(failed)}")
        for f in failed:
            print(f"  - {f['agent']}: {f.get('error', 'Unknown error')}")
    
    print("\n📈 Performance:")
    for r in results:
        status = "✅" if r['success'] else "❌"
        print(f"  {status} {r['agent']}: {r['duration']:.2f}s")
    
    return len(failed) == 0


def list_all_agents():
    """List all available agents."""
    print_header("AVAILABLE AGENTS")
    
    agents = list_agents()
    enabled = settings.enabled_agents
    
    for agent_name in agents:
        status = "✅ enabled" if agent_name in enabled else "⬜ disabled"
        
        try:
            agent = get_agent(agent_name)
            print(f"\n{agent_name.upper()}")
            print(f"  Status: {status}")
            print(f"  Name: {agent.name}")
            print(f"  Description: {agent.description}")
            print(f"  Capabilities: {', '.join(agent.capabilities[:3])}...")
        except Exception as e:
            print(f"\n{agent_name.upper()}")
            print(f"  Status: {status}")
            print(f"  Error loading: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test Agent OS agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/test-agents.py --list
  python scripts/test-agents.py --agent scout
  python scripts/test-agents.py --all
        """
    )
    
    parser.add_argument(
        '--agent',
        type=str,
        choices=list_agents(),
        help='Test a specific agent'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Test all enabled agents'
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all available agents'
    )
    
    args = parser.parse_args()
    
    if args.list:
        list_all_agents()
        return 0
    
    if args.agent:
        result = asyncio.run(test_agent(args.agent))
        return 0 if result['success'] else 1
    
    if args.all:
        success = asyncio.run(test_all_agents())
        return 0 if success else 1
    
    # Default: show help
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
