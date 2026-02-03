# Telegram Integration V2 - Clean Architecture

## 🎯 Overview

Yeni Telegram entegrasyonu **basit, güvenli ve maintainable** bir mimari sunar.

### Eski Yapının Sorunları:
- ❌ 3 farklı Telegram sınıfı (`TelegramNotifier`, `TelegramAgentBot`, `SecureTelegramManager`)
- ❌ Çelişen endpoint'ler (`/telegram/webhook`, `/telegram/secure/command`, vs.)
- ❌ Agent'ların Telegram'a cevap verme mekanizması yok
- ❌ Karmaşık güvenlik kontrolleri
- ❌ Singleton pattern'ler tutarsız

### Yeni Yapının Avantajları:
- ✅ **Tek sorumluluk**: `TelegramManager` tüm Telegram işlemlerini yönetir
- ✅ **Basit API**: Agent'lar `await self.reply_to_telegram(message)` ile cevap verir
- ✅ **Built-in security**: Rate limiting ve sanitization otomatik
- ✅ **Agent agnostic**: Mevcut agent'lara dokunmadan çalışır
- ✅ **Clean separation**: Webhook logic ayrı, agent logic ayrı

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Telegram API                          │
│                 (Webhook Updates)                        │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│            /telegram/webhook Endpoint                    │
│         (src/routes/telegram_v2.py)                     │
│                                                          │
│  • Receives webhook updates                             │
│  • Calls TelegramManager                                │
│  • Activates agents                                     │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              TelegramManager                             │
│      (src/utils/telegram_manager.py)                    │
│                                                          │
│  • handle_webhook_update()                              │
│  • send_message()                                       │
│  • Rate limiting                                        │
│  • Message sanitization                                 │
│  • Agent mention detection                              │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                  BaseAgent                               │
│          (src/agents/base.py)                           │
│                                                          │
│  • telegram_context (Dict or None)                      │
│  • reply_to_telegram(message)                           │
│  • is_telegram_triggered()                              │
│  • get_telegram_user()                                  │
└─────────────────────────────────────────────────────────┘
```

---

## 📝 Usage Guide

### 1. Telegram'dan Agent'ları Tetikleme

Kullanıcılar Telegram'da şu şekilde mesaj gönderir:

```
@SCOUT altın fiyatlarını analiz et
```

veya

```
@all bugün neler var?
```

### 2. Agent'tan Telegram'a Cevap Verme

Agent'lar içinden Telegram'a mesaj göndermek için:

```python
class MyAgent(BaseAgent):
    async def _execute(self, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        # Normal agent logic
        result = await self.analyze_market()

        # If triggered via Telegram, send reply
        if self.is_telegram_triggered():
            await self.reply_to_telegram(
                f"✅ Analysis complete!\n\n"
                f"Found {len(result['opportunities'])} opportunities."
            )

        return result
```

### 3. Telegram Context Kullanımı

Agent'lar Telegram context bilgilerine erişebilir:

```python
# Check if Telegram triggered
if self.is_telegram_triggered():
    user = self.get_telegram_user()  # "johndoe"
    task = self.get_telegram_task()  # "analyze gold prices"

    logger.info(f"Agent triggered by {user} with task: {task}")
```

### 4. Manuel Mesaj Gönderme

API üzerinden direkt mesaj göndermek için:

```python
from src.utils.telegram_manager import get_telegram_manager

telegram = get_telegram_manager()
await telegram.send_message(
    text="🔔 Important notification",
    chat_id="123456789"  # Optional, defaults to configured chat
)
```

---

## 🔐 Security Features

### 1. Rate Limiting

Her kullanıcı için:
- **10 komut/dakika** (ayarlanabilir: `TELEGRAM_RATE_LIMIT_PER_MINUTE`)
- **100 komut/saat** (ayarlanabilir: `TELEGRAM_RATE_LIMIT_PER_HOUR`)

Limit aşılırsa kullanıcı otomatik bloklanır.

### 2. Message Sanitization

Tüm mesajlar otomatik sanitize edilir:
- Script injection koruması
- HTML/JavaScript temizleme
- Maksimum uzunluk kontrolü (4000 karakter)

### 3. User ID Hashing

Loglarda kullanıcı ID'leri SHA256 ile hash'lenir (privacy).

---

## 🚀 Endpoints

### `/telegram/webhook` (POST)
Ana webhook endpoint'i. Telegram'dan gelen tüm mesajlar buraya gelir.

**Response**: Always 200 OK (Telegram retry'larını önlemek için)

### `/telegram/webhook` (GET)
Webhook durumu kontrolü.

**Response**:
```json
{
  "status": "active",
  "message": "Telegram webhook endpoint is ready",
  "version": "2.0"
}
```

### `/telegram/webhook/info` (GET)
Telegram API'den webhook bilgisi alır.

### `/telegram/webhook/set` (POST)
Webhook URL'ini ayarlar.

**Body**:
```json
{
  "webhook_url": "https://your-domain.com/telegram/webhook"
}
```

### `/telegram/send` (POST)
Manuel mesaj gönderir (test için).

**Body**:
```json
{
  "text": "Test message",
  "chat_id": "123456789"  // Optional
}
```

### `/telegram/test` (POST)
Telegram bağlantısını test eder.

**Response**: Test mesajı gönderir ve sonucu döner.

---

## ⚙️ Configuration

`.env` dosyasında:

```env
# Telegram Bot Credentials
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
ENABLE_TELEGRAM_NOTIFICATIONS=true

# Rate Limiting
TELEGRAM_RATE_LIMIT_PER_MINUTE=10
TELEGRAM_RATE_LIMIT_PER_HOUR=100

# Webhook Domain (production)
DOMAIN=your-domain.com
```

---

## 🧪 Testing

### 1. Test Telegram Connection

```bash
curl -X POST http://localhost:8080/telegram/test
```

### 2. Send Test Message

```bash
curl -X POST "http://localhost:8080/telegram/send" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello from API!"}'
```

### 3. Check Webhook Status

```bash
curl http://localhost:8080/telegram/webhook
```

### 4. Get Webhook Info

```bash
curl http://localhost:8080/telegram/webhook/info
```

---

## 🔄 Migration from Old System

Eski sistemden geçiş için:

### Affected Files:
- ✅ `src/utils/telegram_manager.py` - **NEW** (unified manager)
- ✅ `src/routes/telegram_v2.py` - **NEW** (clean routes)
- ✅ `src/agents/base.py` - **UPDATED** (Telegram context support)
- ✅ `src/main.py` - **UPDATED** (uses new routes)

### Deprecated Files (can be removed):
- ⚠️ `src/utils/telegram_bot.py` - OLD (replaced by telegram_manager)
- ⚠️ `src/utils/secure_telegram.py` - OLD (security now in manager)
- ⚠️ `src/routes/telegram.py` - OLD (replaced by telegram_v2)

### Backward Compatibility:
- ✅ `TelegramNotifier` still works (for notifications)
- ✅ Existing agents work without changes
- ✅ No database schema changes

---

## 📚 API Reference

### TelegramManager

```python
class TelegramManager:
    async def handle_webhook_update(update: Dict) -> Dict
    async def send_message(text: str, chat_id: str = None) -> Dict
    async def set_webhook(webhook_url: str) -> Dict
    async def get_webhook_info() -> Dict
    async def notify_agent_activated(...) -> Dict
    async def notify_broadcast_result(...) -> Dict
```

### BaseAgent (New Methods)

```python
class BaseAgent:
    telegram_context: Optional[Dict[str, Any]]

    async def reply_to_telegram(message: str) -> bool
    def is_telegram_triggered() -> bool
    def get_telegram_user() -> Optional[str]
    def get_telegram_task() -> Optional[str]
```

### TelegramContext

```python
@dataclass
class TelegramContext:
    chat_id: str
    user_id: str
    username: str
    message_text: str
    message_id: int
    trigger_type: str  # "mention" or "broadcast"
```

---

## 🐛 Troubleshooting

### Webhook not receiving messages?

1. Check Telegram credentials:
   ```bash
   curl http://localhost:8080/telegram/webhook/info
   ```

2. Verify HTTPS (Telegram requires HTTPS):
   - Use ngrok for local testing
   - Production must have valid SSL

3. Check webhook URL is set:
   ```bash
   curl -X POST "http://localhost:8080/telegram/webhook/set" \
     -H "Content-Type: application/json" \
     -d '{"webhook_url": "https://your-domain.com/telegram/webhook"}'
   ```

### Rate limit issues?

Adjust in `.env`:
```env
TELEGRAM_RATE_LIMIT_PER_MINUTE=20  # Increase if needed
TELEGRAM_RATE_LIMIT_PER_HOUR=200
```

### Agent not replying?

Check agent code:
```python
# Make sure you're using reply_to_telegram
if self.is_telegram_triggered():
    await self.reply_to_telegram("Your message here")
```

---

## 📖 Examples

### Example 1: SCOUT Agent with Telegram Reply

```python
class ScoutAgent(BaseAgent):
    async def _execute(self, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        # Get task from Telegram
        task = self.get_telegram_task() if self.is_telegram_triggered() else None

        # Perform analysis
        opportunities = await self.find_opportunities()

        # Reply to Telegram user
        if self.is_telegram_triggered():
            summary = f"🔍 <b>SCOUT Analysis</b>\n\n"
            summary += f"Found {len(opportunities)} opportunities\n\n"

            for opp in opportunities[:3]:  # Top 3
                summary += f"• {opp['asset']}: {opp['score']}/10\n"

            await self.reply_to_telegram(summary)

        return {
            "success": True,
            "opportunities": opportunities,
        }
```

### Example 2: Manual Notification

```python
from src.utils.telegram_manager import get_telegram_manager

# In any service or agent
telegram = get_telegram_manager()

await telegram.send_message(
    text="🚨 <b>Alert!</b>\n\nMarket volatility detected!",
    chat_id="123456789"
)
```

### Example 3: Broadcast Handling

When user sends: `@all what's happening today?`

The system:
1. Detects broadcast pattern (`@all`)
2. Activates all agents (SCOUT, ORACLE, SETH, ZARA, ELON, MARIA)
3. Each agent processes independently
4. Each agent can reply via `reply_to_telegram()`
5. User receives multiple responses (one per agent)

---

## ✅ Checklist for New Agents

When creating a new agent that supports Telegram:

- [ ] Inherit from `BaseAgent`
- [ ] Check `is_telegram_triggered()` before replying
- [ ] Use `reply_to_telegram()` for responses
- [ ] Add agent pattern to `TelegramManager.AGENT_PATTERNS`
- [ ] Test with `@AGENTNAME message`
- [ ] Test rate limiting
- [ ] Test error handling

---

## 📊 Monitoring

Check Telegram activity in logs:

```bash
# Filter Telegram logs
docker logs agent-os-core | grep "telegram"

# Check webhook status
docker logs agent-os-core | grep "telegram.webhook"

# Monitor agent replies
docker logs agent-os-core | grep "agent.telegram_reply"
```

---

## 🎉 Summary

Yeni Telegram entegrasyonu:
- ✅ **3 sınıftan 1 sınıfa** indirildi
- ✅ **Basit API** ile agent'lar direkt cevap verebilir
- ✅ **Security built-in** (rate limiting, sanitization)
- ✅ **Mevcut agent'lara dokunmadan** çalışır
- ✅ **Maintainable ve test edilebilir**

Agent'larınız artık Telegram'la kolay ve güvenli bir şekilde iletişim kurabilir! 🚀
