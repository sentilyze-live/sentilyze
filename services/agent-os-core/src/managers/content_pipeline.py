"""Content Pipeline - Multi-Platform Content Generation & Distribution.

Generates platform-specific content for:
- Blog (SEO-optimized long-form, auto-publish ready)
- LinkedIn (professional B2B posts)
- Twitter/X (short, viral threads)
- Reddit (community discussion starters)
- Discord (community engagement messages)

Each platform has its own tone, format, and distribution strategy.
Integrates with SETH (blog), ZARA (social), ELON (growth).
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from src.api import KimiClient
from src.config import settings
from src.data_bridge import FirestoreDataClient

logger = structlog.get_logger(__name__)


# Platform configurations
PLATFORM_CONFIGS = {
    "blog": {
        "max_length": 5000,
        "tone": "authoritative, educational, data-driven",
        "format": "SEO-optimized HTML with headings, lists, internal links",
        "agent": "seth",
        "model": "kimi-k2-thinking",
        "max_tokens": 5000,
        "temperature": 0.7,
    },
    "linkedin": {
        "max_length": 3000,
        "tone": "professional, insightful, thought-leadership",
        "format": "LinkedIn post with emojis, line breaks, hashtags. Max 3000 chars.",
        "agent": "zara",
        "model": "kimi-k2-0905-preview",
        "max_tokens": 1500,
        "temperature": 0.7,
    },
    "twitter": {
        "max_length": 280,
        "tone": "concise, witty, data-driven, engaging",
        "format": "Single tweet or thread (max 5 tweets). Include relevant hashtags.",
        "agent": "zara",
        "model": "kimi-k2-0905-preview",
        "max_tokens": 800,
        "temperature": 0.8,
    },
    "reddit": {
        "max_length": 5000,
        "tone": "knowledgeable, humble, community-friendly, never promotional",
        "format": "Reddit post or comment. Markdown formatting. Educational value first.",
        "agent": "zara",
        "model": "kimi-k2-0905-preview",
        "max_tokens": 1500,
        "temperature": 0.7,
    },
    "discord": {
        "max_length": 2000,
        "tone": "casual, helpful, real-time, community-oriented",
        "format": "Discord message. Short paragraphs, code blocks if relevant.",
        "agent": "zara",
        "model": "kimi-k2-0905-preview",
        "max_tokens": 800,
        "temperature": 0.8,
    },
}


class ContentPipeline:
    """Multi-platform content generation and distribution pipeline."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self.firestore = FirestoreDataClient()
        self.kimi = KimiClient(
            model="kimi-k2-thinking",
            max_tokens=5000,
            temperature=0.7,
        )
        self._initialized = True

    async def generate_content(
        self,
        topic: str,
        platform: str,
        context: Optional[Dict[str, Any]] = None,
        source_agent: str = "brainstorming",
    ) -> Optional[Dict[str, Any]]:
        """Generate content for a specific platform.

        Args:
            topic: Content topic/title
            platform: Target platform (blog, linkedin, twitter, reddit, discord)
            context: Additional context (market data, trends, etc.)
            source_agent: Which agent/system requested this content

        Returns:
            Generated content with metadata, or None on failure
        """
        config = PLATFORM_CONFIGS.get(platform)
        if not config:
            logger.error("content_pipeline.unknown_platform", platform=platform)
            return None

        # Use platform-specific model
        kimi = KimiClient(
            model=config["model"],
            max_tokens=config["max_tokens"],
            temperature=config["temperature"],
        )

        # Build the generation prompt
        prompt = self._build_prompt(topic, platform, config, context)

        try:
            if platform == "blog":
                return await self._generate_blog_content(topic, prompt, kimi, config, source_agent)
            elif platform == "twitter":
                return await self._generate_twitter_content(topic, prompt, kimi, config, source_agent)
            else:
                return await self._generate_social_content(topic, platform, prompt, kimi, config, source_agent)
        except Exception as e:
            logger.error("content_pipeline.generation_error", platform=platform, error=str(e))
            return None

    async def generate_multi_platform(
        self,
        topic: str,
        platforms: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
        source_agent: str = "brainstorming",
    ) -> Dict[str, Any]:
        """Generate content for multiple platforms from a single topic.

        Args:
            topic: Content topic
            platforms: Target platforms (default: all)
            context: Additional context
            source_agent: Requesting agent

        Returns:
            Dict of platform -> generated content
        """
        if platforms is None:
            platforms = list(PLATFORM_CONFIGS.keys())

        results = {}
        for platform in platforms:
            content = await self.generate_content(topic, platform, context, source_agent)
            if content:
                results[platform] = content

                # Store each piece of content
                content_id = content.get("content_id", f"cp_{platform}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}")
                await self.firestore.set_document(
                    "agent_os_content_pipeline",
                    content_id,
                    {
                        **content,
                        "timestamp": datetime.utcnow(),
                    },
                )

        logger.info(
            "content_pipeline.multi_platform_complete",
            topic=topic,
            platforms_generated=list(results.keys()),
        )

        return results

    async def _generate_blog_content(
        self,
        topic: str,
        prompt: str,
        kimi: KimiClient,
        config: Dict[str, Any],
        source_agent: str,
    ) -> Dict[str, Any]:
        """Generate SEO-optimized blog content.

        Args:
            topic: Blog topic
            prompt: Generation prompt
            kimi: KimiClient instance
            config: Platform config
            source_agent: Requesting agent

        Returns:
            Blog content with SEO metadata
        """
        response = await kimi.generate(
            prompt=prompt,
            system_prompt="""You are a world-class SEO content writer for Sentilyze,
a crypto and gold sentiment analysis platform. Write comprehensive,
data-driven content that ranks on Google. Always include meta tags,
keywords, and internal linking suggestions.""",
        )

        # Try to parse as JSON, fallback to plain content
        try:
            parsed = json.loads(self._extract_json(response))
        except (json.JSONDecodeError, Exception):
            parsed = {
                "title": topic,
                "content": response,
                "meta_title": topic[:60],
                "meta_description": topic[:160],
                "target_keywords": [],
                "seo_score": 65,
            }

        content_id = f"blog_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        return {
            "content_id": content_id,
            "platform": "blog",
            "title": parsed.get("title", topic),
            "content": parsed.get("content", response),
            "meta_title": parsed.get("meta_title", ""),
            "meta_description": parsed.get("meta_description", ""),
            "target_keywords": parsed.get("target_keywords", []),
            "seo_score": parsed.get("seo_score", 70),
            "internal_links": parsed.get("internal_links", []),
            "word_count": len(parsed.get("content", response).split()),
            "status": "draft",
            "source_agent": source_agent,
            "created_at": datetime.utcnow().isoformat(),
            "auto_publish": False,  # Blog requires review
        }

    async def _generate_twitter_content(
        self,
        topic: str,
        prompt: str,
        kimi: KimiClient,
        config: Dict[str, Any],
        source_agent: str,
    ) -> Dict[str, Any]:
        """Generate Twitter thread content.

        Args:
            topic: Thread topic
            prompt: Generation prompt
            kimi: KimiClient instance
            config: Platform config
            source_agent: Requesting agent

        Returns:
            Twitter content with thread structure
        """
        response = await kimi.generate(
            prompt=prompt,
            system_prompt="""You are a viral crypto/fintech Twitter content creator.
Write engaging tweets that drive discussion and followers.
Use data, insights, and contrarian takes. Include relevant hashtags.""",
        )

        # Parse thread structure
        try:
            parsed = json.loads(self._extract_json(response))
            if isinstance(parsed, list):
                tweets = parsed
            elif isinstance(parsed, dict):
                tweets = parsed.get("tweets", parsed.get("thread", [response]))
            else:
                tweets = [response]
        except (json.JSONDecodeError, Exception):
            # Split by numbered lines or double newlines
            tweets = [t.strip() for t in response.split("\n\n") if t.strip()]
            if not tweets:
                tweets = [response]

        content_id = f"twitter_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        return {
            "content_id": content_id,
            "platform": "twitter",
            "title": topic,
            "tweets": tweets[:5],  # Max 5-tweet thread
            "content": "\n\n".join(tweets[:5]),
            "tweet_count": len(tweets[:5]),
            "hashtags": self._extract_hashtags("\n".join(tweets)),
            "status": "ready_to_publish",
            "source_agent": source_agent,
            "created_at": datetime.utcnow().isoformat(),
            "auto_publish": True,
        }

    async def _generate_social_content(
        self,
        topic: str,
        platform: str,
        prompt: str,
        kimi: KimiClient,
        config: Dict[str, Any],
        source_agent: str,
    ) -> Dict[str, Any]:
        """Generate social media content (LinkedIn, Reddit, Discord).

        Args:
            topic: Content topic
            platform: Target platform
            prompt: Generation prompt
            kimi: KimiClient instance
            config: Platform config
            source_agent: Requesting agent

        Returns:
            Social content
        """
        system_prompts = {
            "linkedin": """You are a LinkedIn thought leader in fintech and AI trading.
Write professional posts that establish authority and drive engagement.
Use relevant emojis sparingly, include hashtags, and end with a question.""",
            "reddit": """You are a knowledgeable crypto community member on Reddit.
Share genuine insights without being promotional. Reference data when possible.
Be humble and add value to discussions. Use markdown formatting.""",
            "discord": """You are a helpful community member in a crypto trading Discord.
Be casual, helpful, and engaging. Share actionable insights.
Use short paragraphs and occasional emojis.""",
        }

        response = await kimi.generate(
            prompt=prompt,
            system_prompt=system_prompts.get(platform, "Generate helpful content."),
        )

        content_id = f"{platform}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        # Determine subreddit for Reddit content
        subreddit = None
        if platform == "reddit":
            topic_lower = topic.lower()
            if "bitcoin" in topic_lower or "btc" in topic_lower or "crypto" in topic_lower:
                subreddit = "r/CryptoCurrency"
            elif "gold" in topic_lower or "xau" in topic_lower:
                subreddit = "r/Gold"
            elif "trading" in topic_lower or "algorithm" in topic_lower:
                subreddit = "r/algotrading"
            else:
                subreddit = "r/Investing"

        result = {
            "content_id": content_id,
            "platform": platform,
            "title": topic,
            "content": response.strip(),
            "char_count": len(response.strip()),
            "status": "ready_to_publish",
            "source_agent": source_agent,
            "created_at": datetime.utcnow().isoformat(),
            "auto_publish": platform != "linkedin",  # LinkedIn needs review
        }

        if subreddit:
            result["subreddit"] = subreddit

        if platform == "linkedin":
            result["hashtags"] = self._extract_hashtags(response)

        return result

    def _build_prompt(
        self,
        topic: str,
        platform: str,
        config: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build platform-specific content generation prompt.

        Args:
            topic: Content topic
            platform: Target platform
            config: Platform config
            context: Additional context

        Returns:
            Formatted prompt string
        """
        context_str = ""
        if context:
            context_str = f"\nEk bilgi:\n{json.dumps(context, indent=2, default=str)[:1500]}"

        if platform == "blog":
            return f""""{topic}" konusunda kapsamli bir blog yazisi yaz.

Platform: Blog (Sentilyze.live)
Ton: {config['tone']}
Format: {config['format']}
{context_str}

SEO gereksinimleri:
- Baslik: 55-60 karakter, anahtar kelime icermeli
- Meta aciklama: 150-160 karakter
- H2/H3 basliklari ile yapilandir
- Dahili link onerileri ekle
- Minimum 1500 kelime
- Anahtar kelimeleri dogal kullan

JSON olarak dondur:
{{
  "title": "...",
  "meta_title": "...",
  "meta_description": "...",
  "content": "...(HTML formatli)...",
  "target_keywords": ["..."],
  "internal_links": ["..."],
  "seo_score": 75
}}"""

        elif platform == "twitter":
            return f""""{topic}" hakkinda viral bir Twitter thread yaz.

Ton: {config['tone']}
Format: {config['format']}
{context_str}

Kurallar:
- Her tweet max 280 karakter
- Ilk tweet hook olmali
- Data/istatistik kullan
- Hashtag ekle (#crypto #trading #AI)
- Max 5 tweet
- Son tweet CTA icermeli (tartisma, takip)

JSON array olarak dondur:
["tweet1", "tweet2", ...]"""

        else:
            return f""""{topic}" hakkinda bir {platform} paylasimlari yaz.

Platform: {platform}
Ton: {config['tone']}
Format: {config['format']}
Max uzunluk: {config['max_length']} karakter
{context_str}

Kurallar:
- Sentilyze'i dogal referans et, promosyon yapma
- Deger ve bilgi odakli ol
- Tartisma baslatici soru ekle
- Platform jargonuna uy
- Ingilizce yaz (uluslararasi kitle)

Sadece icerik metnini dondur, baska bir sey yazma."""

    def _extract_json(self, text: str) -> str:
        """Extract JSON from text that may contain markdown code blocks."""
        text = text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return text.strip()

    def _extract_hashtags(self, text: str) -> List[str]:
        """Extract hashtags from text."""
        import re
        return list(set(re.findall(r"#\w+", text)))

    async def get_content_queue(
        self,
        platform: Optional[str] = None,
        status: str = "ready_to_publish",
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get content queue for publishing.

        Args:
            platform: Filter by platform
            status: Filter by status
            limit: Maximum results

        Returns:
            List of content items
        """
        try:
            query = self.firestore.client.collection("agent_os_content_pipeline")
            if status:
                query = query.where("status", "==", status)
            if platform:
                query = query.where("platform", "==", platform)
            query = query.order_by("created_at", direction="DESCENDING").limit(limit)

            results = []
            for doc in query.stream():
                data = doc.to_dict()
                data["doc_id"] = doc.id
                results.append(data)
            return results

        except Exception as e:
            logger.error("content_pipeline.queue_error", error=str(e))
            return []

    async def mark_published(self, content_id: str) -> bool:
        """Mark content as published.

        Args:
            content_id: Content document ID

        Returns:
            True if successful
        """
        try:
            await self.firestore.set_document(
                "agent_os_content_pipeline",
                content_id,
                {
                    "status": "published",
                    "published_at": datetime.utcnow().isoformat(),
                },
            )
            return True
        except Exception as e:
            logger.error("content_pipeline.mark_published_error", error=str(e))
            return False


# Singleton accessor
_content_pipeline = None


def get_content_pipeline() -> ContentPipeline:
    """Get or create ContentPipeline singleton."""
    global _content_pipeline
    if _content_pipeline is None:
        _content_pipeline = ContentPipeline()
    return _content_pipeline
