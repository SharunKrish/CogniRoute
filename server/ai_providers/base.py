from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class AIResult:
    category: str  # sales, support, urgent, spam, other
    priority: str  # low, medium, high
    summary: str
    confidence: float
    reason: str
    raw_output: Dict[str, Any]


class BaseAIProvider(ABC):
    @abstractmethod
    def classify(self, message: str) -> AIResult:
        """
        Classifies the customer message and returns an AIResult.
        """
        pass
