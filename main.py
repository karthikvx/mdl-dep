from flask import Flask, request, jsonify
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
metrics = PrometheusMetrics(app)

# Sample mortgage dataset (replace with actual data)
data = {
    'loan_amount': [200000, 250000, 180000, 300000],
    'credit_score': [720, 680, 750, 650],
    'dti_ratio': [0.35, 0.45, 0.30, 0.50],
    'defaulted': [0, 1, 0, 1]
}
df = pd.DataFrame(data)

# Train default risk model
X = df[['loan_amount', 'credit_score', 'dti_ratio']]
y = df['defaulted']
model = RandomForestClassifier()
model.fit(X, y)

# Loan Pricing Function
def calculate_interest_rate(loan_amount, credit_score, dti_ratio):
    base_rate = 3.5  # Base interest rate
    risk_premium = 0.0

    # Adjustments based on credit score
    if credit_score < 640:
        risk_premium += 2.0
    elif credit_score < 740:
        risk_premium += 1.0

    # Adjustments based on DTI ratio
    if dti_ratio > 0.4:
        risk_premium += 1.5

    return base_rate + risk_premium

@app.route('/price_loan', methods=['POST'])
def price_loan():
    try:
        data = request.json
        loan_amount = data['loan_amount']
        credit_score = data['credit_score']
        dti_ratio = data['dti_ratio']

        interest_rate = calculate_interest_rate(loan_amount, credit_score, dti_ratio)
        return jsonify({'interest_rate': interest_rate})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/predict_default', methods=['POST'])
def predict_default():
    try:
        data = request.json
        loan_amount = data['loan_amount']
        credit_score = data['credit_score']
        dti_ratio = data['dti_ratio']

        prediction = model.predict([[loan_amount, credit_score, dti_ratio]])
        return jsonify({'default_risk': bool(prediction[0])})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
