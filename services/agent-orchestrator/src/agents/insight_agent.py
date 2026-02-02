"""
Insight Navigator Agent
Provides market sentiment analysis without giving investment advice
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from . import BaseAgent
from utils.bigquery_client import BigQueryClient

class InsightNavigatorAgent(BaseAgent):
    """
    Market insight navigator - analyzes sentiment and trends
    Never provides investment advice
    """
    
    def __init__(self):
        super().__init__(
            agent_type='insight',
            name='Insight Navigator',
            description='Piyasa sentimenti ve trend analizi sunar'
        )
        
        self.capabilities = [
            'Sosyal medya sentiment analizi',
            'Trend takibi',
            'Teknik gösterge açıklamaları',
            'Hacim analizi',
            'Korelasyon analizi'
        ]
        
        self.system_prompt = """Sen Sentilyze Insight Navigator'üsün. Görevin:

1. Kripto/altın piyasalarının sentiment (duygu) analizini sunmak
2. Sosyal medya trendlerini ve hacimleri göstermek
3. Teknik göstergeleri açıklamak (nedir, nasıl okunur)
4. Tarihsel verilere dayalı istatistikler sunmak

KESİNLİKLE YAPMAYACAKLARIN:
- Asla "al", "sat", "tavsiye", "öneri" kelimeleri kullanma
- Asla hedef fiyat verme
- Asla portföy önerisi yapma
- Asla "şimdi yatırım zamanı" deme

HER YANITIN SONUNDA EKLE:
"⚠️ BU BİLGİLER YATIRIM TAVSİYESİ DEĞİLDİR. Kripto varlıklar yüksek risk içerir."

Kullanıcı "ne almalıyım?" veya "satmalı mıyım?" gibi sorular sorarsa:
"Bu platform yatırım tavsiyesi vermemektedir. Sadece piyasa verilerini görüntülerim."

