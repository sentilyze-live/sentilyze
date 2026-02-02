"""
Data Interpreter Agent
Explains charts, technical indicators, and model outputs
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from . import BaseAgent

class DataInterpreterAgent(BaseAgent):
    """
    Data interpreter - explains technical analysis and charts
    Educational focus, no investment advice
    """
    
    def __init__(self):
        super().__init__(
            agent_type='interpreter',
            name='Data Interpreter',
            description='Teknik göstergeler ve veri açıklamaları'
        )
        
        self.capabilities = [
            'Teknik gösterge açıklamaları',
            'Grafik okuma eğitimi',
            'Model confidence açıklaması',
            'Korelasyon analizi eğitimi',
            'Veri kaynağı açıklamaları'
        ]
        
        self.system_prompt = """Sen Sentilyze Data Interpreter'üsün. Görevin:

1. Teknik göstergeleri açıklamak (nedir, nasıl okunur)
2. Grafikleri eğitim amaçlı yorumlamak
3. Model çıktılarını açıklamak (confidence skoru vb.)
4. Veri kaynaklarını tanımlamak

KESİNLİKLE YAPMAYACAKLARIN:
- Asla "bu alış sinyali" veya "bu satış sinyali" deme
- Asla "fiyat şuraya gider" tahmini yapma
- Asla yatırım stratejisi önerisi

EĞİTİM ODAKLI:
• "RSI şu anlama gelir..."
• "MACD şöyle hesaplanır..."
• "Bu grafikte şunu görüyoruz..."

