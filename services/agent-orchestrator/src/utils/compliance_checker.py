"""
Compliance Checker Module
Ensures all agent responses comply with Turkish regulations
Prevents investment advice while allowing educational content
"""

import re
from typing import Tuple, List

class ComplianceChecker:
    """Checks user input and AI output for compliance with financial regulations"""
    
    # Forbidden keywords that indicate investment advice requests or responses
    FORBIDDEN_KEYWORDS = [
        # Turkish - Yatırım Tavsiyesi
        'al', 'sat', 'tavsiye', 'öneri', 'yatırım yap', 'portföyüne ekle',
        'portföy oluştur', 'portföy yönetimi', 'portföy yapılandırma',
        'hedef fiyat', 'kâr realizasyonu', 'zararına sat', 'alsam', 'satsam',
        'tutmalıyım', 'silmeliyim', 'girmeli', 'çıkmalı', 'pozisyon aç',
        'pozisyon kapat', 'long', 'short', 'emir ver', 'alım', 'satım',
        # Turkish - Sinyal ve Danışmanlık (KRİTİK RİSK)
        'sinyal', 'signal', 'al sinyali', 'sat sinyali', 'tetikle', 'trigger',
        'robo-advisor', 'robo advisor', 'danışmanlık', 'danismanlik', 'advisory',
        'yönlendirme', 'yonlendirme', 'yönlendir', 'yonlendir', 'tahmin', 'kehanet',
        'future price', 'gelecek fiyat', 'fiyat tahmini', 'price prediction',
        # English - Investment Advice
        'buy', 'sell', 'invest', 'recommendation', 'advice', 'should i',
        'target price', 'take profit', 'stop loss', 'position', 'long',
        'short', 'order', 'enter', 'exit', 'hold', 'portfolio', 'portfolio management',
        # English - Signal and Advisory (CRITICAL RISK)
        'signal', 'buy signal', 'sell signal', 'trigger', 'robo-advisor',
        'robo advisor', 'financial advisory', 'investment advisory', 'guidance',
        'direction', 'prediction', 'forecast', 'price target', 'guaranteed',
    ]
    
    # Risk warning keywords that must trigger additional warnings
    HIGH_RISK_KEYWORDS = [
        'kar', 'profit', 'kazanç', 'gain', 'yükseliş', 'düşüş',
        'bullish', 'bearish', 'pump', 'dump', 'moon'
    ]
    
    # Safe educational keywords
    SAFE_KEYWORDS = [
        'nedir', 'nasıl', 'eğitim', 'bilgi', 'açıklama',
        'what is', 'how to', 'education', 'information', 'explain'
    ]
    
    def __init__(self):
        self.violation_count = 0
    
    def check_input(self, user_message: str) -> Tuple[bool, str]:
        """
        Check if user message is asking for investment advice
        
        Returns:
            (is_safe, reason): True if safe, False if blocked with reason
        """
        message_lower = user_message.lower()
        
        # Check for direct investment questions
        investment_patterns = [
            r'(ne|hangi).*?(almalı|satmalı).*',
            r'(alsam|satsam|tutsam).*',
            r'yatırım.*?(tavsiye|öneri|danışmanlık)',
            r'portföy.*?(oluştur|yapılandır)',
        ]
        
        for pattern in investment_patterns:
            if re.search(pattern, message_lower):
                return False, "Yatırım tavsiyesi/önerisi isteği"
        
        # Check for forbidden keywords
        found_keywords = []
        for keyword in self.FORBIDDEN_KEYWORDS:
            if keyword in message_lower:
                found_keywords.append(keyword)
        
        if found_keywords:
            return False, f"Yasak kelime tespit edildi: {', '.join(found_keywords[:3])}"
        
        return True, "OK"
    
    def check_output(self, ai_response: str) -> str:
        """
        Check and clean AI response
        
        Returns:
            Cleaned response or safe fallback if violations found
        """
        response_lower = ai_response.lower()
        
        # Check for forbidden keywords in response
        found_violations = []
        for keyword in self.FORBIDDEN_KEYWORDS:
            if keyword in response_lower:
                found_violations.append(keyword)
        
        if found_violations:
            self.violation_count += 1
            return self.get_safe_fallback()
        
        # Check if response contains high-risk statements without warnings
        has_high_risk = any(keyword in response_lower for keyword in self.HIGH_RISK_KEYWORDS)
        has_warning = '⚠️' in ai_response or 'risk' in response_lower or 'sorumluluk' in response_lower
        
        if has_high_risk and not has_warning:
            # Add warning if missing
            ai_response += "\n\n⚠️ UYARI: Bu bilgiler geçmiş verilere dayanmaktadır. Gelecek performans garanti edilmez."
        
        return ai_response
    
    def get_safe_fallback(self, lang='tr') -> str:
        """Return safe fallback response when violations detected (Bilingual)"""
        
        messages = {
            'tr': """⚠️ Bu platform yatırım tavsiyesi vermemektedir.

Sentilyze, sosyal medya metinlerini analiz eden bir piyasa araştırma aracıdır.
Finansal analiz veya yatırım danışmanlığı değildir.

Yatırım kararlarınızı vermeden önce lisanslı bir finansal danışmana başvurun.

⚠️ Kripto varlıklar yüksek risk içerir. Kaybetmeyi göze alamayacağınız parayla işlem yapmayın.

---

⚠️ This platform does not provide investment advice.

Sentilyze is a market research tool that analyzes social media texts.
It is not financial analysis or investment advisory.

Consult a licensed financial advisor before making investment decisions.

⚠️ Crypto assets carry high risk. Do not trade with money you cannot afford to lose.""",
            'en': """⚠️ This platform does not provide investment advice.

Sentilyze is a market research tool that analyzes social media texts.
It is not financial analysis or investment advisory.

Consult a licensed financial advisor before making investment decisions.

⚠️ Crypto assets carry high risk. Do not trade with money you cannot afford to lose.

---

⚠️ Bu platform yatırım tavsiyesi vermemektedir.

Sentilyze, sosyal medya metinlerini analiz eden bir piyasa araştırma aracıdır.
Finansal analiz veya yatırım danışmanlığı değildir.

Yatırım kararlarınızı vermeden önce lisanslı bir finansal danışmana başvurun.

⚠️ Kripto varlıklar yüksek risk içerir."""
        }
        
        return messages.get(lang, messages['tr'])
    
    def get_stats(self) -> dict:
        """Get compliance checking statistics"""
        return {
            'violation_count': self.violation_count,
            'forbidden_keywords_count': len(self.FORBIDDEN_KEYWORDS)
        }
