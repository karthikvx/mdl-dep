from flask import request, jsonify
from app.utils.loan_calculator import calculate_interest_rate

def price_loan():
    data = request.json
    loan_amount = data['loan_amount']
    credit_score = data['credit_score']
    dti_ratio = data['dti_ratio']

    interest_rate = calculate_interest_rate(loan_amount, credit_score, dti_ratio)
    return jsonify({'interest_rate': interest_rate})
