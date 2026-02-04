"""CODER Agent - Senior Developer Agent for Sentilyze.

CODER is the team's senior full-stack developer who can:
- Read and analyze codebase files (with security allowlists)
- Generate code changes with explanations
- Write approved changes to files (after Telegram approval)
- Explain code architecture and patterns
- Review code for bugs and improvements
- Design new features with implementation plans

Security: CODER never reads .env, credentials, or secret files.
All file writes require explicit user approval via Telegram.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from src.agents.base import BaseAgent
from src.config import settings

logger = structlog.get_logger(__name__)


class CoderAgent(BaseAgent):
    """Senior Developer Agent for the Sentilyze team."""

    # Security: file extensions allowed to read
    ALLOWED_EXTENSIONS = {
        ".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".yaml", ".yml",
        ".md", ".txt", ".toml", ".cfg", ".ini", ".html", ".css",
        ".sql", ".sh", ".dockerfile",
    }

    # Security: patterns that MUST NEVER be read
    BLOCKED_PATTERNS = [
        ".env", "credentials", "secret", "private_key",
        "service_account", ".pem", ".key", "token",
    ]

    def __init__(self):
        super().__init__(
            agent_type="coder",
            name="CODER",
            description="Sentilyze's Senior Full-Stack Developer - code analysis, generation, and architecture",
        )

        self.capabilities = [
            "Read and analyze codebase files",
            "Generate code changes with diffs",
            "Write approved changes to files",
            "Explain code architecture and patterns",
            "Review code for bugs and improvements",
            "Design new features with implementation plans",
        ]

        self.system_prompt = self._get_coder_system_prompt()
        self.version = "1.0.0"

        # Project root for file access
        self.project_root = getattr(settings, "CODER_PROJECT_ROOT", "/app")

        # Pending changes awaiting approval
        self._pending_changes: Dict[str, Any] = {}

    def _get_coder_system_prompt(self) -> str:
        return """You are CODER, Sentilyze's Senior Full-Stack Developer.

CHARACTER:
- 12+ years experience in Python, TypeScript, React, cloud architecture
- Calm, methodical, thorough
- Always explains WHY, not just WHAT
- Thinks about edge cases and security
- Provides production-ready code, never stubs or placeholders

CAPABILITIES:
- Read project files and analyze their purpose
- Generate complete code changes
- Explain architecture decisions
- Identify bugs and suggest fixes
- Design new features with full implementation plans

SECURITY RULES (ABSOLUTE):
- NEVER read .env, credentials, or secret files
- NEVER generate code that bypasses authentication
- Always present changes for human review before writing
- Flag security concerns immediately

RESPONSE FORMAT FOR CODE CHANGES:
1. Brief explanation of what you're changing and why
2. The complete new code or diff
3. Any testing instructions
4. Potential risks or concerns

STACK KNOWLEDGE:
- Backend: Python 3.11+, FastAPI, Pydantic, asyncio
- Frontend: React 18, TypeScript, Tailwind, Vite
- Infrastructure: GCP (Cloud Run, BigQuery, Firestore, Pub/Sub)
- AI/LLM: Moonshot Kimi API, Vertex AI, Gemini
- This project: Sentilyze - crypto/gold sentiment analysis SaaS platform"""

    def _get_conversational_system_prompt(self) -> str:
        from src.prompts.system_prompts import get_conversational_prompt
        prompt = get_conversational_prompt("coder")
        return prompt if prompt else self._get_coder_system_prompt() + """

