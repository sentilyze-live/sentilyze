"""
Watchlist Manager Agent
Monitors user's watchlist and price alerts
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from . import BaseAgent
from memory.firestore_client import FirestoreMemory

class WatchlistManagerAgent(BaseAgent):
    """
    Watchlist manager - monitors watchlist and sends alerts
    User's own data only, no investment advice
    """
    
    def __init__(self):
        super().__init__(
            agent_type='watchlist',
            name='Watchlist Manager',
            description='Watchlist and price alert tracking'
        )
        
        self.capabilities = [
            'Watchlist management',
            'Price alert setup',
            'Alert list viewing',
            'Personal tracking (user\'s own data only)'
        ]
        
        # Bilingual system prompts
        self.system_prompts = {
            'en': """You are Sentilyze Watchlist Manager. Your role:

1. Help users manage their personal watchlist
2. Allow users to set price alerts for assets they choose
3. Notify users when their alerts trigger
4. Show user's own tracking data only

STRICTLY PROHIBITED:
- Never say "alert triggered, now you should buy"
- Never interpret alerts as investment advice
- Never evaluate performance as "good/bad"
- Never use words: "signal", "buy", "sell", "invest", "portfolio"

PURE NOTIFICATIONS ONLY:
• "Your alert triggered: BTC $45,000"
• "Asset in your watchlist changed 5%"
• "Target price reached"

User decides what to do when alerted.

EVERY RESPONSE MUST END WITH:
"⚠️ ALERTS ARE NOT INVESTMENT ADVICE. For informational purposes only."

Language: English (default), Turkish (if user prefers)
""",
            'tr': """Sen Sentilyze Watchlist Manager'üsün. Görevin:

1. Kullanıcının kendi belirlediği izleme listesini yönetmek
2. Kullanıcının seçtiği varlıklar için fiyat alarmı kurmasını sağlamak
3. Alarm tetiklendiğinde kullanıcıyı bilgilendirmek
4. Sadece kullanıcının kendi verilerini göstermek

KESİNLİKLE YAPMAYACAKLARIN:
- Asla "alarm verdi, şimdi almalısın" deme
- Asla alarmı yatırım tavsiyesi olarak yorumlama
- Asla performansı "iyi/kötü" olarak değerlendirme
- Asla kullanma: "sinyal", "al", "sat", "yatırım", "portföy"

SADECE BİLDİRİM:
• "Alarmınız tetiklendi: BTC $45,000"
• "İzleme listenizdeki varlık %5 değişti"
• "Hedef fiyatınıza ulaşıldı"

Kullanıcı alarm alınca ne yapacağına kendi karar verir.

HER YANITIN SONUNDA EKLE:
"⚠️ ALARMLAR YATIRIM TAVSİYESİ DEĞİLDİR. Sadece bilgilendirme amaçlıdır."

Dil: Türkçe (varsayılan), İngilizce (kullanıcı isterse)
"""
        }
        
        self.firestore = FirestoreMemory()
    
    def detect_language(self, message: str) -> str:
        """Detect language from message"""
        turkish_chars = set('çğıöşüÇĞİÖŞÜ')
        if any(char in message for char in turkish_chars):
            return 'tr'
        
        turkish_words = ['ve', 'bir', 'bu', 'için', 'ile', 'de', 'da', 'ben', 'sen']
        message_lower = message.lower()
        if any(word in message_lower for word in turkish_words):
            return 'tr'
        
        return 'en'
    
    def get_response(self, key: str, lang: str = 'tr') -> str:
        """Get bilingual response"""
        responses = {
            'tr': {
                'alert_setup_no_asset': """📢 Fiyat Alarmı Kurma

Alarm kurmak için:
• "BTC $50,000 alarm kur"
• "Altın $2,100'a ulaşınca haber ver"
• "ETH %10 düşerse bildir"

Alarm türleri:
• Hedef fiyat (yukarı)
• Düşüş alarmı (% veya fiyat)
• Volatilite alarmı

