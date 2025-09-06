from flask import Flask, request, jsonify
import time
import math
import boto3
from prometheus_client import Counter, Histogram, generate_latest

# Prometheus metrics
pricing_requests = Counter('pricing_requests_total', 'Total pricing requests')
pricing_duration = Histogram('pricing_duration_seconds', 'Time spent processing pricing requests')

class LoanPricingService:
    def __init__(self):
        self.event_publisher = EventPublisher()
        self.dynamodb = boto3.resource('dynamodb')
        self.pricing_table = self.dynamodb.Table('loan-pricing-parameters')
    
    def calculate_interest_rate(self, loan_app: LoanApplication) -> float:
        """Calculate interest rate based on loan parameters"""
        # Base rate from DynamoDB (fast lookup)
        try:
            response = self.pricing_table.get_item(
                Key={'parameter_type': 'base_rate'}
            )
            base_rate = response.get('Item', {}).get('value', 4.5)
        except:
            base_rate = 4.5  # Fallback
        
        # Risk adjustments
        credit_adjustment = 0
        if loan_app.credit_score < 620:
            credit_adjustment = 2.0
        elif loan_app.credit_score < 680:
            credit_adjustment = 1.0
        elif loan_app.credit_score > 750:
            credit_adjustment = -0.5
        
        dti_adjustment = 0
        if loan_app.debt_to_income_ratio > 0.43:
            dti_adjustment = 0.75
        elif loan_app.debt_to_income_ratio > 0.36:
            dti_adjustment = 0.25
        
        # Loan-to-value adjustment
        ltv = (loan_app.loan_amount) / loan_app.property_value
        ltv_adjustment = 0
        if ltv > 0.95:
            ltv_adjustment = 1.0
        elif ltv > 0.90:
            ltv_adjustment = 0.5
        elif ltv < 0.80:
            ltv_adjustment = -0.25
        
        final_rate = base_rate + credit_adjustment + dti_adjustment + ltv_adjustment
        return max(final_rate, 3.0)  # Minimum rate floor
    
    def calculate_monthly_payment(self, principal: float, rate: float, term_months: int) -> float:
        """Calculate monthly payment using standard mortgage formula"""
        monthly_rate = rate / 100 / 12
        if monthly_rate == 0:
            return principal / term_months
        
        payment = principal * (monthly_rate * (1 + monthly_rate) ** term_months) / \
                 ((1 + monthly_rate) ** term_months - 1)
        return payment
    
    @pricing_duration.time()
    def process_pricing(self, loan_app: LoanApplication) -> PricingResult:
        """Process loan pricing and return result"""
        pricing_requests.inc()
        start_time = time.time()
        
        interest_rate = self.calculate_interest_rate(loan_app)
        monthly_payment = self.calculate_monthly_payment(
            loan_app.loan_amount, 
            interest_rate, 
            loan_app.loan_term * 12
        )
        total_interest = (monthly_payment * loan_app.loan_term * 12) - loan_app.loan_amount
        
        processing_time = (time.time() - start_time) * 1000
        
        result = PricingResult(
            application_id=loan_app.application_id,
            interest_rate=round(interest_rate, 3),
            monthly_payment=round(monthly_payment, 2),
            total_interest=round(total_interest, 2),
            processing_time_ms=processing_time
        )
        
        return result
