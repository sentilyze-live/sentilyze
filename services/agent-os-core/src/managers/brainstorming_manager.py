"""Brainstorming Manager - Autonomous Agent Brainstorming Sessions.

Orchestrates periodic brainstorming sessions where agents collaborate
to push the product forward. Each session:
1. Gathers current state from all agents
2. Runs a multi-agent brainstorming pipeline
3. Produces actionable items (content, code, experiments, community posts)
4. Dispatches actions to the appropriate agents for execution

Runs every 2 days by default.
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog

from src.config import settings
from src.data_bridge import FirestoreDataClient
from src.api import KimiClient
from src.utils.telegram_manager import get_telegram_manager

logger = structlog.get_logger(__name__)


class BrainstormingManager:
    """Orchestrates autonomous brainstorming sessions between agents."""

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
            max_tokens=6000,
            temperature=0.8,
        )
        self.telegram = get_telegram_manager()
        self._initialized = True
        self.last_session: Optional[datetime] = None

    async def should_run(self) -> bool:
        """Check if a brainstorming session should run now.

        Returns:
            True if enough time has passed since the last session
        """
        interval_hours = getattr(settings, "BRAINSTORMING_INTERVAL_HOURS", 48)

        # Check last session from Firestore
        try:
            docs = (
                self.firestore.client.collection("agent_os_brainstorming")
                .order_by("timestamp", direction="DESCENDING")
                .limit(1)
                .stream()
            )
            for doc in docs:
                data = doc.to_dict()
                last_ts = data.get("timestamp")
                if last_ts:
                    if isinstance(last_ts, datetime):
                        self.last_session = last_ts
                    elif isinstance(last_ts, str):
                        self.last_session = datetime.fromisoformat(last_ts.replace("Z", "+00:00").replace("+00:00", ""))

                    if self.last_session:
                        elapsed = (datetime.utcnow() - self.last_session).total_seconds() / 3600
                        if elapsed < interval_hours:
                            return False
        except Exception as e:
            logger.warning("brainstorming.check_error", error=str(e))

        return True

    async def run_session(self) -> Dict[str, Any]:
        """Run a full brainstorming session.

        Steps:
        1. Gather intelligence from each agent domain
        2. Synthesize into a brainstorming agenda
        3. Generate actionable proposals per domain
        4. Dispatch actions to agents
        5. Report results to Telegram

        Returns:
            Session results with all proposals and dispatched actions
        """
        session_id = f"brainstorm_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        logger.info("brainstorming.session_started", session_id=session_id)

        # ──── Step 1: Gather Intelligence ────
        intelligence = await self._gather_intelligence()

        # ──── Step 2: Generate Brainstorming Agenda ────
        agenda = await self._generate_agenda(intelligence)

        # ──── Step 3: Generate Proposals per Domain ────
        proposals = await self._generate_proposals(agenda, intelligence)

        # ──── Step 4: Prioritize and Filter ────
        prioritized = self._prioritize_proposals(proposals)

        # ──── Step 5: Dispatch Actions ────
        dispatched = await self._dispatch_actions(prioritized)

        # ──── Step 6: Build Session Report ────
        session_report = {
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "intelligence_summary": self._summarize_intelligence(intelligence),
            "agenda": agenda,
            "total_proposals": len(proposals),
            "dispatched_actions": len(dispatched),
            "proposals": prioritized[:10],  # Top 10 for storage
            "dispatched": dispatched,
        }

        # ──── Step 7: Store & Notify ────
        await self.firestore.set_document(
            "agent_os_brainstorming",
            session_id,
            {
                **session_report,
                "timestamp": datetime.utcnow(),
            },
        )

        # Send report to Telegram
        report_message = self._format_telegram_report(session_report)
        await self.telegram.send_message(report_message)

        self.last_session = datetime.utcnow()
        logger.info(
            "brainstorming.session_completed",
            session_id=session_id,
            proposals=len(proposals),
            dispatched=len(dispatched),
        )

        return session_report

    async def _gather_intelligence(self) -> Dict[str, Any]:
        """Gather current state intelligence from all agent domains.

        Returns:
            Intelligence data per domain
        """
        from src.agents import get_agent, list_agents

        intelligence = {
            "market": {},
            "content": {},
            "community": {},
            "growth": {},
            "data_quality": {},
            "anomalies": {},
            "agent_states": {},
        }

        # Gather agent states
        for agent_name in list_agents():
            try:
                agent = get_agent(agent_name)
                state = await self.firestore.get_agent_state(agent_name)
                memory = await agent.get_memory_context()
                intelligence["agent_states"][agent_name] = {
                    "last_run": state.get("last_run_at", "N/A") if state else "N/A",
                    "run_count": state.get("run_count", 0) if state else 0,
                    "last_success": state.get("last_run_success", False) if state else False,
                    "working_memory": memory.get("working", {}),
                }
            except Exception as e:
                intelligence["agent_states"][agent_name] = {"error": str(e)}

        # Market data (SCOUT domain)
        try:
            from src.data_bridge import BigQueryDataClient
            bq = BigQueryDataClient()
            sentiment = await bq.get_sentiment_data(hours=72)
            market = await bq.get_market_data(hours=72)
            intelligence["market"] = {
                "sentiment_data_points_72h": len(sentiment) if sentiment else 0,
                "market_data_points_72h": len(market) if market else 0,
                "top_sentiment": sentiment[:3] if sentiment else [],
                "top_market": market[:3] if market else [],
            }
        except Exception as e:
            intelligence["market"]["error"] = str(e)

        # Content status (SETH domain)
        try:
            content = await self.firestore.get_content(content_type="blog", limit=10)
            intelligence["content"] = {
                "recent_blog_count": len(content) if content else 0,
                "recent_titles": [c.get("title", "") for c in (content or [])[:5]],
            }
        except Exception as e:
            intelligence["content"]["error"] = str(e)

        # Growth metrics (ELON domain)
        try:
            experiments = await self.firestore.get_experiments(status="proposed", limit=10)
            intelligence["growth"] = {
                "pending_experiments": len(experiments) if experiments else 0,
                "experiment_titles": [e.get("name", "") for e in (experiments or [])[:3]],
            }
        except Exception as e:
            intelligence["growth"]["error"] = str(e)

        return intelligence

    async def _generate_agenda(self, intelligence: Dict[str, Any]) -> List[str]:
        """Generate brainstorming agenda from intelligence.

        Args:
            intelligence: Gathered intelligence data

        Returns:
            List of agenda topics
        """
        intel_summary = json.dumps(intelligence, indent=2, default=str)[:4000]

        prompt = f"""Sen Sentilyze'in stratejik beyin takimi koordinatorusun.