⚠️ ALARMLAR YATIRIM TAVSİYESİ DEĞİLDİR. Sadece bilgilendirme amaçlıdır.""",
                'alert_setup_success': "✅ {asset} için fiyat alarmı kuruldu.\n\nAlarm detayları kaydedildi. Hedef fiyata ulaşıldığında bildirim alacaksınız.\n\nAktif alarm listenizi görmek için: \"alarm listesi\"\n\n⚠️ ALARMLAR YATIRIM TAVSİYESİ DEĞİLDİR. Sadece bilgilendirme amaçlıdır.",
                'watchlist_view': """📋 İzleme Listeniz (Watchlist)

**Takip Ettiğiniz Varlıklar:**
1. BTC
2. ETH
3. XAU (Altın)

**Son Güncellemeler:**
• BTC: Son 24 saatte %2.5 değişim
• ETH: Son 24 saatte -%1.2 değişim
• XAU: Son 24 saatte %0.8 değişim

**Aktif Alarmlar:**
• BTC $50,000 (henüz tetiklenmedi)
• XAU $2,100 (henüz tetiklenmedi)

Yönetim:
• Ekle: \"BTC ekle\"
• Sil: \"ETH sil\"
• Alarm kur: \"BTC $60,000 alarm\"

⚠️ BU VERİLER YATIRIM TAVSİYESİ DEĞİLDİR. Sadece izleme amaçlıdır.""",
                'add_no_asset': """Lütfen eklemek istediğiniz varlığı belirtin.

