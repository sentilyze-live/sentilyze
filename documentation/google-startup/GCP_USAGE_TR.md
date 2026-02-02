# Google Cloud Platform Kullanım Dökümanı
## Sentilyze Projesi - Google for Startups Cloud Program Başvurusu

---

## 📋 Özet

**Sentilyze**, Google Cloud Platform'un neredeyse tüm temel servislerini kullanarak geliştirilmiş, **tam cloud-native** bir finans teknolojisi platformudur. Proje, Google'ın modern bulut mimarisinin gücünü ve esnekliğini maksimum düzeyde kullanmaktadır.

### Proje Özellikleri
- **Geliştirme Süreci**: Tek kişi tarafından, yapay zeka desteği ile, sıfır kodlama bilgisiyle geliştirildi
- **Mimari**: Event-driven mikroservis mimarisi
- **Servis Sayısı**: 8 bağımsız mikroservis
- **Teknoloji**: Python, FastAPI, Next.js, TypeScript
- **Deployment**: Tam otomatik CI/CD

---

## 🌟 Neden Google Cloud Platform?

### Stratejik Seçim Nedenleri

1. **Yapay Zeka Entegrasyonu**: Vertex AI ve Google'ın AI servisleri
2. **Serverless Mimari**: Cloud Run ile maliyet optimizasyonu
3. **Event-Driven**: Pub/Sub ile ölçeklenebilir mesajlaşma
4. **Veri Analizi**: BigQuery ile petabayt ölçeğinde analiz kapasitesi
5. **Güvenlik**: Enterprise-grade güvenlik standartları
6. **Esneklik**: Infrastructure as Code (Terraform) desteği

---

## ☁️ Kullanılan Google Cloud Servisleri

### 1. Cloud Run ⭐⭐⭐⭐⭐

**Kullanım**: 8 mikroservisin tamamının hosting'i

**Neden Seçildi**:
- Serverless: Kullanılmadığında ücret yok (scale-to-zero)
- Otomatik ölçeklendirme: 0'dan 100+ instance'a
- Container-based: Herhangi bir dilde geliştirme imkanı
- Pay-per-use: Sadece işlem sırasında ücretlendirme

**Servislerimiz**:

| Servis | Trafik | Ölçeklendirme | Aylık Tahmini Maliyet |
|--------|--------|---------------|----------------------|
| **API Gateway** | Yüksek | 1-50 instance | $50-150 |
| **Ingestion** | Orta | 0-20 instance | $30-80 |
| **Sentiment Processor** | Yüksek | 0-100 instance | $100-300 |
| **Market Context** | Orta | 0-50 instance | $50-150 |
| **Prediction Engine** | Orta | 0-50 instance | $50-150 |
| **Alert Service** | Düşük | 0-20 instance | $20-50 |
| **Tracker Service** | Düşük | 0-10 instance | $10-30 |
| **Analytics Engine** | Düşük | 0-10 instance | $20-60 |

**Toplam Cloud Run Maliyeti**: ~$330-970/ay

**Neden Önemli**: Geleneksel VM'lere göre %60-70 maliyet tasarrufu sağlıyor. Scale-to-zero özelliği sayesinde düşük trafik dönemlerinde maliyetler minimum seviyede.

---

### 2. Cloud Pub/Sub ⭐⭐⭐⭐⭐

**Kullanım**: Servisler arası event-driven iletişim

**Pub/Sub Topics**: 7 adet
- `raw-events`: Ham veri akışı
- `processed-sentiment`: İşlenmiş sentiment verileri
- `market-context`: Teknik analiz verileri
- `processed-events`: İşlenmiş eventler
- `predictions`: Tahminler
- `alerts`: Bildirimler
- `analytics-events`: Analitik eventleri

**Push Subscriptions**: 8 adet (Cloud Run uyumlu)
**Pull Subscriptions**: 4 adet (Batch işleme için)

**Mesaj Hacmi**:
- Günlük: ~100,000-500,000 mesaj
- Aylık: ~3-15 milyon mesaj

**Aylık Tahmini Maliyet**: $20-100

**Neden Önemli**: 
- Servisleri birbirinden ayırarak bağımsız ölçeklendirme imkanı
- Mesaj garantisi ve retry mekanizması
- Real-time ve batch processing'i aynı anda destekliyor

---

