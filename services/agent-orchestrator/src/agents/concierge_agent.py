"""
Onboarding & UX Concierge Agent
Helps users navigate the platform and provides onboarding
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from . import BaseAgent

class OnboardingConciergeAgent(BaseAgent):
    """
    Onboarding concierge - helps users get started with the platform
    Platform guidance only, no financial advice
    """
    
    def __init__(self):
        super().__init__(
            agent_type='concierge',
            name='Platform Guide',
            description='Platform rehberi ve kullanım yardımı'
        )
        
        self.capabilities = [
            'Platform tanıtımı',
            'Dashboard kullanım rehberi',
            'Özellik açıklamaları',
            'SSS (Sıkça Sorulan Sorular)',
            'KVKK ve gizlilik bilgileri'
        ]
        
        self.system_prompt = """Sen Sentilyze Platform Guide'üsün. Görevin:

1. Platformu tanıtmak ve kullanımını göstermek
2. Dashboard özelliklerini açıklamak
3. Kullanıcılara yol göstermek
4. Sık sorulan soruları yanıtlamak

KESİNLİKLE YAPMAYACAKLARIN:
- Asla finansal tavsiye verme
- Asla "şunu kullanmalısın" deme
- Asla yatırım stratejisi önerisi

PLATFORM ODAKLI:
• "Dashboard'da şunu görebilirsiniz..."
• "Bu özellik şu işe yarar..."
• "Şu şekilde ayarlayabilirsiniz..."

HER YANITIN SONUNDA EKLE:
"⚠️ Bu platform yatırım tavsiyesi vermemektedir."