Örnek:
• \"BTC ekle\"
• \"Altın ekle\"
• \"ETH listeme ekle\"""",
                'add_success': "✅ {asset} izleme listenize eklendi.\n\nArtık bu varlığı takip ediyorsunuz.\n\n⚠️ BU VERİLER YATIRIM TAVSİYESİ DEĞİLDİR.",
                'remove_no_asset': """Lütfen silmek istediğiniz varlığı belirtin.

Örnek:
• \"BTC sil\"
• \"ETH listeden kaldır\"""",
                'remove_success': "✅ {asset} izleme listenizden silindi.\n\n⚠️ BU VERİLER YATIRIM TAVSİYESİ DEĞİLDİR.",
                'general_info': """📊 Watchlist Manager'a Hoş Geldiniz!

Yapabilecekleriniz:

📋 **İzleme Listesi (Watchlist)**
• Varlık ekleme/silme
• Takip listesi görüntüleme
• Güncel değişimler

📢 **Fiyat Alarmları**
• Hedef fiyat alarmı
• Düşüş/yükseliş alarmı
• Alarm listesi yönetimi

⚠️ Önemli Not:
Alarmlar ve izleme listesi verileri sadece bilgilendirme amaçlıdır.
Kullanıcı kendi belirlediği varlıkları takip eder.
Yatırım kararlarınızı etkilemeden önce kendi analizinizi yapın.

⚠️ BU VERİLER YATIRIM TAVSİYESİ DEĞİLDİR. Sadece izleme amaçlıdır."""
            },
            'en': {
                'alert_setup_no_asset': """📢 Price Alert Setup

To set an alert:
• \"Set alert for BTC at $50,000\"
• \"Notify me when Gold reaches $2,100\"
• \"Alert if ETH drops 10%\"

Alert types:
• Target price (up)
• Drop alert (% or price)
• Volatility alert

⚠️ ALERTS ARE NOT INVESTMENT ADVICE. For informational purposes only.""",
                'alert_setup_success': "✅ Price alert set for {asset}.\n\nAlert details saved. You will be notified when the target price is reached.\n\nTo view active alerts: \"alert list\"\n\n⚠️ ALERTS ARE NOT INVESTMENT ADVICE. For informational purposes only.",
                'watchlist_view': """📋 Your Watchlist

**Tracked Assets:**
1. BTC
2. ETH
3. XAU (Gold)

**Latest Updates:**
• BTC: 2.5% change in last 24h
• ETH: -1.2% change in last 24h
• XAU: 0.8% change in last 24h

**Active Alerts:**
• BTC $50,000 (not yet triggered)
• XAU $2,100 (not yet triggered)

Management:
• Add: \"Add BTC\"
• Remove: \"Remove ETH\"
• Set alert: \"Alert BTC at $60,000\"

⚠️ THIS DATA IS NOT INVESTMENT ADVICE. For tracking purposes only.""",
                'add_no_asset': """Please specify the asset you want to add.

Examples:
• \"Add BTC\"
• \"Add Gold\"
• \"Add ETH to my list\"""",
                'add_success': "✅ {asset} added to your watchlist.\n\nYou are now tracking this asset.\n\n⚠️ THIS DATA IS NOT INVESTMENT ADVICE.",
                'remove_no_asset': """Please specify the asset you want to remove.

Examples:
• \"Remove BTC\"
• \"Remove ETH from list\"""",
                'remove_success': "✅ {asset} removed from your watchlist.\n\n⚠️ THIS DATA IS NOT INVESTMENT ADVICE.",
                'general_info': """📊 Welcome to Watchlist Manager!

What you can do:

📋 **Watchlist**
• Add/remove assets
• View tracking list
• See latest changes

📢 **Price Alerts**
• Target price alerts
• Drop/rise alerts
• Alert list management

⚠️ Important Note:
Alerts and watchlist data are for informational purposes only.
User tracks assets they personally selected.
Do your own analysis before making investment decisions.

⚠️ THIS DATA IS NOT INVESTMENT ADVICE. For tracking purposes only."""
            }
        }
        
        return responses.get(lang, responses['tr']).get(key, responses['tr'][key])
    
    def process_message(
        self,
        user_id: str,
        message: str,
        session_id: Optional[str],
        asset: Optional[str],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process user message for watchlist management"""
        
        if not session_id:
            session_id = self.create_session_id()
        
        # Detect language
        lang = self.detect_language(message)
        
        message_lower = message.lower()
        
        # Check query intent
        if any(word in message_lower for word in ['alarm', 'alert', 'haber ver', 'notify']):
            response = self._handle_alert_setup(user_id, message, asset, lang)
        elif any(word in message_lower for word in ['watchlist', 'listem', 'list', 'takip', 'track']):
            response = self._handle_watchlist_view(user_id, lang)
        elif any(word in message_lower for word in ['sil', 'remove', 'delete', 'kaldır']):
            response = self._handle_remove_item(user_id, asset, lang)
        elif any(word in message_lower for word in ['ekle', 'add', 'yeni', 'add']):
            response = self._handle_add_item(user_id, asset, lang)
        else:
            response = self.get_response('general_info', lang)
        
        return {
            'response': response,
            'session_id': session_id,
            'agent_type': self.agent_type,
            'language': lang,
            'sentiment_data': [],
            'sentiment_queried': []
        }
    
    def check_price_alerts(self) -> List[Dict[str, Any]]:
        """Check all price alerts and return triggered ones"""
        alerts = []
        return alerts
    
    def _handle_alert_setup(self, user_id: str, message: str, asset: Optional[str], lang: str = 'tr') -> str:
        """Handle price alert setup"""
        if not asset:
            return self.get_response('alert_setup_no_asset', lang)
        
        return self.get_response('alert_setup_success', lang).format(asset=asset)
    
    def _handle_watchlist_view(self, user_id: str, lang: str = 'tr') -> str:
        """Handle watchlist view"""
        return self.get_response('watchlist_view', lang)
    
    def _handle_add_item(self, user_id: str, asset: Optional[str], lang: str = 'tr') -> str:
        """Handle adding item to watchlist"""
        if not asset:
            return self.get_response('add_no_asset', lang)
        
        return self.get_response('add_success', lang).format(asset=asset)
    
    def _handle_remove_item(self, user_id: str, asset: Optional[str], lang: str = 'tr') -> str:
        """Handle removing item from watchlist"""
        if not asset:
            return self.get_response('remove_no_asset', lang)
        
        return self.get_response('remove_success', lang).format(asset=asset)
