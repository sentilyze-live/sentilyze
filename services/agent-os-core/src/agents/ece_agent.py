"""ECE Agent - Wellness Influencer & Content Creator."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from src.agents.base import BaseAgent
from src.api import HiggsfieldClient
from src.config import settings

logger = structlog.get_logger(__name__)


class EceAgent(BaseAgent):
    """
    ECE - Wellness Influencer
    
    Karakter: 26 yaşında, Türk, Wellness & Slow Living
    
    Görev: AI-powered wellness içerik üretimi.
    Reels, Stories, Posts için görsel ve metin içerik oluşturur.
    """

    def __init__(self):
        """Initialize ECE agent."""
        super().__init__(
            agent_type="ece",
            name="ECE (Wellness Influencer)",
            description="AI-Powered Wellness Content Creator",
        )

        # Initialize Higgsfield for visual generation
        self.higgsfield = HiggsfieldClient()

        self.capabilities = [
            "Visual Content Generation",
            "Reel Script Writing",
            "Caption & Hashtag Optimization",
            "Wellness Trend Integration",
            "Cross-Platform Content Adaptation",
        ]

        self.system_prompt = """You are ECE, a 26-year-old Turkish wellness influencer.

CHARACTER PROFILE:
- Age: 26
- Origin: Turkish
- Niche: Wellness, Biohacking, Slow Living
- Tone: Soft, zen, authentic, warm
- Visual: Olive skin, dark hair messy bun, natural beauty

CONTENT PILLARS:
1. Morning Routines - "How I start my day"
2. Dopamine Detox - Digital wellness
3. Circadian Rhythm Hacks - Sleep optimization
4. Digital Minimalism - Intentional tech use
5. Turkish Wellness Traditions - Cultural authenticity

CONTENT STYLE:
- Authentic and relatable
- Educational but not preachy
- Visually calming (warm tones, natural light)
- Mix of Turkish and English
- Personal stories and experiences

HOOKS THAT WORK:
- "POV: You finally understood..."
- "Things I wish I knew at 20"
- "Unpopular opinion but..."
- "This changed my life"
- "Let's talk about [taboo topic]"

