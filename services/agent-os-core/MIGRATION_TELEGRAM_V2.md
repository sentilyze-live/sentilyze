# Telegram V2 Migration Guide

## 🎯 Migration Summary

Eski karmaşık Telegram yapısından yeni temiz mimariye geçiş kılavuzu.

---

## 📋 What Changed

### New Files ✨
```
services/agent-os-core/
├── src/utils/telegram_manager.py          # NEW - Unified manager
├── src/routes/telegram_v2.py              # NEW - Clean routes
├── TELEGRAM_V2_GUIDE.md                   # NEW - Documentation
└── MIGRATION_TELEGRAM_V2.md               # NEW - This file
```

### Updated Files 🔄
```
services/agent-os-core/
├── src/agents/base.py                     # Added Telegram context support
└── src/main.py                            # Uses new routes & manager
```

### Deprecated Files ⚠️
```
services/agent-os-core/src/
├── utils/telegram_bot.py                  # DEPRECATED - Use telegram_manager
├── utils/secure_telegram.py               # DEPRECATED - Security now in manager
└── routes/telegram.py                     # DEPRECATED - Use telegram_v2
```

---

## 🚀 Migration Steps

### Step 1: Backup (Optional but Recommended)

```bash
# Backup old Telegram files
cd services/agent-os-core
mkdir -p .backup/telegram_v1
cp src/utils/telegram_bot.py .backup/telegram_v1/
cp src/utils/secure_telegram.py .backup/telegram_v1/
cp src/routes/telegram.py .backup/telegram_v1/
```

### Step 2: No Code Changes Required!

**Önemli**: Mevcut agent'larınıza **dokunmanıza gerek yok**!

Yeni sistem backward compatible:
- ✅ Eski `TelegramNotifier` hala çalışıyor
- ✅ Mevcut agent'lar değişiklik gerektirmiyor
- ✅ Eski endpoint'ler disable edildi ama sistem çalışıyor

### Step 3: Test New System

```bash
# 1. Start the service
cd services/agent-os-core
python -m src.main

# 2. Test connection
curl -X POST http://localhost:8080/telegram/test

# 3. Check webhook
curl http://localhost:8080/telegram/webhook

# 4. Test agent mention (in Telegram)
# Send: "@SCOUT analyze gold"
```

### Step 4: Update Agents to Use New Features (Optional)

Eğer agent'larınızın Telegram'a cevap vermesini istiyorsanız:

**Before (Old - Still works but limited)**:
```python
class MyAgent(BaseAgent):
    async def _execute(self, context):
        result = await self.do_work()

        # Old way - uses TelegramNotifier (still works)
        await self.telegram.send_message(
            f"Done! Result: {result}"
        )

        return result
```

**After (New - Recommended)**:
```python
class MyAgent(BaseAgent):
    async def _execute(self, context):
        result = await self.do_work()

        # New way - context-aware reply
        if self.is_telegram_triggered():
            await self.reply_to_telegram(
                f"✅ Done! Result: {result}"
            )

        return result
```

Avantajları:
- ✅ Doğru chat'e otomatik gönderir
- ✅ User context bilir (kim tetikledi)
- ✅ Rate limiting otomatik
- ✅ Message formatting standardized

---

## 🔄 API Changes

### Old Endpoints (Deprecated)

❌ `/telegram/secure/command` - REMOVED
❌ `/telegram/secure/message` - REMOVED
❌ `/telegram/secure/audit-log` - REMOVED
❌ `/telegram/wake/{agent_name}` - REMOVED

### New Endpoints (Active)

✅ `/telegram/webhook` (POST) - Main webhook
✅ `/telegram/webhook` (GET) - Status check
✅ `/telegram/webhook/info` (GET) - Get webhook info
✅ `/telegram/webhook/set` (POST) - Set webhook
✅ `/telegram/send` (POST) - Send message
✅ `/telegram/test` (POST) - Test connection

---

## 🗑️ Cleanup Old Files (After Testing)

Once you've confirmed everything works:

```bash
cd services/agent-os-core

# Option 1: Delete old files
rm src/utils/telegram_bot.py
rm src/utils/secure_telegram.py
rm src/routes/telegram.py

# Option 2: Keep as backup
mkdir -p .deprecated/telegram_v1
mv src/utils/telegram_bot.py .deprecated/telegram_v1/
mv src/utils/secure_telegram.py .deprecated/telegram_v1/
mv src/routes/telegram.py .deprecated/telegram_v1/
```

**Warning**: `TelegramNotifier` (`src/utils/telegram.py`) is **NOT deprecated**.
It's still used by the system and MARIA agent. Do not delete it.

---

## 📝 Configuration Changes

### Old Config (Still Works)
```env
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
ENABLE_TELEGRAM_NOTIFICATIONS=true
```

### New Config (Add These)
```env
# Old config remains the same
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
ENABLE_TELEGRAM_NOTIFICATIONS=true

# New: Rate limiting (optional, has defaults)
TELEGRAM_RATE_LIMIT_PER_MINUTE=10
TELEGRAM_RATE_LIMIT_PER_HOUR=100

# Production: Domain for webhook
DOMAIN=your-domain.com
```

---

