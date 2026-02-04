"""Agent Ecosystem Orchestrator - Autonomous Agent Coordination System.

This module enables agents to:
1. Listen to each other's events and outputs
2. Trigger each other based on results
3. Build a continuous learning ecosystem
4. Share knowledge and improve collectively
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

import structlog
from src.config import settings
from src.data_bridge.pubsub_client import PubSubDataClient

logger = structlog.get_logger(__name__)


class EventType(Enum):
    """Types of events agents can publish/subscribe to."""
    TREND_DETECTED = "trend_detected"
    OPPORTUNITY_FOUND = "opportunity_found"
    VALIDATION_COMPLETED = "validation_completed"
    CONTENT_CREATED = "content_created"
    EXPERIMENT_PROPOSED = "experiment_proposed"
    INSIGHT_GENERATED = "insight_generated"
    AGENT_TRIGGERED = "agent_triggered"
    COORDINATION_REQUEST = "coordination_request"
    LEARNING_UPDATE = "learning_update"


class TriggerCondition(Enum):
    """Conditions for agent triggering."""
    ALWAYS = "always"
    HIGH_CONFIDENCE = "high_confidence"
    VALIDATION_NEEDED = "validation_needed"
    CONTENT_OPPORTUNITY = "content_opportunity"
    CRISIS_DETECTED = "crisis_detected"


@dataclass
class AgentEvent:
    """Represents an event in the agent ecosystem."""
    event_type: EventType
    source_agent: str
    target_agents: List[str]
    payload: Dict[str, Any]
    priority: int = 5  # 1 (highest) to 10 (lowest)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    

@dataclass
class AgentRelationship:
    """Defines relationship between two agents."""
    source_agent: str
    target_agent: str
    trigger_conditions: List[TriggerCondition]
    event_types: List[EventType]
    enabled: bool = True
    cooldown_minutes: int = 30
    last_triggered: Optional[datetime] = None


class AgentEcosystemOrchestrator:
    """Orchestrates autonomous agent interactions and continuous learning.
    
    Features:
    - Event-driven agent coordination
    - Automatic agent triggering based on results
    - Knowledge sharing between agents
    - Continuous learning and adaptation
    - Self-improving agent ecosystem
    """
    
    def __init__(self):
        """Initialize the orchestrator."""
        self.pubsub = PubSubDataClient()
        self.event_handlers: Dict[EventType, List[Callable]] = {}
        self.agent_relationships: Dict[str, List[AgentRelationship]] = {}
        self.event_history: List[AgentEvent] = []
        self.max_history_size = 1000
        self.running = False
        self.subscribers: List[Any] = []
        self.learning_data: Dict[str, Any] = {}
        
        # Initialize event handlers
        self._initialize_event_handlers()
        # Initialize agent relationships
        self._initialize_agent_relationships()
        
        logger.info("agent_ecosystem.initialized")
    
    def _initialize_event_handlers(self) -> None:
        """Initialize event handlers for each event type."""
        self.event_handlers = {
            EventType.TREND_DETECTED: [
                self._handle_trend_detected,
            ],
            EventType.OPPORTUNITY_FOUND: [
                self._handle_opportunity_found,
            ],
            EventType.VALIDATION_COMPLETED: [
                self._handle_validation_completed,
            ],
            EventType.CONTENT_CREATED: [
                self._handle_content_created,
            ],
            EventType.EXPERIMENT_PROPOSED: [
                self._handle_experiment_proposed,
            ],
            EventType.INSIGHT_GENERATED: [
                self._handle_insight_generated,
            ],
            EventType.AGENT_TRIGGERED: [
                self._handle_agent_triggered,
            ],
            EventType.LEARNING_UPDATE: [
                self._handle_learning_update,
            ],
        }
    
    def _initialize_agent_relationships(self) -> None:
        """Initialize agent relationships for ecosystem coordination."""
        relationships = [
            # SCOUT discovers trends → ORACLE validates them
            AgentRelationship(
                source_agent="scout",
                target_agent="oracle",
                trigger_conditions=[TriggerCondition.ALWAYS, TriggerCondition.VALIDATION_NEEDED],
                event_types=[EventType.TREND_DETECTED, EventType.OPPORTUNITY_FOUND],
                cooldown_minutes=15
            ),
            
            # ORACLE validates → SCOUT learns from validation
            AgentRelationship(
                source_agent="oracle",
                target_agent="scout",
                trigger_conditions=[TriggerCondition.HIGH_CONFIDENCE],
                event_types=[EventType.VALIDATION_COMPLETED],
                cooldown_minutes=20
            ),
            
            # SCOUT finds opportunity → SETH creates content
            AgentRelationship(
                source_agent="scout",
                target_agent="seth",
                trigger_conditions=[TriggerCondition.CONTENT_OPPORTUNITY, TriggerCondition.HIGH_CONFIDENCE],
                event_types=[EventType.OPPORTUNITY_FOUND],
                cooldown_minutes=60
            ),
            
            # ZARA gets insights → ORACLE validates insights
            AgentRelationship(
                source_agent="zara",
                target_agent="oracle",
                trigger_conditions=[TriggerCondition.VALIDATION_NEEDED],
                event_types=[EventType.INSIGHT_GENERATED],
                cooldown_minutes=30
            ),
            
            # ORACLE validates → ZARA acts on validation
            AgentRelationship(
                source_agent="oracle",
                target_agent="zara",
                trigger_conditions=[TriggerCondition.ALWAYS],
                event_types=[EventType.VALIDATION_COMPLETED],
                cooldown_minutes=20
            ),
            
            # SCOUT/ELON propose experiments → ELON coordinates
            AgentRelationship(
                source_agent="scout",
                target_agent="elon",
                trigger_conditions=[TriggerCondition.CONTENT_OPPORTUNITY],
                event_types=[EventType.OPPORTUNITY_FOUND],
                cooldown_minutes=120
            ),
            
            # ELON experiments → SETH implements
            AgentRelationship(
                source_agent="elon",
                target_agent="seth",
                trigger_conditions=[TriggerCondition.HIGH_CONFIDENCE],
                event_types=[EventType.EXPERIMENT_PROPOSED],
                cooldown_minutes=180
            ),

            # SENTINEL detects anomaly → ORACLE validates
            AgentRelationship(
                source_agent="sentinel",
                target_agent="oracle",
                trigger_conditions=[TriggerCondition.VALIDATION_NEEDED],
                event_types=[EventType.TREND_DETECTED],
                cooldown_minutes=30
            ),

            # SENTINEL critical alert → SCOUT reassesses market
            AgentRelationship(
                source_agent="sentinel",
                target_agent="scout",
                trigger_conditions=[TriggerCondition.CRISIS_DETECTED],
                event_types=[EventType.TREND_DETECTED],
                cooldown_minutes=60
            ),

            # ATLAS data quality drop → SENTINEL rechecks
            AgentRelationship(
                source_agent="atlas",
                target_agent="sentinel",
                trigger_conditions=[TriggerCondition.ALWAYS],
                event_types=[EventType.INSIGHT_GENERATED],
                cooldown_minutes=120
            ),

            # SETH creates content → ZARA amplifies on social platforms
            AgentRelationship(
                source_agent="seth",
                target_agent="zara",
                trigger_conditions=[TriggerCondition.CONTENT_OPPORTUNITY],
                event_types=[EventType.CONTENT_CREATED],
                cooldown_minutes=30
            ),

            # All agents feed into learning system
            AgentRelationship(
                source_agent="*",
                target_agent="learning_system",
                trigger_conditions=[TriggerCondition.ALWAYS],
                event_types=list(EventType),
                cooldown_minutes=5
            ),
        ]
        
        for rel in relationships:
            key = f"{rel.source_agent}_to_{rel.target_agent}"
            if key not in self.agent_relationships:
                self.agent_relationships[key] = []
            self.agent_relationships[key].append(rel)
    
    async def start(self) -> None:
        """Start the orchestrator and begin listening to events."""
        if self.running:
            logger.warning("agent_ecosystem.already_running")
            return
        
        self.running = True
        logger.info("agent_ecosystem.started")
        
        # Start listening to all Pub/Sub topics
        await self._start_listeners()
        
        # Start continuous learning loop
        asyncio.create_task(self._continuous_learning_loop())
        
        # Start ecosystem health monitoring
        asyncio.create_task(self._ecosystem_health_monitor())
    
    async def stop(self) -> None:
        """Stop the orchestrator."""
        self.running = False
        for subscriber in self.subscribers:
            subscriber.cancel()
        logger.info("agent_ecosystem.stopped")
    
    async def _start_listeners(self) -> None:
        """Start listening to all agent event topics."""
        topics = [
            (self.pubsub.TOPIC_TRENDS, EventType.TREND_DETECTED),
            (self.pubsub.TOPIC_PREDICTIONS, EventType.VALIDATION_COMPLETED),
            (self.pubsub.TOPIC_EXPERIMENTS, EventType.EXPERIMENT_PROPOSED),
            (self.pubsub.TOPIC_COMMUNITY_INSIGHTS, EventType.INSIGHT_GENERATED),
            (self.pubsub.TOPIC_CONTENT, EventType.CONTENT_CREATED),
            (self.pubsub.TOPIC_AGENT_DIRECTIVES, EventType.AGENT_TRIGGERED),
        ]
        
        for topic_name, event_type in topics:
            try:
                subscriber = self.pubsub.subscribe_to_topic(
                    topic_name,
                    lambda msg, et=event_type: self._process_incoming_event(msg, et)
                )
                self.subscribers.append(subscriber)
                logger.info("agent_ecosystem.listener_started", topic=topic_name)
            except Exception as e:
                logger.error("agent_ecosystem.listener_error", topic=topic_name, error=str(e))
    
    def _process_incoming_event(self, message: Dict[str, Any], event_type: EventType) -> None:
        """Process incoming events from Pub/Sub."""
        try:
            event = AgentEvent(
                event_type=event_type,
                source_agent=message.get("agent", "unknown"),
                target_agents=message.get("target_agents", []),
                payload=message.get("data", message),
                priority=message.get("priority", 5),
                correlation_id=message.get("correlation_id"),
            )
            
            # Store in history
            self._add_to_history(event)
            
            # Execute handlers
            handlers = self.event_handlers.get(event_type, [])
            for handler in handlers:
                try:
                    asyncio.create_task(handler(event))
                except Exception as e:
                    logger.error("agent_ecosystem.handler_error", 
                               handler=handler.__name__, error=str(e))
            
            logger.debug("agent_ecosystem.event_processed", 
                        event_type=event_type.value, 
                        source=event.source_agent)
        
        except Exception as e:
            logger.error("agent_ecosystem.process_error", error=str(e))
    
    async def publish_event(self, event: AgentEvent) -> str:
        """Publish an event to the ecosystem."""
        message = {
            "event_type": event.event_type.value,
            "agent": event.source_agent,
            "target_agents": event.target_agents,
            "data": event.payload,
            "priority": event.priority,
            "timestamp": event.timestamp.isoformat(),
            "correlation_id": event.correlation_id,
        }
        
        # Map event type to topic
        topic_mapping = {
            EventType.TREND_DETECTED: self.pubsub.TOPIC_TRENDS,
            EventType.OPPORTUNITY_FOUND: self.pubsub.TOPIC_TRENDS,
            EventType.VALIDATION_COMPLETED: self.pubsub.TOPIC_PREDICTIONS,
            EventType.CONTENT_CREATED: self.pubsub.TOPIC_CONTENT,
            EventType.EXPERIMENT_PROPOSED: self.pubsub.TOPIC_EXPERIMENTS,
            EventType.INSIGHT_GENERATED: self.pubsub.TOPIC_COMMUNITY_INSIGHTS,
            EventType.AGENT_TRIGGERED: self.pubsub.TOPIC_AGENT_DIRECTIVES,
            EventType.LEARNING_UPDATE: self.pubsub.TOPIC_STRATEGY,
        }
        
        topic = topic_mapping.get(event.event_type, self.pubsub.TOPIC_AGENT_DIRECTIVES)
        
        try:
            message_id = await self.pubsub._publish(topic, message)
            self._add_to_history(event)
            logger.info("agent_ecosystem.event_published", 
                       event_type=event.event_type.value,
                       message_id=message_id)
            return message_id
        except Exception as e:
            logger.error("agent_ecosystem.publish_error", error=str(e))
            raise
    
    async def trigger_agent(self, 
                          agent_name: str, 
                          context: Dict[str, Any],
                          triggered_by: str = "ecosystem") -> None:
        """Trigger an agent with context from another agent's results."""
        from src.agents import get_agent
        
        try:
            agent = get_agent(agent_name)
            
            # Enhance context with ecosystem data
            enhanced_context = {
                **context,
                "ecosystem_triggered": True,
                "triggered_by": triggered_by,
                "ecosystem_timestamp": datetime.utcnow().isoformat(),
                "related_events": self._get_recent_events(5),
            }
            
            # Trigger agent
            logger.info("agent_ecosystem.triggering_agent", 
                       agent=agent_name,
                       triggered_by=triggered_by)
            
            asyncio.create_task(agent.run(enhanced_context))
            
        except Exception as e:
            logger.error("agent_ecosystem.trigger_error", 
                        agent=agent_name, error=str(e))
    
    async def _handle_trend_detected(self, event: AgentEvent) -> None:
        """Handle trend detection events from SCOUT."""
        trend_data = event.payload
        confidence = trend_data.get("confidence", 0)
        
        # Trigger ORACLE for validation
        if confidence >= 7.0:
            await self.trigger_agent(
                "oracle",
                {
                    "task": f"Validate trend: {trend_data.get('asset', 'unknown')}",
                    "trend_data": trend_data,
                    "validation_type": "trend_confidence",
                },
                triggered_by="scout"
            )
        
        # Trigger SETH for content if high opportunity
        opportunity_score = trend_data.get("opportunity_score", 0)
        if opportunity_score >= 7.5:
            await self.trigger_agent(
                "seth",
                {
                    "task": f"Create content for {trend_data.get('asset', 'trend')}",
                    "trend_data": trend_data,
                    "content_type": "market_analysis",
                },
                triggered_by="scout"
            )
    
    async def _handle_opportunity_found(self, event: AgentEvent) -> None:
        """Handle opportunity detection events."""
        opp_data = event.payload
        score = opp_data.get("score", 0)
        
        # Trigger multiple agents based on opportunity type
        if score >= 8.0:
            # High-value opportunity - trigger all relevant agents
            await self.trigger_agent(
                "oracle",
                {"task": "Validate high-value opportunity", "data": opp_data},
                triggered_by=event.source_agent
            )
            
            await self.trigger_agent(
                "elon",
                {"task": "Design experiment for opportunity", "data": opp_data},
                triggered_by=event.source_agent
            )
    
    async def _handle_validation_completed(self, event: AgentEvent) -> None:
        """Handle validation results from ORACLE."""
        validation = event.payload
        is_valid = validation.get("is_valid", False)
        confidence = validation.get("confidence", 0)
        
        # Feed validation back to source agent for learning
        if is_valid and confidence >= 0.8:
            # Validated with high confidence - trigger action
            source_agent = validation.get("source_agent")
            if source_agent:
                await self.trigger_agent(
                    source_agent,
                    {
                        "task": "Act on validated opportunity",
                        "validation": validation,
                        "validated": True,
                    },
                    triggered_by="oracle"
                )
    
    async def _handle_content_created(self, event: AgentEvent) -> None:
        """Handle content creation events from SETH."""
        content_data = event.payload
        
        # Trigger ZARA for content amplification
        await self.trigger_agent(
            "zara",
            {
                "task": "Amplify created content",
                "content": content_data,
            },
            triggered_by="seth"
        )
    
    async def _handle_experiment_proposed(self, event: AgentEvent) -> None:
        """Handle experiment proposals from ELON."""
        experiment = event.payload
        ice_score = experiment.get("ice_score", {})
        
        if ice_score.get("total", 0) >= 25:
            # High-ICE experiment - implement
            await self.trigger_agent(
                "seth",
                {
                    "task": "Implement high-priority experiment",
                    "experiment": experiment,
                },
                triggered_by="elon"
            )
    
    async def _handle_insight_generated(self, event: AgentEvent) -> None:
        """Handle insights from ZARA."""
        insight = event.payload
        
        # Validate insights with ORACLE
        await self.trigger_agent(
            "oracle",
            {
                "task": "Validate community insight",
                "insight": insight,
            },
            triggered_by="zara"
        )
    
    async def _handle_agent_triggered(self, event: AgentEvent) -> None:
        """Handle agent trigger events."""
        # Log for monitoring
        logger.info("agent_ecosystem.agent_triggered",
                   agent=event.payload.get("agent"),
                   triggered_by=event.source_agent)
    
    async def _handle_learning_update(self, event: AgentEvent) -> None:
        """Handle learning updates and improve agent coordination."""
        learning_data = event.payload
        
        # Update agent relationships based on learning
        for agent_pair, success_rate in learning_data.get("success_rates", {}).items():
            if success_rate > 0.8:
                # High success rate - reduce cooldown
                self._update_relationship_cooldown(agent_pair, reduction=0.5)
            elif success_rate < 0.3:
                # Low success rate - increase cooldown or disable
                self._update_relationship_cooldown(agent_pair, increase=2.0)
    
    def _add_to_history(self, event: AgentEvent) -> None:
        """Add event to history with size limit."""
        self.event_history.append(event)
        if len(self.event_history) > self.max_history_size:
            self.event_history.pop(0)
    
    def _get_recent_events(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent events for context."""
        recent = self.event_history[-count:]
        return [
            {
                "type": e.event_type.value,
                "source": e.source_agent,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in recent
        ]
    
    def _update_relationship_cooldown(self, agent_pair: str, 
                                     reduction: float = 1.0,
                                     increase: float = 1.0) -> None:
        """Update cooldown for agent relationships based on performance."""
        if agent_pair in self.agent_relationships:
            for rel in self.agent_relationships[agent_pair]:
                if reduction != 1.0:
                    rel.cooldown_minutes = max(5, int(rel.cooldown_minutes * reduction))
                elif increase != 1.0:
                    rel.cooldown_minutes = min(300, int(rel.cooldown_minutes * increase))
    
    async def _continuous_learning_loop(self) -> None:
        """Continuously learn from agent interactions and improve coordination."""
        while self.running:
            try:
                # Analyze event history for patterns
                await self._analyze_ecosystem_patterns()
                
                # Update agent strategies
                await self._update_agent_strategies()
                
                # Publish learning updates
                await self._publish_learning_update()
                
                await asyncio.sleep(300)  # Every 5 minutes
            except Exception as e:
                logger.error("agent_ecosystem.learning_error", error=str(e))
                await asyncio.sleep(60)
    
    async def _analyze_ecosystem_patterns(self) -> None:
        """Analyze patterns in agent interactions."""
        if len(self.event_history) < 10:
            return
        
        # Calculate success rates for agent pairs
        success_rates = {}
        
        for key, relationships in self.agent_relationships.items():
            for rel in relationships:
                # Count successful triggers
                relevant_events = [
                    e for e in self.event_history
                    if e.source_agent == rel.source_agent or rel.source_agent == "*"
                ]
                
                if relevant_events:
                    # Simple heuristic: more events = more engagement
                    success_rates[key] = min(1.0, len(relevant_events) / 20)
        
        self.learning_data["success_rates"] = success_rates
    
    async def _update_agent_strategies(self) -> None:
        """Update agent strategies based on ecosystem learning."""
        # Adjust agent coordination parameters
        for key, rate in self.learning_data.get("success_rates", {}).items():
            if rate > 0.9:
                logger.info("agent_ecosystem.high_success_rate", relationship=key, rate=rate)
    
    async def _publish_learning_update(self) -> None:
        """Publish learning updates to the ecosystem."""
        event = AgentEvent(
            event_type=EventType.LEARNING_UPDATE,
            source_agent="ecosystem_orchestrator",
            target_agents=list(settings.enabled_agents),
            payload=self.learning_data,
        )
        
        await self.publish_event(event)
    
    async def _ecosystem_health_monitor(self) -> None:
        """Monitor ecosystem health and agent coordination."""
        while self.running:
            try:
                # Check agent activity
                active_agents = set()
                for event in self.event_history[-50:]:
                    active_agents.add(event.source_agent)
                
                # Report ecosystem status
                logger.info("agent_ecosystem.health_check",
                           active_agents=len(active_agents),
                           total_events=len(self.event_history),
                           relationships=len(self.agent_relationships))
                
                await asyncio.sleep(600)  # Every 10 minutes
            except Exception as e:
                logger.error("agent_ecosystem.health_error", error=str(e))
                await asyncio.sleep(60)
    
    def get_ecosystem_stats(self) -> Dict[str, Any]:
        """Get current ecosystem statistics."""
        return {
            "total_events": len(self.event_history),
            "active_agents": len(set(e.source_agent for e in self.event_history[-100:])),
            "relationships": len(self.agent_relationships),
            "running": self.running,
            "learning_data": self.learning_data,
        }


# Global orchestrator instance
_orchestrator: Optional[AgentEcosystemOrchestrator] = None


def get_ecosystem_orchestrator() -> AgentEcosystemOrchestrator:
    """Get or create global orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentEcosystemOrchestrator()
    return _orchestrator