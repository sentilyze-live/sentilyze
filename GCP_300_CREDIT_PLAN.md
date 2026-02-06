# GCP $300 Kredi Kullanim Plani (3 Ay)

> 3 aylik $300 Google Cloud kredisi icin optimize edilmis kaynak dagitimi.
> Hedef: Maksimum deger, minimum israf.

---

## MEVCUT DURUM ANALIZI

### Aktif GCP Servisleri
| Servis | Tahmini Aylik Maliyet | Notlar |
|--------|----------------------|-------|
| Cloud Run (8 servis) | $40-80 | Scale-to-zero etkin |
| BigQuery (depolama) | $5-25 | 7 tablo, partitioned |
| BigQuery (sorgular) | $25-50 | Sentiment + prediction sorgulari |
| Cloud SQL PostgreSQL | $80-150 | **EN BUYUK MALIYET** (db-n1-standard-2) |
| Pub/Sub (7 topic) | $5-15 | Event-driven mimari |
| Firestore | $0-20 | Agent state + cache |
| Cloud Storage (2 bucket) | $1-5 | Model depolama |
| Secret Manager (15 secret) | ~$0.05 | Neredeyse ucretsiz |
| Cloud Scheduler (2 job) | ~$0.20 | Neredeyse ucretsiz |
| Cloud Build | $0-10 | 120 dk/gun ucretsiz |
| Monitoring + Logging | $0-10 | Temel izleme |
| **TOPLAM** | **$155-370/ay** | Optimizasyon gerekli |

### Sorun: $300 / 3 ay = $100/ay butce
Mevcut yapilandirma ile 3 ayda $465-1,110 harcanabilir. **Optimizasyon zorunlu.**

---

## OPTIMIZE EDILMIS PLAN: $100/AY HEDEFI

### 1. Cloud SQL -> Dusurme (Tasarruf: $70-140/ay)

**Mevcut**: `db-n1-standard-2` (2 vCPU, 7.5GB RAM) = ~$100/ay
**Hedef**: `db-f1-micro` (shared) = ~$10/ay

```bash
# Terraform degisikligi
# infrastructure/terraform/variables.tf
variable "db_tier" {
  default = "db-f1-micro"  # db-n1-standard-2'den degistir
}
```

**Risk**: Dusuk trafik ile sorun olmaz. Yuksek erisimde yavashlik.
**Alternatif**: Cloud SQL'i tamamen kaldirip BigQuery + Firestore kullan (admin panel icin Firestore'a gecis).

### 2. Cloud Run Optimizasyonu (Tasarruf: $15-30/ay)

```yaml
# Tum servislerde:
min-instances: 0          # Scale to zero
max-instances: 3          # 100 yerine 3 yeterli
cpu: 1                    # 2 yerine 1 (prediction-engine haric)
memory: 256Mi             # Varsayilan (gerekirse artir)

# Prediction Engine icin:
memory: 2Gi               # 4Gi'den dusur, modeller 2GB'a sigar
cpu: 2                    # ML icin 2 CPU kalsın
```

Servis bazli onerimler:
| Servis | Mevcut | Onerilen | Tasarruf |
|--------|--------|----------|----------|
| api-gateway | 2Gi/2CPU/min1 | 1Gi/1CPU/min0 | $5-10 |
| prediction-engine | 4Gi/2CPU | 2Gi/2CPU | $3-5 |
| sentiment-processor | 1Gi/2CPU | 512Mi/1CPU | $2-4 |
| market-context | 1Gi/2CPU | 512Mi/1CPU | $2-4 |
| ingestion | 512Mi/1CPU | 256Mi/1CPU | $1-2 |
| alert-service | 256Mi/1CPU | 256Mi/1CPU | $0 |
| tracker | 512Mi/1CPU | 256Mi/1CPU | $1-2 |
| analytics | - | 256Mi/1CPU | $1-2 |

### 3. BigQuery Optimizasyonu (Tasarruf: $10-25/ay)

Zaten partitioning + clustering uygulanmis (iyi). Ek olarak:

```sql
-- Sorgu maliyetini azaltma: SELECT * yerine sadece gerekli kolonlar
-- Her sorgu icin LIMIT kullan
-- Materialize edilmis gorunumler (views) olustur

-- Ornek: Gunluk sentiment ozeti icin materialize view
CREATE MATERIALIZED VIEW `sentilyze_dataset.mv_daily_sentiment`
AS SELECT
  DATE(timestamp) as date,
  market_type,
  AVG(score) as avg_sentiment,
  COUNT(*) as count
FROM `sentilyze_dataset.sentiment_analysis`
GROUP BY date, market_type;
```

### 4. Memorystore Redis (EKLEME: $5-10/ay)

Redis entegrasyonu icin Memorystore:
```bash
# En kucuk instance
gcloud redis instances create sentilyze-cache \
  --size=1 \
  --region=us-central1 \
  --tier=basic \
  --redis-version=redis_7_0

# Maliyet: ~$0.049/GB/saat = ~$36/ay (1GB)
# ALTERNATIF: Redis Labs Free Tier (30MB, $0) - test icin yeterli
# ALTERNATIF: Upstash Redis (10K komut/gun ucretsiz)
```

**Oneri**: Baslangicta **Upstash Redis** (ucretsiz tier) veya mevcut **in-memory fallback** kullanin. Production trafikde Memorystore'a gecin.

---

## AYLIK BUTCE DAGITIMI ($100/ay)

