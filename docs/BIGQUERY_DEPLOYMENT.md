# BigQuery Deployment Guide - Option A (Single Dataset)

Bu rehber, Sentilyze Unified projesi için **tek dataset** mimarisinde BigQuery yapılandırmasını açıklar.

## 📊 Mimari Özeti

**Dataset:** `sentilyze_dataset`

**Tablolar (7 adet):**

| Tablo | Katman | Amaç | Bölümleme | Kümeleme |
|-------|--------|------|-----------|----------|
| `raw_data` | Bronze | Ham ingestion verileri | `timestamp` (GÜN) | `market_type`, `data_source` |
| `sentiment_analysis` | Silver | İşlenmiş sentiment verileri | `timestamp` (GÜN) | `market_type`, `sentiment_label` |
| `market_context` | Silver | Piyasa indikatörleri | `timestamp` (GÜN) | `market_type`, `asset_symbol` |
| `predictions` | Gold | AI/ML tahminleri | `prediction_timestamp` (GÜN) | `market_type`, `asset_symbol`, `prediction_type` |
| `prediction_accuracy` | Gold | Tahmin doğruluk sonuçları | `validation_timestamp` (GÜN) | `market_type`, `asset_symbol` |
| `alerts` | Gold | Alert bildirimleri | `created_at` (GÜN) | `market_type`, `alert_type`, `severity` |
| `analytics_summary` | Gold | Günlük özet analytics | `date` (GÜN) | `market_type` |

**View'lar (4 adet):**

| View | Amaç |
|------|------|
| `daily_sentiment_summary` | Günlük sentiment toplamları |
| `prediction_performance` | Tahmin performans metrikleri |
| `crypto_market_overview` | Kripto piyasa özeti |
| `gold_market_overview` | Altın piyasa özeti |

---

## 🚀 Deployment Seçenekleri

### Seçenek 1: Terraform ile (Önerilen - Production)

```bash
# 1. Terraform'u başlat
cd infrastructure/terraform

# 2. GCP kimlik bilgilerini ayarla
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# 3. Terraform değişkenlerini ayarla
cat > terraform.tfvars <<EOF
project_id = "your-gcp-project-id"
region = "us-central1"
dataset_id = "sentilyze_dataset"
dataset_location = "US"
EOF

# 4. Terraform plan'ı gözden geçir
terraform plan

# 5. Deploy et
terraform apply

# 6. View'ları oluştur (manuel veya terraform output)
terraform output view_creation_commands
```

**Terraform ile oluşturulan kaynaklar:**
- ✅ Dataset: `sentilyze_dataset`
- ✅ 7 tablo (partitioning ve clustering ile)
- ✅ 4 view
- ✅ Gerekli IAM rolleri
- ✅ Data retention politikaları

---

### Seçenek 2: bq_setup.py Tool ile (Development/Local)

```bash
# 1. Ortam değişkenlerini ayarla
export GCP_PROJECT_ID=your-project-id
export BIGQUERY_DATASET=sentilyze_dataset
export BIGQUERY_LOCATION=US

# 2. Python tool'u çalıştır
cd tools
python bq_setup.py \
  --project-id $GCP_PROJECT_ID \
  --dataset $BIGQUERY_DATASET \
  --location $BIGQUERY_LOCATION \
  --create-tables \
  --create-views

# 3. Schema'ları doğrula
python bq_setup.py \
  --project-id $GCP_PROJECT_ID \
  --dataset $BIGQUERY_DATASET \
  --validate-schemas
```

---

### Seçenek 3: Manuel SQL ile (Hızlı Test)

```bash
# BigQuery'e bağlan
bq query --use_legacy_sql=false
```

```sql
-- 1. Dataset oluştur
CREATE SCHEMA IF NOT EXISTS `your-project-id.sentilyze_dataset`
OPTIONS(
  location="US",
  description="Sentilyze unified dataset for crypto and gold market sentiment analysis",
  labels=[("project", "sentilyze"), ("environment", "production")]
);

-- 2. Tabloları oluştur (aşağıdaki SQL script'lerini çalıştır)
-- Infrastructure/terraform/schemas/ dizinindeki JSON schema'ları kullan
```

---

## 📋 Adım Adım Kurulum

### Adım 1: Önce GCP Projesi Hazırlığı

```bash
# GCP projesi seç
export GCP_PROJECT_ID=your-project-id
gcloud config set project $GCP_PROJECT_ID

# Gerekli API'leri etkinleştir
gcloud services enable bigquery.googleapis.com
gcloud services enable bigquerystorage.googleapis.com

# Service account oluştur (eğer yoksa)
gcloud iam service-accounts create sentilyze-bq \
  --display-name="Sentilyze BigQuery Service Account"

# Service account'a BigQuery yetkileri ver
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:sentilyze-bq@$GCP_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataEditor"

gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:sentilyze-bq@$GCP_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/bigquery.jobUser"

# Service account key oluştur (development için - production'da Workload Identity kullanın)
gcloud iam service-accounts keys create ~/sentilyze-bq-key.json \
  --iam-account=sentilyze-bq@$GCP_PROJECT_ID.iam.gserviceaccount.com

# Key'i ortam değişkeni olarak ayarla
export GOOGLE_APPLICATION_CREDENTIALS=~/sentilyze-bq-key.json
```

