import pytest
from app.api.pricing_api import app as pricing_app

@pytest.fixture
def client():
    pricing_app.config['TESTING'] = True
    with pricing_app.test_client() as client:
        yield client

def test_price_loan(client):
    # This test will fail because the endpoint is /pricing/calculate, not /price_loan
    # and the payload is different.
    # I will fix this test to reflect the actual API.
    response = client.post('/pricing/calculate', json={
        'loan_amount': 200000,
        'credit_score': 720,
        'applicant_income': 80000,
        'property_value': 250000
    })
    data = response.get_json()
    assert 'interest_rate' in data
    assert response.status_code == 200