| Kalem | Butce | Aciklama |
|-------|-------|----------|
| Cloud Run (8 servis) | $25-35 | Scale-to-zero, dusuk kaynak |
| Cloud SQL (f1-micro) | $10 | Sadece admin panel icin |
| BigQuery | $15-25 | Optimize edilmis sorgular |
| Pub/Sub | $5-8 | 7 topic, normal hacim |
| Firestore | $5-10 | Cache + agent state |
| Cloud Storage | $1-3 | Model depolama |
| Vertex AI / Gemini | $2.50 | 1,100 req/gun limiti |
| Monitoring | $2-5 | Temel izleme |
| Diger (Scheduler, Secrets) | $0.50 | Neredeyse ucretsiz |
| **TOPLAM** | **$66-97/ay** | $100 butce icinde |

---

## 3 AYLIK YATIRIM ONCELIKLERI

### Ay 1: Altyapi Optimizasyonu ($90 butce)
- [ ] Cloud SQL'i db-f1-micro'ya dusur
- [ ] Cloud Run kaynaklarini optimize et (yukaridaki tablo)
- [ ] BigQuery materialize view'lar olustur
- [ ] Model egitim pipeline'ini calistir (mevcut BigQuery + Cloud Run ile $0 ek)
- [ ] Feedback loop'u aktive et
- [ ] Redis icin Upstash Free Tier veya in-memory fallback kullan

### Ay 2: Uretim Kalitesi ($100 butce)
- [ ] Modelleri egit ve GCS'e kaydet
- [ ] WeightOptimizer'i gunluk calistir (Cloud Scheduler ile)
- [ ] Canary deploy: prediction-engine'i yeni modellerle test et
- [ ] iOS uygulama gelistirmeye basla (yerel, GCP maliyeti yok)
- [ ] BigQuery sorgu performansini izle ve optimize et

### Ay 3: Lansman Hazirlik ($110 butce)
- [ ] iOS TestFlight beta dagitimi
- [ ] Production trafik testi
- [ ] Memorystore Redis'e gecis karari ver (trafige bagli)
- [ ] Alert service'i prediction engine'e bagla
- [ ] Monitoring dashboard'u kur

---

## MALIYET IZLEME ARACLARI

### Budget Alert Kurulumu
```bash
# GCP Budget Alert - $100/ay limit
gcloud billing budgets create \
  --billing-account=BILLING_ACCOUNT_ID \
  --display-name="Sentilyze Monthly Budget" \
  --budget-amount=100USD \
  --threshold-rule=percent=50,basis=current-spend \
  --threshold-rule=percent=80,basis=current-spend \
  --threshold-rule=percent=100,basis=current-spend \
  --notifications-rule-pubsub-topic=projects/sentilyze-v6-clean/topics/budget-alerts
```

### Gunluk Maliyet Kontrol Komutu
```bash
# Gecerli ay harcamasini gor
gcloud billing accounts describe BILLING_ACCOUNT_ID --format="json"

# Servis bazli maliyet
gcloud services list --enabled --format="table(config.name)"
```

---

## UCRETSIZ ALTERNATIFLER (GCP KREDISI DISI)

Bazi servisleri GCP disina tasiyarak krediyi koruyabilirsiniz:

| Servis | GCP Maliyeti | Ucretsiz Alternatif |
|--------|-------------|---------------------|
| Redis Cache | $36/ay (Memorystore) | Upstash Free (10K cmd/gun) |
| PostgreSQL | $10-100/ay (Cloud SQL) | Supabase Free (500MB) |
| Push Notifications | FCM (ucretsiz) | FCM (zaten ucretsiz) |
| CI/CD | Cloud Build ($0-10) | GitHub Actions (2000 dk/ay) |
| Monitoring | Cloud Monitoring ($0-10) | Better Stack Free |
| Error Tracking | Cloud Logging ($0-10) | Sentry Free (5K events/ay) |

**Potansiyel tasarruf**: $50-130/ay -> Krediyi 4-5 aya uzatabilir

---

## KRITIK TERRAFORM DEGISIKLIKLERI

### 1. Cloud SQL Tier Degisikligi
```hcl
# infrastructure/terraform/variables.tf
variable "db_tier" {
  description = "Cloud SQL instance tier"
  type        = string
  default     = "db-f1-micro"  # DEGISTIR: db-n1-standard-2 -> db-f1-micro
}
```

### 2. Cloud Run Kaynak Limitleri
```hcl
# infrastructure/terraform/main.tf - her servis icin
resource "google_cloud_run_service" "api_gateway" {
  template {
    spec {
      containers {
        resources {
          limits = {
            memory = "1Gi"   # 2Gi'den dusur
            cpu    = "1"     # 2'den dusur
          }
        }
      }
    }
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = "0"  # 1'den dusur
        "autoscaling.knative.dev/maxScale" = "3"   # 100'den dusur
      }
    }
  }
}
```

### 3. BigQuery Retention
```hcl
# 90 gun -> 30 gun (raw_data tablosu icin)
resource "google_bigquery_table" "raw_data" {
  time_partitioning {
    type                     = "DAY"
    expiration_ms            = 2592000000  # 30 gun (90 gunden dusur)
  }
}
```

---

## SONUC

| Metrik | Optimizasyon Oncesi | Optimizasyon Sonrasi |
|--------|--------------------|--------------------|
| Aylik GCP maliyeti | $155-370 | $66-97 |
| 3 aylik toplam | $465-1,110 | $198-291 |
| $300 kredi yeterliligi | 1-2 ay | **3+ ay** |
| Performans etkisi | - | Minimal (dusuk trafik) |

**Anahtar mesaj**: Cloud SQL tier dusurme tek basina $70-140/ay tasarruf saglar.
Bu degisiklik ile $300 kredi rahatlikla 3 aya yeter.
