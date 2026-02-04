"""SCOUT Agent - Sentilyze Market Intelligence & Trend Hunter."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from src.agents.base import BaseAgent
from src.config import settings

logger = structlog.get_logger(__name__)


class ScoutAgent(BaseAgent):
    """
    SCOUT - Sentilyze Market Intelligence
    
    Metodoloji: Neil Patel (Veri) + Real-time Sentiment Analysis
    
    Görev: Sentilyze için pazar zekası ve fırsat tespiti.
    Kripto, altın ve AI finans trendlerini 24-48 saat öncesinden yakalar.
    Diğer agentlar için actionable intelligence üretir.
    """

    def __init__(self):
        """Initialize SCOUT agent."""
        super().__init__(
            agent_type="scout",
            name="SCOUT (Market Intelligence)",
            description="Sentilyze Market Intelligence & Opportunity Detection",
        )

        self.capabilities = [
            "Real-time Sentiment Monitoring",
            "Predictive Trend Scoring (1-10)",
            "Cross-Asset Correlation Analysis",
            "Content Opportunity Detection",
            "Competitive Intelligence",
        ]

        self.system_prompt = """You are SCOUT, Sentilyze's market intelligence analyst.

Your mission: Identify opportunities for Sentilyze before competitors.

MONITORING SCOPE:
1. Crypto Markets (BTC, ETH, major alts)
2. Gold/XAU Markets
3. AI in Finance trends
4. Sentiment Analysis industry
5. Competitor movements

SCORING CRITERIA:
- Opportunity Score (1-10): Value for Sentilyze
- Content Potential: Can SETH create content around this?
- Growth Potential: Can ELON leverage this for experiments?
- Community Angle: Can ZARA engage around this?
- Urgency: How quickly must we act?

SIGNALS TO WATCH:
- Major sentiment shifts (>20% change)
- Viral crypto discussions
- Gold price volatility
- AI trading tool launches
- Competitor feature releases

