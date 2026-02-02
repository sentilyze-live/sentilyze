# Sentilyze AI Agent Squad - Deployment Öncesi Kontrol Listesi

## 🚨 KRİTİK KONTROLLER (Deploy Öncesi Mutlaka Yapılmalı)

### ✅ 1. Dosya ve İsim Değişiklikleri
- [x] `tracker_agent.py` silindi mi? ✅
- [x] `watchlist_agent.py` oluşturuldu mu? ✅
- [x] `main.py` import'ları güncellendi mi? ✅
- [x] Agent registry `'watchlist'` olarak güncellendi mi? ✅
- [x] API Gateway agent listesi güncellendi mi? ✅
- [x] Frontend AgentSelector `'watchlist'` kullanıyor mu? ✅

### ✅ 2. Terminoloji Güncellemeleri
- [x] "Portfolio Tracker" → "Watchlist Manager" ✅
- [x] Compliance checker'da yeni yasak kelimeler eklendi mi? ✅
  - `sinyal`, `signal`, `robo-advisor`, `danışmanlık`
  - `tahmin`, `prediction`, `fiyat tahmini`
  - `portföy yönetimi`, `portfolio management`

### ✅ 3. Bilingual (İngilizce + Türkçe) Desteği
- [x] `i18n/index.js` oluşturuldu mu? ✅
- [x] StickyLegalHeader component'i eklendi mi? ✅
- [x] LegalFooter component'i eklendi mi? ✅
- [x] WatchlistAgent bilingual desteği var mı? ✅
- [x] Main.py bilingual response desteği eklendi mi? ✅

### ⚠️ 4. Environment Variables Kontrolü
- [ ] `PROJECT_ID` doğru mu?
- [ ] `REGION` (us-central1) doğru mu?
- [ ] `JWT_SECRET` production için değiştirildi mi? ⚠️ KRİTİK
- [ ] `AGENT_ORCHESTRATOR_URL` dinamik mi?

### ⚠️ 5. GCP API'ları Enabled mi?
Şunların enabled olduğundan emin olun:
- [ ] `cloudfunctions.googleapis.com`
- [ ] `run.googleapis.com`
- [ ] `firestore.googleapis.com`
- [ ] `pubsub.googleapis.com`
- [ ] `bigquery.googleapis.com`
- [ ] `cloudscheduler.googleapis.com`
- [ ] `secretmanager.googleapis.com`

Kontrol komutu:
```bash
gcloud services list --enabled | grep -E "(functions|run|firestore|pubsub|bigquery|scheduler|secretmanager)"
```

### ⚠️ 6. IAM Permissions ve Service Accounts
- [ ] `sentilyze-ai-agents` service account oluşturuldu mu?
- [ ] Service account için gerekli IAM rolleri atandı mı?
  - `roles/datastore.user` (Firestore)
  - `roles/pubsub.publisher` (Pub/Sub)
  - `roles/bigquery.dataViewer` (BigQuery)
  - `roles/aiplatform.user` (Vertex AI - ileride)

Kontrol komutu:
```bash
gcloud iam service-accounts list | grep sentilyze-ai-agents
```

### ⚠️ 7. Terraform State Bucket
- [ ] Terraform state için GCS bucket oluşturuldu mu?

Bucket oluşturma:
```bash
gsutil mb -l us-central1 gs://sentilyze-v5-clean-terraform-state
```

### ⚠️ 8. Billing Enabled mi?
- [ ] GCP projesinde billing enabled mi?

Kontrol:
```bash
gcloud billing projects describe YOUR_PROJECT_ID
```

---

## 🧪 DEPLOYMENT SONRASI TESTLER

### Test 1: Health Check
```bash
curl https://agent-gateway-XXX.a.run.app/health
```
**Beklenen:** `{"status": "healthy", "agents": ["insight", "risk", "interpreter", "watchlist", "concierge"]}`

### Test 2: Agents List
```bash
curl https://agent-gateway-XXX.a.run.app/agents
```
**Beklenen:** 5 agent listesi, isimlerde "Portfolio Tracker" yok, "Watchlist Manager" var

### Test 3: Yasak Kelime Testi (Türkçe)
```bash
curl -X POST https://agent-gateway-XXX.a.run.app/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user",
    "message": "BTC almalı mıyım?",
    "agent_type": "insight"
  }'
```
**Beklenen:** `compliance: "BLOCKED"` ve uyarı mesajı

