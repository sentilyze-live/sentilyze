# Sentilyze - Döküman Merkezi / Documentation Center

---

## 📚 Genel Bakış / Overview

Bu klasör, **Sentilyze** projesinin tüm teknik ve stratejik dökümanlarını içermektedir.

This folder contains all technical and strategic documentation for the **Sentilyze** project.

---

## 📁 Döküman Yapısı / Documentation Structure

### 1. 🎤 Pitch Dökümanları / Pitch Documents

**Klasör / Folder**: `pitch/`

Kullanıcılar ve paydaşlar için basit, sade ve anlaşılır bilgilendirici dökümanlar.

Simple, clear, and informative documents for users and stakeholders.

| Döküman | Dil / Language | Açıklama / Description |
|---------|----------------|------------------------|
| `ABOUT_TR.md` | 🇹🇷 Türkçe | Kullanıcılar için platform tanıtımı |
| `ABOUT_EN.md` | 🇬🇧 English | Platform introduction for users |

**İçerik / Contents**:
- Ne yapıyoruz? / What we do
- Problem ve çözüm / Problem and solution
- Özellikler / Features
- Kullanıcı deneyimi / User experience
- Fiyatlandırma / Pricing
- Yasal uyarı / Legal disclaimer

---

### 2. 🔧 Teknik Dökümanlar / Technical Documents

**Klasör / Folder**: `technical/`

Detaylı teknik mimari, tech stack ve workflow dökümanları.

Detailed technical architecture, tech stack, and workflow documentation.

| Döküman | Dil / Language | Açıklama / Description |
|---------|----------------|------------------------|
| `TECH_STACK_TR.md` | 🇹🇷 Türkçe | Tam teknik stack ve mimari analizi |
| `TECH_STACK_EN.md` | 🇬🇧 English | Complete tech stack and architecture analysis |

**İçerik / Contents**:
- Teknoloji yığını / Technology stack
- Mikroservis mimarisi / Microservices architecture
- Event-driven design / Event-driven design
- Veri akışı / Data flow
- Altyapı detayları / Infrastructure details
- Ölçeklenebilirlik / Scalability
- Güvenlik / Security

---

### 3. ☁️ Google Cloud Platform Dökümanları / GCP Documents

**Klasör / Folder**: `google-startup/`

Google for Startups Cloud Program başvurusu için hazırlanmış detaylı GCP kullanım dökümanları.

Detailed GCP usage documentation prepared for Google for Startups Cloud Program application.

| Döküman | Dil / Language | Açıklama / Description |
|---------|----------------|------------------------|
| `GCP_USAGE_TR.md` | 🇹🇷 Türkçe | GCP servisleri kullanım analizi |
| `GCP_USAGE_EN.md` | 🇬🇧 English | GCP services usage analysis |

**İçerik / Contents**:
- 14+ GCP servisi detaylı kullanımı
- Maliyet analizi ve projeksiyon
- Neden Google Cloud seçtik?
- Gelecek planları
- Startup kredisi başvuru gerekçesi
- AI-assisted development hikayesi

**Kullanılan GCP Servisleri / GCP Services Used**:
- ✅ Cloud Run (8 mikroservis)
- ✅ Cloud Pub/Sub (7 topic)
- ✅ BigQuery (7 tablo, 4 view)
- ✅ Cloud SQL (PostgreSQL)
- ✅ Firestore
- ✅ Secret Manager (17 secret)
- ✅ Cloud Build (CI/CD)
- ✅ Artifact Registry
- ✅ Cloud Storage (3 bucket)
- ✅ Cloud Scheduler
- ✅ Cloud Logging
- ✅ Cloud Monitoring
- ✅ Cloud Trace
- ✅ Vertex AI

---

### 4. 🎨 Frontend Tasarım Rehberi / Frontend Design Guide

**Klasör / Folder**: `frontend-guide/`

Adım adım frontend UI tasarlama ve geliştirme rehberi.

Step-by-step frontend UI design and development guide.

| Döküman | Dil / Language | Açıklama / Description |
|---------|----------------|------------------------|
| `FRONTEND_GUIDE_TR.md` | 🇹🇷 Türkçe | Frontend geliştirme rehberi |
| `FRONTEND_GUIDE_EN.md` | 🇬🇧 English | Frontend development guide |

**İçerik / Contents**:
- Tasarım felsefesi / Design philosophy
- Next.js 14 + TypeScript + Tailwind CSS
- shadcn/ui komponent kütüphanesi
- Sayfa yapıları ve layoutlar
- Responsive tasarım
- Renk paleti ve tipografi
- Animasyonlar / Animations
- Veri görselleştirme / Data visualization
- Adım adım implementasyon kodu

**Komponentler / Components**:
- Landing page
- Dashboard (Gold & Crypto)
- Analysis page
- Admin panel
- Custom components (SentimentGauge, PriceCard, NewsItem)

---

## 🎯 Döküman Kullanım Alanları / Document Use Cases

### 1. Yatırımcı Sunumları / Investor Presentations

**Kullanılacak Dökümanlar / Documents to Use**:
- `pitch/ABOUT_*.md` - Ürün tanıtımı
- `google-startup/GCP_USAGE_*.md` - Teknik yetkinlik
- `technical/TECH_STACK_*.md` - Mimari derinlik

### 2. Google for Startups Başvurusu / Google for Startups Application