OUTPUT: JSON with opportunity_score, recommended_action, target_agents, content_angles"""

        self.version = "2.0.0"
        
        # Opportunity detection thresholds
        self.opportunity_threshold = 7.0
        self.sentiment_shift_threshold = 0.20  # 20% change

    def _get_conversational_system_prompt(self) -> str:
        from src.prompts.system_prompts import get_conversational_prompt
        return get_conversational_prompt(self.agent_type)

    async def _execute(self, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute SCOUT market intelligence workflow.

        Args:
            context: Optional context with focus areas

        Returns:
            Detected opportunities
        """
        results = {
            "opportunities_detected": [],
            "sentiment_alerts": [],
            "content_ideas": [],
            "competitive_intel": [],
            "agent_directives": {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        # 1. Analyze Sentilyze sentiment data for major shifts
        logger.info("scout.analyzing_sentiment_data")
        sentiment_opportunities = await self._analyze_sentiment_opportunities()
        results["sentiment_alerts"] = sentiment_opportunities

        # 2. Detect content opportunities for SETH
        logger.info("scout.detecting_content_opportunities")
        content_ideas = await self._detect_content_opportunities(sentiment_opportunities)
        results["content_ideas"] = content_ideas

        # 3. Identify growth opportunities for ELON
        logger.info("scout.identifying_growth_opportunities")
        growth_signals = await self._identify_growth_signals(sentiment_opportunities)

        # 4. Find community engagement angles for ZARA
        logger.info("scout.finding_community_angles")
        community_angles = await self._find_community_angles(sentiment_opportunities)

        # 5. Compile all opportunities
        all_opportunities = sentiment_opportunities + content_ideas
        
        for opp in all_opportunities:
            if opp["opportunity_score"] >= self.opportunity_threshold:
                results["opportunities_detected"].append(opp)
                
                # Save to Firestore
                await self.firestore.save_trend(
                    trend_id=opp["id"],
                    trend_data=opp,
                )
                
                # Publish event
                await self.pubsub.publish_trend(opp, agent_name="SCOUT")
                
                # Notify if high priority
                if opp["opportunity_score"] >= 8.5:
                    await self.telegram.notify_trend_detected(opp, agent_name="SCOUT")

        # 6. Generate agent-specific directives
        results["agent_directives"] = await self._generate_agent_directives(
            sentiment_opportunities, content_ideas, growth_signals, community_angles
        )

        # 7. Publish directives to Pub/Sub for other agents
        for agent, directives in results["agent_directives"].items():
            if directives:
                await self.pubsub.publish_agent_directive(
                    target_agent=agent,
                    directive=directives,
                    source_agent="SCOUT",
                )

        logger.info(
            "scout.intelligence_complete",
            opportunities=len(results["opportunities_detected"]),
            directives_sent=len(results["agent_directives"]),
        )

        return results

    async def _analyze_sentiment_opportunities(self) -> List[Dict[str, Any]]:
        """Analyze Sentilyze sentiment data for opportunities.

        Returns:
            List of opportunities
        """
        opportunities = []

        # Track assets
        assets = ["BTC", "ETH", "XAU", "SOL", "ADA"]
        
        for asset in assets:
            try:
                # Get multi-timeframe sentiment
                sentiment_24h = await self.bigquery.get_sentiment_data(
                    asset=asset,
                    hours=24,
                )
                sentiment_7d = await self.bigquery.get_sentiment_data(
                    asset=asset,
                    hours=168,
                )

                if not sentiment_24h or not sentiment_7d:
                    continue

                # Calculate metrics
                current_sentiment = self._calculate_avg_sentiment(sentiment_24h)
                prev_sentiment = self._calculate_avg_sentiment(sentiment_7d[:len(sentiment_24h)])
                sentiment_change = current_sentiment - prev_sentiment
                volume_24h = len(sentiment_24h)
                volume_7d_avg = len(sentiment_7d) / 7
                volume_spike = volume_24h / volume_7d_avg if volume_7d_avg > 0 else 1

                # Detect opportunity
                if abs(sentiment_change) > self.sentiment_shift_threshold or volume_spike > 2:
                    opportunity_score = self._calculate_opportunity_score(
                        sentiment_change, volume_spike, asset
                    )

                    opportunities.append({
                        "id": f"scout-{asset}-{datetime.utcnow().strftime('%Y%m%d-%H%M')}",
                        "type": "sentiment_shift",
                        "asset": asset,
                        "opportunity_score": opportunity_score,
                        "sentiment_change": sentiment_change,
                        "current_sentiment": current_sentiment,
                        "volume_spike": volume_spike,
                        "urgency": "High" if abs(sentiment_change) > 0.30 else "Medium",
                        "content_hook": self._generate_content_hook(asset, sentiment_change),
                        "recommended_action": self._recommend_action(asset, sentiment_change),
                        "target_agents": self._determine_target_agents(asset, sentiment_change),
                        "timestamp": datetime.utcnow().isoformat(),
                    })

            except Exception as e:
                logger.error("scout.sentiment_analysis_error", asset=asset, error=str(e))

        return opportunities

    def _calculate_avg_sentiment(self, data: List[Dict]) -> float:
        """Calculate average sentiment from data."""
        if not data:
            return 0.0
        sentiments = [d.get("sentiment_score", 0) for d in data if d.get("sentiment_score")]
        return sum(sentiments) / len(sentiments) if sentiments else 0.0

    def _calculate_opportunity_score(
        self, 
        sentiment_change: float, 
        volume_spike: float,
        asset: str
    ) -> float:
        """Calculate opportunity score."""
        base_score = 5.0
        
        # Sentiment change impact (0-3 points)
        base_score += min(abs(sentiment_change) * 10, 3.0)
        
        # Volume spike impact (0-2 points)
        base_score += min((volume_spike - 1) * 0.5, 2.0)
        
        # Asset priority bonus
        priority_assets = {"BTC": 0.5, "ETH": 0.4, "XAU": 0.3}
        base_score += priority_assets.get(asset, 0)
        
        return min(base_score, 10.0)

    def _generate_content_hook(self, asset: str, sentiment_change: float) -> str:
        """Generate content hook for SETH."""
        direction = "surged" if sentiment_change > 0 else "plunged"
        magnitude = "massively" if abs(sentiment_change) > 0.30 else "significantly"
        
        hooks = {
            "BTC": f"Bitcoin sentiment just {direction} {magnitude}. Here's what the data reveals...",
            "ETH": f"Ethereum social signals {direction} unexpectedly. Smart money is watching...",
            "XAU": f"Gold sentiment {direction} as markets react. Safe haven narrative shifting...",
        }
        
        return hooks.get(asset, f"{asset} sentiment {direction} {magnitude}. Analysis inside...")

    def _recommend_action(self, asset: str, sentiment_change: float) -> str:
        """Recommend action based on opportunity."""
        if abs(sentiment_change) > 0.40:
            return "Immediate content creation + community engagement"
        elif abs(sentiment_change) > 0.25:
            return "Content creation within 24 hours"
        else:
            return "Monitor and prepare content"

    def _determine_target_agents(self, asset: str, sentiment_change: float) -> List[str]:
        """Determine which agents should act on this opportunity."""
        agents = ["SCOUT"]  # Always includes self
        
        if abs(sentiment_change) > 0.20:
            agents.append("SETH")  # Content opportunity
        
        if abs(sentiment_change) > 0.30:
            agents.append("ELON")  # Growth experiment opportunity
            agents.append("ZARA")  # Community engagement opportunity
        
        return agents

    async def _detect_content_opportunities(
        self, 
        sentiment_opportunities: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Detect content opportunities from sentiment data.

        Args:
            sentiment_opportunities: Detected sentiment opportunities

        Returns:
            Content ideas for SETH
        """
        content_ideas = []

        for opp in sentiment_opportunities:
            if opp["opportunity_score"] >= 7.0:
                asset = opp["asset"]
                change = opp["sentiment_change"]
                
                content_ideas.append({
                    "id": f"content-{asset}-{datetime.utcnow().strftime('%Y%m%d')}",
                    "type": "content_opportunity",
                    "asset": asset,
                    "opportunity_score": opp["opportunity_score"],
                    "pillar": self._map_to_pillar(asset),
                    "topic": self._generate_topic(asset, change),
                    "content_type": "thought_leadership" if abs(change) > 0.30 else "cluster",
                    "target_agent": "SETH",
                    "priority": "High" if abs(change) > 0.30 else "Medium",
                    "seo_potential": self._estimate_seo_potential(asset, change),
                    "timestamp": datetime.utcnow().isoformat(),
                })

        return content_ideas

    def _map_to_pillar(self, asset: str) -> str:
        """Map asset to content pillar."""
        pillars = {
            "BTC": "Crypto Sentiment Analysis",
            "ETH": "Crypto Sentiment Analysis",
            "XAU": "Gold Market Intelligence",
            "SOL": "Crypto Sentiment Analysis",
            "ADA": "Crypto Sentiment Analysis",
        }
        return pillars.get(asset, "AI in Financial Markets")

    def _generate_topic(self, asset: str, sentiment_change: float) -> str:
        """Generate content topic."""
        direction = "Bullish" if sentiment_change > 0 else "Bearish"
        return f"Why {asset} Sentiment Just Went {direction} (Data Analysis)"

    def _estimate_seo_potential(self, asset: str, sentiment_change: float) -> int:
        """Estimate SEO potential (0-100)."""
        base = 60
        if asset in ["BTC", "ETH", "XAU"]:
            base += 15
        if abs(sentiment_change) > 0.30:
            base += 10
        return min(base, 95)

    async def _identify_growth_signals(
        self,
        sentiment_opportunities: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Identify growth experiment opportunities.

        Args:
            sentiment_opportunities: Detected opportunities

        Returns:
            Growth signals for ELON
        """
        growth_signals = []

        # Count high-opportunity events
        high_opp_count = sum(1 for opp in sentiment_opportunities if opp["opportunity_score"] >= 8.0)
        
        if high_opp_count >= 2:
            growth_signals.append({
                "type": "landing_page_test",
                "rationale": f"{high_opp_count} high-opportunity events detected - test real-time sentiment display",
                "target_metric": "conversion_rate",
                "potential_lift": "+15-25%",
                "target_agent": "ELON",
            })

        return growth_signals

    async def _find_community_angles(
        self,
        sentiment_opportunities: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Find community engagement angles.

        Args:
            sentiment_opportunities: Detected opportunities

        Returns:
            Community angles for ZARA
        """
        community_angles = []

        for opp in sentiment_opportunities:
            if opp["opportunity_score"] >= 7.5:
                community_angles.append({
                    "platform": "reddit",
                    "subreddit": "r/CryptoCurrency" if opp["asset"] != "XAU" else "r/Gold",
                    "angle": opp["content_hook"],
                    "asset": opp["asset"],
                    "engagement_type": "data_sharing",
                    "target_agent": "ZARA",
                })

        return community_angles

    async def _generate_agent_directives(
        self,
        sentiment_opportunities: List[Dict],
        content_ideas: List[Dict],
        growth_signals: List[Dict],
        community_angles: List[Dict],
    ) -> Dict[str, List[Dict]]:
        """Generate specific directives for each agent.

        Args:
            sentiment_opportunities: Sentiment opportunities
            content_ideas: Content opportunities
            growth_signals: Growth signals
            community_angles: Community angles

        Returns:
            Agent directives
        """
        directives = {
            "SETH": [],
            "ELON": [],
            "ZARA": [],
        }

        # Directives for SETH
        high_priority_content = [c for c in content_ideas if c["priority"] == "High"]
        for content in high_priority_content[:3]:  # Top 3
            directives["SETH"].append({
                "action": "create_content",
                "type": content["content_type"],
                "topic": content["topic"],
                "pillar": content["pillar"],
                "priority": content["priority"],
                "deadline": "24 hours",
                "rationale": f"{content['asset']} showing major sentiment movement - capitalize on search interest",
            })

        # Directives for ELON
        for signal in growth_signals:
            directives["ELON"].append({
                "action": "design_experiment",
                "type": signal["type"],
                "target_metric": signal["target_metric"],
                "potential_lift": signal["potential_lift"],
                "priority": "High",
                "rationale": signal["rationale"],
            })

        # Directives for ZARA
        for angle in community_angles[:5]:  # Top 5
            directives["ZARA"].append({
                "action": "engage_community",
                "platform": angle["platform"],
                "asset": angle["asset"],
                "angle": angle["angle"],
                "engagement_type": angle["engagement_type"],
                "priority": "Medium",
            })

        return directives

    def _summarize_result(self, result: Dict[str, Any]) -> str:
        """Summarize results for notifications.

        Args:
            result: Execution results

        Returns:
            Summary string
        """
        opportunities = result.get("opportunities_detected", [])
        high_priority = sum(1 for o in opportunities if o.get("opportunity_score", 0) >= 8.5)
        
        directives = result.get("agent_directives", {})
        directive_count = sum(len(d) for d in directives.values())

        assets = set(o.get("asset", "") for o in opportunities)
        
        return (
            f"Detected {len(opportunities)} opportunities "
            f"({high_priority} high-priority). "
            f"Assets: {', '.join(assets) if assets else 'none'}. "
            f"Sent {directive_count} directives to agents."
        )

    async def get_opportunities_for_agent(
        self,
        agent_name: str,
        min_score: float = 7.0,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get opportunities filtered for a specific agent.

        Args:
            agent_name: Target agent name
            min_score: Minimum opportunity score
            limit: Maximum results

        Returns:
            Filtered opportunities
        """
        opportunities = await self.firestore.get_trends(status="active", limit=50)
        
        # Filter by target agent and score
        filtered = [
            o for o in opportunities
            if agent_name in o.get("target_agents", [])
            and o.get("opportunity_score", 0) >= min_score
        ]
        
        # Sort by score
        filtered.sort(key=lambda x: x.get("opportunity_score", 0), reverse=True)
        
        return filtered[:limit]
