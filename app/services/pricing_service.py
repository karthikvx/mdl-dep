import time
from app.models.schemas import LoanApplication, PricingResult

class LoanPricingService:
    def __init__(self):
        self.base_rate = 3.5
    
    def calculate_interest_rate(self, loan_amount: float, credit_score: int, dti_ratio: float) -> float:
        """Calculate interest rate based on loan parameters"""
        if not 300 <= credit_score <= 850:
            raise ValueError("Credit score must be between 300 and 850")
        if loan_amount <= 0:
            raise ValueError("Loan amount must be positive")
        if not 0 <= dti_ratio <= 1:
            raise ValueError("DTI ratio must be between 0 and 1")

        risk_premium = 0.0
        
        # Credit score adjustments
        if credit_score < 640:
            risk_premium += 2.0
        elif credit_score < 740:
            risk_premium += 1.0
        
        # DTI ratio adjustments
        if dti_ratio > 0.4:
            risk_premium += 1.5
        
        return self.base_rate + risk_premium
    
    def process_loan_pricing(self, loan_app: LoanApplication) -> PricingResult:
        """Process loan pricing and return structured result"""
        start_time = time.time()
        
        interest_rate = self.calculate_interest_rate(
            loan_app.loan_amount,
            loan_app.credit_score,
            loan_app.dti_ratio
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        return PricingResult(
            application_id=loan_app.application_id,
            interest_rate=round(interest_rate, 3),
            processing_time_ms=processing_time
        )