HER YANITIN SONUNDA EKLE:
"⚠️ BU BİLGİLER EĞİTİM AMAÇLIDIR. Yatırım tavsiyesi değildir."

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
        """Process user message and return data interpretation"""
        
        if not session_id:
            session_id = self.create_session_id()
        
        message_lower = message.lower()
        
        # Check query intent
        if any(word in message_lower for word in ['rsi', 'macd', 'bollinger', 'indicator']):
            response = self._explain_indicator(message)
        elif any(word in message_lower for word in ['confidence', 'güven', 'model']):
            response = self._explain_model_confidence()
        elif any(word in message_lower for word in ['grafik', 'chart', 'grafik']):
            response = self._explain_chart_reading()
        elif any(word in message_lower for word in ['korelasyon', 'correlation']):
            response = self._explain_correlation()
        elif any(word in message_lower for word in ['veri', 'data', 'kaynak', 'source']):
            response = self._explain_data_sources()
        else:
            response = self._generate_general_response()
        
        return {
            'response': response,
            'session_id': session_id,
            'agent_type': self.agent_type,
            'sentiment_data': [],
            'sentiment_queried': []
        }
    
    def _explain_indicator(self, message: str) -> str:
        """Explain technical indicators"""
        
        message_lower = message.lower()
        
        if 'rsi' in message_lower:
            return """📊 RSI (Relative Strength Index) Nedir?

**Tanım:**
Aşırı alım ve aşırı satım bölgelerini gösteren momentum göstergesi.

**Okuma:**
• 70 üzeri: Aşırı alım bölgesi (fiyat yüksek olabilir)
• 30 altı: Aşırı satım bölgesi (fiyat düşük olabilir)
• 50: Nötr bölge

**Formül:**
RSI = 100 - (100 / (1 + RS))
RS = Ortalama kazanç / Ortalama kayıp

**Not:**
RSI tek başına al/sat sinyali değildir. Diğer göstergelerle birlikte değerlendirilmeli.

⚠️ BU BİLGİLER EĞİTİM AMAÇLIDIR. Yatırım tavsiyesi değildir."""
        
        elif 'macd' in message_lower:
            return """📈 MACD (Moving Average Convergence Divergence)

**Tanım:**
Trend takip göstergesi. İki hareketli ortalamanın farkını gösterir.

**Bileşenler:**
• MACD Line: 12 EMA - 26 EMA
• Signal Line: 9 EMA of MACD
• Histogram: MACD - Signal

**Yorumlama:**
• MACD üzeri keserse: Yükseliş momentumu
• MACD altı keserse: Düşüş momentumu
• Histogram genişlerse: Momentum artıyor

**Not:**
MACD trend göstergesidir, yan pazarlarda yanlış sinyal verebilir.

⚠️ BU BİLGİLER EĞİTİM AMAÇLIDIR. Yatırım tavsiyesi değildir."""
        
        elif 'bollinger' in message_lower:
            return """📉 Bollinger Bantları

**Tanım:**
Fiyat volatilitesini gösteren bantlar. Hareketli ortalamanın etrafında 2 standart sapma.

**Bileşenler:**
• Orta Bant: 20 günlük SMA
• Üst Bant: SMA + (2 × Standart Sapma)
• Alt Bant: SMA - (2 × Standart Sapma)

**Yorumlama:**
• Bant daralır: Düşük volatilite (patlama yaklaşıyor olabilir)
• Bant genişler: Yüksek volatilite
• Fiyat üst banda dokunur: Güçlü trend
• Fiyat alt banda dokunur: Zayıf trend

**Not:**
Fiyatın banda dokunması al/sat sinyali değildir.

⚠️ BU BİLGİLER EĞİTİM AMAÇLIDIR. Yatırım tavsiyesi değildir."""
        
        else:
            return """📊 Teknik Göstergeler Rehberi

Mevcut göstergeler:
• RSI - Momentum göstergesi
• MACD - Trend takip
• Bollinger Bantları - Volatilite
• MA (Moving Average) - Ortalama fiyat

Hangi gösterge hakkında bilgi almak istersiniz?

⚠️ BU BİLGİLER EĞİTİM AMAÇLIDIR. Yatırım tavsiyesi değildir."""
    
    def _explain_model_confidence(self) -> str:
        """Explain model confidence scores"""
        return """🎯 Model Confidence Skoru Nedir?

**Tanım:**
Sentilyze'deki ML modellerinin tahmin güvenilirliği ölçüsü.

**Confidence Seviyeleri:**
• %80-100: Çok yüksek güven
• %60-80: Yüksek güven
• %40-60: Orta güven
• %20-40: Düşük güven
• 0-20: Çok düşük güven

**Nasıl Hesaplanır?**
Ensemble model (LSTM + ARIMA + XGBoost) fikir birliği:
• Tüm modeller aynı yönde tahmin ederse → Yüksek confidence
• Modeller farklı tahminlerde bulunursa → Düşük confidence

**Önemli:**
Yüksek confidence ≠ Garanti doğru tahmin
Düşük confidence ≠ Garanti yanlış tahmin

Confidence skoru modelin ne kadar emin olduğunu gösterir, 
garanti etmez.

⚠️ BU BİLGİLER EĞİTİM AMAÇLIDIR. Yatırım tavsiyesi değildir."""
    
    def _explain_chart_reading(self) -> str:
        """Explain chart reading basics"""
        return """📈 Grafik Okuma Temelleri

**Candlestick (Mum) Yapısı:**
• Gövde: Açılış-kapanış fiyat aralığı
• Fitiller: Yüksek-düşük fiyat aralığı
• Yeşil: Kapanış > Açılış (yükseliş)
• Kırmızı: Kapanış < Açılış (düşüş)

**Destek ve Direnç:**
• Destek: Fiyatın altına inmekte zorlandığı seviye
• Direnç: Fiyatın üstüne çıkmakta zorlandığı seviye

**Trend Çizgileri:**
• Yükselen trend: Daha yüksek dipler
• Düşen trend: Daha düşük tepeler
• Yatay trend: Fiyat aralığında hareket

**Not:**
Grafikler geçmiş veriyi gösterir. Geleceği tahmin etmez.

⚠️ BU BİLGİLER EĞİTİM AMAÇLIDIR. Yatırım tavsiyesi değildir."""
    
    def _explain_correlation(self) -> str:
        """Explain correlation analysis"""
        return """🔗 Korelasyon Analizi Nedir?

**Tanım:**
İki varlığın fiyat hareketlerinin ne kadar ilişkili olduğunun ölçüsü.

**Korelasyon Katsayısı:**
• +1.0: Mükemmel pozitif (biri yükselirse diğeri de)
• 0: İlişki yok
• -1.0: Mükemmel negatif (biri yükselirse diğeri düşer)

**Örnekler:**
• BTC-ETH: Genellikle +0.7 ile +0.9 arası
• XAU-USD: Genellikle -0.6 ile -0.8 arası (ters)
• BTC-XAU: Genellikle +0.3 ile +0.5 arası

**Not:**
Korelasyon nedensellik değildir.
Sadece hareketlerin benzerliğini gösterir.

⚠️ BU BİLGİLER EĞİTİM AMAÇLIDIR. Yatırım tavsiyesi değildir."""
    
    def _explain_data_sources(self) -> str:
        """Explain data sources"""
        return """📡 Veri Kaynaklarımız

**Fiyat Verileri:**
• CoinMarketCap (Kripto)
• GoldAPI (Altın)
• Finnhub (Emtia)

**Sosyal Medya:**
• Twitter/X API
• Reddit API
• CryptoPanic
• LunarCrush

**Haber:**
• NewsAPI
• RSS Feed'ler
• Finnhub

**Güncelleme Sıklığı:**
• Fiyat: Her 5 dakika (kripto), 15 dk (altın)
• Sosyal: Gerçek zamanlı
• Haber: Her saat

**Veri Kalitesi:**
Tüm veriler çoklu kaynaktan doğrulanır.
Yanlış/outlier veriler filtrelenir.

⚠️ BU BİLGİLER EĞİTİM AMAÇLIDIR. Yatırım tavsiyesi değildir."""
    
    def _generate_general_response(self) -> str:
        """Generate general response"""
        return """🎓 Data Interpreter'a Hoş Geldiniz!

Size şunları açıklayabilirim:

📊 **Teknik Göstergeler**
• RSI, MACD, Bollinger nedir?
• Nasıl hesaplanır?
• Ne anlama gelir?

🤖 **Model Açıklamaları**
• Confidence skoru nedir?
• Ensemble model nasıl çalışır?
• Prediction doğruluğu

📈 **Grafik Eğitimi**
• Mum grafikleri nasıl okunur?
• Trend çizgileri
• Destek/direnç

🔗 **Korelasyon**
• Korelasyon nedir?
• Nasıl yorumlanır?

Ne öğrenmek istersiniz?

⚠️ BU BİLGİLER EĞİTİM AMAÇLIDIR. Yatırım tavsiyesi değildir."""
