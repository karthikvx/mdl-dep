import pytest
from app.services.pricing_service import LoanPricingService

@pytest.fixture
def pricing_service():
    return LoanPricingService()

def test_calculate_interest_rate_valid_inputs(pricing_service):
    # Test with a standard case
    rate = pricing_service.calculate_interest_rate(200000, 700, 0.3)
    assert rate == 4.5  # base (3.5) + credit_score (1.0)

    # Test another standard case
    rate = pricing_service.calculate_interest_rate(300000, 600, 0.5)
    assert rate == 7.0  # base (3.5) + credit_score (2.0) + dti (1.5)

def test_calculate_interest_rate_invalid_credit_score(pricing_service):
    with pytest.raises(ValueError, match="Credit score must be between 300 and 850"):
        pricing_service.calculate_interest_rate(200000, 200, 0.3)
    with pytest.raises(ValueError, match="Credit score must be between 300 and 850"):
        pricing_service.calculate_interest_rate(200000, 900, 0.3)

def test_calculate_interest_rate_invalid_loan_amount(pricing_service):
    with pytest.raises(ValueError, match="Loan amount must be positive"):
        pricing_service.calculate_interest_rate(-1000, 700, 0.3)
    with pytest.raises(ValueError, match="Loan amount must be positive"):
        pricing_service.calculate_interest_rate(0, 700, 0.3)

def test_calculate_interest_rate_invalid_dti_ratio(pricing_service):
    with pytest.raises(ValueError, match="DTI ratio must be between 0 and 1"):
        pricing_service.calculate_interest_rate(200000, 700, -0.1)
    with pytest.raises(ValueError, match="DTI ratio must be between 0 and 1"):
        pricing_service.calculate_interest_rate(200000, 700, 1.1)
