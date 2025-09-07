import pytest
import requests

@pytest.fixture
def client():
    from app import app
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_price_loan(client):
    response = client.post('/price_loan', json={
        'loan_amount': 200000,
        'credit_score': 720,
        'dti_ratio': 0.35
    })
    data = response.get_json()
    assert 'interest_rate' in data
    assert response.status_code == 200

def test_predict_default(client):
    response = client.post('/predict_default', json={
        'loan_amount': 200000,
        'credit_score': 720,
        'dti_ratio': 0.35
    })
    data = response.get_json()
    assert 'default_risk' in data
    assert response.status_code == 200