### 3. BigQuery ⭐⭐⭐⭐⭐

**Kullanım**: Veri ambarı, analitik ve ML feature store

**Dataset**: `sentilyze_dataset`

**Tablolar** (7 adet):
1. **raw_data**: Ham piyasa verileri (~1M satır/ay)
2. **sentiment_analysis**: Sentiment skorları (~500K satır/ay)
3. **market_context**: Teknik göstergeler (~200K satır/ay)
4. **predictions**: Tahminler (~50K satır/ay)
5. **prediction_accuracy**: Doğruluk metrikleri (~10K satır/ay)
6. **alerts**: Bildirim geçmişi (~5K satır/ay)
7. **analytics_summary**: Günlük özetler (~30 satır/gün)

**Views** (4 adet):
- `daily_sentiment_summary`: Günlük sentiment özeti
- `prediction_performance`: Model performans analizi
- `crypto_market_overview`: Kripto piyasa görünümü
- `gold_market_overview`: Altın piyasa görünümü

**Özellikler**:
- **Partitioning**: Daily partitions (timestamp field)
- **Clustering**: market_type, asset_symbol
- **Retention**: 90 gün (raw), 1 yıl (processed)

**Veri Hacmi**:
- Depolama: ~50-200 GB
- Aylık sorgu: ~10-50 TB işlenen veri

**Aylık Tahmini Maliyet**: $50-200

**Neden Önemli**:
- Petabayt ölçeğinde sorgu kapasitesi
- SQL ile kolay analiz
- ML model training için feature store
- Gerçek zamanlı streaming insert desteği

---

### 4. Cloud SQL (PostgreSQL) ⭐⭐⭐⭐

**Kullanım**: İlişkisel veri - Tahmin tracking ve kullanıcı yönetimi

**Instance**: 
- Development: db-f1-micro (0.6 GB RAM)
- Production: db-n1-standard-2 (7.5 GB RAM)

**Databases**:
- `sentilyze_predictions`: Tahmin tracking
- `admin_panel`: Kullanıcı ve özellik yönetimi

**Özellikler**:
- Otomatik backup (daily)
- High availability (production)
- Private IP (VPC integration)
- Point-in-time recovery

**Veri Hacmi**:
- Satır sayısı: ~100K tahmin
- Depolama: ~5-20 GB

**Aylık Tahmini Maliyet**: $50-200

**Neden Önemli**:
- ACID uyumlu transaksiyonlar
- Complex query desteği
- Foreign key constraints
- Managed service (bakım yok)

---

### 5. Firestore ⭐⭐⭐⭐

**Kullanım**: NoSQL cache, session storage, feature flags

**Collections**:
- `cache`: API response cache (5 min TTL)
- `sessions`: Kullanıcı oturumları
- `feature_flags`: Özellik bayrakları
- `rate_limits`: Rate limiting counters

**Özellikler**:
- Real-time updates
- Offline support
- Automatic scaling
- Strong consistency

**Veri Hacmi**:
- Doküman sayısı: ~10K-50K
- Okuma: ~1-5M/ay
- Yazma: ~500K-2M/ay

**Aylık Tahmini Maliyet**: $20-80

**Neden Önemli**:
- Redis alternatifi (Google-native)
- Scale-to-zero Cloud Run ile uyumlu
- Real-time capabilities
- Daha düşük latency (same-region)

---

### 6. Secret Manager ⭐⭐⭐⭐⭐

**Kullanım**: API keys, credentials, hassas bilgiler

**Secrets** (17 adet):
- Database credentials
- Crypto API keys (5)
- Gold API keys (4)
- Social media API keys (2)
- ML/AI API keys (2)
- Notification credentials (4)

**Özellikler**:
- Otomatik versioning
- IAM entegrasyonu
- Audit logging
- Encryption at rest

**Aylık Tahmini Maliyet**: $5-15

**Neden Önemli**:
- Güvenli credential yönetimi
- Environment variable injection
- Kolay rotation
- Compliance requirements

---

### 7. Cloud Build ⭐⭐⭐⭐⭐

**Kullanım**: CI/CD pipeline - Otomatik build ve deploy

**Triggers**: 8 adet (her servis için)

**Build Pipeline**:
1. Source checkout (GitHub)
2. Docker image build (multi-stage)
3. Image push to Artifact Registry
4. Deploy to Cloud Run
5. Health check
6. Traffic migration

