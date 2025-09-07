import time
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from app.models.schemas import LoanApplication, RiskResult

class DefaultPredictionService:
    def __init__(self):
        self.model = self._train_model()
    
    def _train_model(self):
        """Train the default risk model with sample data"""
        # Sample dataset - in production, load from S3 or database
        data = {
            'loan_amount': [200000, 250000, 180000, 300000, 220000, 280000],
            'credit_score': [720, 680, 750, 650, 700, 620],
            'dti_ratio': [0.35, 0.45, 0.30, 0.50, 0.40, 0.55],
            'defaulted': [0, 1, 0, 1, 0, 1]
        }
        df = pd.DataFrame(data)
        
        X = df[['loan_amount', 'credit_score', 'dti_ratio']]
        y = df['defaulted']
        
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X, y)
        return model
    
    def predict_default_risk(self, loan_app: LoanApplication) -> RiskResult:
        """Predict default risk and return structured result"""
        start_time = time.time()
        
        # Prepare features
        features = np.array([[
            loan_app.loan_amount,
            loan_app.credit_score,
            loan_app.dti_ratio
        ]])
        
        # Get prediction and probability
        prediction = self.model.predict(features)[0]
        probabilities = self.model.predict_proba(features)[0]
        risk_probability = probabilities[1]  # Probability of default
        
        processing_time = (time.time() - start_time) * 1000
        
        return RiskResult(
            application_id=loan_app.application_id,
            default_risk=bool(prediction),
            risk_probability=round(risk_probability, 4),
            processing_time_ms=processing_time
        )