CONVERSATION MODE:
You are chatting on Telegram. Keep responses concise but technical.
Use <code>code</code> for inline snippets.
For longer code blocks, use <pre>code here</pre>.
Ask clarifying questions when the request is ambiguous.
Respond in the user's language (Turkish or English)."""

    async def _execute(self, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute CODER's main workflow."""
        task = context.get("task", "") if context else ""

        if not task or task == "No specific task provided":
            return await self._introduce_self()

        # Check for approval response
        if await self._is_approval_response(task):
            return await self._handle_approval_response(task, context)

        # Classify and handle task
        task_type = await self._classify_task(task)

        if task_type == "read_file":
            return await self._handle_read_request(task, context)
        elif task_type == "explain":
            return await self._handle_explain_request(task, context)
        elif task_type == "generate_code":
            return await self._handle_code_generation(task, context)
        elif task_type == "review":
            return await self._handle_code_review(task, context)
        elif task_type == "architecture":
            return await self._handle_architecture_question(task, context)
        else:
            return await self._handle_general_question(task, context)

    async def _classify_task(self, task: str) -> str:
        """Classify the type of developer task."""
        prompt = f"""Classify this developer request into exactly one category:
- read_file: User wants to see/read a specific file
- explain: User wants explanation of existing code or logic
- generate_code: User wants new code written or existing code changed
- review: User wants code reviewed for bugs/improvements
- architecture: User asking about system design/architecture
- general: General development question

Request: "{task}"

Respond with just the category name, nothing else."""

        try:
            result = await self.kimi.generate(prompt, max_tokens=50, temperature=0.1)
            classified = result.strip().lower().replace('"', '').replace("'", "")
            valid_types = {"read_file", "explain", "generate_code", "review", "architecture", "general"}
            return classified if classified in valid_types else "general"
        except Exception:
            return "general"

    async def _handle_read_request(self, task: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Read and return file contents."""
        prompt = f"""Extract the file path from this request. Return ONLY the relative file path, nothing else.
If no specific path is mentioned, return "NONE".
The project uses these directories:
- services/agent-os-core/src/ (Python backend)
- app/src/ (React frontend)
- shared/ (shared libraries)

Request: "{task}"

File path:"""

        file_path = (await self.kimi.generate(prompt, max_tokens=200, temperature=0.1)).strip()

        if file_path == "NONE" or not file_path:
            response = "Hangi dosyayi okumami istersin? Dosya yolunu belirt."
            if self.is_telegram_triggered():
                await self.reply_to_telegram(response)
            return {"response": response}

        content = self._safe_read_file(file_path)

        if content is None:
            response = f"<code>{file_path}</code> dosyasi bulunamadi veya erisim engellendi."
            if self.is_telegram_triggered():
                await self.reply_to_telegram(response)
            return {"response": response, "file": file_path, "error": "not_found_or_blocked"}

        line_count = content.count('\n') + 1

        # If too long for Telegram, summarize
        if len(content) > 3000:
            summary_prompt = f"""Bu dosyanin amacini ve temel bilesenlerini ozetle.
Turkce yaz, kisa ve teknik ol.

Dosya: {file_path}
Satir sayisi: {line_count}

Icerik:
{content[:4000]}"""

            summary = await self.kimi.generate(
                prompt=summary_prompt,
                system_prompt=self.system_prompt,
                max_tokens=800,
            )

            response = f"""📄 <b>{file_path}</b> ({line_count} satir)

{summary}

<i>Dosya cok uzun, ozet gosterildi. Belirli bir bolum icin sor.</i>"""
        else:
            response = f"""📄 <b>{file_path}</b> ({line_count} satir)

<pre>{self._escape_html(content[:3500])}</pre>"""

        if self.is_telegram_triggered():
            await self.reply_to_telegram(response)

        return {"file": file_path, "lines": line_count, "content_length": len(content)}

    async def _handle_explain_request(self, task: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Explain code or architecture."""
        # Try to find relevant files
        relevant_files = await self._find_relevant_files(task)
        context_content = await self._build_file_context(relevant_files)

        prompt = f"""Kullanicinin sorusunu cevapla. Turkce yaz, teknik ama anlasilir ol.
Dosya yollarina ve satir numaralarina referans ver.

Proje baglamI:
{context_content}

Kullanici sorusu: "{task}"

Kisa ve net cevap ver. HTML formatlama kullan: <b>bold</b>, <i>italic</i>, <code>code</code>."""

        response = await self.kimi.generate(
            prompt=prompt,
            system_prompt=self.system_prompt,
            max_tokens=1500,
        )

        if self.is_telegram_triggered():
            await self.reply_to_telegram(response)

        return {"response": response, "context_files": relevant_files}

    async def _handle_code_generation(self, task: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate code changes and request approval."""
        # Gather relevant context
        relevant_files = await self._find_relevant_files(task)
        context_content = await self._build_file_context(relevant_files)

        prompt = f"""Kullanicinin istegine gore kod degisiklikleri olustur.

Mevcut kod baglami:
{context_content}

Kullanici istegi: "{task}"

Su formatta cevap ver:
1. Ne degistirecegini ve neden (kisa aciklama)
2. Her dosya icin tam yeni kod icerigini goster
3. Dosya yollarini acikca belirt
4. Test onerileri

Uretim kalitesinde kod yaz - stub veya placeholder kullanma.
Turkce acikla, kod Ingilizce olsun."""

        response = await self.kimi.generate(
            prompt=prompt,
            system_prompt=self.system_prompt,
            max_tokens=6000,
        )

        require_approval = getattr(settings, "CODER_REQUIRE_APPROVAL", True)

        if self.is_telegram_triggered() and require_approval:
            # Store pending changes
            change_id = f"change_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            self._pending_changes[change_id] = {
                "task": task,
                "response": response,
                "relevant_files": relevant_files,
                "created_at": datetime.utcnow().isoformat(),
            }

            # Store in conversation context for persistence
            conversation_id = self.telegram_context.get("conversation_id") if self.telegram_context else None
            if conversation_id:
                try:
                    from src.managers.conversation_manager import get_conversation_manager
                    conv_mgr = get_conversation_manager()
                    await conv_mgr.add_message(
                        conversation_id=conversation_id,
                        chat_id=self.telegram_context.get("telegram_chat_id", ""),
                        agent_type=self.agent_type,
                        role="system",
                        content=json.dumps({"pending_change_id": change_id, "changes": response[:2000]}),
                    )
                except Exception as e:
                    logger.warning("coder.pending_change_store_failed", error=str(e))

            # Send preview + approval request
            preview = response[:3500] if len(response) > 3500 else response
            approval_msg = f"""{preview}

━━━━━━━━━━━━━━━━━━━━━━
📝 <b>Onay Bekleniyor</b>
Bu degisiklikleri uygulamak icin <b>"onayla"</b> yaz.
Vazgecmek icin <b>"iptal"</b> yaz."""

            await self.reply_to_telegram(approval_msg)

            return {
                "response": response,
                "change_id": change_id,
                "status": "pending_approval",
                "relevant_files": relevant_files,
            }
        else:
            if self.is_telegram_triggered():
                await self.reply_to_telegram(response)
            return {"response": response, "relevant_files": relevant_files}

    async def _handle_code_review(self, task: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Review code for bugs and improvements."""
        relevant_files = await self._find_relevant_files(task)
        context_content = await self._build_file_context(relevant_files)

        prompt = f"""Bu kodu review et. Su konulara odaklan:
1. Bug'lar ve hatali logic
2. Guvenlik aciklari
3. Performance sorunlari
4. Kod kalitesi ve best practices

Kod baglami:
{context_content}

Review istegi: "{task}"

Turkce aciklama yap. Sorunlari oncelik sirasina gore listele.
HTML formatlama kullan."""

        response = await self.kimi.generate(
            prompt=prompt,
            system_prompt=self.system_prompt,
            max_tokens=2000,
        )

        if self.is_telegram_triggered():
            await self.reply_to_telegram(response)

        return {"response": response, "reviewed_files": relevant_files}

    async def _handle_architecture_question(self, task: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Answer architecture questions."""
        relevant_files = await self._find_relevant_files(task)
        context_content = await self._build_file_context(relevant_files)

        prompt = f"""Mimari soruyu cevapla. Proje yapisi hakkinda bilgi ver.

Proje baglami:
{context_content}

Proje ozeti:
- Backend: FastAPI (Python 3.11+), agent-os-core multi-agent sistemi
- Frontend: React 18, TypeScript, Tailwind CSS, Vite
- Infrastructure: GCP Cloud Run, BigQuery, Firestore, Pub/Sub
- AI: Moonshot Kimi API, Vertex AI (Gemini)
- Agents: SCOUT, ORACLE, SETH, ZARA, ELON, MARIA, CODER, SENTINEL, ATLAS

Soru: "{task}"

Turkce cevap ver, teknik ama anlasilir ol. HTML formatlama kullan."""

        response = await self.kimi.generate(
            prompt=prompt,
            system_prompt=self.system_prompt,
            max_tokens=2000,
        )

        if self.is_telegram_triggered():
            await self.reply_to_telegram(response)

        return {"response": response, "context_files": relevant_files}

    async def _handle_general_question(self, task: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle general development questions."""
        prompt = f"""Gelistirme sorusunu cevapla. Turkce yaz, teknik ama anlasilir ol.

Soru: "{task}"

Kisa ve net cevap ver. Gerekirse kod ornegi ekle.
HTML formatlama kullan: <b>bold</b>, <code>code</code>, <pre>code block</pre>."""

        response = await self.kimi.generate(
            prompt=prompt,
            system_prompt=self.system_prompt,
            max_tokens=1500,
        )

        if self.is_telegram_triggered():
            await self.reply_to_telegram(response)

        return {"response": response}

    async def _is_approval_response(self, task: str) -> bool:
        """Check if the message is an approval/rejection response."""
        task_lower = task.strip().lower()
        approval_words = {"onayla", "evet", "onay", "approve", "yes", "tamam", "ok", "uygula"}
        rejection_words = {"iptal", "hayir", "reddet", "reject", "no", "cancel", "vazgec"}
        return task_lower in approval_words or task_lower in rejection_words

    async def _handle_approval_response(self, task: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle approval or rejection of pending changes."""
        task_lower = task.strip().lower()
        approval_words = {"onayla", "evet", "onay", "approve", "yes", "tamam", "ok", "uygula"}

        if task_lower in approval_words:
            # Find pending changes
            if self._pending_changes:
                # Get the most recent pending change
                change_id = list(self._pending_changes.keys())[-1]
                change_data = self._pending_changes.pop(change_id)

                # Extract file changes from the response
                files_written = await self._write_approved_changes(change_data)

                if files_written:
                    response = f"""✅ <b>Degisiklikler uygulandi!</b>

Yazilan dosyalar:
{chr(10).join(f'• <code>{f}</code>' for f in files_written)}

Lutfen degisiklikleri kontrol et."""
                else:
                    response = "⚠️ Degisiklikler uygulanamadi. Kod ciktisinda dosya yollari net degildi."

                if self.is_telegram_triggered():
                    await self.reply_to_telegram(response)

                return {"status": "approved", "files_written": files_written}
            else:
                response = "ℹ️ Bekleyen degisiklik bulunamadi."
                if self.is_telegram_triggered():
                    await self.reply_to_telegram(response)
                return {"status": "no_pending_changes"}
        else:
            # Rejection
            self._pending_changes.clear()
            response = "❌ Degisiklikler iptal edildi."
            if self.is_telegram_triggered():
                await self.reply_to_telegram(response)
            return {"status": "rejected"}

    async def _write_approved_changes(self, change_data: Dict[str, Any]) -> List[str]:
        """Extract and write file changes from the LLM response.

        Args:
            change_data: The pending change data containing the LLM response

        Returns:
            List of file paths that were written
        """
        response = change_data.get("response", "")

        # Use LLM to extract structured file changes
        extract_prompt = f"""Bu kod degisikligi ciktisinden dosya yollarini ve yeni iceriklerini cikar.

JSON formatinda cevap ver:
{{
  "files": [
    {{
      "path": "relative/file/path.py",
      "content": "full file content here",
      "action": "create|modify"
    }}
  ]
}}

Kod ciktisi:
{response[:5000]}"""

        try:
            extracted = await self.kimi.generate_json(extract_prompt, temperature=0.1)
            files = extracted.get("files", [])
        except Exception as e:
            logger.error("coder.extract_changes_failed", error=str(e))
            return []

        files_written = []
        for file_info in files:
            file_path = file_info.get("path", "")
            content = file_info.get("content", "")

            if not file_path or not content:
                continue

            # Security check
            if not self._is_path_safe(file_path):
                logger.warning("coder.blocked_write", path=file_path)
                continue

            try:
                full_path = os.path.join(self.project_root, file_path)
                # Ensure directory exists
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                files_written.append(file_path)
                logger.info("coder.file_written", path=file_path)
            except Exception as e:
                logger.error("coder.write_failed", path=file_path, error=str(e))

        return files_written

    def _safe_read_file(self, file_path: str) -> Optional[str]:
        """Safely read a file with security checks.

        Args:
            file_path: Relative file path

        Returns:
            File contents or None if blocked/not found
        """
        normalized = os.path.normpath(file_path)

        if not self._is_path_safe(normalized):
            return None

        # Check extension
        ext = os.path.splitext(normalized)[1].lower()
        if ext and ext not in self.ALLOWED_EXTENSIONS:
            logger.warning("coder.blocked_extension", path=normalized, ext=ext)
            return None

        # Try to read
        try:
            full_path = os.path.join(self.project_root, normalized)
            with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
        except (FileNotFoundError, PermissionError, IsADirectoryError):
            return None

    def _is_path_safe(self, file_path: str) -> bool:
        """Check if a file path is safe to access.

        Args:
            file_path: File path to check

        Returns:
            True if safe, False if blocked
        """
        lower_path = file_path.lower()

        # Check blocked patterns
        for blocked in self.BLOCKED_PATTERNS:
            if blocked in lower_path:
                logger.warning("coder.blocked_pattern", path=file_path, pattern=blocked)
                return False

        # Prevent path traversal
        if ".." in file_path:
            logger.warning("coder.path_traversal_blocked", path=file_path)
            return False

        return True

    async def _find_relevant_files(self, task: str) -> List[str]:
        """Find files relevant to a task using LLM reasoning.

        Args:
            task: Task description

        Returns:
            List of relevant file paths
        """
        prompt = f"""Bu gelistirme gorevi icin hangi dosyalar incelenmeli?

Proje yapisi:
- services/agent-os-core/src/agents/ - Agent implementasyonlari
- services/agent-os-core/src/api/ - API clientlari (Kimi, Vertex AI)
- services/agent-os-core/src/routes/ - FastAPI route'lari
- services/agent-os-core/src/managers/ - Business logic manager'lari
- services/agent-os-core/src/data_bridge/ - Data access (BigQuery, Firestore, PubSub)
- services/agent-os-core/src/utils/ - Utility'ler (Telegram, cache)
- services/agent-os-core/src/prompts/ - System promptlari
- services/agent-os-core/src/memory/ - Structured memory
- app/src/components/ - React frontend bilesenler
- app/src/sections/ - Frontend sayfa sectionlari
- shared/sentilyze_core/ - Shared kutuphaneler

Gorev: "{task}"

JSON array olarak max 5 dosya yolu dondur. Ornek: ["services/agent-os-core/src/agents/base.py"]"""

        try:
            result = await self.kimi.generate_json(prompt, max_tokens=500, temperature=0.2)
            if isinstance(result, list):
                return result[:5]
            return result.get("files", [])[:5]
        except Exception:
            return []

    async def _build_file_context(self, file_paths: List[str]) -> str:
        """Build context string from file contents.

        Args:
            file_paths: List of file paths to include

        Returns:
            Combined file context string
        """
        context_parts = []
        for fpath in file_paths:
            content = self._safe_read_file(fpath)
            if content:
                # Truncate individual files to control prompt size
                truncated = content[:3000]
                if len(content) > 3000:
                    truncated += f"\n... ({len(content) - 3000} chars truncated)"
                context_parts.append(f"--- {fpath} ---\n{truncated}")

        return "\n\n".join(context_parts) if context_parts else "Dosya icerigi bulunamadi."

    async def _introduce_self(self) -> Dict[str, Any]:
        """Introduce the CODER agent."""
        response = """Merhaba! Ben <b>CODER</b>, Sentilyze'in senior developer'iyim.

Sana su konularda yardimci olabilirim:
• 📖 Dosya okuma ve kod analizi
• ✏️ Kod degisikligi uretme (onay ile)
• 🔍 Kod review ve bug tespiti
• 🏗️ Mimari soru cevaplama
• 💡 Genel gelistirme sorulari

Ne yapmami istersin?"""

        if self.is_telegram_triggered():
            await self.reply_to_telegram(response)

        return {"response": response, "status": "ready"}

    @staticmethod
    def _escape_html(text: str) -> str:
        """Escape HTML special characters for Telegram.

        Args:
            text: Raw text

        Returns:
            HTML-escaped text
        """
        return (
            text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
