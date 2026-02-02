"""
Risk & Education Guardian Agent
Monitors market risks and provides financial education
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from . import BaseAgent

class RiskGuardianAgent(BaseAgent):
    """
    Risk monitoring and education agent
    Provides risk warnings and financial literacy content
    """
    
    def __init__(self):
        super().__init__(
            agent_type='risk',
            name='Risk Guardian',
            description='Risk eğitimi ve piyasa uyarıları'
        )
        
        self.capabilities = [
            'Risk eğitimi',
            'Volatilite monitoring',
            'Risk toleransı değerlendirmesi',
            'Finansal okuryazarlık',
            'Portföy çeşitlendirme eğitimi'
        ]
        
        self.system_prompt = """Sen Sentilyze Risk & Education Guardian'üsün. Görevin:

1. Finansal okuryazarlık eğitimi vermek
2. Kripto/altın risklerini açıklamak
3. Risk yönetimi stratejileri öğretmek
4. Yüksek volatilite anlarında uyarmak

KESİNLİKLE YAPMAYACAKLARIN:
- Asla "al", "sat", "yatırım yap" önerileri
- Asla kişisel risk toleransı dışında yönlendirme
- Asla "bu güvenli" veya "bu riskli" deme

EĞİTİM KONULARI:
- Volatilite nedir?
- Diversifikasyon nedir?
- Leverage riskleri
- Duygusal trading (FOMO, panic)
- Kayıp toleransı belirleme

HER YANITIN SONUNDA EKLE:
"⚠️ BU BİLGİLER EĞİTİM AMAÇLIDIR. Kripto varlıklar yüksek risk içerir."