## 🧪 Testing Checklist

After migration, test these:

### Basic Functionality
- [ ] Telegram test endpoint works: `/telegram/test`
- [ ] Webhook status returns OK: `/telegram/webhook` (GET)
- [ ] Webhook info accessible: `/telegram/webhook/info`

### Agent Activation
- [ ] Single agent mention works: `@SCOUT test`
- [ ] Broadcast works: `@all test`
- [ ] Agent receives correct context
- [ ] Agent can reply via `reply_to_telegram()`

### Security
- [ ] Rate limiting triggers after 10 commands/min
- [ ] Blocked users can't send more commands
- [ ] Messages are sanitized (no script injection)
- [ ] User IDs are hashed in logs

### Error Handling
- [ ] Invalid agent name handled gracefully
- [ ] Empty messages handled
- [ ] API errors don't crash system
- [ ] Telegram downtime doesn't block agents

---

## 🐛 Rollback Plan

If something goes wrong:

### Quick Rollback (5 minutes)

1. **Restore old routes in main.py**:
```python
# In src/main.py, change:
from src.routes.telegram_v2 import router as telegram_router

# To:
from src.routes.telegram import router as telegram_router
```

2. **Restart service**:
```bash
docker restart agent-os-core
# or
systemctl restart agent-os-core
```

### Full Rollback (10 minutes)

1. Restore from backup:
```bash
cp .backup/telegram_v1/* src/utils/
cp .backup/telegram_v1/telegram.py src/routes/
```

2. Revert `src/main.py` changes
3. Revert `src/agents/base.py` changes
4. Restart service

---

## 💡 Common Issues

### Issue 1: "telegram_manager module not found"

**Cause**: New file not deployed

**Fix**:
```bash
# Make sure file exists
ls src/utils/telegram_manager.py

# Restart service
systemctl restart agent-os-core
```

### Issue 2: "Agent doesn't reply to Telegram"

**Cause**: Agent not using new API

**Fix**: Update agent code:
```python
# Add this to your agent's _execute method
if self.is_telegram_triggered():
    await self.reply_to_telegram("Your message")
```

### Issue 3: "Webhook not working"

**Cause**: Domain not configured or not HTTPS

**Fix**:
```bash
# Check config
echo $DOMAIN

# Set webhook manually
curl -X POST "http://localhost:8080/telegram/webhook/set" \
  -H "Content-Type: application/json" \
  -d '{"webhook_url": "https://your-domain.com/telegram/webhook"}'
```

### Issue 4: "Rate limit too strict"

**Fix**: Adjust in `.env`:
```env
TELEGRAM_RATE_LIMIT_PER_MINUTE=20
TELEGRAM_RATE_LIMIT_PER_HOUR=200
```

---

## 📊 Verification

After migration, verify with:

```bash
# 1. Check service health
curl http://localhost:8080/health

# 2. Check Telegram status
curl http://localhost:8080/telegram/webhook

# 3. Check webhook info
curl http://localhost:8080/telegram/webhook/info

# 4. Send test message
curl -X POST http://localhost:8080/telegram/test

# 5. Check logs
docker logs agent-os-core --tail 100 | grep telegram
```

Expected output:
```
✅ telegram_manager.initialized
✅ telegram.webhook_configured
✅ telegram.message_sent
```

---

## 🎓 Training for Your Team

Key points to communicate:

1. **For Developers**:
   - Use `reply_to_telegram()` instead of direct API calls
   - Check `is_telegram_triggered()` before replying
   - Telegram context is automatically available

2. **For DevOps**:
   - New endpoint: `/telegram/webhook`
   - Rate limiting: 10/min, 100/hour per user
   - Webhook requires HTTPS (use ngrok for local)

3. **For Users**:
   - Nothing changed! Same commands work
   - Mention agents: `@SCOUT`, `@ORACLE`, etc.
   - Broadcast: `@all` or `@herkes`

---

## ✅ Success Criteria

Migration is successful when:

- ✅ All tests pass
- ✅ Agents respond to Telegram mentions
- ✅ No errors in logs
- ✅ Rate limiting works
- ✅ Broadcast works
- ✅ Old functionality preserved

---

## 📚 Additional Resources

- [Telegram V2 Guide](./TELEGRAM_V2_GUIDE.md) - Complete documentation
- [API Reference](./TELEGRAM_V2_GUIDE.md#api-reference) - Method signatures
- [Examples](./TELEGRAM_V2_GUIDE.md#examples) - Code samples

---

## 🎉 Benefits After Migration

1. **Simpler codebase**: 3 sınıf → 1 sınıf
2. **Better DX**: Easier for developers to use
3. **More secure**: Built-in rate limiting & sanitization
4. **More maintainable**: Single source of truth
5. **Better tested**: Simpler to test
6. **Better documented**: Clear API and guides

---

## 🆘 Support

Issues? Check:

1. Logs: `docker logs agent-os-core | grep telegram`
2. Documentation: `TELEGRAM_V2_GUIDE.md`
3. Code: `src/utils/telegram_manager.py`

Still stuck? Rollback using the plan above.

---

**Migration completed!** 🚀

Your Telegram integration is now cleaner, simpler, and more maintainable.
