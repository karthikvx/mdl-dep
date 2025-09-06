import pickle
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import boto3
from prometheus_client import Counter, Histogram

# Prometheus metrics
prediction_requests = Counter('prediction_requests_total', 'Total prediction requests')
prediction_duration = Histogram('prediction_duration_seconds', 'Time spent processing predictions')
model_load_time = Histogram('model_load_time_seconds', 'Time to load ML model')

class DefaultPredictionService:
    def __init__(self):
        self.event_publisher = EventPublisher()
        self.s3_client = boto3.client('s3')
        self.model = None
        self.load_model()
    
    @model_load_time.time()
    def load_model(self):
        """Load pre-trained Random Forest model from S3"""
        try:
            # Download model from S3
            response = self.s3_client.get_object(
                Bucket='mortgage-ml-models',
                Key='random_forest_default_model.pkl'
            )
            model_data = response['Body'].read()
            self.model = pickle.loads(model_data)
            print("Model loaded successfully from S3")
        except Exception as e:
            print(f"Error loading model: {e}")
            # Create a dummy model for demo purposes
            self.model = RandomForestClassifier(n_estimators=100, random_state=42)
            # Generate some dummy training data
            X_dummy = np.random.rand(1000, 8)
            y_dummy = np.random.randint(0, 2, 1000)
            self.model.fit(X_dummy, y_dummy)
            print("Using dummy model for demo")
    
    def prepare_features(self, loan_app: LoanApplication) -> np.ndarray:
        """Prepare features for model prediction"""
        # Feature engineering based on loan application
        ltv = loan_app.loan_amount / loan_app.property_value
        loan_to_income = loan_app.loan_amount / loan_app.annual_income
        down_payment_percent = loan_app.down_payment / loan_app.property_value
        
        # Normalize credit score
        credit_score_norm = (loan_app.credit_score - 300) / (850 - 300)
        
        features = np.array([
            credit_score_norm,
            loan_app.debt_to_income_ratio,
            ltv,
            loan_to_income,
            down_payment_percent,
            loan_app.employment_years / 40,  # Normalize to decades
            loan_app.loan_term / 30,  # Normalize to standard term
            loan_app.loan_amount / 1000000  # Normalize loan amount
        ]).reshape(1, -1)
        
        return features
    
    def categorize_risk(self, probability: float) -> str:
        """Categorize risk based on default probability"""
        if probability < 0.1:
            return "LOW"
        elif probability < 0.25:
            return "MEDIUM"
        elif probability < 0.5:
            return "HIGH"
        else:
            return "VERY_HIGH"
    
    @prediction_duration.time()
    def predict_default_risk(self, loan_app: LoanApplication) -> RiskResult:
        """Predict default risk and return result"""
        prediction_requests.inc()
        start_time = time.time()
        
        features = self.prepare_features(loan_app)
        
        # Get prediction probability
        probabilities = self.model.predict_proba(features)
        default_probability = probabilities[0][1]  # Probability of default (class 1)
        
        # Get prediction confidence (use max probability as confidence)
        confidence = np.max(probabilities)
        
        risk_category = self.categorize_risk(default_probability)
        processing_time = (time.time() - start_time) * 1000
        
        result = RiskResult(
            application_id=loan_app.application_id,
            default_probability=round(default_probability, 4),
            risk_category=risk_category,
            confidence_score=round(confidence, 4),
            processing_time_ms=processing_time
        )
        
        return result