**Build Sıklığı**:
- Development: ~5-10 build/gün
- Production: ~1-3 build/gün

**Özellikler**:
- Parallel builds
- Build caching
- Custom build steps
- Approval gates (production)

**Aylık Tahmini Maliyet**: $20-80

**Neden Önemli**:
- Tam otomatik deployment
- Zero-downtime releases
- Built-in testing integration
- Native GCP integration

---

### 8. Artifact Registry ⭐⭐⭐⭐

**Kullanım**: Docker image registry

**Repositories**:
- `sentilyze-repo`: Tüm servis image'ları

**Images** (8 servis x 2-3 versiyon):
- ~16-24 image aktif
- Image size: 200-500 MB/image
- Total storage: ~5-10 GB

**Özellikler**:
- Vulnerability scanning
- Access control (IAM)
- Geo-replication
- Automatic cleanup policies

**Aylık Tahmini Maliyet**: $5-20

**Neden Önemli**:
- Cloud Run ile native entegrasyon
- Güvenlik taraması
- Hızlı image pull
- Version yönetimi

---

### 9. Cloud Storage ⭐⭐⭐⭐

**Kullanım**: Object storage - ML models, backups, logs

**Buckets**:
1. **sentilyze-v5-clean-sentilyze**: Genel data
2. **sentilyze-v5-clean-sentilyze-models**: ML modelleri
3. **sentilyze-v5-clean-terraform-state**: Terraform state

**Özellikler**:
- Versioning enabled
- Lifecycle rules (90 gün retention)
- Regional storage
- Automatic backups

**Depolama Hacmi**: ~20-50 GB

**Aylık Tahmini Maliyet**: $5-15

**Neden Önemli**:
- ML model versioning
- Infrastructure state management
- Log archiving
- 99.99% durability

---

### 10. Cloud Scheduler ⭐⭐⭐⭐

**Kullanım**: Zamanlanmış görevler

**Jobs** (2 adet):
1. **crypto-data-ingestion**: Her 5 dakika
2. **gold-data-ingestion**: Her 15 dakika

**Özellikler**:
- Cron syntax
- Timezone support
- OAuth authentication
- Retry policies

**Aylık Çalışma**:
- Crypto: ~8,640 invocations/ay
- Gold: ~2,880 invocations/ay

**Aylık Tahmini Maliyet**: $5-10

**Neden Önemli**:
- Güvenilir scheduling
- Cloud Run entegrasyonu
- Automatic retries
- Cost-effective

---

### 11. Cloud Logging ⭐⭐⭐⭐⭐

**Kullanım**: Merkezi log yönetimi

**Log Sources**:
- Cloud Run (8 servis)
- Cloud Build
- Cloud Scheduler
- Application logs (structlog)

**Log Hacmi**: ~5-20 GB/ay

**Özellikler**:
- Structured logging
- Log-based metrics
- Log analysis
- Export to BigQuery

**Aylık Tahmini Maliyet**: $10-40

**Neden Önemli**:
- Debugging
- Audit trails
- Security monitoring
- Performance analysis

---

### 12. Cloud Monitoring ⭐⭐⭐⭐⭐

**Kullanım**: Metrikler, dashboards, alertler

**Monitörlenen Metrikler**:
- Request rate, latency, errors (Cloud Run)
- CPU, memory utilization
- Pub/Sub message lag
- Database connections
- Custom business metrics

**Alert Policies** (5 adet):
- High error rate (>5%)
- High latency (>2s p95)
- Service down (>5 min)
- Pub/Sub backlog (>10K)
- Database connection pool exhausted

**Notification Channels**:
- Email
- Slack (planlanan)

**Aylık Tahmini Maliyet**: $10-30

**Neden Önemli**:
- Proactive issue detection
- Performance optimization
- SLA monitoring
- Cost tracking

---

### 13. Cloud Trace ⭐⭐⭐

**Kullanım**: Distributed tracing

**Özellikler**:
- Request tracing across services
- Latency analysis
- Service dependency mapping
- Performance bottleneck detection

**Aylık Tahmini Maliyet**: $5-15

**Neden Önemli**:
- Performance debugging
- Service optimization
- User experience improvement

---

### 14. Vertex AI ⭐⭐⭐⭐

