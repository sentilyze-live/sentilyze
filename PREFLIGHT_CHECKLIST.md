# Sentilyze - Preflight Checklist

Deploy öncesi ve lokal geliştirme sırasında yapılması gereken kontroller.

## Hızlı Başlangıç

```bash
# 1. Environment değişkenlerini kontrol et
./scripts/preflight-check.sh

# 2. Servisleri lokalde test et
docker-compose up -d

# 3. Health check'leri çalıştır
./scripts/health-check.sh --environment local
```

## 1. Environment Variables Kontrolü

### Zorunlu Değişkenler (Servisler çalışmadan önce mutlaka set edilmeli)

| Değişken | Açıklama | Örnek Değer |
|----------|----------|-------------|
| `PUBSUB_PROJECT_ID` | **REQUIRED** - GCP Project ID | `sentilyze-v5-clean` |
| `ENVIRONMENT` | Ortam (development/staging/production) | `development` |
| `LOG_LEVEL` | Log seviyesi | `INFO` |

### Kontrol Komutu

```bash
# .env dosyasını kontrol et
if [ -z "$PUBSUB_PROJECT_ID" ]; then
  echo "❌ HATA: PUBSUB_PROJECT_ID set edilmemiş!"
  echo "   Çözüm: .env dosyasına PUBSUB_PROJECT_ID=your-project-id ekleyin"
  exit 1
else
  echo "✅ PUBSUB_PROJECT_ID: $PUBSUB_PROJECT_ID"
fi
```

## 2. Shared Library Import Testleri

Tüm servisler sentilyze_core modülünü doğru import edebilmeli:

```bash
# Test için Python komutları
cd services/api-gateway
python -c "from sentilyze_core import Settings; print('✅ api-gateway: Import OK')"

cd services/sentiment-processor
python -c "from sentilyze_core import Settings; print('✅ sentiment-processor: Import OK')"

cd services/market-context-processor
python -c "from sentilyze_core import Settings; print('✅ market-context-processor: Import OK')"

cd services/prediction-engine
python -c "from sentilyze_core import Settings; print('✅ prediction-engine: Import OK')"

cd services/tracker-service
python -c "from sentilyze_core import Settings; print('✅ tracker-service: Import OK')"

cd services/alert-service
python -c "from sentilyze_core import Settings; print('✅ alert-service: Import OK')"

cd services/analytics-engine
python -c "from sentilyze_core import Settings; print('✅ analytics-engine: Import OK')"

cd services/ingestion
python -c "from sentilyze_core import Settings; print('✅ ingestion: Import OK')"
```

## 3. Health Endpoint Testleri

Tüm servisler `/health` endpoint'i döndürmeli:

```bash
#!/bin/bash
# health-check-local.sh

SERVICES=(
  "api-gateway:8080"
  "sentiment-processor:8082"
  "market-context-processor:8083"
  "prediction-engine:8084"
  "alert-service:8085"
  "analytics-engine:8086"
  "tracker-service:8087"
  "ingestion:8081"
)

for service in "${SERVICES[@]}"; do
  IFS=':' read -r name port <<< "$service"
  
  response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$port/health)
  
  if [ "$response" == "200" ]; then
    echo "✅ $name (port $port): Healthy"
  else
    echo "❌ $name (port $port): Unhealthy (HTTP $response)"
  fi
done
```

**Çalıştırma:**
```bash
chmod +x health-check-local.sh
./health-check-local.sh
```

**Beklenen Output:**
```
✅ api-gateway (port 8080): Healthy
✅ sentiment-processor (port 8082): Healthy
✅ market-context-processor (port 8083): Healthy
✅ prediction-engine (port 8084): Healthy
✅ alert-service (port 8085): Healthy
✅ analytics-engine (port 8086): Healthy
✅ tracker-service (port 8087): Healthy
✅ ingestion (port 8081): Healthy
```

## 4. Docker Build Kontrolleri