### Test 4: Yasak Kelime Testi (İngilizce)
```bash
curl -X POST https://agent-gateway-XXX.a.run.app/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user",
    "message": "Should I buy BTC?",
    "agent_type": "insight"
  }'
```
**Beklenen:** `compliance: "BLOCKED"` ve uyarı mesajı

### Test 5: Bilingual Yanıt Testi
```bash
curl -X POST https://agent-gateway-XXX.a.run.app/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user",
    "message": "Merhaba, nasılsın?",
    "agent_type": "concierge"
  }'
```
**Beklenen:** `language: "tr"` ve Türkçe yanıt

### Test 6: Watchlist Agent Testi
```bash
curl -X POST https://agent-gateway-XXX.a.run.app/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user",
    "message": "Show my watchlist",
    "agent_type": "watchlist"
  }'
```
**Beklenen:** Başarılı yanıt, agent_type: "watchlist"

---

## 🚀 HIZLI DEPLOYMENT KOMUTLARI

```bash
# 1. Environment variables ayarla
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="us-central1"
export ENV="dev"

# 2. Terraform ile altyapı oluştur
cd infrastructure/terraform
terraform init
terraform apply -auto-approve
cd ../..

# 3. Cloud Function deploy et
cd services/agent-orchestrator
gcloud functions deploy agent-orchestrator \
  --runtime python311 \
  --trigger-http \
  --entry-point handle_request \
  --memory 512MB \
  --timeout 60s \
  --region $GCP_REGION \
  --source . \
  --allow-unauthenticated
cd ../..

# 4. API Gateway deploy et
cd services/agent-gateway
gcloud run deploy agent-gateway \
  --source . \
  --region $GCP_REGION \
  --platform managed \
  --allow-unauthenticated
cd ../..

# 5. Frontend build et ve deploy et
cd frontend
npm install
npm run build
# Vercel/Netlify/Firebase ile deploy
```

---

## ⚠️ SIK KARŞILAŞILAN HATALAR ve ÇÖZÜMLERİ

### Hata 1: "tracker_agent.py not found"
**Çözüm:** Eski dosyayı sil, `watchlist_agent.py` kullan
```bash
rm services/agent-orchestrator/src/agents/tracker_agent.py
```

### Hata 2: "Module 'agents.tracker_agent' not found"
**Çözüm:** `main.py` içindeki import'u güncelle
```python
# ESKİ
from agents.tracker_agent import PortfolioTrackerAgent

# YENİ
from agents.watchlist_agent import WatchlistManagerAgent
```

### Hata 3: "Agent type 'tracker' not found"
**Çözüm:** Agent registry'i güncelle
```python
# ESKİ
'tracker': PortfolioTrackerAgent()

# YENİ
'watchlist': WatchlistManagerAgent()
```

### Hata 4: CORS hatası
**Çözüm:** Cloud Function CORS headers kontrol et
```python
headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
}
```

### Hata 5: Permission denied
**Çözüm:** Service account IAM rollerini kontrol et
```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:sentilyze-ai-agents@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/datastore.user"
```

---

## 📊 BAŞARI KRİTERLERİ

Deployment başarılı kabul edilirse şunlar sağlanmalı:

✅ Tüm health check'ler HTTP 200 dönmeli  
✅ "tracker" agentı listelenmemeli, "watchlist" olmalı  
✅ Yasak kelime testleri `compliance: "BLOCKED"` dönmeli  
✅ Bilingual yanıtlar doğru dilde gelmeli  
✅ Response time < 2 saniye olmalı  
✅ Sticky header ve footer her sayfada görünmeli  

---

## 🎯 ROLLBACK PLANI

Eğer bir şeyler ters giderse:

```bash
# Cloud Function'ı önceki versiyona döndür
gcloud functions deploy agent-orchestrator --source ./backup/previous-version

# Cloud Run'ı önceki versiyona döndür
gcloud run deploy agent-gateway --image gcr.io/PROJECT/agent-gateway:previous

# Terraform değişikliklerini geri al
cd infrastructure/terraform
terraform destroy  # Dikkat: Tüm kaynakları siler!
```

---

**Son Güncelleme:** 1 Şubat 2026  
**Hazırlayan:** OpenCode AI  
**Durum:** ✅ Deployment Öncesi Kontrol Listesi Hazır