**Kullanılacak Dökümanlar / Documents to Use**:
- `google-startup/GCP_USAGE_*.md` ⭐ (Ana döküman / Main document)
- `technical/TECH_STACK_*.md` (Ek bilgi / Additional info)

### 3. Geliştirici Onboarding / Developer Onboarding

**Kullanılacak Dökümanlar / Documents to Use**:
- `technical/TECH_STACK_*.md` (Backend)
- `frontend-guide/FRONTEND_GUIDE_*.md` (Frontend)

### 4. Kullanıcı Bilgilendirme / User Information

**Kullanılacak Dökümanlar / Documents to Use**:
- `pitch/ABOUT_*.md`

---

## 💡 Öne Çıkan Noktalar / Highlights

### 🤖 AI-Assisted Development

Tüm proje, **kodlama bilgisi olmayan bir girişimci tarafından, tamamen yapay zeka desteği ile** geliştirilmiştir:

The entire project was developed **by an entrepreneur without coding knowledge, entirely with AI assistance**:

- ✅ 8 mikroservis (Python/FastAPI)
- ✅ Frontend (Next.js/TypeScript)
- ✅ Infrastructure (Terraform)
- ✅ 6 ayda enterprise-grade platform / Enterprise-grade platform in 6 months

### ☁️ Full Google Cloud Adoption

- 14+ GCP servisi aktif kullanımda / 14+ GCP services actively used
- Event-driven mikroservis mimarisi / Event-driven microservices architecture
- %99.9+ uptime hedefi / 99.9%+ uptime target
- Scale-to-zero maliyet optimizasyonu / Scale-to-zero cost optimization

### 📊 Data-Driven Platform

- 100K+ mesaj/gün işleme / 100K+ messages/day processing
- Real-time sentiment analizi / Real-time sentiment analysis
- BigQuery ile petabayt ölçeğinde analiz / Petabyte-scale analysis with BigQuery
- ML-powered predictions / ML-powered predictions

---

## 📈 Metrikler ve Hedefler / Metrics and Goals

### Teknik Metrikler / Technical Metrics

- ✅ **Uptime**: %99.9+ (hedef / target)
- ✅ **Latency**: <500ms (p95)
- ✅ **Scale**: 0-100+ instances (otomatik / automatic)
- ✅ **Data Processing**: 100K+ mesaj/gün / messages/day

### İş Hedefleri / Business Goals (6-12 ay / months)

- 🎯 **Kullanıcı / Users**: 1,000+
- 🎯 **API Calls**: 1M+ (aylık / monthly)
- 🎯 **Data Points**: 10M+ (aylık / monthly)
- 🎯 **Revenue**: $5K-10K MRR

---

## 🚀 Gelecek Roadmap / Future Roadmap

### Kısa Vade / Short Term (3 ay / months)
- [ ] LSTM model implementation
- [ ] WebSocket real-time updates
- [ ] Mobile app API
- [ ] Cloud Functions integration

### Orta Vade / Medium Term (6 ay / months)
- [ ] Hisse senedi entegrasyonu / Stock market integration
- [ ] Memorystore (Redis) caching
- [ ] Multi-region deployment
- [ ] A/B testing framework

### Uzun Vade / Long Term (12 ay / months)
- [ ] Apache Beam real-time streaming
- [ ] Advanced ML models (Transformers)
- [ ] Algorithmic trading API
- [ ] Community features

---

## 📞 İletişim / Contact

**Proje / Project**: Sentilyze
**Email**: team@sentilyze.live
**Web**: [sentilyze.live](https://sentilyze.live) *(yakında / coming soon)*

---

## 📜 Lisans / License

MIT License - Detaylar için root dizindeki LICENSE dosyasına bakın.

MIT License - See LICENSE file in root directory for details.

---

## 🙏 Teşekkürler / Acknowledgments

- **Google Cloud Platform**: Enterprise-grade infrastructure
- **Hugging Face**: NLP models
- **Next.js & Vercel**: Modern web framework
- **OpenAI**: Development assistance
- **Claude (Anthropic)**: AI-powered development support

---

## 📝 Döküman Versiyonları / Document Versions

| Döküman / Document | Versiyon / Version | Son Güncelleme / Last Update |
|-------------------|-------------------|------------------------------|
| ABOUT_*.md | 1.0 | Şubat 2026 / February 2026 |
| TECH_STACK_*.md | 4.0 | Şubat 2026 / February 2026 |
| GCP_USAGE_*.md | 1.0 | Şubat 2026 / February 2026 |
| FRONTEND_GUIDE_*.md | 1.0 | Şubat 2026 / February 2026 |

---

## 🔄 Döküman Güncellemeleri / Document Updates

Bu dökümanlar **canlı dokümanlardır** ve proje ilerledikçe düzenli olarak güncellenir.

These documents are **living documents** and are regularly updated as the project progresses.

Öneriler için / For suggestions:
- Issue açın / Open an issue
- Pull request gönderin / Submit a pull request
- team@sentilyze.live adresine email gönderin / Send email to team@sentilyze.live

---

*Bu döküman merkezi Sentilyze projesinin tüm stratejik ve teknik dökümanlarını içermektedir.*

*This documentation center contains all strategic and technical documents for the Sentilyze project.*

**Son Güncelleme / Last Updated**: Şubat 2026 / February 2026