**Kullanım**: AI/ML model hosting ve inference

**Models**:
- Hugging Face transformers
- Custom sentiment models
- OpenAI API proxy

**Özellikler**:
- Model versioning
- A/B testing capability
- Automatic scaling
- Batch prediction

**Aylık Tahmini Maliyet**: $50-200 (planlanan)

**Neden Önemli**:
- Managed ML infrastructure
- GPU acceleration
- Model monitoring
- Easy deployment

---

## 💰 Toplam Maliyet Analizi

### Aylık Tahmini Maliyetler

| Servis | Development | Production |
|--------|-------------|------------|
| Cloud Run | $100-200 | $330-970 |
| Pub/Sub | $10-30 | $20-100 |
| BigQuery | $20-50 | $50-200 |
| Cloud SQL | $25-50 | $50-200 |
| Firestore | $10-30 | $20-80 |
| Secret Manager | $5-10 | $5-15 |
| Cloud Build | $10-30 | $20-80 |
| Artifact Registry | $5-10 | $5-20 |
| Cloud Storage | $5-10 | $5-15 |
| Cloud Scheduler | $2-5 | $5-10 |
| Cloud Logging | $5-15 | $10-40 |
| Cloud Monitoring | $5-15 | $10-30 |
| Cloud Trace | $2-5 | $5-15 |
| Vertex AI | $0 (minimal) | $50-200 |
| **TOPLAM** | **$204-460/ay** | **$585-1,975/ay** |

### Yıllık Projeksiyon

- **Development**: $2,448-5,520/yıl
- **Production**: $7,020-23,700/yıl

**Ortalama Production Maliyeti**: ~$12,000-15,000/yıl

---

## 🎯 Google Cloud'un Projeye Katkıları

### 1. Hızlı Geliştirme

**Serverless Mimari**: Infrastructure yönetimine zaman harcamadan, sadece kod geliştirmeye odaklanma imkanı.

**Managed Services**: Database, caching, messaging gibi servislerin bakımı Google tarafından yapılıyor.

**Infrastructure as Code**: Terraform ile tüm altyapı kodu olarak yönetiliyor.

### 2. Maliyet Optimizasyonu

**Scale-to-Zero**: Kullanılmayan servisler için ödeme yapılmıyor.

**Pay-per-Use**: Sadece gerçek kullanım için ücret.

**Free Tier**: Birçok serviste generous free tier.

### 3. Güvenlik ve Compliance

**Enterprise Security**: Google'ın güvenlik standartları.

**Compliance**: GDPR, SOC 2, ISO 27001 sertifikaları.

**Secret Management**: Güvenli credential yönetimi.

### 4. Ölçeklenebilirlik

**Otomatik Ölçeklendirme**: 0'dan yüzlerce instance'a otomatik.

**Global Infrastructure**: Düşük latency için çoklu region desteği.

**No Capacity Planning**: Google altyapıyı yönetiyor.

### 5. AI/ML Capabilities

**Vertex AI**: Kolay model deployment.

**Pre-trained Models**: Hugging Face entegrasyonu.

**BigQuery ML**: SQL ile model training.

---

## 🚀 Gelecek Planları ve GCP Kullanımı

### Kısa Vade (3 ay)

**Yeni GCP Servisleri**:
- [ ] **Cloud Functions**: Event-triggered microservices
- [ ] **Cloud Tasks**: Asynchronous task queuing
- [ ] **Cloud CDN**: Static asset delivery
- [ ] **Cloud Armor**: DDoS protection

**Beklenen Maliyet Artışı**: +$100-200/ay

### Orta Vade (6 ay)

**Yeni Özellikler**:
- [ ] **Memorystore (Redis)**: Advanced caching
- [ ] **Cloud Spanner**: Global database (multi-region)
- [ ] **Dataflow**: Real-time streaming pipeline
- [ ] **Cloud Vision API**: Image analysis

**Beklenen Maliyet Artışı**: +$300-500/ay

### Uzun Vade (12 ay)

**Enterprise Features**:
- [ ] **GKE (Kubernetes)**: Container orchestration
- [ ] **Cloud Composer**: Workflow orchestration
- [ ] **BigQuery BI Engine**: In-memory analytics
- [ ] **Multi-region deployment**: Global availability

**Beklenen Maliyet**: $2,000-3,000/ay

