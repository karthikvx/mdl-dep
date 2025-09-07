from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class LoanApplication:
    loan_amount: float
    credit_score: int
    dti_ratio: float
    application_id: Optional[str] = None
    timestamp: Optional[str] = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()
        if not self.application_id:
            import uuid
            self.application_id = str(uuid.uuid4())

@dataclass
class PricingResult:
    application_id: str
    interest_rate: float
    processing_time_ms: float
    timestamp: Optional[str] = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()

@dataclass
class RiskResult:
    application_id: str
    default_risk: bool
    risk_probability: float
    processing_time_ms: float
    timestamp: Optional[str] = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()