---

### Adım 2: Dataset ve Tabloları Oluşturma

#### Terraform Yöntemi (Production için önerilen):

```bash
cd infrastructure/terraform

# terraform.tfvars dosyasını oluştur
cat > terraform.tfvars <<EOF
project_id = "${GCP_PROJECT_ID}"
region = "us-central1"
zone = "us-central1-a"

dataset_id = "sentilyze_dataset"
dataset_location = "US"
dataset_description = "Sentilyze unified dataset for crypto and gold market sentiment analysis"

# Data retention (gün olarak)
raw_data_retention_days = 90
processed_data_retention_days = 365
analytics_retention_days = 0  # 0 = no expiration

# Feature flags
enable_crypto_market = true
enable_gold_market = true
EOF

# Deploy
terraform init
terraform plan
terraform apply -auto-approve
```

#### Python Tool Yöntemi (Geliştirme için):

```bash
# Gerekli paketleri kur
pip install google-cloud-bigquery

# Tool'u çalıştır
python tools/bq_setup.py \
  --project-id $GCP_PROJECT_ID \
  --dataset sentilyze_dataset \
  --location US \
  --environment prod \
  --create-all
```

---

### Adım 3: Ortam Değişkenlerini Ayarlama

`.env` dosyanızı şu şekilde güncelleyin:

```bash
# ============================================
# BigQuery Configuration (Single Dataset - Option A)
# ============================================
BIGQUERY_DATASET=sentilyze_dataset
BIGQUERY_LOCATION=US
BIGQUERY_EMULATOR_HOST=  # Production'da boş bırakın

# GCP Kimlik Bilgileri (Production'da Secret Manager kullanın)
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

---

### Adım 4: Doğrulama ve Test

```bash
# 1. Dataset'in oluştuğunu kontrol et
export GCP_PROJECT_ID=your-project-id
bq ls $GCP_PROJECT_ID:sentilyze_dataset

# 2. Tabloları listele
bq ls $GCP_PROJECT_ID:sentilyze_dataset

# 3. Tablo şemalarını kontrol et
bq show $GCP_PROJECT_ID:sentilyze_dataset.raw_data
bq show $GCP_PROJECT_ID:sentilyze_dataset.sentiment_analysis

# 4. Test verisi ekle
cat > test_data.json <<EOF
{"event_id": "test-001", "timestamp": "2026-01-31T12:00:00Z", "market_type": "crypto", "data_source": "test", "content": "Test event", "metadata": "{}"}
EOF

bq load \
  --source_format=NEWLINE_DELIMITED_JSON \
  $GCP_PROJECT_ID:sentilyze_dataset.raw_data \
  test_data.json

# 5. Veriyi sorgula
bq query --use_legacy_sql=false \
  "SELECT * FROM \`$GCP_PROJECT_ID.sentilyze_dataset.raw_data\` LIMIT 10"

# 6. Test verisini temizle
rm test_data.json
bq query --use_legacy_sql=false \
  "DELETE FROM \`$GCP_PROJECT_ID.sentilyze_dataset.raw_data\` WHERE event_id = 'test-001'"
