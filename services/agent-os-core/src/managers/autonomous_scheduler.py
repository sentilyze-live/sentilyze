"""Autonomous Agent Scheduler - Continuous Background Agent Execution.

This module enables agents to run continuously in the background without
user intervention, creating a self-improving ecosystem.
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass

import structlog

from src.agents import get_agent, list_agents
from src.config import settings
from src.managers.agent_ecosystem_orchestrator import (
    get_ecosystem_orchestrator, AgentEvent, EventType
)

logger = structlog.get_logger(__name__)


@dataclass
class AgentSchedule:
    """Schedule configuration for an agent."""
    agent_name: str
    min_interval_minutes: int
    max_interval_minutes: int
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    adaptive_interval: bool = True  # Adjust based on results
    success_count: int = 0
    failure_count: int = 0
    consecutive_failures: int = 0


class AutonomousAgentScheduler:
    """Schedules and runs agents autonomously in the background.
    
    Features:
    - Continuous agent execution without user intervention
    - Adaptive scheduling based on results
    - Self-improving intervals based on success/failure
    - Ecosystem integration - triggers other agents
    - Background task management
    """
    
    def __init__(self):
        """Initialize the scheduler."""
        self.schedules: Dict[str, AgentSchedule] = {}
        self.running = False
        self.tasks: List[asyncio.Task] = []
        self.orchestrator = get_ecosystem_orchestrator()
        
        # Initialize schedules for all enabled agents
        self._initialize_schedules()
        
        logger.info("autonomous_scheduler.initialized", 
                   agent_count=len(self.schedules))
    
    def _initialize_schedules(self) -> None:
        """Initialize schedules for all enabled agents."""
        schedule_configs = {
            "scout": AgentSchedule(
                agent_name="scout",
                min_interval_minutes=settings.SCOUT_INTERVAL_MINUTES,
                max_interval_minutes=settings.SCOUT_INTERVAL_MINUTES * 2,
                enabled=settings.ENABLE_SCOUT,
            ),
            "oracle": AgentSchedule(
                agent_name="oracle",
                min_interval_minutes=settings.ORACLE_INTERVAL_MINUTES,
                max_interval_minutes=settings.ORACLE_INTERVAL_MINUTES * 2,
                enabled=settings.ENABLE_ORACLE,
            ),
            "zara": AgentSchedule(
                agent_name="zara",
                min_interval_minutes=settings.ZARA_INTERVAL_MINUTES,
                max_interval_minutes=settings.ZARA_INTERVAL_MINUTES * 2,
                enabled=settings.ENABLE_ZARA,
            ),
            "elon": AgentSchedule(
                agent_name="elon",
                min_interval_minutes=settings.ELON_INTERVAL_MINUTES,
                max_interval_minutes=settings.ELON_INTERVAL_MINUTES * 2,
                enabled=settings.ENABLE_ELON,
            ),
            "seth": AgentSchedule(
                agent_name="seth",
                min_interval_minutes=settings.SETH_INTERVAL_MINUTES,
                max_interval_minutes=settings.SETH_INTERVAL_MINUTES * 2,
                enabled=settings.ENABLE_SETH,
            ),
            "sentinel": AgentSchedule(
                agent_name="sentinel",
                min_interval_minutes=settings.SENTINEL_INTERVAL_MINUTES,
                max_interval_minutes=settings.SENTINEL_INTERVAL_MINUTES * 2,
                enabled=settings.ENABLE_SENTINEL,
            ),
            "atlas": AgentSchedule(
                agent_name="atlas",
                min_interval_minutes=settings.ATLAS_INTERVAL_MINUTES,
                max_interval_minutes=settings.ATLAS_INTERVAL_MINUTES * 2,
                enabled=settings.ENABLE_ATLAS,
            ),
        }

        for agent_name, schedule in schedule_configs.items():
            if agent_name in settings.enabled_agents:
                schedule.next_run = datetime.utcnow() + timedelta(
                    minutes=random.randint(1, 10)  # Stagger initial runs
                )
                self.schedules[agent_name] = schedule
    
    async def start(self) -> None:
        """Start the autonomous scheduler."""
        if self.running:
            logger.warning("autonomous_scheduler.already_running")
            return

        self.running = True
        logger.info("autonomous_scheduler.started")

        # Start ecosystem orchestrator
        await self.orchestrator.start()

        # Start scheduler loop
        task = asyncio.create_task(self._scheduler_loop())
        self.tasks.append(task)

        # Start adaptive optimization loop
        task = asyncio.create_task(self._adaptive_optimization_loop())
        self.tasks.append(task)

        # Start brainstorming loop (every 2 days)
        if getattr(settings, "ENABLE_BRAINSTORMING", True):
            task = asyncio.create_task(self._brainstorming_loop())
            self.tasks.append(task)

        # Start autonomous action cleanup loop
        if getattr(settings, "ENABLE_AUTONOMOUS_ACTIONS", True):
            task = asyncio.create_task(self._action_cleanup_loop())
            self.tasks.append(task)

        logger.info("autonomous_scheduler.background_tasks_started")
    
    async def stop(self) -> None:
        """Stop the scheduler."""
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Stop orchestrator
        await self.orchestrator.stop()
        
        self.tasks.clear()
        logger.info("autonomous_scheduler.stopped")
    
    async def _scheduler_loop(self) -> None:
        """Main scheduler loop - continuously checks and runs agents."""
        logger.info("autonomous_scheduler.loop_started")
        
        while self.running:
            try:
                now = datetime.utcnow()
                
                # Check which agents need to run
                for agent_name, schedule in self.schedules.items():
                    if not schedule.enabled:
                        continue
                    
                    if schedule.next_run and now >= schedule.next_run:
                        # Run agent
                        asyncio.create_task(self._run_agent(agent_name))
                        
                        # Schedule next run
                        await self._schedule_next_run(agent_name)
                
                # Check every 30 seconds
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error("autonomous_scheduler.loop_error", error=str(e))
                await asyncio.sleep(60)
    
    async def _run_agent(self, agent_name: str) -> None:
        """Run a specific agent with ecosystem integration."""
        schedule = self.schedules.get(agent_name)
        if not schedule:
            return
        
        try:
            agent = get_agent(agent_name)
            
            # Build context with ecosystem data
            context = {
                "autonomous_run": True,
                "run_timestamp": datetime.utcnow().isoformat(),
                "previous_success_count": schedule.success_count,
                "previous_failure_count": schedule.failure_count,
                "ecosystem_mode": True,
            }
            
            logger.info("autonomous_scheduler.running_agent", 
                       agent=agent_name,
                       run_number=schedule.success_count + schedule.failure_count + 1)
            
            # Run agent
            result = await agent.run(context)
            
            # Update schedule stats
            schedule.last_run = datetime.utcnow()
            if result.get("success", False):
                schedule.success_count += 1
                schedule.consecutive_failures = 0
                
                # Publish success event to ecosystem
                await self._publish_agent_event(agent_name, result, success=True)
                
            else:
                schedule.failure_count += 1
                schedule.consecutive_failures += 1
                
                # Publish failure event
                await self._publish_agent_event(agent_name, result, success=False)
            
            logger.info("autonomous_scheduler.agent_completed",
                       agent=agent_name,
                       success=result.get("success", False))
            
        except Exception as e:
            logger.error("autonomous_scheduler.agent_error",
                        agent=agent_name,
                        error=str(e))
            schedule.failure_count += 1
            schedule.consecutive_failures += 1
    
    async def _schedule_next_run(self, agent_name: str) -> None:
        """Calculate and set the next run time for an agent."""
        schedule = self.schedules.get(agent_name)
        if not schedule:
            return
        
        # Adaptive scheduling
        if schedule.adaptive_interval:
            interval = self._calculate_adaptive_interval(schedule)
        else:
            interval = random.randint(
                schedule.min_interval_minutes,
                schedule.max_interval_minutes
            )
        
        schedule.next_run = datetime.utcnow() + timedelta(minutes=interval)
        
        logger.debug("autonomous_scheduler.scheduled",
                    agent=agent_name,
                    interval_minutes=interval,
                    next_run=schedule.next_run.isoformat())
    
    def _calculate_adaptive_interval(self, schedule: AgentSchedule) -> int:
        """Calculate adaptive interval based on performance."""
        base_interval = random.randint(
            schedule.min_interval_minutes,
            schedule.max_interval_minutes
        )
        
        # If many consecutive failures, increase interval (back off)
        if schedule.consecutive_failures >= 3:
            base_interval *= 2
            logger.warning("autonomous_scheduler.backoff",
                          agent=schedule.agent_name,
                          consecutive_failures=schedule.consecutive_failures)
        
        # If high success rate, can decrease interval slightly
        total_runs = schedule.success_count + schedule.failure_count
        if total_runs > 5:
            success_rate = schedule.success_count / total_runs
            if success_rate > 0.9:
                base_interval = max(
                    schedule.min_interval_minutes,
                    int(base_interval * 0.9)
                )
        
        return base_interval
    
    async def _publish_agent_event(self, agent_name: str, 
                                   result: Dict[str, Any], 
                                   success: bool) -> None:
        """Publish agent result to the ecosystem."""
        event_type = EventType.LEARNING_UPDATE if success else EventType.COORDINATION_REQUEST
        
        event = AgentEvent(
            event_type=event_type,
            source_agent=agent_name,
            target_agents=[],  # Broadcast to all
            payload={
                "result": result,
                "success": success,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
        
        try:
            await self.orchestrator.publish_event(event)
        except Exception as e:
            logger.error("autonomous_scheduler.publish_error", error=str(e))
    
    async def _adaptive_optimization_loop(self) -> None:
        """Continuously optimize agent schedules based on performance."""
        while self.running:
            try:
                for agent_name, schedule in self.schedules.items():
                    total_runs = schedule.success_count + schedule.failure_count
                    
                    if total_runs > 10:
                        success_rate = schedule.success_count / total_runs
                        
                        # Adjust intervals based on success rate
                        if success_rate < 0.5:
                            # Poor performance - increase intervals
                            schedule.min_interval_minutes = int(
                                schedule.min_interval_minutes * 1.2
                            )
                            schedule.max_interval_minutes = int(
                                schedule.max_interval_minutes * 1.2
                            )
                            logger.warning("autonomous_scheduler.optimization",
                                          agent=agent_name,
                                          action="increased_intervals",
                                          success_rate=success_rate)
                        
                        elif success_rate > 0.95 and schedule.consecutive_failures == 0:
                            # Excellent performance - can be more aggressive
                            schedule.min_interval_minutes = max(
                                15,  # Don't go below 15 minutes
                                int(schedule.min_interval_minutes * 0.95)
                            )
                            logger.info("autonomous_scheduler.optimization",
                                       agent=agent_name,
                                       action="decreased_intervals",
                                       success_rate=success_rate)
                
                # Run every 30 minutes
                await asyncio.sleep(1800)
                
            except Exception as e:
                logger.error("autonomous_scheduler.optimization_error", error=str(e))
                await asyncio.sleep(300)
    
    def get_scheduler_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        stats = {
            "running": self.running,
            "total_schedules": len(self.schedules),
            "active_tasks": len(self.tasks),
            "agents": {}
        }
        
        for agent_name, schedule in self.schedules.items():
            total_runs = schedule.success_count + schedule.failure_count
            success_rate = (
                schedule.success_count / total_runs if total_runs > 0 else 0
            )
            
            stats["agents"][agent_name] = {
                "enabled": schedule.enabled,
                "next_run": schedule.next_run.isoformat() if schedule.next_run else None,
                "last_run": schedule.last_run.isoformat() if schedule.last_run else None,
                "total_runs": total_runs,
                "success_rate": round(success_rate, 2),
                "consecutive_failures": schedule.consecutive_failures,
            }
        
        return stats
    
    async def trigger_agent_now(self, agent_name: str, 
                                context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Manually trigger an agent immediately."""
        if agent_name not in self.schedules:
            return {"error": f"Agent {agent_name} not found"}
        
        schedule = self.schedules[agent_name]
        
        try:
            agent = get_agent(agent_name)
            run_context = context or {}
            run_context["manual_trigger"] = True
            
            result = await agent.run(run_context)
            
            # Update stats
            schedule.last_run = datetime.utcnow()
            if result.get("success", False):
                schedule.success_count += 1
                schedule.consecutive_failures = 0
            else:
                schedule.failure_count += 1
            
            # Reschedule
            await self._schedule_next_run(agent_name)
            
            return result
            
        except Exception as e:
            logger.error("autonomous_scheduler.manual_trigger_error",
                        agent=agent_name, error=str(e))
            return {"success": False, "error": str(e)}

    async def _brainstorming_loop(self) -> None:
        """Run brainstorming sessions periodically."""
        logger.info("autonomous_scheduler.brainstorming_loop_started")

        # Wait 5 minutes after startup before first check
        await asyncio.sleep(300)

        while self.running:
            try:
                from src.managers.brainstorming_manager import get_brainstorming_manager

                brainstorming = get_brainstorming_manager()

                if await brainstorming.should_run():
                    logger.info("autonomous_scheduler.brainstorming_session_starting")
                    result = await brainstorming.run_session()
                    logger.info(
                        "autonomous_scheduler.brainstorming_session_completed",
                        proposals=result.get("total_proposals", 0),
                        dispatched=result.get("dispatched_actions", 0),
                    )

                # Check every hour
                await asyncio.sleep(3600)

            except Exception as e:
                logger.error("autonomous_scheduler.brainstorming_error", error=str(e))
                await asyncio.sleep(1800)  # Retry in 30 minutes

    async def _action_cleanup_loop(self) -> None:
        """Clean up expired pending actions periodically."""
        logger.info("autonomous_scheduler.action_cleanup_loop_started")

        while self.running:
            try:
                from src.managers.autonomous_actions import get_action_manager

                action_mgr = get_action_manager()
                expiry_hours = getattr(settings, "AUTONOMOUS_ACTION_EXPIRY_HOURS", 48)
                cleaned = await action_mgr.cleanup_expired(hours=expiry_hours)

                if cleaned > 0:
                    logger.info("autonomous_scheduler.actions_cleaned", count=cleaned)

                # Run every 6 hours
                await asyncio.sleep(21600)

            except Exception as e:
                logger.error("autonomous_scheduler.cleanup_error", error=str(e))
                await asyncio.sleep(3600)


# Global scheduler instance
_scheduler: Optional[AutonomousAgentScheduler] = None


def get_autonomous_scheduler() -> AutonomousAgentScheduler:
    """Get or create global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AutonomousAgentScheduler()
    return _scheduler