### Önce poetry.lock dosyalarının varlığını kontrol et

```bash
SERVICES=("api-gateway" "sentiment-processor" "market-context-processor" 
          "prediction-engine" "tracker-service" "alert-service" 
          "analytics-engine" "ingestion")

for service in "${SERVICES[@]}"; do
  if [ -f "services/$service/poetry.lock" ]; then
    echo "✅ $service/poetry.lock exists"
  else
    echo "⚠️  $service/poetry.lock MISSING - Build will be slow"
    echo "   Çözüm: cd services/$service && poetry lock"
  fi
done
```

### Docker Build Test

```bash
# Tek bir servisi build et (cache test)
docker build -f services/api-gateway/Dockerfile -t api-gateway:test .

# Eğer "poetry.lock not found" hatası alırsan:
# 1. poetry.lock dosyası eksik demektir
# 2. O servis için önce `poetry lock` çalıştır
```

## 5. Pub/Sub Bağlantı Testi

```bash
# Pub/Sub emulator çalışıyor mu?
curl http://localhost:8085/v1/projects/$PUBSUB_PROJECT_ID/topics

# Başarılı response: {"topics": [...]}
```

## 6. BigQuery Bağlantı Testi

```bash
# BigQuery emulator çalışıyor mu?
curl http://localhost:9050/v1/projects/$PUBSUB_PROJECT_ID/datasets

# Başarılı response: {"datasets": [...]}
```

## 7. Redis Bağlantı Testi

```bash
# Redis çalışıyor mu?
redis-cli ping

# Başarılı response: PONG
```

## 8. PostgreSQL Bağlantı Testi

```bash
# PostgreSQL çalışıyor mu?
psql -h localhost -U sentilyze -d sentilyze_predictions -c "SELECT 1;"

# Başarılı response: 1 row returned
```

## 9. Özet Kontrol Scripti

`scripts/preflight-check.sh`:

```bash
#!/bin/bash
set -e

echo "======================================"
echo "Sentilyze Preflight Check"
echo "======================================"
echo ""

# 1. Environment kontrolü
echo "🔍 Checking Environment Variables..."
if [ -z "$PUBSUB_PROJECT_ID" ]; then
  echo "   ❌ PUBSUB_PROJECT_ID not set"
  exit 1
else
  echo "   ✅ PUBSUB_PROJECT_ID: $PUBSUB_PROJECT_ID"
fi

if [ -z "$ENVIRONMENT" ]; then
  echo "   ⚠️  ENVIRONMENT not set (defaulting to 'development')"
else
  echo "   ✅ ENVIRONMENT: $ENVIRONMENT"
fi
echo ""

# 2. poetry.lock kontrolü
echo "🔍 Checking poetry.lock files..."
SERVICES=("api-gateway" "sentiment-processor" "market-context-processor" 
          "prediction-engine" "tracker-service" "alert-service" 
          "analytics-engine" "ingestion")

missing_lock=0
for service in "${SERVICES[@]}"; do
  if [ -f "services/$service/poetry.lock" ]; then
    echo "   ✅ $service/poetry.lock"
  else
    echo "   ⚠️  $service/poetry.lock MISSING"
    missing_lock=$((missing_lock + 1))
  fi
done

if [ $missing_lock -gt 0 ]; then
  echo ""
  echo "⚠️  Warning: $missing_lock poetry.lock files missing"
  echo "   This will slow down Docker builds."
  echo "   Run: cd services/<service> && poetry lock"
fi
echo ""

# 3. Health check
echo "🔍 Checking service health..."
echo "   (Make sure services are running: docker-compose up -d)"
echo ""

for service in "${SERVICES[@]}"; do
  # Port mapping
  case $service in
    "api-gateway") port=8080 ;;
    "ingestion") port=8081 ;;
    "sentiment-processor") port=8082 ;;
    "market-context-processor") port=8083 ;;
    "prediction-engine") port=8084 ;;
    "alert-service") port=8085 ;;
    "analytics-engine") port=8086 ;;
    "tracker-service") port=8087 ;;
  esac
  
  if curl -s http://localhost:$port/health > /dev/null 2>&1; then
    echo "   ✅ $service (port $port): Healthy"
  else
    echo "   ❌ $service (port $port): Not responding"
  fi
done

echo ""
echo "======================================"
echo "Preflight check completed!"
echo "======================================"
```

