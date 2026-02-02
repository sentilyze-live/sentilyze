"""SETH Agent - Sentilyze SEO Authority & Content Engine."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from src.agents.base import BaseAgent
from src.config import settings

logger = structlog.get_logger(__name__)


class SethAgent(BaseAgent):
    """
    SETH - Sentilyze SEO Authority
    
    Metodoloji: Brian Dean (Skyscraper) + Semantic SEO + Topic Authority
    
    Görev: Sentilyze için rakiplerin geçemeyeceği kalitede SEO content üretmek.
    SCOUT'tan gelen fırsatları anında content'e dönüştürür.
    ELON'un deneylerini content ile destekler.
    """

    def __init__(self):
        """Initialize SETH agent."""
        super().__init__(
            agent_type="seth",
            name="SETH (SEO Authority)",
            description="Sentilyze SEO Powerhouse & Content Engine",
        )

        self.capabilities = [
            "Skyscraper Content Creation",
            "Pillar-Cluster Architecture",
            "Real-Time SEO Optimization",
            "Semantic Keyword Mapping",
            "Content Gap Analysis",
            "Trend-Responsive Publishing",
        ]

        self.system_prompt = """You are SETH, Sentilyze's SEO authority and content strategist.

Your mission: Build an unbeatable SEO moat that drives qualified traffic to Sentilyze.

CONTENT STRATEGY:
1. Pillar-Cluster Model: 1 massive pillar page + 10+ supporting cluster articles
2. Skyscraper Technique: Create content 10x better than top 3 ranking results
3. Search Intent Matching: Informational → Educational; Commercial → Comparison
4. Semantic SEO: Cover entire topic, not just keywords

CONTENT PILLARS:
1. Crypto Sentiment Analysis (primary)
2. Gold Market Intelligence (secondary)
3. AI in Financial Markets (emerging)

QUALITY STANDARDS:
- Pillar content: 4000+ words, comprehensive
- Cluster content: 1500+ words, focused
- SEO Score: Minimum 75/100
- Original research/data when possible
- Internal linking strategy implemented

SCOUT INTEGRATION:
- Respond to sentiment shifts with timely content
- Capitalize on trending topics within 24 hours
- Turn market events into educational content

ELON INTEGRATION:
- Create content supporting growth experiments
- Write landing page copy for tests
- Develop comparison pages for conversion

