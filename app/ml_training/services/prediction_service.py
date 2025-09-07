import boto3
import pickle
import numpy as np
import json
import time
from datetime import datetime, timedelta
from app.models.schemas import LoanApplication, RiskResult
import logging

logger = logging.getLogger(__name__)

class DefaultPredictionService:
    def __init__(self, s3_bucket='mortgage-ml-models'):
        self.s3_client = boto3.client('s3')
        self.s3_bucket = s3_bucket
        self.model_key = 'models/random_forest_default_model.pkl'
        self.scaler_key = 'models/feature_scaler.pkl'
        self.metadata_key = 'models/model_metadata.json'
        
        # Model caching
        self.model = None
        self.scaler = None
        self.feature_columns = None
        self.model_version = None
        self.last_model_check = None
        self.model_refresh_interval = timedelta(minutes=5)  # Check for updates every 5 minutes
        
        # Load initial model
        self.load_model_from_s3()
    
    def should_refresh_model(self):
        """Check if model should be refreshed"""
        if self.last_model_check is None:
            return True
        
        return datetime.utcnow() - self.last_model_check > self.model_refresh_interval
    
    def get_s3_object_modified_time(self, key):
        """Get last modified time of S3 object"""
        try:
            response = self.s3_client.head_object(Bucket=self.s3_bucket, Key=key)
            return response['LastModified'].replace(tzinfo=None)
        except Exception:
            return None
    
    def load_model_metadata(self):
        """Load model metadata from S3"""
        try:
            response = self.s3_client.get_object(
                Bucket=self.s3_bucket,
                Key=self.metadata_key
            )
            metadata = json.loads(response['Body'].read().decode('utf-8'))
            return metadata
        except Exception as e:
            logger.warning(f"Failed to load model metadata: {e}")
            return None
    
    def load_model_from_s3(self, force_refresh=False):
        """Load model and scaler from S3"""
        try:
            # Check if refresh is needed
            if not force_refresh and not self.should_refresh_model():
                if self.model is not None:
                    return True
            
            logger.info("Loading model from S3...")
            
            # Load metadata
            metadata = self.load_model_metadata()
            if metadata:
                new_version = metadata.get('model_version')
                if new_version == self.model_version and self.model is not None:
                    logger.info(f"Model version {new_version} already loaded")
                    self.last_model_check = datetime.utcnow()
                    return True
                
                self.feature_columns = metadata.get('feature_columns', [])
                logger.info(f"Loading model version: {new_version}")
            
            # Load model
            model_response = self.s3_client.get_object(
                Bucket=self.s3_bucket,
                Key=self.model_key
            )
            self.model = pickle.loads(model_response['Body'].read())
            
            # Load scaler
            scaler_response = self.s3_client.get_object(
                Bucket=self.s3_bucket,
                Key=self.scaler_key
            )
            self.scaler = pickle.loads(scaler_response['Body'].read())
            
            # Update tracking variables
            self.model_version = metadata.get('model_version') if metadata else 'unknown'
            self.last_model_check = datetime.utcnow()
            
            logger.info(f"Successfully loaded model version {self.model_version} from S3")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model from S3: {e}")
            if self.model is None:
                # Fallback to creating a simple model
                logger.warning("Creating fallback model...")
                self._create_fallback_model()
            return False
    
    def _create_fallback_model(self):
        """Create a simple fallback model if S3 loading fails"""
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.preprocessing import StandardScaler
        
        # Simple fallback model with dummy data
        X_dummy = np.random.rand(100, 6)
        y_dummy = np.random.randint(0, 2, 100)
        
        self.model = RandomForestClassifier(n_estimators=10, random_state=42)
        self.model.fit(X_dummy, y_dummy)
        
        self.scaler = StandardScaler()
        self.scaler.fit(X_dummy)
        
        self.feature_columns = [
            'loan_amount', 'credit_score_normalized', 'dti_ratio',
            'ltv_ratio', 'loan_to_income', 'employment_stability'
        ]
        self.model_version = 'fallback'
        logger.warning("Using fallback model - predictions may be inaccurate")
    
    def prepare_features(self, loan_app: LoanApplication) -> np.ndarray:
        """Prepare features for model prediction"""
        # Ensure model is loaded and up-to-date
        self.load_model_from_s3()
        
        # Calculate derived features (matching training pipeline)
        ltv_ratio = getattr(loan_app, 'loan_amount', 0) / getattr(loan_app, 'property_value', 1)
        loan_to_income = getattr(loan_app, 'loan_amount', 0) / getattr(loan_app, 'annual_income', 1)
        credit_score_normalized = (getattr(loan_app, 'credit_score', 600) - 300) / (850 - 300)
        employment_stability = min(getattr(loan_app, 'employment_years', 0) / 10, 1.0)
        
        # Create feature array matching training format
        features = np.array([
            getattr(loan_app, 'loan_amount', 0),
            credit_score_normalized,
            getattr(loan_app, 'dti_ratio', 0),
            ltv_ratio,
            loan_to_income,
            employment_stability
        ]).reshape(1, -1)
        
        # Apply scaling
        if self.scaler:
            features = self.scaler.transform(features)
        
        return features
    
    def predict_default_risk(self, loan_app: LoanApplication) -> RiskResult:
        """Predict default risk using S3-stored model"""
        start_time = time.time()
        
        try:
            # Prepare features
            features = self.prepare_features(loan_app)
            
            # Get prediction and probabilities
            prediction = self.model.predict(features)[0]
            probabilities = self.model.predict_proba(features)[0]
            default_probability = probabilities[1]  # Probability of default (class 1)
            
            # Categorize risk
            if default_probability < 0.1:
                risk_category = "LOW"
            elif default_probability < 0.25:
                risk_category = "MEDIUM"
            elif default_probability < 0.5:
                risk_category = "HIGH"
            else:
                risk_category = "VERY_HIGH"
            
            processing_time = (time.time() - start_time) * 1000
            
            result = RiskResult(
                application_id=loan_app.application_id,
                default_risk=bool(prediction),
                risk_probability=round(default_probability, 4),
                risk_category=risk_category,
                confidence_score=round(np.max(probabilities), 4),
                processing_time_ms=processing_time,
                model_version=self.model_version
            )
            
            logger.info(f"Prediction completed for {loan_app.application_id} using model {self.model_version}")
            return result
            
        except Exception as e:
            logger.error(f"Prediction failed for {loan_app.application_id}: {e}")
            # Return safe default prediction
            return RiskResult(
                application_id=loan_app.application_id,
                default_risk=True,  # Conservative default
                risk_probability=0.5,
                risk_category="UNKNOWN",
                confidence_score=0.0,
                processing_time_ms=(time.time() - start_time) * 1000,
                model_version="error"
            )
