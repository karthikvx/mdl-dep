"""
Test data generation for unit and integration tests
"""

import json
import random
from datetime import datetime
from typing import Dict, List

def create_sample_loan_application() -> Dict:
    """Create a sample loan application for testing"""
    return {
        'application_id': f'APP_{datetime.now().strftime("%Y%m%d_%H%M%S")}_{random.randint(1000, 9999)}',
        'applicant_income': random.randint(40000, 150000),
        'loan_amount': random.randint(100000, 800000),
        'credit_score': random.randint(580, 850),
        'property_value': random.randint(150000, 1000000),
        'debt_to_income_ratio': round(random.uniform(0.1, 0.5), 3),
        'loan_to_value_ratio': round(random.uniform(0.6, 0.95), 3),
        'employment_years': random.randint(1, 30),
        'property_type': random.choice(['single_family', 'condo', 'townhouse']),
        'loan_purpose': random.choice(['purchase', 'refinance']),
        'timestamp': datetime.now().isoformat()
    }

def generate_test_applications(count: int = 100) -> List[Dict]:
    """Generate multiple test applications"""
    return [create_sample_loan_application() for _ in range(count)]