Asagidaki veriyi analiz ederek bugunun brainstorming gundemini olustur.

Mevcut durum:
{intel_summary}

Sentilyze hakkinda:
- Kripto ve altin piyasasi icin AI-powered sentiment analiz platformu
- SaaS modeli, hedef: MRR buyume
- Hedef kitle: kripto traderlar, yatirimcilar, hedge fonlar
- Platformlar: Blog, LinkedIn, Twitter, Reddit, Discord

5-7 gundem maddesi olustur. Her biri:
1. Urun gelistirme firsati (yeni feature, iyilestirme)
2. Icerik/marketing firsati
3. Topluluk buyume stratejisi
4. Teknik iyilestirme
5. Rekabet avantaji

JSON array olarak dondur: ["gundem1", "gundem2", ...]
Sadece JSON dondur, baska bir sey yazma."""

        try:
            response = await self.kimi.generate(
                prompt=prompt,
                system_prompt="Sen stratejik bir urun yoneticisisin. Sadece JSON dondur.",
                max_tokens=1500,
            )
            # Parse JSON from response
            agenda = json.loads(self._extract_json(response))
            if isinstance(agenda, list):
                return agenda[:7]
        except Exception as e:
            logger.error("brainstorming.agenda_error", error=str(e))

        return [
            "Yeni feature fikirleri",
            "Icerik stratejisi",
            "Topluluk buyumesi",
            "Teknik iyilestirmeler",
            "Pazarlama firsatlari",
        ]

    async def _generate_proposals(
        self,
        agenda: List[str],
        intelligence: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Generate actionable proposals for each agenda item.

        Each proposal is assigned to a specific agent for execution.

        Args:
            agenda: Brainstorming agenda topics
            intelligence: Current intelligence data

        Returns:
            List of proposals with agent assignments
        """
        intel_summary = json.dumps(intelligence, indent=2, default=str)[:3000]

        prompt = f"""Sen Sentilyze'in otonom agent takimi icin aksiyon plani olusturucu.

Brainstorming gundemi:
{json.dumps(agenda, ensure_ascii=False)}

Mevcut durum:
{intel_summary}

Her gundem maddesi icin 1-2 somut, uygulanabilir aksiyon uret.
Her aksiyon su formatta olsun:

{{
  "title": "Kisa baslik",
  "description": "Ne yapilacak, detayli aciklama",
  "assigned_agent": "scout|seth|elon|zara|oracle|coder|sentinel|atlas",
  "action_type": "content|code|experiment|community|analysis|monitoring",
  "priority": "high|medium|low",
  "platform": "blog|linkedin|twitter|reddit|discord|internal",
  "estimated_impact": "Beklenen etki aciklamasi",
  "auto_executable": true/false
}}

AGENT GOREVLERI:
- scout: Piyasa analizi, trend tespiti
- seth: Blog yazilari, SEO icerigi
- elon: Buyume deneyleri, A/B testleri
- zara: Topluluk paylasimlari, sosyal medya icerigi
- oracle: Dogrulama, istatistiksel analiz
- coder: Kod degisiklikleri, yeni feature gelistirme
- sentinel: Anomali tespiti, risk izleme
- atlas: Data kalitesi, pipeline sagligi

PLATFORMLAR:
- Blog: Uzun form SEO icerigi (seth)
- LinkedIn: Profesyonel B2B icerigi (zara)
- Twitter: Kisa, viral icerik (zara)
- Reddit: Topluluk tartismalari (zara)
- Discord: Topluluk engagement (zara)

JSON array olarak dondur. Sadece JSON.
auto_executable=true olan aksiyonlar otomatik calistirilacak.
auto_executable=false olanlar onay bekleyecek (deploy, finansal kararlar)."""

        try:
            response = await self.kimi.generate(
                prompt=prompt,
                system_prompt="Sen bir aksiyon plani olusturucusun. Sadece JSON array dondur.",
                max_tokens=4000,
            )
            proposals = json.loads(self._extract_json(response))
            if isinstance(proposals, list):
                # Add unique IDs
                for i, p in enumerate(proposals):
                    p["proposal_id"] = f"prop_{datetime.utcnow().strftime('%Y%m%d')}_{i:03d}"
                    p["status"] = "proposed"
                    p["created_at"] = datetime.utcnow().isoformat()
                return proposals
        except Exception as e:
            logger.error("brainstorming.proposals_error", error=str(e))

        return []

    def _prioritize_proposals(self, proposals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prioritize proposals by impact and executability.

        Args:
            proposals: Raw proposals

        Returns:
            Sorted proposals
        """
        priority_scores = {"high": 3, "medium": 2, "low": 1}

        def score(p):
            base = priority_scores.get(p.get("priority", "medium"), 2)
            # Boost auto-executable items
            if p.get("auto_executable", False):
                base += 1
            # Boost content and community (quick wins)
            if p.get("action_type") in ("content", "community"):
                base += 0.5
            return base

        proposals.sort(key=score, reverse=True)
        return proposals

    async def _dispatch_actions(self, proposals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Dispatch approved actions to agents for execution.

        Only auto_executable proposals are dispatched immediately.
        Non-auto proposals are stored for manual approval.

        Args:
            proposals: Prioritized proposals

        Returns:
            List of dispatched actions
        """
        dispatched = []

        for proposal in proposals:
            if not proposal.get("auto_executable", False):
                # Store for manual approval
                proposal["status"] = "pending_approval"
                await self.firestore.set_document(
                    "agent_os_pending_actions",
                    proposal["proposal_id"],
                    proposal,
                )
                continue

            # Dispatch to the assigned agent
            agent_name = proposal.get("assigned_agent", "")
            action_type = proposal.get("action_type", "")

            try:
                dispatch_result = await self._execute_proposal(proposal)
                proposal["status"] = "dispatched"
                proposal["dispatch_result"] = dispatch_result
                dispatched.append(proposal)

                logger.info(
                    "brainstorming.action_dispatched",
                    agent=agent_name,
                    action_type=action_type,
                    title=proposal.get("title", ""),
                )
            except Exception as e:
                proposal["status"] = "dispatch_failed"
                proposal["error"] = str(e)
                logger.error(
                    "brainstorming.dispatch_error",
                    agent=agent_name,
                    error=str(e),
                )

        return dispatched

    async def _execute_proposal(self, proposal: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single proposal by dispatching to the appropriate agent.

        Args:
            proposal: Proposal to execute

        Returns:
            Execution result
        """
        from src.agents import get_agent

        agent_name = proposal.get("assigned_agent", "")
        action_type = proposal.get("action_type", "")

        # Build context for the agent
        context = {
            "task": proposal.get("description", proposal.get("title", "")),
            "brainstorming_proposal": True,
            "proposal_id": proposal.get("proposal_id"),
            "action_type": action_type,
            "platform": proposal.get("platform", "internal"),
            "priority": proposal.get("priority", "medium"),
            "autonomous_run": True,
        }

        # For content actions, add platform-specific context
        if action_type == "content":
            context["content_platform"] = proposal.get("platform", "blog")
            context["content_title"] = proposal.get("title", "")

        # For community actions, add platform context
        if action_type == "community":
            context["community_platform"] = proposal.get("platform", "reddit")

        agent = get_agent(agent_name)
        result = await agent.run(context)

        return {
            "success": result.get("success", False),
            "agent": agent_name,
            "run_id": result.get("run_id"),
        }

    def _summarize_intelligence(self, intelligence: Dict[str, Any]) -> str:
        """Create a brief summary of the intelligence data."""
        parts = []
        market = intelligence.get("market", {})
        if market.get("sentiment_data_points_72h"):
            parts.append(f"Piyasa: {market['sentiment_data_points_72h']} sentiment verisi")
        content = intelligence.get("content", {})
        if content.get("recent_blog_count"):
            parts.append(f"Icerik: {content['recent_blog_count']} son blog")
        growth = intelligence.get("growth", {})
        if growth.get("pending_experiments"):
            parts.append(f"Buyume: {growth['pending_experiments']} bekleyen deney")
        return " | ".join(parts) if parts else "Veri toplaniyor"

    def _format_telegram_report(self, report: Dict[str, Any]) -> str:
        """Format brainstorming session report for Telegram.

        Args:
            report: Session report data

        Returns:
            Formatted HTML message
        """
        proposals = report.get("proposals", [])
        dispatched = report.get("dispatched", [])

        parts = [
            "🧠 <b>Brainstorming Oturumu Tamamlandi</b>",
            f"📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC",
            "",
            f"📊 <b>Toplam Oneri:</b> {report.get('total_proposals', 0)}",
            f"🚀 <b>Otomatik Calistirilan:</b> {len(dispatched)}",
            f"⏳ <b>Onay Bekleyen:</b> {report.get('total_proposals', 0) - len(dispatched)}",
            "",
        ]

        # Top proposals
        if proposals:
            parts.append("📋 <b>Oneriler:</b>")
            for i, p in enumerate(proposals[:7], 1):
                agent = p.get("assigned_agent", "?").upper()
                title = p.get("title", "?")
                priority = p.get("priority", "medium")
                platform = p.get("platform", "")
                status = "✅" if p.get("status") == "dispatched" else "⏳" if p.get("status") == "pending_approval" else "📝"
                icon = "🔴" if priority == "high" else "🟡" if priority == "medium" else "🟢"
                platform_tag = f" [{platform}]" if platform and platform != "internal" else ""
                parts.append(f"{status} {icon} <b>{agent}</b>: {title}{platform_tag}")

        parts.extend([
            "",
            "<i>Sonraki brainstorming: 2 gun sonra</i>",
        ])

        return "\n".join(parts)

    def _extract_json(self, text: str) -> str:
        """Extract JSON from LLM response that may contain markdown."""
        text = text.strip()
        # Remove markdown code blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return text.strip()


# Singleton accessor
_brainstorming_manager = None


def get_brainstorming_manager() -> BrainstormingManager:
    """Get or create BrainstormingManager singleton."""
    global _brainstorming_manager
    if _brainstorming_manager is None:
        _brainstorming_manager = BrainstormingManager()
    return _brainstorming_manager