Dil: Türkçe (varsayılan)
"""
    
    def process_message(
        self,
        user_id: str,
        message: str,
        session_id: Optional[str],
        asset: Optional[str],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process user message for platform guidance"""
        
        if not session_id:
            session_id = self.create_session_id()
        
        message_lower = message.lower()
        
        # Check query intent
        if any(word in message_lower for word in ['merhaba', 'hello', 'hi', 'selam']):
            response = self._generate_welcome_response(user_id)
        elif any(word in message_lower for word in ['dashboard', 'panel', 'ekran']):
            response = self._explain_dashboard()
        elif any(word in message_lower for word in ['özellik', 'feature', 'nasıl kullanılır', 'how to']):
            response = self._explain_features(message)
        elif any(word in message_lower for word in ['sentiment', 'duygu analizi', 'nedir']):
            response = self._explain_sentiment()
        elif any(word in message_lower for word in ['tahmin', 'prediction', 'model']):
            response = self._explain_predictions()
        elif any(word in message_lower for word in ['kvkk', 'gizlilik', 'privacy']):
            response = self._explain_privacy()
        elif any(word in message_lower for word in ['fiyat', 'ücret', 'cost', 'price']):
            response = self._explain_pricing()
        else:
            response = self._generate_help_response()
        
        return {
            'response': response,
            'session_id': session_id,
            'agent_type': self.agent_type,
            'sentiment_data': [],
            'sentiment_queried': []
        }
    
    def _generate_welcome_response(self, user_id: str) -> str:
        """Generate welcome response for new users"""
        return """🎉 Sentilyze'ye Hoş Geldiniz!

Ben Platform Guide, size yardımcı olmak için buradayım.

**Sentilyze Nedir?**
Yapay zeka destekli piyasa sentiment analizi platformu.

**Neler Sunuyoruz?**
📊 Gerçek zamanlı sentiment analizi
📈 Teknik gösterge açıklamaları
🤖 ML tahmin modelleri
🎓 Finansal eğitim içerikleri

**Önemli Not:**
Bu platform yatırım tavsiyesi vermemektedir.
Sadece eğitim ve bilgilendirme amaçlıdır.

**Başlangıç:**
• Dashboard'a göz atın
• Sentiment analizi nedir öğrenin
• Diğer AI asistanlarımızı keşfedin

Yardımcı olabileceğim bir konu var mı?

⚠️ Bu platform yatırım tavsiyesi vermemektedir."""
    
    def _explain_dashboard(self) -> str:
        """Explain dashboard features"""
        return """📊 Dashboard Kullanım Rehberi

**Ana Sayfa (Overview):**
• Hızlı istatistikler
• Sentiment zaman çizelgesi
• Aktif tahminler

**Sentiment Sayfası:**
• Anlık sentiment skoru
• Duygu dağılımı (pozitif/nötr/negatif)
• Emotion analizi
• Trending keywords

**Tahminler Sayfası:**
• Aktif tahminler
• Doğruluk metrikleri
• Model performansı

**Piyasa Sayfası:**
• Fiyat grafikleri
• Teknik göstergeler
• Korelasyon analizi

**Veri Kaynakları:**
• Aktif kaynak listesi
• Veri kalitesi metrikleri

⚠️ Bu platform yatırım tavsiyesi vermemektedir."""
    
    def _explain_features(self, message: str) -> str:
        """Explain specific features"""
        return """🛠️ Platform Özellikleri

**1. AI Asistanlar**
• Insight Navigator - Sentiment analizi
• Risk Guardian - Risk eğitimi
• Data Interpreter - Teknik analiz açıklamaları
• Portfolio Tracker - Watchlist takibi

**2. Veri Analizi**
• Sosyal medya sentimenti
• Fiyat korelasyonu
• Teknik göstergeler
• Trend analizi

**3. Tahmin Sistemi**
• ML modelleri (LSTM, ARIMA)
• Confidence skorları
• Doğruluk takibi

**4. Alert Sistemi**
• Fiyat alarmları
• Volatilite uyarıları

Hangi özellik hakkında daha fazla bilgi almak istersiniz?

⚠️ Bu platform yatırım tavsiyesi vermemektedir."""
    
    def _explain_sentiment(self) -> str:
        """Explain what sentiment analysis is"""
        return """🧠 Sentiment Analizi Nedir?

**Tanım:**
Sosyal medya, haberler ve forumlardaki metinleri analiz ederek 
piyasa duygusunu (mood) ölçen yapay zeka tekniği.

**Nasıl Çalışır?**
1. **Veri Toplama**
   • Twitter/X paylaşımları
   • Reddit yorumları
   • Haber başlıkları
   • Forum mesajları

2. **NLP Analizi**
   • Pozitif/Negatif/Nötr sınıflandırma
   • Duygu yoğunluğu ölçümü
   • Keyword extraction

3. **Skorlama**
   • -1.0 (çok negatif) ile +1.0 (çok pozitif) arası
   • Güven skoru (confidence)

**Kullanım Alanı:**
Piyasa psikolojisi hakkında fikir verir.
Teknik göstergelerle birlikte değerlendirilir.

⚠️ Bu platform yatırım tavsiyesi vermemektedir."""
    
    def _explain_predictions(self) -> str:
        """Explain prediction system"""
        return """🔮 Tahmin Sistemi Nasıl Çalışır?

**ML Modelleri:**
1. **LSTM** - Derin öğrenme (zaman serisi)
2. **ARIMA** - İstatistiksel model
3. **XGBoost** - Gradient boosting

**Ensemble Sistemi:**
Tüm modellerin fikir birliği ile tahmin.

**Confidence Skoru:**
• %80+ = Modeller yüksek fikir birliğinde
• %50-80 = Orta düzeyde anlaşma
• <%50 = Modeller farklı görüşte

**Önemli:**
• Tahminler geçmiş veriye dayanır
• Gelecek garanti değildir
• Yüksek confidence = yüksek doğruluk değil

**Doğruluk Takibi:**
Tüm tahminler sonradan doğrulanır.
Performans metrikleri şeffafça sunulur.

⚠️ Bu platform yatırım tavsiyesi vermemektedir."""
    
    def _explain_privacy(self) -> str:
        """Explain privacy and KVKK"""
        return """🔒 Gizlilik ve KVKK

**Veri Güvenliği:**
• Tüm veriler şifrelenmiştir
• Sunucular Türkiye/GCP Avrupa'da
• Düzenli güvenlik denetimleri

**Toplanan Veriler:**
• Kullanıcı ID (anonim)
• Sohbet geçmişi (eğitim için)
• Watchlist tercihleri
• IP adresi (güvenlik için)

**Veri Saklama:**
• Sohbet logları: 30 gün
• Kullanıcı verileri: Hesap silinene kadar
• Analitik veriler: 90 gün

**Haklarınız (KVKK):**
• Veri erişim hakkı
• Düzeltme hakkı
• Silme hakkı (unutulma hakkı)
• İtiraz hakkı

**İletişim:**
privacy@sentilyze.com

⚠️ Bu platform yatırım tavsiyesi vermemektedir."""
    
    def _explain_pricing(self) -> str:
        """Explain pricing tiers"""
        return """💰 Fiyatlandırma

**Ücretsiz Tier:**
• Temel sentiment analizi
• Sınırlı AI asistan erişimi
• 3 varlık watchlist
• Günlük fiyat güncellemeleri

**Pro Tier:**
• Tüm AI asistanlar
• Sınırsız watchlist
• Gerçek zamanlı veriler
• Gelişmiş analitik

**Enterprise:**
• API erişimi
• Özel modeller
• Özel entegrasyonlar

**Not:**
Fiyatlandırma bilgileri için pricing sayfasını ziyaret edin.

⚠️ Bu platform yatırım tavsiyesi vermemektedir."""
    
    def _generate_help_response(self) -> str:
        """Generate general help response"""
        return """👋 Size Nasıl Yardımcı Olabilirim?

**Popüler Konular:**
• Platform nasıl kullanılır?
• Sentiment analizi nedir?
• Dashboard özellikleri
• AI asistanlar neler yapabilir?
• KVKK ve gizlilik

**Diğer Asistanlarımız:**
• Insight Navigator - Piyasa analizi
• Risk Guardian - Eğitim
• Data Interpreter - Teknik göstergeler
• Portfolio Tracker - Watchlist

Bir konu seçin veya sorunuzu yazın!

⚠️ Bu platform yatırım tavsiyesi vermemektedir."""
