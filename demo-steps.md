# ===============================================
# USAGE EXAMPLE
# ===============================================

# To run pricing service:
# export SERVICE_TYPE=pricing
# export PORT=5000
# python main.py

# To run prediction service:
# export SERVICE_TYPE=prediction  
# export PORT=5001
# python main.py

# To run orchestrator:
# export SERVICE_TYPE=orchestrator
# export PORT=5002
# python main.py

# Test requests:
"""
# Test pricing service
curl -X POST http://localhost:5000/price_loan \
  -H "Content-Type: application/json" \
  -d '{"loan_amount": 250000, "credit_score": 720, "dti_ratio": 0.35}'

# Test prediction service
curl -X POST http://localhost:5001/predict_default \
  -H "Content-Type: application/json" \
  -d '{"loan_amount": 250000, "credit_score": 720, "dti_ratio": 0.35}'

# Test orchestrator (processes both)
curl -X POST http://localhost:5002/process_application \
  -H "Content-Type: application/json" \
  -d '{"loan_amount": 250000, "credit_score": 720, "dti_ratio": 0.35}'
"""