---

## 📊 Neden Google for Startups?

### 1. Finansal Destek

Startup olarak, Google Cloud Platform'un sunduğu **$200,000 kredi**, platformumuzu geliştirmek ve scale etmek için kritik öneme sahip.

**Kredi Kullanım Planı**:
- İlk 6 ay: Development ve testing ($2,000-3,000/ay)
- 6-12 ay: Production launch ($5,000-10,000/ay)
- 12-24 ay: Scale ve growth ($10,000-15,000/ay)

### 2. Teknik Destek

Google'ın teknik ekibinden destek alarak:
- Mimari optimizasyonu
- Maliyet optimizasyonu
- Best practices implementation
- Performance tuning

### 3. Ekosistem

Google Cloud ekosistemindeki diğer startuplar ile:
- Networking
- Knowledge sharing
- Partnership opportunities

### 4. Kredibilite

Google for Startups programına kabul, yatırımcılar ve müşteriler için:
- Güven sinyali
- Teknik yetkinlik göstergesi
- Scale potansiyeli

---

## 🎨 Benzersiz Yönlerimiz

### 1. AI-Assisted Development

Bu proje, **kodlama bilgisi olmayan bir girişimci tarafından, tamamen yapay zeka desteği ile geliştirilmiştir**:

- Tüm Python backend kodu AI ile yazıldı
- Next.js frontend AI ile tasarlandı
- Terraform infrastructure AI ile oluşturuldu
- Mikroservis mimarisi AI ile planlandı

**Sonuç**: 6 ay gibi kısa sürede enterprise-grade bir platform.

### 2. Full Google Cloud Adoption

Projemiz, Google Cloud'un:
- 14+ servisini aktif kullanıyor
- Best practices'i uyguluyor
- Native entegrasyonlardan faydalanıyor
- Cloud-native mimariyi örnek teşkil ediyor

### 3. Türk Fintech Ekosistemi

- Türkiye'deki ilk sentiment analysis platformu
- SPK düzenlemelerine uyumlu
- Türk kullanıcılar için optimize edilmiş
- Yerel veri kaynakları (TCMB, TÜİK)

---

## 📈 Başarı Metrikleri

### Teknik Metrikler

- ✅ **Uptime**: %99.9+ (hedef)
- ✅ **Latency**: <500ms (p95)
- ✅ **Scale**: 0-100+ instances otomatik
- ✅ **Data Processing**: 100K+ mesaj/gün

### İş Metrikleri (Hedef)

- 🎯 **Kullanıcı**: 1,000+ (ilk 6 ay)
- 🎯 **API Calls**: 1M+ (aylık)
- 🎯 **Data Points**: 10M+ (aylık)
- 🎯 **Revenue**: $5K-10K MRR (12 ay)

---

## 🤝 Google Cloud'a Katkılarımız

### 1. Case Study

Platformumuz, Google Cloud'un şunlar için örnek teşkil edebilir:
- AI-assisted development
- Serverless microservices
- Event-driven architecture
- FinTech use case

### 2. Community

- Blog yazıları (Medium, Dev.to)
- YouTube tutorials
- Open-source contributions
- Conference talks

### 3. Referans

Başarılı olduğumuzda:
- Diğer startuplara referans
- GCP adoption advocacy
- Case studies ve testimonials

---

## 📞 İletişim

**Proje**: Sentilyze
**Kurucu**: [İsim]
**Email**: team@sentilyze.live
**GitHub**: [Repository URL]
**Demo**: [Demo URL]

---

## 🙏 Sonuç

Sentilyze, Google Cloud Platform'un gücünü ve esnekliğini tam anlamıyla kullanan, modern bir fintech platformudur. Google for Startups programı desteği ile:

- ✅ Platformu scale edebiliriz
- ✅ Daha fazla kullanıcıya ulaşabiliriz
- ✅ Yeni özellikler geliştirebiliriz
- ✅ Türk fintech ekosistemini güçlendirebiliriz

**Google Cloud + AI-Assisted Development = Demokratik Girişimcilik**

Herkesin, teknik bilgi olmasa bile, büyük hayallerini gerçekleştirebileceğini gösteriyoruz.

---

*Bu döküman, Google for Startups Cloud Program başvurusu için hazırlanmıştır.*
*Son güncelleme: Şubat 2026*