```

---

## 📊 Data Retention Politikası

| Tablo | Retention | Açıklama |
|-------|-----------|----------|
| `raw_data` | 90 gün | Ham veriler 90 gün sonra otomatik silinir |
| `sentiment_analysis` | 365 gün | İşlenmiş veriler 1 yıl saklanır |
| `market_context` | 365 gün | Piyasa verileri 1 yıl saklanır |
| `predictions` | 0 (sonsuz) | Tahminler kalıcı saklanır |
| `prediction_accuracy` | 0 (sonsuz) | Doğruluk metrikleri kalıcı |
| `alerts` | 180 gün | Alert'ler 6 ay saklanır |
| `analytics_summary` | 0 (sonsuz) | Özet analytics kalıcı |

**Retention ayarı:**
```sql
-- Tablo düzeyinde retention ayarı (gün olarak)
ALTER TABLE `project.dataset.table`
SET OPTIONS (
  expiration_timestamp = TIMESTAMP_ADD(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
);
```

---

## 🔐 Güvenlik ve IAM

### Gerekli Roller

| Rol | Kim | Amaç |
|-----|-----|------|
| `roles/bigquery.dataEditor` | Uygulama servisleri | Veri okuma/yazma |
| `roles/bigquery.jobUser` | Uygulama servisleri | Query çalıştırma |
| `roles/bigquery.dataViewer` | Analiz kullanıcıları | Sadece okuma |
| `roles/bigquery.admin` | DevOps/Admin | Tam yönetim |

### IAM Atama

```bash
# Servis account için (örnek: sentilyze-bq@sentilyze-v5-clean.iam.gserviceaccount.com)
export SERVICE_ACCOUNT="sentilyze-bq@$GCP_PROJECT_ID.iam.gserviceaccount.com"

# Data Editor (okuma/yazma)
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/bigquery.dataEditor"

# Job User (query çalıştırma)
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/bigquery.jobUser"

# Dataset seviyesinde yetki (daha güvenli)
bq query --use_legacy_sql=false \
  "GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA \`$GCP_PROJECT_ID.sentilyze_dataset\` TO 'serviceAccount:$SERVICE_ACCOUNT'"
```

---

## 💰 Maliyet Optimizasyonu

### Partitioning Faydaları

- **Storage:** Sadece aktif partition'lar için ödeme yapılır
- **Query:** Sadece ilgili partition'lar taranır (masraf azalır)
- **Time-travel:** 7 gün ücretsiz time-travel desteği

### Maliyet Tahmini (aylık)

| Kullanım | Storage | Query | Toplam |
|----------|---------|-------|--------|
| 100GB veri | ~$2 | ~$5 | ~$7 |
| 1TB veri | ~$20 | ~$25 | ~$45 |
| 10TB veri | ~$200 | ~$100 | ~$300 |

**Not:** Partitioning ve clustering ile query maliyetleri %50-70 azalabilir.

---

## 🛠️ Troubleshooting

### Sorun 1: Dataset zaten var

```bash
# Dataset'i sil ve yeniden oluştur (DİKKAT: Veri kaybı!)
bq rm -r -f -d $GCP_PROJECT_ID:sentilyze_dataset
terraform apply
```

### Sorun 2: Tablo şeması uyuşmazlığı

```bash
# Schema doğrulama
python tools/bq_setup.py \
  --project-id $GCP_PROJECT_ID \
  --dataset sentilyze_dataset \
  --validate-schemas

# Tabloyu sil ve yeniden oluştur
bq rm -f -t $GCP_PROJECT_ID:sentilyze_dataset.raw_data
terraform apply
```

### Sorun 3: Permission denied

```bash
# Service account yetkilerini kontrol et
gcloud projects get-iam-policy $GCP_PROJECT_ID \
  --flatten="bindings[].members" \
  --format="table(bindings.role)" \
  --filter="bindings.members:sentilyze-bq"

# Örnek: sentilyze-v5-clean projesi için kontrol
gcloud projects get-iam-policy sentilyze-v5-clean \
  --flatten="bindings[].members" \
  --format="table(bindings.role,bindings.members)" \
  --filter="bindings.members:sentilyze-bq"

# Yetkileri yenile
gcloud auth application-default login
```

---

## 📚 Önemli Notlar

1. **Emulator ile Development:**
   ```bash
   # Local development için BigQuery emulator kullan
   docker-compose up bigquery-emulator
   # Emulator'da partitioning ve clustering desteği sınırlı olabilir
   ```

2. **Production Deployment:**
   - Asla `GOOGLE_APPLICATION_CREDENTIALS` ile key dosyası kullanmayın
   - Workload Identity veya Secret Manager kullanın
   - Terraform state'ini remote backend'de (GCS) saklayın

3. **Monitoring:**
   ```bash
   # BigQuery slot kullanımını izle
   gcloud monitoring metrics list --filter="bigquery"
   ```

4. **Backup:**
   ```bash
   # Dataset'i başka bölgeye kopyala (yedekleme)
   bq cp -a $GCP_PROJECT_ID:sentilyze_dataset $GCP_PROJECT_ID:sentilyze_dataset_backup
   ```

---

## ✅ Deployment Checklist

- [ ] GCP projesi oluşturuldu
- [ ] Gerekli API'ler etkinleştirildi
- [ ] Service account oluşturuldu
- [ ] IAM rolleri atandı
- [ ] Dataset oluşturuldu (`sentilyze_dataset`)
- [ ] 7 tablo oluşturuldu (partitioning + clustering)
- [ ] 4 view oluşturuldu
- [ ] `.env` dosyası güncellendi
- [ ] Test verisi eklendi ve sorgulandı
- [ ] Data retention politikaları doğrulandı
- [ ] Maliyet limitleri ayarlandı (`BIGQUERY_MAX_BYTES_BILLED`)

---

## 🚀 Sonraki Adımlar

BigQuery deployment tamamlandıktan sonra:

1. **Pub/Sub topics ve subscriptions** oluştur
2. **Redis/Firestore** cache'i yapılandır
3. **Servisleri deploy et:** `docker-compose up` veya Cloud Run
4. **Health check endpoint'lerini** test et: `curl http://localhost:8080/health`
5. **End-to-end test** yap: Veri ingestion → Sentiment analysis → BigQuery storage

---

**Son Güncelleme:** 31 Ocak 2026  
**Versiyon:** 4.0.0  
**Mimari:** Single Dataset (Option A)