Dil: Türkçe (varsayılan)
"""
        
        self.volatility_threshold = 0.15  # 15% change threshold
    
    def process_message(
        self,
        user_id: str,
        message: str,
        session_id: Optional[str],
        asset: Optional[str],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process user message and return risk/education content"""
        
        if not session_id:
            session_id = self.create_session_id()
        
        message_lower = message.lower()
        
        # Check query intent
        if any(word in message_lower for word in ['eğitim', 'education', 'öğren', 'learn']):
            response = self._generate_education_response(message)
        elif any(word in message_lower for word in ['risk', 'riskli', 'tehlike', 'danger']):
            response = self._generate_risk_response(asset)
        elif any(word in message_lower for word in ['volatilite', 'volatility', 'oynak']):
            response = self._generate_volatility_education()
        elif any(word in message_lower for word in ['diversifikasyon', 'çeşitlendirme', 'spread']):
            response = self._generate_diversification_education()
        else:
            response = self._generate_general_risk_info()
        
        return {
            'response': response,
            'session_id': session_id,
            'agent_type': self.agent_type,
            'sentiment_data': [],
            'sentiment_queried': []
        }
    
    def check_volatility(self) -> List[Dict[str, Any]]:
        """Check market volatility and return alerts"""
        # This would query market data and check for high volatility
        alerts = []
        
        # Example alert structure
        # alerts.append({
        #     'type': 'volatility',
        #     'asset': 'BTC',
        #     'change_24h': 0.18,  # 18%
        #     'severity': 'high',
        #     'message': 'BTC 24 saatte %18 değişim gösterdi'
        # })
        
        return alerts
    
    def _generate_education_response(self, message: str) -> str:
        """Generate education content response"""
        return """📚 Finansal Okuryazarlık Eğitimi

Mevcut eğitim modülleri:

1️⃣ **Kripto Riskleri 101**
   • Volatilite nedir?
   • Neden %20-50 düşebilir?
   • Kayıp toleransı belirleme

2️⃣ **Risk Yönetimi**
   • Diversifikasyon (çeşitlendirme)
   • Pozisyon büyüklüğü
   • Stop-loss stratejileri

3️⃣ **Duygusal Trading**
   • FOMO (Kaçırma korkusu)
   • Panik satışları
   • Sabır ve disiplin

Hangi konu hakkında bilgi almak istersiniz?

⚠️ BU BİLGİLER EĞİTİM AMAÇLIDIR. Kripto varlıklar yüksek risk içerir."""
    
    def _generate_risk_response(self, asset: Optional[str]) -> str:
        """Generate risk explanation response"""
        asset_text = f" {asset}" if asset else ""
        
        return f"""⚠️{asset_text} Risk Faktörleri

Kripto varlıklar ve emtialar aşağıdaki riskleri içerir:

1. **Yüksek Volatilite**
   • 24 saatte %20-50 değişim mümkün
   • Geçmiş veriler geleceği garanti etmez

2. **Regülasyon Riski**
   • Yasal düzenlemeler değişebilir
   • Platformlar kapatılabilir

3. **Likidite Riski**
   • Düşük hacimli varlıklarda satış zorluğu

4. **Teknoloji Riski**
   • Hack saldırıları
   • Cüzdan kaybı

5. **Piyasa Riski**
   • Manipülasyon
   • Balon riski

Önemli: Kaybetmeyi göze alamayacağınız parayla işlem yapmayın.

⚠️ BU BİLGİLER EĞİTİM AMAÇLIDIR. Kripto varlıklar yüksek risk içerir."""
    
    def _generate_volatility_education(self) -> str:
        """Generate volatility education response"""
        return """📊 Volatilite (Oynaklık) Nedir?

**Tanım:**
Bir varlığın fiyatının ne kadar hızlı değiştiğinin ölçüsü.

**Volatilite Seviyeleri:**
• Düşük: Günlük %1-3 değişim
• Orta: Günlük %5-10 değişim
• Yüksek: Günlük %10+ değişim

**Kripto Volatilitesi:**
Kripto varlıklar geleneksel piyasalara göre 10-20 kat daha volatildir.

**Neden Yüksek?**
• Düşük piyasa hacmi
• Spekülasyon
• Duygu odaklı trading
• Leverage kullanımı

**Risk Yönetimi:**
• Yüksek volatilite = yüksek risk
• Pozisyon büyüklüğünü buna göre ayarla
• Panik yapmamaya çalış

⚠️ BU BİLGİLER EĞİTİM AMAÇLIDIR. Kripto varlıklar yüksek risk içerir."""
    
    def _generate_diversification_education(self) -> str:
        """Generate diversification education response"""
        return """🎯 Diversifikasyon (Çeşitlendirme)

**Tanım:**
"Tüm yumurtaları tek sepete koyma" prensibi.

**Neden Önemli?**
• Tek varlık çökse bile portföy zarar görmez
• Risk dağıtımı
• Daha istikrarlı getiri

**Kripto'da Diversifikasyon:**
❌ Yanlış: Sadece BTC
✅ Doğru: BTC, ETH, ve diğerleri

**Aşırı Diversifikasyon:**
Çok fazla varlık da takibi zorlaştırır. 5-10 varlık optimal.

**Not:**
Diversifikasyon kayıpları tamamen önlemez, sadece azaltır.

⚠️ BU BİLGİLER EĞİTİM AMAÇLIDIR. Kripto varlıklar yüksek risk içerir."""
    
    def _generate_general_risk_info(self) -> str:
        """Generate general risk information response"""
        return """🛡️ Risk Guardian'a Hoş Geldiniz!

Size şu konularda yardımcı olabilirim:

📚 **Eğitim**
• Kripto riskleri nedir?
• Volatilite nasıl ölçülür?
• Risk toleransı belirleme
• Finansal okuryazarlık

⚠️ **Risk Uyarıları**
• Yüksek volatilite anları
• Piyasa riskleri
• Regülasyon değişiklikleri

💡 **İpuçları**
• Duygusal trading'den kaçınma
• FOMO yönetimi
• Panik satışları önleme

Ne öğrenmek istersiniz?

⚠️ BU BİLGİLER EĞİTİM AMAÇLIDIR. Kripto varlıklar yüksek risk içerir."""
