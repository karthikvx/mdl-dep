
# Test training service
curl -X POST http://localhost:5003/train-model

# Check model status
curl http://localhost:5003/model-status

# Test prediction with updated model
curl -X POST http://localhost:5001/predict_default \
  -H "Content-Type: application/json" \
  -d '{
    "loan_amount": 250000,
    "credit_score": 720,
    "dti_ratio": 0.35,
    "property_value": 320000,
    "annual_income": 80000,
    "employment_years": 5
  }'