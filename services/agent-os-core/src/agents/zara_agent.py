"""ZARA Agent - Sentilyze Community Architect & Lead Generation Engine."""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

import structlog

from src.agents.base import BaseAgent
from src.config import settings

logger = structlog.get_logger(__name__)


class ZaraAgent(BaseAgent):
    """
    ZARA - Sentilyze Community Architect
    
    Metodoloji: Data-Driven Community Management + Smart Lead Qualification
    
    Görev: Sentilyze için community engagement ve lead generation.
    SCOUT'tan gelen fırsatları community açılarına dönüştürür.
    ELON'un deneylerini community feedback'iyle destekler.
    SETH'in content'ini community'de yayar.
    """

    def __init__(self):
        """Initialize ZARA agent."""
        super().__init__(
            agent_type="zara",
            name="ZARA (Community Architect)",
            description="Sentilyze Community Engagement & Lead Generation Engine",
        )

        self.capabilities = [
            "Multi-Platform Community Management",
            "Smart Lead Qualification",
            "VIP Follower Tracking",
            "Sentiment-Based Engagement",
            "Content Amplification",
            "Crisis Detection & Response",
        ]

        self.system_prompt = """You are ZARA, Sentilyze's community architect.

Your mission: Build and nurture a thriving community that drives qualified leads to Sentilyze.

PLATFORMS:
1. Reddit (r/CryptoCurrency, r/Gold, r/Investing, r/algotrading)
2. Discord (Crypto trading communities)
3. Twitter/X (Crypto Twitter, FinTwit)
4. LinkedIn (B2B audience)

ENGAGEMENT PRINCIPLES:
1. 2-Hour SLA: Rapid response during market hours
2. Value First: Never sell, always educate
3. Data-Driven: Reference Sentilyze insights naturally
4. Lead Qualification: Identify and nurture high-value prospects
5. Escalation: Route enterprise inquiries to sales

COMMUNITY LIFECYCLE:
Newbie → Regular → Advocate → Ambassador → Customer

VIP TRACKING:
- Engagement score > 100: VIP status
- Engagement score > 500: Advocate tier
- Engagement score > 1000: Ambassador tier

SCOUT INTEGRATION:
- Amplify SCOUT discoveries in communities
- Create discussions around sentiment shifts
- Position Sentilyze as market intelligence source

SETH INTEGRATION:
- Share SETH content in relevant communities
- Drive traffic to blog posts
- Generate discussions from content themes

ELON INTEGRATION:
- Gather community feedback for experiments
- Test messaging variations
- Validate hypotheses with real users

OUTPUT: Engagement actions, lead reports, community health metrics, and escalation alerts"""

        self.version = "2.0.0"
        
        # Configuration
        self.vip_threshold = 100
        self.escalation_keywords = {
            "enterprise", "api", "whitelabel", "partnership", 
            "integration", "demo", "pricing", "investment",
            "institutional", "hedge fund", "trading firm",
        }
        
        self.lead_keywords = {
            "tool", "platform", "software", "service",
            "track", "monitor", "analyze", "sentiment",
            "recommendation", "signal", "alert", "bot",
        }
        
        self.platforms = {
            "reddit": {
                "subreddits": ["r/CryptoCurrency", "r/Gold", "r/Investing", "r/algotrading"],
                "tone": "knowledgeable, humble, data-backed",
                "response_length": "medium",
            },
            "discord": {
                "servers": ["Crypto communities", "Trading groups"],
                "tone": "casual, helpful, real-time",
                "response_length": "short",
            },
            "twitter": {
                "tone": "witty, concise, data-driven",
                "response_length": "short",
            },
            "linkedin": {
                "tone": "professional, insightful, B2B",
                "response_length": "medium",
            },
        }

    def _get_conversational_system_prompt(self) -> str:
        from src.prompts.system_prompts import get_conversational_prompt
        return get_conversational_prompt(self.agent_type)

    async def _execute(self, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute ZARA community engagement workflow.

        Args:
            context: Optional context with directives from other agents

        Returns:
            Engagement results and community insights
        """
        results = {
            "engagements_created": [],
            "leads_identified": [],
            "escalations": [],
            "community_insights": [],
            "vip_updates": [],
            "content_amplified": [],
            "timestamp": datetime.utcnow().isoformat(),
        }

        # 1. Process SCOUT directives for community angles
        logger.info("zara.processing_scout_directives")
        scout_engagements = await self._process_scout_directives(context)
        results["engagements_created"].extend(scout_engagements)

        # 2. Process ELON requests for community feedback
        logger.info("zara.processing_elon_requests")
        elon_engagements = await self._process_elon_requests(context)
        results["engagements_created"].extend(elon_engagements)

        # 3. Monitor and respond to mentions
        logger.info("zara.monitoring_mentions")
        mention_engagements = await self._monitor_and_respond()
        results["engagements_created"].extend(mention_engagements)

        # 4. Identify and qualify leads
        logger.info("zara.qualifying_leads")
        for engagement in results["engagements_created"]:
            lead_info = await self._qualify_lead(engagement)
            if lead_info:
                results["leads_identified"].append(lead_info)

        # 5. Check for escalations
        logger.info("zara.checking_escalations")
        for engagement in results["engagements_created"]:
            if self._should_escalate(engagement):
                escalation = await self._create_escalation(engagement)
                results["escalations"].append(escalation)
                await self._notify_escalation(escalation)

        # 6. Update VIP list
        logger.info("zara.updating_vips")
        vip_updates = await self._update_vip_statuses()
        results["vip_updates"] = vip_updates

        # 7. Amplify SETH content
        logger.info("zara.amplifying_content")
        amplification_results = await self._amplify_recent_content()
        results["content_amplified"] = amplification_results

        # 8. Generate community insights
        logger.info("zara.generating_insights")
        insights = await self._generate_community_insights()
        results["community_insights"] = insights

        # 9. Save all engagements
        for engagement in results["engagements_created"]:
            await self.firestore.save_community_engagement(
                engagement_id=engagement["engagement_id"],
                engagement_data=engagement,
            )

        # 10. Publish insights to Pub/Sub for other agents
        if insights:
            await self.pubsub.publish_community_insights(
                insights=insights,
                agent_name="ZARA",
            )

        logger.info(
            "zara.community_workflow_complete",
            engagements=len(results["engagements_created"]),
            leads=len(results["leads_identified"]),
            escalations=len(results["escalations"]),
        )

        return results

    async def _process_scout_directives(
        self, 
        context: Optional[Dict]
    ) -> List[Dict[str, Any]]:
        """Process SCOUT directives into community engagements.

        Args:
            context: Execution context

        Returns:
            Engagements to create
        """
        engagements = []
        
        if not context or "scout_directives" not in context:
            return engagements
        
        for directive in context["scout_directives"]:
            if directive.get("target_agent") == "ZARA":
                angle = directive.get("angle", "")
                platform = directive.get("platform", "reddit")
                asset = directive.get("asset", "")
                
                # Create engagement
                engagement = await self._create_community_engagement(
                    platform=platform,
                    angle=angle,
                    asset=asset,
                    source="SCOUT",
                    engagement_type="data_sharing",
                )
                
                if engagement:
                    engagements.append(engagement)

        return engagements

    async def _process_elon_requests(
        self, 
        context: Optional[Dict]
    ) -> List[Dict[str, Any]]:
        """Process ELON requests for community feedback.

        Args:
            context: Execution context

        Returns:
            Engagements to create
        """
        engagements = []
        
        if not context or "elon_requests" not in context:
            return engagements
        
        for request in context["elon_requests"]:
            if request.get("target_agent") == "ZARA":
                if request.get("type") == "engagement_focus":
                    # Create feedback-seeking engagement
                    engagement = await self._create_community_engagement(
                        platform="reddit",
                        angle="What features would you want in a crypto sentiment analysis tool?",
                        asset="general",
                        source="ELON",
                        engagement_type="feedback_collection",
                    )
                    
                    if engagement:
                        engagements.append(engagement)

        return engagements

    async def _monitor_and_respond(self) -> List[Dict[str, Any]]:
        """Monitor social mentions and generate responses.

        Returns:
            Engagements created
        """
        engagements = []
        
        # In production, this would connect to social APIs
        # For now, simulate with high-volume sentiment data
        try:
            # Get recent high-engagement sentiment mentions
            sentiment_data = await self.bigquery.get_sentiment_data(
                hours=2,
                limit=20,
            )
            
            for item in sentiment_data:
                # Only respond to items with significant engagement
                if item.get("volume", 0) > 50:
                    # Determine platform (default to reddit for simulation)
                    platform = self._detect_platform(item.get("source", "reddit"))
                    
                    engagement = await self._create_response_engagement(
                        mention=item,
                        platform=platform,
                    )
                    
                    if engagement:
                        engagements.append(engagement)
        
        except Exception as e:
            logger.error("zara.monitoring_error", error=str(e))
        
        return engagements

    def _detect_platform(self, source: str) -> str:
        """Detect platform from source.

        Args:
            source: Data source

        Returns:
            Platform name
        """
        source_lower = source.lower()
        
        if "reddit" in source_lower:
            return "reddit"
        elif "twitter" in source_lower or "x.com" in source_lower:
            return "twitter"
        elif "discord" in source_lower:
            return "discord"
        elif "linkedin" in source_lower:
            return "linkedin"
        else:
            return "reddit"  # Default

    async def _create_response_engagement(
        self,
        mention: Dict[str, Any],
        platform: str,
    ) -> Optional[Dict[str, Any]]:
        """Create response engagement for a mention.

        Args:
            mention: Mention data
            platform: Platform name

        Returns:
            Engagement data
        """
        content = mention.get("text", "")
        asset = mention.get("asset", "")
        sentiment = mention.get("sentiment_label", "neutral")
        
        # Check if this is worth responding to
        if not self._is_response_worthy(content, platform):
            return None
        
        # Generate response
        response = await self._generate_platform_response(
            content=content,
            platform=platform,
            asset=asset,
            sentiment=sentiment,
        )
        
        if not response:
            return None
        
        engagement_id = f"zara-{platform}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{hash(content) % 10000}"
        
        return {
            "engagement_id": engagement_id,
            "platform": platform,
            "type": "response",
            "original_content": content[:500],
            "response": response,
            "asset": asset,
            "sentiment": sentiment,
            "source": "monitoring",
            "lead_potential": self._assess_lead_potential(content),
            "escalation_potential": self._should_escalate_content(content),
            "timestamp": datetime.utcnow().isoformat(),
            "status": "ready_to_send",
        }

    def _is_response_worthy(self, content: str, platform: str) -> bool:
        """Determine if content is worth responding to.

        Args:
            content: Content to check
            platform: Platform

        Returns:
            True if worth responding
        """
        content_lower = content.lower()
        
        # Skip if too short
        if len(content) < 20:
            return False
        
        # Check for relevant keywords
        relevant_keywords = {
            "sentiment", "crypto", "bitcoin", "btc", "eth", "ethereum",
            "gold", "xau", "trading", "market", "analysis", "prediction",
            "fear", "greed", "bullish", "bearish", "signal",
        }
        
        has_relevant = any(kw in content_lower for kw in relevant_keywords)
        
        # Check for question or discussion starter
        is_question = "?" in content or any(
            phrase in content_lower 
            for phrase in ["what", "how", "why", "when", "who", "which"]
        )
        
        return has_relevant and (is_question or len(content) > 100)

    async def _generate_platform_response(
        self,
        content: str,
        platform: str,
        asset: str,
        sentiment: str,
    ) -> Optional[str]:
        """Generate platform-appropriate response.

        Args:
            content: Original content
            platform: Platform
            asset: Asset mentioned
            sentiment: Sentiment

        Returns:
            Response text
        """
        platform_config = self.platforms.get(platform, self.platforms["reddit"])
        tone = platform_config["tone"]
        
        prompt = f"""Generate a {platform} response to this crypto/sentiment discussion:

Original: "{content[:300]}"
Asset mentioned: {asset or "general crypto"}
Detected sentiment: {sentiment}

Guidelines:
- Tone: {tone}
- Be helpful and add value
- Reference data/insights when relevant
- Mention Sentilyze naturally if appropriate
- Keep it concise (2-4 sentences)
- Ask a follow-up question when relevant
- Never be promotional or salesy
- Platform style: {platform}

Example good responses:
- "Interesting observation. Our data shows similar patterns in {asset} sentiment over the last 48h. Have you noticed any correlation with volume spikes?"
- "This aligns with what we're seeing in sentiment analysis. The fear index just hit a 30-day low. What's your take on the reversal potential?"

Generate response:"""

        try:
            response = await self.kimi.generate(
                prompt=prompt,
                system_prompt=self.system_prompt,
                temperature=0.8,
                max_tokens=150,
            )
            
            return response.strip() if response else None
            
        except Exception as e:
            logger.error("zara.response_generation_error", error=str(e))
            return None

    def _assess_lead_potential(self, content: str) -> str:
        """Assess lead potential of content.

        Args:
            content: Content to assess

        Returns:
            Lead potential level
        """
        content_lower = content.lower()
        
        # Count lead indicators
        indicators = sum(1 for kw in self.lead_keywords if kw in content_lower)
        
        # Check for intent signals
        intent_signals = [
            "looking for", "need", "want", "searching", "recommend",
            "best", "tool", "platform", "alternative to",
        ]
        has_intent = any(signal in content_lower for signal in intent_signals)
        
        if indicators >= 3 and has_intent:
            return "High"
        elif indicators >= 2 or has_intent:
            return "Medium"
        else:
            return "Low"

    def _should_escalate_content(self, content: str) -> bool:
        """Check if content should be escalated.

        Args:
            content: Content to check

        Returns:
            True if should escalate
        """
        content_lower = content.lower()
        return any(kw in content_lower for kw in self.escalation_keywords)

    async def _qualify_lead(self, engagement: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Qualify lead from engagement.

        Args:
            engagement: Engagement data

        Returns:
            Lead info if qualified
        """
        lead_potential = engagement.get("lead_potential", "Low")
        
        if lead_potential in ["High", "Medium"]:
            return {
                "lead_id": f"lead-{engagement['engagement_id']}",
                "platform": engagement["platform"],
                "source_engagement": engagement["engagement_id"],
                "lead_score": 80 if lead_potential == "High" else 50,
                "lead_tier": "Hot" if lead_potential == "High" else "Warm",
                "asset_interest": engagement.get("asset", ""),
                "detected_at": datetime.utcnow().isoformat(),
                "status": "identified",
            }
        
        return None

    def _should_escalate(self, engagement: Dict[str, Any]) -> bool:
        """Determine if engagement needs escalation.

        Args:
            engagement: Engagement data

        Returns:
            True if should escalate
        """
        return engagement.get("escalation_potential", False)

    async def _create_escalation(
        self, 
        engagement: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create escalation record.

        Args:
            engagement: Engagement data

        Returns:
            Escalation data
        """
        return {
            "escalation_id": f"esc-{engagement['engagement_id']}",
            "source_engagement": engagement["engagement_id"],
            "platform": engagement["platform"],
            "priority": "High",
            "reason": "Enterprise/Integration keywords detected",
            "original_content": engagement["original_content"],
            "asset": engagement.get("asset", ""),
            "escalated_at": datetime.utcnow().isoformat(),
            "status": "pending_sales_review",
        }

    async def _notify_escalation(self, escalation: Dict[str, Any]) -> None:
        """Notify about escalation.

        Args:
            escalation: Escalation data
        """
        message = f"""🚨 High-Value Lead Escalated

Platform: {escalation['platform']}
Asset: {escalation.get('asset', 'N/A')}
Priority: {escalation['priority']}

Content Preview:
{escalation['original_content'][:300]}...

This lead mentioned enterprise keywords and should be contacted by the sales team."""

        await self.telegram.send_message(message)

    async def _update_vip_statuses(self) -> List[Dict[str, Any]]:
        """Update VIP follower statuses.

        Returns:
            VIP updates
        """
        updates = []
        
        try:
            # Get recent engagements
            recent_engagements = await self.firestore.get_community_engagements(
                limit=500,
            )
            
            # Calculate engagement scores by user
            user_scores: Dict[str, Dict] = {}
            
            for eng in recent_engagements:
                # Extract user identifier (platform + author)
                user_key = f"{eng.get('platform', 'unknown')}_{hash(eng.get('original_content', '')) % 100000}"
                
                if user_key not in user_scores:
                    user_scores[user_key] = {
                        "engagement_count": 0,
                        "total_score": 0,
                        "platforms": set(),
                        "last_engagement": None,
                    }
                
                user_scores[user_key]["engagement_count"] += 1
                user_scores[user_key]["total_score"] += 10  # Base score per engagement
                user_scores[user_key]["platforms"].add(eng.get("platform", "unknown"))
                
                eng_time = eng.get("timestamp")
                if eng_time:
                    user_scores[user_key]["last_engagement"] = eng_time
            
            # Identify and update VIPs
            for user_key, data in user_scores.items():
                if data["total_score"] >= self.vip_threshold:
                    # Determine tier
                    if data["total_score"] >= 1000:
                        tier = "ambassador"
                    elif data["total_score"] >= 500:
                        tier = "advocate"
                    else:
                        tier = "vip"
                    
                    vip_data = {
                        "user_key": user_key,
                        "tier": tier,
                        "engagement_score": data["total_score"],
                        "engagement_count": data["engagement_count"],
                        "platforms": list(data["platforms"]),
                        "last_engagement": data["last_engagement"],
                        "updated_at": datetime.utcnow().isoformat(),
                    }
                    
                    # Save VIP data
                    await self.firestore.save_vip_follower(
                        vip_id=user_key,
                        vip_data=vip_data,
                    )
                    
                    updates.append(vip_data)
        
        except Exception as e:
            logger.error("zara.vip_update_error", error=str(e))
        
        return updates

    async def _amplify_recent_content(self) -> List[Dict[str, Any]]:
        """Amplify recent SETH content in communities.

        Returns:
            Amplification results
        """
        results = []
        
        try:
            # Get recent content from SETH
            recent_content = await self.firestore.get_content(
                content_type="blog",
                status="approved",
                limit=5,
            )
            
            for content in recent_content:
                # Create amplification engagement
                engagement = await self._create_content_amplification(content)
                
                if engagement:
                    results.append({
                        "content_id": content.get("content_id"),
                        "title": content.get("title"),
                        "platform": engagement["platform"],
                        "amplification_type": engagement["type"],
                    })
        
        except Exception as e:
            logger.error("zara.amplification_error", error=str(e))
        
        return results

    async def _create_content_amplification(
        self, 
        content: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create engagement to amplify content.

        Args:
            content: Content to amplify

        Returns:
            Amplification engagement
        """
        title = content.get("title", "")
        pillar = content.get("pillar", "")
        
        # Determine best platform based on content type
        platform = "reddit" if "Crypto" in pillar or "Gold" in pillar else "linkedin"
        
        prompt = f"""Create a {platform} post to share this blog article:

Title: {title}
Topic: {pillar}

Guidelines:
- Share the key insight, not just the link
- Ask an engaging question
- Match {platform} style and tone
- Encourage discussion
- Keep it natural, not promotional

Format: Just the post text (no "Post:" prefix)"""

        try:
            post_text = await self.kimi.generate(
                prompt=prompt,
                system_prompt=self.system_prompt,
                temperature=0.7,
                max_tokens=200,
            )
            
            engagement_id = f"zara-amp-{content.get('content_id', '')}-{datetime.utcnow().strftime('%Y%m%d')}"
            
            return {
                "engagement_id": engagement_id,
                "platform": platform,
                "type": "content_amplification",
                "content_id": content.get("content_id"),
                "post_text": post_text.strip(),
                "source": "SETH",
                "timestamp": datetime.utcnow().isoformat(),
                "status": "ready_to_publish",
            }
            
        except Exception as e:
            logger.error("zara.amplification_creation_error", error=str(e))
            return None

    async def _generate_community_insights(self) -> List[Dict[str, Any]]:
        """Generate insights from community activity.

        Returns:
            Community insights
        """
        insights = []
        
        try:
            # Get recent sentiment trends
            sentiment_7d = await self.bigquery.get_sentiment_data(hours=168)
            
            # Analyze for community trends
            if sentiment_7d:
                # Find most discussed asset
                asset_counts: Dict[str, int] = {}
                for item in sentiment_7d:
                    asset = item.get("asset", "unknown")
                    asset_counts[asset] = asset_counts.get(asset, 0) + 1
                
                top_asset = max(asset_counts.items(), key=lambda x: x[1])
                
                insights.append({
                    "type": "community_trend",
                    "asset": top_asset[0],
                    "mention_count": top_asset[1],
                    "insight": f"{top_asset[0]} is the most discussed asset in communities",
                    "recommendation": "Create targeted content and engagement around this asset",
                    "priority": "High" if top_asset[1] > 100 else "Medium",
                })
            
            # Count recent leads
            recent_leads = await self.firestore.get_leads(
                hours=24,
                limit=100,
            )
            
            if len(recent_leads) > 5:
                insights.append({
                    "type": "lead_velocity",
                    "leads_24h": len(recent_leads),
                    "insight": f"High lead generation velocity: {len(recent_leads)} leads in 24h",
                    "recommendation": "Ensure sales team is prepared for follow-up",
                    "priority": "High",
                })
        
        except Exception as e:
            logger.error("zara.insights_error", error=str(e))
        
        return insights

    def _summarize_result(self, result: Dict[str, Any]) -> str:
        """Summarize results for notifications.

        Args:
            result: Execution results

        Returns:
            Summary string
        """
        engagements = len(result.get("engagements_created", []))
        leads = len(result.get("leads_identified", []))
        escalations = len(result.get("escalations", []))
        vips = len(result.get("vip_updates", []))
        
        hot_leads = sum(1 for l in result.get("leads_identified", []) if l.get("lead_tier") == "Hot")
        
        return (
            f"Created {engagements} engagements, "
            f"identified {leads} leads ({hot_leads} hot), "
            f"{escalations} escalations, "
            f"{vips} VIPs updated"
        )