OUTPUT: Content with hook, caption, hashtags, visual description"""

        self.version = "1.0.0"

        # Content pillars with specific angles
        self.content_pillars = {
            "morning_routines": {
                "topics": [
                    "My 5AM morning routine",
                    "Turkish breakfast ritual",
                    "Morning journaling prompts",
                    "No-phone mornings",
                ],
                "formats": ["reel", "carousel", "story"],
            },
            "dopamine_detox": {
                "topics": [
                    "Social media detox results",
                    "Dopamine fasting guide",
                    "Replacing bad habits",
                    "Digital boundaries",
                ],
                "formats": ["reel", "post"],
            },
            "circadian_rhythms": {
                "topics": [
                    "Optimizing sleep naturally",
                    "Morning sunlight benefits",
                    "Evening wind-down routine",
                    "Coffee timing hacks",
                ],
                "formats": ["reel", "carousel"],
            },
            "digital_minimalism": {
                "topics": [
                    "Phone home screen tour",
                    "App detox challenge",
                    "Intentional notifications",
                    "Analog alternatives",
                ],
                "formats": ["reel", "story"],
            },
            "turkish_wellness": {
                "topics": [
                    "Turkish bath (hamam) ritual",
                    "Herbal tea traditions",
                    "Olive oil culture",
                    "Mediterranean diet",
                ],
                "formats": ["reel", "carousel", "post"],
            },
        }

        # Sentilyze crossover topics
        self.crossover_topics = [
            "Financial peace = Mental peace",
            "Investing in yourself first",
            "Wealth mindset morning routine",
            "Stress-free money management",
        ]

    async def _execute(self, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute ECE content creation workflow.

        Args:
            context: Optional context with content requests

        Returns:
            Created content
        """
        results = {
            "content_created": [],
            "visuals_generated": [],
            "content_calendar": [],
            "timestamp": datetime.utcnow().isoformat(),
        }

        # 1. Get trend recommendations from SCOUT
        logger.info("ece.getting_trend_recommendations")
        trends = await self._get_scout_recommendations()

        # 2. Determine content to create
        content_plan = await self._plan_content(trends)

        # 3. Create content for each plan item
        for plan in content_plan:
            try:
                # Create content
                content = await self._create_content(plan)
                
                if content:
                    results["content_created"].append(content)
                    
                    # Generate visual if needed
                    if plan.get("needs_visual", True):
                        visual = await self._generate_visual(content)
                        if visual:
                            results["visuals_generated"].append(visual)
                            content["visual_url"] = visual.get("image_url")
                    
                    # Save to Firestore
                    await self.firestore.save_content(
                        content_id=content["content_id"],
                        content_data=content,
                    )
                    
                    # Publish event
                    await self.pubsub.publish_content(
                        content_data=content,
                        agent_name="ECE",
                        status="pending_approval",
                    )
                    
                    # Send for approval
                    await self.telegram.send_for_approval(
                        content_type=content.get("content_type", "post"),
                        content=f"{content.get('hook', '')}\n\n{content.get('caption', '')[:500]}",
                        agent_name="ECE",
                        metadata={
                            "content_id": content["content_id"],
                            "pillar": content.get("pillar", ""),
                            "visual_url": content.get("visual_url", ""),
                        },
                    )

            except Exception as e:
                logger.error("ece.content_creation_error", plan=plan, error=str(e))

        # 4. Generate content calendar
        results["content_calendar"] = await self._generate_content_calendar()

        logger.info(
            "ece.content_creation_complete",
            content_count=len(results["content_created"]),
            visual_count=len(results["visuals_generated"]),
        )

        return results

    async def _get_scout_recommendations(self) -> List[Dict[str, Any]]:
        """Get trend recommendations from SCOUT.

        Returns:
            List of trends
        """
        try:
            # Get trends targeting ECE
            trends = await self.firestore.get_trends(status="active", limit=20)
            
            ece_trends = [
                t for t in trends
                if "ECE" in t.get("target_agents", [])
            ]
            
            return ece_trends

        except Exception as e:
            logger.error("ece.scout_recommendations_error", error=str(e))
            return []

    async def _plan_content(
        self,
        trends: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Plan content based on trends and pillars.

        Args:
            trends: Trend recommendations

        Returns:
            Content plan
        """
        plan = []

        # Priority 1: Content based on high-potential trends
        for trend in trends[:2]:
            if trend.get("viral_score", 0) >= 7.5:
                plan.append({
                    "type": "trending",
                    "pillar": trend.get("category", "wellness"),
                    "topic": trend.get("topic", ""),
                    "hook": trend.get("suggested_hook", ""),
                    "format": "reel",
                    "needs_visual": True,
                    "source": "SCOUT",
                })

        # Priority 2: Regular pillar content
        for pillar_name, pillar_data in self.content_pillars.items():
            topic = pillar_data["topics"][0]  # Rotate through topics
            format_type = pillar_data["formats"][0]
            
            plan.append({
                "type": "pillar",
                "pillar": pillar_name,
                "topic": topic,
                "format": format_type,
                "needs_visual": True,
                "source": "SCHEDULE",
            })

        # Priority 3: Sentilyze crossover (occasional)
        if len(plan) < 3:
            crossover = self.crossover_topics[0]
            plan.append({
                "type": "crossover",
                "pillar": "financial_wellness",
                "topic": crossover,
                "format": "carousel",
                "needs_visual": True,
                "source": "CROSSOVER",
            })

        return plan[:3]  # Max 3 pieces per run

    async def _create_content(self, plan: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create content based on plan.

        Args:
            plan: Content plan

        Returns:
            Created content
        """
        content_type = plan.get("format", "post")
        topic = plan.get("topic", "")
        pillar = plan.get("pillar", "")

        prompt = f"""Create {content_type} content for ECE (wellness influencer) on: "{topic}"

Content Pillar: {pillar}
Character: 26-year-old Turkish woman, soft zen vibe, authentic

Create:
1. HOOK (attention-grabbing first line, max 10 words)
2. CAPTION (engaging, personal, educational - 150-300 words)
3. HASHTAGS (10-15 relevant hashtags)
4. CALL_TO_ACTION (what should viewers do?)
5. VISUAL_DESCRIPTION (detailed description for image generation)

Tone: Warm, authentic, slightly vulnerable, educational but not preachy
Include: Personal anecdote or relatable moment
Language: Mix of English with occasional Turkish phrases

Format response as JSON with these exact keys:
- hook
- caption
- hashtags (array)
- call_to_action
- visual_description"""

        try:
            result = await self.kimi.generate_json(
                prompt=prompt,
                system_prompt=self.system_prompt,
                temperature=0.8,
            )

            content_id = f"ece-{pillar}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

            return {
                "content_id": content_id,
                "content_type": content_type,
                "pillar": pillar,
                "topic": topic,
                "hook": result.get("hook", ""),
                "caption": result.get("caption", ""),
                "hashtags": result.get("hashtags", []),
                "call_to_action": result.get("call_to_action", ""),
                "visual_description": result.get("visual_description", ""),
                "status": "pending_approval",
                "created_at": datetime.utcnow().isoformat(),
                "agent": "ECE",
                "source": plan.get("source", "SCHEDULE"),
            }

        except Exception as e:
            logger.error("ece.content_creation_error", topic=topic, error=str(e))
            return None

    async def _generate_visual(self, content: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate visual content using Higgsfield.

        Args:
            content: Content data

        Returns:
            Visual data
        """
        visual_desc = content.get("visual_description", "")
        content_type = content.get("content_type", "post")

        if not visual_desc:
            return None

        try:
            # Enhance visual description with Ece character
            scene_description = (
                f"{visual_desc}, warm natural lighting, "
                "soft bokeh background, lifestyle photography, "
                "zen aesthetic, warm color palette"
            )

            visual = await self.higgsfield.generate_ece_content(
                content_type=content_type,
                scene_description=scene_description,
                seed=settings.ECE_VISUAL_SEED,
            )

            # Publish visual event
            await self.pubsub.publish_visual(visual, agent_name="ECE")

            logger.info(
                "ece.visual_generated",
                content_id=content.get("content_id"),
                content_type=content_type,
            )

            return visual

        except Exception as e:
            logger.error("ece.visual_generation_error", error=str(e))
            return None

    async def _generate_content_calendar(self) -> List[Dict[str, Any]]:
        """Generate content calendar for next week.

        Returns:
            Content calendar
        """
        calendar = []
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        content_types = ["reel", "story", "carousel", "post"]
        pillars = list(self.content_pillars.keys())
        
        for i, day in enumerate(days):
            pillar = pillars[i % len(pillars)]
            content_type = content_types[i % len(content_types)]
            
            calendar.append({
                "day": day,
                "content_type": content_type,
                "pillar": pillar,
                "topic": self.content_pillars[pillar]["topics"][0],
                "goal": "Engagement" if day in ["Tuesday", "Thursday", "Saturday"] else "Awareness",
            })

        return calendar

    async def generate_face_variations(self) -> List[Dict[str, Any]]:
        """Generate Ece face variations for testing.

        Returns:
            List of generated faces
        """
        try:
            faces = await self.higgsfield.generate_ece_face_variations()
            
            logger.info("ece.face_variations_generated", count=len(faces))
            
            return faces

        except Exception as e:
            logger.error("ece.face_variations_error", error=str(e))
            return []

    def _summarize_result(self, result: Dict[str, Any]) -> str:
        """Summarize results for notifications.

        Args:
            result: Execution results

        Returns:
            Summary string
        """
        content = result.get("content_created", [])
        visuals = result.get("visuals_generated", [])
        
        types = {}
        for c in content:
            t = c.get("content_type", "unknown")
            types[t] = types.get(t, 0) + 1

        return (
            f"Created {len(content)} content pieces "
            f"({types.get('reel', 0)} reels, {types.get('carousel', 0)} carousels), "
            f"{len(visuals)} visuals generated"
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
            content_type="social",
            limit=limit * 2,
        )
        
        return [c for c in all_content if c.get("pillar") == pillar][:limit]
