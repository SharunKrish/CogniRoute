import time
import random
from .base import BaseAIProvider, AIResult

class MockAIProvider(BaseAIProvider):
    def classify(self, message: str) -> AIResult:
        # Sleep to simulate API network latency (1.5 seconds)
        time.sleep(1.5)
        
        msg_lower = message.lower()
        
        # 1. Check for urgent keywords
        urgent_keywords = ['hack', 'exploit', 'leak', 'down', 'broken', 'fire', 'crash', 'critical', 'immediate', 'asap', 'emergency', 'security']
        # 2. Check for support keywords
        support_keywords = ['payment', 'billing', 'charge', 'refund', 'credit card', 'checkout', 'pay', 'subscription', 'account', 'login', 'reset password']
        # 3. Check for sales keywords
        sales_keywords = ['pricing', 'sales', 'quote', 'discount', 'demo', 'contract', 'enterprise', 'partnership', 'buy', 'purchase']
        # 4. Check for spam keywords
        spam_keywords = ['viagra', 'crypto', 'casino', 'lottery', 'win', 'prize', 'free money', 'cheap', 'weight loss', 'rich quick', 'pill']
        
        category = 'other'
        priority = 'low'
        reason = "Message matched standard classification heuristic parameters."
        
        if any(keyword in msg_lower for keyword in urgent_keywords):
            category = 'urgent'
            priority = 'high'
            reason = "Detected critical keywords representing potential outage, data leak, or immediate blocker."
        elif any(keyword in msg_lower for keyword in support_keywords):
            category = 'support'
            priority = 'high' if ('login' in msg_lower or 'reset' in msg_lower or 'billing' in msg_lower) else 'medium'
            reason = "Message indicates a post-purchase issue or account/payment related query requiring support."
        elif any(keyword in msg_lower for keyword in sales_keywords):
            category = 'sales'
            priority = 'medium'
            reason = "Message contains commercial intent or purchase interest related to pricing/demos."
        elif any(keyword in msg_lower for keyword in spam_keywords):
            category = 'spam'
            priority = 'low'
            reason = "High density of typical promotional, high-risk financial, or clickbait keyphrases."
            
        # Summary generation
        summary = message[:80] + "..." if len(message) > 80 else message
        if category == 'urgent':
            summary = f"[CRITICAL] {summary}"
        elif category == 'support':
            summary = f"[SUPPORT] {summary}"
        elif category == 'sales':
            summary = f"[SALES] {summary}"
        elif category == 'spam':
            summary = f"[SPAM] {summary}"
            
        confidence = round(random.uniform(0.78, 0.97), 2)
        
        raw_output = {
            "mocked_response": True,
            "heuristic_category": category,
            "heuristic_priority": priority,
            "confidence_score": confidence,
            "latency_ms": 1500,
        }
        
        return AIResult(
            category=category,
            priority=priority,
            summary=summary,
            confidence=confidence,
            reason=reason,
            raw_output=raw_output
        )