Dil: Türkçe (varsayılan), İngilizce (kullanıcı isterse)
"""
        
        self.bigquery = BigQueryClient()
    
    def process_message(
        self,
        user_id: str,
        message: str,
        session_id: Optional[str],
        asset: Optional[str],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process user message and return sentiment analysis"""
        
        if not session_id:
            session_id = self.create_session_id()
        
        # Extract asset from message if not provided
        if not asset:
            asset = self._extract_asset(message)
        
        # Get sentiment data from BigQuery
        sentiment_data = []
        sentiment_queried = []
        
        if asset:
            sentiment_data = self._get_sentiment_data(asset)
            sentiment_queried.append(asset)
        
        # Generate response based on query type
        response = self._generate_response(message, asset, sentiment_data)
        
        return {
            'response': response,
            'session_id': session_id,
            'agent_type': self.agent_type,
            'sentiment_data': sentiment_data,
            'sentiment_queried': sentiment_queried
        }
    
    def _extract_asset(self, message: str) -> Optional[str]:
        """Extract asset symbol from message"""
        assets = {
            'btc': 'BTC', 'bitcoin': 'BTC', 'bitcoin': 'BTC',
            'eth': 'ETH', 'ethereum': 'ETH',
            'xau': 'XAU', 'altın': 'XAU', 'gold': 'XAU', 'ons': 'XAU',
            'sol': 'SOL', 'solana': 'SOL',
            'ada': 'ADA', 'cardano': 'ADA',
        }
        
        message_lower = message.lower()
        for key, symbol in assets.items():
            if key in message_lower:
                return symbol
        
        return None
    
    def _get_sentiment_data(self, asset: str) -> List[Dict[str, Any]]:
        """Query sentiment data from BigQuery"""
        try:
            return self.bigquery.get_latest_sentiment(asset)
        except Exception as e:
            print(f"Error fetching sentiment data: {e}")
            return []
    
    def _generate_response(
        self,
        message: str,
        asset: Optional[str],
        sentiment_data: List[Dict[str, Any]]
    ) -> str:
        """Generate response based on query type"""
        
        message_lower = message.lower()
        
        # Check query intent
        if any(word in message_lower for word in ['nasıl', 'how', 'durum', 'status']):
            return self._generate_status_response(asset, sentiment_data)
        
        elif any(word in message_lower for word in ['sentiment', 'duygu', 'mood']):
            return self._generate_sentiment_response(asset, sentiment_data)
        
        elif any(word in message_lower for word in ['trend', 'artış', 'düşüş', 'volume', 'hacim']):
            return self._generate_trend_response(asset, sentiment_data)
        
        else:
            # General response
            return self._generate_general_response(asset, sentiment_data)
    
    def _generate_status_response(
        self,
        asset: Optional[str],
        sentiment_data: List[Dict[str, Any]]
    ) -> str:
        """Generate current status response"""
        
        if not asset:
            return """Merhaba! Sentiment analizi için bir varlık belirtin. Örneğin:
- "BTC durumu"
- "Altın nasıl?"
- "ETH sentimenti"

⚠️ BU BİLGİLER YATIRIM TAVSİYESİ DEĞİLDİR."""
        
        if not sentiment_data:
            return f"""{asset} için güncel sentiment verisi bulunmamaktadır.

⚠️ BU BİLGİLER YATIRIM TAVSİYESİ DEĞİLDİR. Kripto varlıklar yüksek risk içerir."""
        
        latest = sentiment_data[0]
        
        return f"""📊 {asset} Sentiment Özeti

• Sentiment Skoru: {latest.get('sentiment_score', 'N/A')}
• Duygu: {latest.get('sentiment_label', 'N/A')}
• Güven Oranı: {latest.get('confidence', 'N/A')}%
• Son Güncelleme: {latest.get('timestamp', 'N/A')}

Son 24 saatte sosyal medyada {asset} hakkında {latest.get('mention_count', 'N/A')} paylaşım analiz edildi.

⚠️ BU BİLGİLER YATIRIM TAVSİYESİ DEĞİLDİR. Kripto varlıklar yüksek risk içerir."""
    
    def _generate_sentiment_response(
        self,
        asset: Optional[str],
        sentiment_data: List[Dict[str, Any]]
    ) -> str:
        """Generate sentiment analysis response"""
        
        if not asset:
            return """Sentiment skoru -1.0 (çok negatif) ile +1.0 (çok pozitif) arasında değişir:

• +0.75 ile +1.0: Güçlü pozitif
• +0.25 ile +0.75: Pozitif
• -0.25 ile +0.25: Nötr
• -0.75 ile -0.25: Negatif
• -1.0 ile -0.75: Güçlü negatif

⚠️ BU BİLGİLER YATIRIM TAVSİYESİ DEĞİLDİR."""
        
        return f"""{asset} için sentiment verileri analiz ediliyor...

[SENTIMENT VERİLERİ BURADA]

⚠️ BU BİLGİLER YATIRIM TAVSİYESİ DEĞİLDİR. Kripto varlıklar yüksek risk içerir."""
    
    def _generate_trend_response(
        self,
        asset: Optional[str],
        sentiment_data: List[Dict[str, Any]]
    ) -> str:
        """Generate trend analysis response"""
        
        return f"""📈 {asset or 'Genel'} Trend Analizi

Son 7 günün sentiment trendi:
[GRAFİK VERİSİ]

Not: Trend analizi geçmiş verilere dayanır. Gelecek performans garanti edilmez.

⚠️ BU BİLGİLER YATIRIM TAVSİYESİ DEĞİLDİR. Kripto varlıklar yüksek risk içerir."""
    
    def _generate_general_response(
        self,
        asset: Optional[str],
        sentiment_data: List[Dict[str, Any]]
    ) -> str:
        """Generate general response"""
        
        return """Merhaba! Ben Insight Navigator. Size şunları sunabilirim:

📊 Sentiment Analizi
• Sosyal medya duygu analizi
• Trend takibi
• Hacim analizi

📚 Eğitim
• Sentiment skoru nasıl okunur?
• Teknik göstergeler nedir?
• Korelasyon analizi

Hangi varlık hakkında bilgi almak istersiniz?

⚠️ BU BİLGİLER YATIRIM TAVSİYESİ DEĞİLDİR. Kripto varlıklar yüksek risk içerir."""