## 10. Yaygın Hatalar ve Çözümleri

### Hata 1: `PUBSUB_PROJECT_ID` not set

```
❌ pydantic_settings.SettingsError: The following environment variables are missing: PUBSUB_PROJECT_ID
```

**Çözüm:**
```bash
export PUBSUB_PROJECT_ID=sentilyze-v5-clean
# Veya .env dosyasına ekleyin
echo "PUBSUB_PROJECT_ID=sentilyze-v5-clean" >> .env
```

### Hata 2: `sentilyze_core` import hatası

```
ModuleNotFoundError: No module named 'sentilyze_core'
```

**Çözüm:**
```bash
# pyproject.toml path yanlış olabilir
# ../shared yerine ../../shared olmalı
# 1. pyproject.toml kontrol et
cat services/api-gateway/pyproject.toml | grep "sentilyze-core"

# 2. Docker build sırasında shared kopyalanmalı
# Dockerfile'da: COPY shared /shared
```

### Hata 3: poetry.lock eksik - build yavaş

```
Creating virtualenv... (slow)
Resolving dependencies... (very slow)
```

**Çözüm:**
```bash
cd services/<service>
poetry lock
# poetry.lock dosyasını commit et!
git add poetry.lock
git commit -m "Add poetry.lock for faster builds"
```

### Hata 4: Health check başarısız

```
❌ api-gateway (port 8080): Not responding
```

**Çözüm:**
```bash
# Logları kontrol et
docker-compose logs api-gateway

# Servisi yeniden başlat
docker-compose restart api-gateway

# Port çakışması olabilir
lsof -i :8080
```

## 11. Deployment Öncesi Son Kontrol

Deploy etmeden önce bu listedeki tüm maddeleri kontrol edin:

- [ ] `PUBSUB_PROJECT_ID` set edildi
- [ ] `ENVIRONMENT` set edildi (production için)
- [ ] Tüm poetry.lock dosyaları var
- [ ] Dockerfile'lar poetry.lock kopyalıyor
- [ ] pyproject.toml'da path = "../../shared"
- [ ] Health endpoint'ler çalışıyor
- [ ] Docker build test başarılı
- [ ] Secret Manager'da gerekli secret'lar var
- [ ] GCP API'ları enabled (Pub/Sub, BigQuery, etc.)
- [ ] Billing enabled

## 12. Hızlı Referans Kartı

| Servis | Port | Health Endpoint | Zorunlu Env Var |
|--------|------|-----------------|-----------------|
| api-gateway | 8080 | /health | PUBSUB_PROJECT_ID |
| ingestion | 8081 | /health | PUBSUB_PROJECT_ID |
| sentiment-processor | 8082 | /health | PUBSUB_PROJECT_ID |
| market-context-processor | 8083 | /health | PUBSUB_PROJECT_ID |
| prediction-engine | 8084 | /health | PUBSUB_PROJECT_ID |
| alert-service | 8085 | /health | PUBSUB_PROJECT_ID |
| analytics-engine | 8086 | /health | PUBSUB_PROJECT_ID |
| tracker-service | 8087 | /health | PUBSUB_PROJECT_ID |

## 13. İletişim

Sorun yaşarsanız:
- README.md dosyalarına bakın
- `docs/` klasörünü kontrol edin
- Health endpoint loglarını inceleyin
- Environment değişkenlerini kontrol edin

---

**Not:** Bu checklist düzenli olarak güncellenmelidir. Servis ekledikçe buraya da ekleyin.