OUTPUT: SEO-optimized blog posts with complete metadata, keyword strategy, and internal linking"""

        self.version = "2.0.0"
        
        # Content pillars with expanded clusters
        self.content_pillars = {
            "Crypto Sentiment Analysis": {
                "priority": 1,
                "target_keywords": [
                    "crypto sentiment analysis",
                    "bitcoin fear and greed index",
                    "social media crypto signals",
                ],
                "clusters": [
                    "What is Crypto Sentiment Analysis (Complete Guide)",
                    "How to Read the Crypto Fear & Greed Index",
                    "Bitcoin Sentiment vs Price: Correlation Analysis",
                    "Best Tools for Crypto Sentiment Tracking [2026]",
                    "Twitter Sentiment Analysis for Crypto Trading",
                    "Reddit Crypto Sentiment: How to Use It",
                    "News Sentiment Impact on Cryptocurrency Prices",
                    "Building a Sentiment-Based Trading Strategy",
                    "Crypto Market Sentiment Indicators Explained",
                    "Historical Crypto Sentiment Analysis Case Studies",
                ],
            },
            "Gold Market Intelligence": {
                "priority": 2,
                "target_keywords": [
                    "gold price prediction",
                    "XAU/USD analysis",
                    "gold market sentiment",
                ],
                "clusters": [
                    "Gold Price Prediction Methods That Work",
                    "XAU/USD Technical Analysis Complete Guide",
                    "Gold Market Sentiment Indicators",
                    "Central Bank Gold Reserves Impact on Price",
                    "Gold vs Inflation: Historical Correlation",
                    "Safe Haven Asset Analysis: Why Gold Matters",
                    "Gold Trading Psychology: Fear and Greed",
                    "Gold Market Manipulation: Signs to Watch",
                    "Physical Gold vs ETF: Sentiment Differences",
                    "Gold Seasonality Patterns for Traders",
                ],
            },
            "AI in Financial Markets": {
                "priority": 3,
                "target_keywords": [
                    "AI trading signals",
                    "machine learning price prediction",
                    "NLP financial sentiment",
                ],
                "clusters": [
                    "Machine Learning for Price Prediction: How It Works",
                    "NLP for Financial Sentiment Analysis Explained",
                    "AI vs Human Traders: Performance Comparison",
                    "Future of AI in Investing: Trends & Predictions",
                    "How AI Trading Bots Actually Work",
                    "AI Sentiment Analysis Accuracy: Real Data",
                    "Deep Learning in Market Prediction",
                    "AI-Powered Risk Management Strategies",
                    "Ethical AI in Trading: What You Need to Know",
                    "AI Trading Regulations: Global Landscape",
                ],
            },
        }

    async def _execute(self, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute SETH content creation workflow.

        Args:
            context: Optional context with SCOUT/ELON directives

        Returns:
            Created content and content strategy updates
        """
        results = {
            "content_created": [],
            "content_queue": [],
            "seo_analysis": {},
            "pillar_status": {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        # 1. Check for SCOUT content opportunities
        logger.info("seth.checking_scout_opportunities")
        scout_opportunities = await self._get_scout_opportunities(context)

        # 2. Check for ELON content requests
        logger.info("seth.checking_elon_requests")
        elon_requests = await self._get_elon_requests(context)

        # 3. Analyze content gaps
        logger.info("seth.analyzing_content_gaps")
        content_gaps = await self._analyze_content_gaps()
        results["seo_analysis"]["content_gaps"] = len(content_gaps)

        # 4. Prioritize content requests
        content_queue = self._prioritize_content_requests(
            scout_opportunities, elon_requests, content_gaps
        )
        results["content_queue"] = content_queue

        # 5. Create high-priority content
        for request in content_queue[:2]:  # Top 2
            try:
                content = await self._create_content(request)
                
                if content:
                    results["content_created"].append(content)
                    
                    # Save to Firestore
                    await self.firestore.save_content(
                        content_id=content["content_id"],
                        content_data=content,
                    )
                    
                    # Publish event
                    await self.pubsub.publish_content(
                        content_data=content,
                        agent_name="SETH",
                        status="pending_approval",
                    )
                    
                    # Send for approval
                    await self.telegram.send_for_approval(
                        content_type="blog",
                        content=content["content"][:1000],
                        agent_name="SETH",
                        metadata={
                            "content_id": content["content_id"],
                            "title": content["title"],
                            "seo_score": content.get("seo_score", 0),
                            "pillar": content.get("pillar", ""),
                        },
                    )

            except Exception as e:
                logger.error("seth.content_creation_error", request=request, error=str(e))

        # 6. Update pillar status
        results["pillar_status"] = await self._update_pillar_status()

        # 7. Generate content strategy recommendations
        strategy_recommendations = await self._generate_strategy_recommendations(
            results["pillar_status"], content_gaps
        )
        
        # 8. Publish recommendations to Pub/Sub
        if strategy_recommendations:
            await self.pubsub.publish_strategy_update(
                recommendations=strategy_recommendations,
                agent_name="SETH",
            )

        logger.info(
            "seth.content_workflow_complete",
            created=len(results["content_created"]),
            queue_size=len(results["content_queue"]),
        )

        return results

    async def _get_scout_opportunities(
        self, 
        context: Optional[Dict]
    ) -> List[Dict[str, Any]]:
        """Get content opportunities from SCOUT.

        Args:
            context: Execution context

        Returns:
            Content opportunities
        """
        opportunities = []
        
        # Check context for SCOUT directives
        if context and "scout_directives" in context:
            for directive in context["scout_directives"]:
                if directive.get("target_agent") == "SETH":
                    opportunities.append({
                        "source": "SCOUT",
                        "type": "trend_response",
                        "topic": directive.get("topic", ""),
                        "pillar": directive.get("pillar", ""),
                        "priority": directive.get("priority", "Medium"),
                        "asset": directive.get("asset", ""),
                        "deadline": directive.get("deadline", "24 hours"),
                        "rationale": directive.get("rationale", ""),
                    })
        
        # Also check Firestore for recent SCOUT trends
        try:
            recent_trends = await self.firestore.get_trends(status="active", limit=10)
            for trend in recent_trends:
                if "SETH" in trend.get("target_agents", []) and trend.get("opportunity_score", 0) >= 7.5:
                    opportunities.append({
                        "source": "SCOUT_TREND",
                        "type": "trend_response",
                        "topic": trend.get("content_hook", ""),
                        "pillar": trend.get("pillar", ""),
                        "priority": "High" if trend.get("opportunity_score", 0) >= 8.5 else "Medium",
                        "asset": trend.get("asset", ""),
                        "opportunity_score": trend.get("opportunity_score", 0),
                    })
        except Exception as e:
            logger.error("seth.scout_opportunities_error", error=str(e))
        
        return opportunities

    async def _get_elon_requests(
        self, 
        context: Optional[Dict]
    ) -> List[Dict[str, Any]]:
        """Get content requests from ELON.

        Args:
            context: Execution context

        Returns:
            Content requests
        """
        requests = []
        
        if context and "elon_requests" in context:
            for request in context["elon_requests"]:
                if request.get("target_agent") == "SETH":
                    requests.append({
                        "source": "ELON",
                        "type": "experiment_support",
                        "topic": request.get("topic", ""),
                        "target_keyword": request.get("target_keyword", ""),
                        "priority": request.get("priority", "Medium"),
                        "rationale": request.get("rationale", ""),
                    })
        
        return requests

    async def _analyze_content_gaps(self) -> List[Dict[str, Any]]:
        """Analyze content gaps for each pillar.

        Returns:
            List of content gaps
        """
        gaps = []
        
        # Get existing content
        try:
            existing_content = await self.firestore.get_content(
                content_type="blog",
                limit=100,
            )
            existing_topics = {c.get("title", "").lower() for c in existing_content}
            
            # Check each pillar
            for pillar_name, pillar_data in self.content_pillars.items():
                for cluster_topic in pillar_data["clusters"]:
                    # Check if content exists
                    if not any(cluster_topic.lower() in existing for existing in existing_topics):
                        # Calculate opportunity score
                        opp_score = 10 - pillar_data["priority"]  # Higher priority = higher score
                        
                        gaps.append({
                            "source": "GAP_ANALYSIS",
                            "type": "cluster_content",
                            "pillar": pillar_name,
                            "topic": cluster_topic,
                            "priority": "High" if opp_score >= 8 else "Medium",
                            "opportunity_score": opp_score,
                            "target_keywords": pillar_data["target_keywords"],
                        })
        
        except Exception as e:
            logger.error("seth.gap_analysis_error", error=str(e))
        
        # Sort by opportunity score
        gaps.sort(key=lambda x: x.get("opportunity_score", 0), reverse=True)
        
        return gaps[:10]  # Top 10 gaps

    def _prioritize_content_requests(
        self,
        scout_opps: List[Dict],
        elon_requests: List[Dict],
        content_gaps: List[Dict],
    ) -> List[Dict[str, Any]]:
        """Prioritize all content requests.

        Args:
            scout_opps: SCOUT opportunities
            elon_requests: ELON requests
            content_gaps: Content gaps

        Returns:
            Prioritized queue
        """
        all_requests = scout_opps + elon_requests + content_gaps
        
        # Priority scoring
        def get_priority_score(request):
            priority_scores = {"High": 3, "Medium": 2, "Low": 1}
            base_score = priority_scores.get(request.get("priority", "Medium"), 2)
            
            # Boost for time-sensitive SCOUT opportunities
            if request.get("source") == "SCOUT":
                base_score += 2
            
            # Boost for high opportunity score
            opp_score = request.get("opportunity_score", 5)
            base_score += opp_score / 5
            
            return base_score
        
        # Sort by priority score
        all_requests.sort(key=get_priority_score, reverse=True)
        
        return all_requests

    async def _create_content(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create content based on request.

        Args:
            request: Content request

        Returns:
            Created content
        """
        content_type = request.get("type", "cluster")
        
        if content_type == "trend_response":
            return await self._create_trend_response_content(request)
        elif content_type == "pillar_content":
            return await self._create_cluster_content(request)
        else:
            return await self._create_cluster_content(request)

    async def _create_trend_response_content(
        self, 
        request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create timely content responding to trends.

        Args:
            request: Trend response request

        Returns:
            Created content
        """
        topic = request.get("topic", "")
        pillar = request.get("pillar", "")
        asset = request.get("asset", "")
        
        prompt = f"""Create a timely, SEO-optimized blog post about: "{topic}"

Context: This is responding to a {asset} sentiment shift detected by our market intelligence.

This is a trend-response piece that needs to:
1. Hook readers with the timely angle
2. Provide immediate value and analysis
3. Position Sentilyze as the authoritative source
4. Include a soft CTA to try Sentilyze

Structure:
- Compelling headline with timely angle
- Brief intro explaining why this matters now
- Data-driven analysis (use placeholder data)
- Expert insights and interpretation
- What this means for traders/investors
- How Sentilyze helps (soft CTA)
- Conclusion with next steps

SEO Requirements:
- Meta title: 55-60 characters
- Meta description: 150-160 characters
- Include primary keyword in first 100 words
- 3-5 related keywords naturally woven in
- 3 internal link suggestions
- SEO score target: 75+

Tone: Authoritative but accessible, data-driven, timely

Format response as JSON with:
- title (headline)
- meta_title
- meta_description
- content (full article, 1500-2000 words)
- target_keywords (array)
- internal_links (array of suggested links)
- seo_score (estimated 0-100)"""

        try:
            result = await self.kimi.generate_json(
                prompt=prompt,
                system_prompt=self.system_prompt,
                temperature=0.7,
            )
            
            content_id = f"seth-trend-{asset.lower()}-{datetime.utcnow().strftime('%Y%m%d')}"
            
            return {
                "content_id": content_id,
                "type": "trend_response",
                "pillar": pillar,
                "asset": asset,
                "title": result.get("title", topic),
                "meta_title": result.get("meta_title", ""),
                "meta_description": result.get("meta_description", ""),
                "content": result.get("content", ""),
                "target_keywords": result.get("target_keywords", []),
                "internal_links": result.get("internal_links", []),
                "seo_score": result.get("seo_score", 70),
                "status": "pending_approval",
                "created_at": datetime.utcnow().isoformat(),
                "agent": "SETH",
                "source": "SCOUT",
            }
            
        except Exception as e:
            logger.error("seth.trend_content_error", topic=topic, error=str(e))
            return None

    async def _create_cluster_content(
        self, 
        request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create cluster (supporting) content.

        Args:
            request: Content request

        Returns:
            Created content
        """
        topic = request.get("topic", "")
        pillar = request.get("pillar", "")
        
        prompt = f"""Create a comprehensive, SEO-optimized blog post: "{topic}"

This is a cluster article supporting the pillar: "{pillar}"

Requirements:
- 1500-2000 words
- Go deep on this specific topic
- Naturally reference the broader pillar concept
- Target long-tail keywords
- Include practical, actionable advice
- Use real examples where possible

Structure:
- SEO-optimized H1 headline
- Hook intro explaining importance
- 3-5 main H2 sections with H3 subsections
- Real-world examples or case studies
- Clear takeaways in each section
- Strong conclusion with CTA

SEO Requirements:
- Meta title: 55-60 characters
- Meta description: 150-160 characters
- 1 primary keyword + 3-4 secondary
- Suggest pillar page to link to
- Target SEO score: 75+

Format response as JSON with:
- title
- meta_title
- meta_description
- content (full article)
- target_keywords (array)
- pillar_page (which pillar this supports)
- seo_score (estimated)"""

        try:
            result = await self.kimi.generate_json(
                prompt=prompt,
                system_prompt=self.system_prompt,
                temperature=0.7,
            )
            
            topic_slug = topic.lower().replace(" ", "-")[:30]
            content_id = f"seth-{topic_slug}-{datetime.utcnow().strftime('%Y%m%d')}"
            
            return {
                "content_id": content_id,
                "type": "cluster",
                "pillar": pillar,
                "title": result.get("title", topic),
                "meta_title": result.get("meta_title", ""),
                "meta_description": result.get("meta_description", ""),
                "content": result.get("content", ""),
                "target_keywords": result.get("target_keywords", []),
                "pillar_page": result.get("pillar_page", pillar),
                "seo_score": result.get("seo_score", 70),
                "status": "pending_approval",
                "created_at": datetime.utcnow().isoformat(),
                "agent": "SETH",
                "source": request.get("source", "SCHEDULE"),
            }
            
        except Exception as e:
            logger.error("seth.cluster_content_error", topic=topic, error=str(e))
            return None

    async def _update_pillar_status(self) -> Dict[str, Any]:
        """Update status of content pillars.

        Returns:
            Pillar status
        """
        status = {}
        
        try:
            existing_content = await self.firestore.get_content(
                content_type="blog",
                limit=200,
            )
            
            for pillar_name, pillar_data in self.content_pillars.items():
                # Count existing content for this pillar
                pillar_content = [
                    c for c in existing_content 
                    if c.get("pillar") == pillar_name
                ]
                
                clusters_covered = len(pillar_content)
                clusters_total = len(pillar_data["clusters"])
                coverage = clusters_covered / clusters_total if clusters_total > 0 else 0
                
                status[pillar_name] = {
                    "clusters_covered": clusters_covered,
                    "clusters_total": clusters_total,
                    "coverage_percentage": f"{coverage:.0%}",
                    "status": "complete" if coverage >= 0.8 else "in_progress" if coverage >= 0.3 else "started",
                    "next_priority_clusters": pillar_data["clusters"][clusters_covered:clusters_covered+3],
                }
        
        except Exception as e:
            logger.error("seth.pillar_status_error", error=str(e))
        
        return status

    async def _generate_strategy_recommendations(
        self,
        pillar_status: Dict[str, Any],
        content_gaps: List[Dict],
    ) -> List[Dict[str, Any]]:
        """Generate content strategy recommendations.

        Args:
            pillar_status: Pillar status
            content_gaps: Content gaps

        Returns:
            Recommendations
        """
        recommendations = []
        
        # Identify underperforming pillars
        for pillar_name, status in pillar_status.items():
            if status["status"] != "complete":
                recommendations.append({
                    "type": "pillar_development",
                    "pillar": pillar_name,
                    "priority": "High" if status["coverage_percentage"] < "50%" else "Medium",
                    "recommendation": f"Develop {len(status.get('next_priority_clusters', []))} more cluster articles",
                    "impact": "Improved topical authority and SEO rankings",
                })
        
        # Recommend content batching if many gaps
        if len(content_gaps) > 5:
            recommendations.append({
                "type": "batch_creation",
                "priority": "Medium",
                "recommendation": f"Batch create {min(len(content_gaps), 5)} cluster articles",
                "impact": "Rapid pillar coverage and SEO boost",
            })
        
        return recommendations

    def _summarize_result(self, result: Dict[str, Any]) -> str:
        """Summarize results for notifications.

        Args:
            result: Execution results

        Returns:
            Summary string
        """
        content = result.get("content_created", [])
        avg_seo = sum(c.get("seo_score", 0) for c in content) / len(content) if content else 0
        
        types = {}
        for c in content:
            t = c.get("type", "unknown")
            types[t] = types.get(t, 0) + 1
        
        pillar_status = result.get("pillar_status", {})
        incomplete = sum(1 for p in pillar_status.values() if p.get("status") != "complete")
        
        return (
            f"Created {len(content)} pieces "
            f"({types.get('trend_response', 0)} trend, {types.get('cluster', 0)} cluster). "
            f"Avg SEO: {avg_seo:.0f}. "
            f"{incomplete} pillars in progress."
        )

    async def get_content_by_pillar(
        self,
        pillar: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get content by pillar.

        Args:
            pillar: Content pillar
            limit: Maximum results

        Returns:
            List of content
        """
        all_content = await self.firestore.get_content(
            content_type="blog",
            limit=limit * 2,
        )
        
        return [c for c in all_content if c.get("pillar") == pillar][:limit]
