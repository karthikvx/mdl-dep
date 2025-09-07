import boto3
import pandas as pd
import numpy as np
import pickle
import joblib
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.preprocessing import StandardScaler
import logging

logger = logging.getLogger(__name__)

class ModelTrainingService:
    def __init__(self, s3_bucket='mortgage-ml-models'):
        self.s3_client = boto3.client('s3')
        self.s3_bucket = s3_bucket
        self.model_key = 'models/random_forest_default_model.pkl'
        self.scaler_key = 'models/feature_scaler.pkl'
        self.metadata_key = 'models/model_metadata.json'
        
    def load_training_data(self, data_source='s3'):
        """Load training data from S3 or database"""
        if data_source == 's3':
            # Load from S3 CSV file
            try:
                response = self.s3_client.get_object(
                    Bucket=self.s3_bucket, 
                    Key='training-data/loan_dataset.csv'
                )
                df = pd.read_csv(response['Body'])
                logger.info(f"Loaded {len(df)} training records from S3")
                return df
            except Exception as e:
                logger.warning(f"Failed to load from S3: {e}, using synthetic data")
                return self._generate_synthetic_data()
        else:
            # Could load from RDS, Redshift, etc.
            return self._load_from_database()
    
    def _generate_synthetic_data(self, n_samples=10000):
        """Generate synthetic training data for demo purposes"""
        np.random.seed(42)
        
        # Generate realistic loan data
        loan_amounts = np.random.normal(300000, 100000, n_samples)
        loan_amounts = np.clip(loan_amounts, 50000, 1000000)
        
        credit_scores = np.random.normal(680, 80, n_samples)
        credit_scores = np.clip(credit_scores, 300, 850).astype(int)
        
        dti_ratios = np.random.beta(2, 3, n_samples) * 0.6  # Realistic DTI distribution
        
        # Additional features
        employment_years = np.random.exponential(5, n_samples)
        employment_years = np.clip(employment_years, 0, 40)
        
        annual_incomes = np.random.lognormal(11, 0.5, n_samples)  # Log-normal income
        annual_incomes = np.clip(annual_incomes, 30000, 500000)
        
        property_values = loan_amounts / (0.7 + np.random.normal(0, 0.1, n_samples))
        property_values = np.clip(property_values, loan_amounts, loan_amounts * 2)
        
        # Calculate LTV
        ltv_ratios = loan_amounts / property_values
        
        # Generate default labels based on risk factors
        risk_scores = (
            (credit_scores < 640) * 0.3 +
            (dti_ratios > 0.43) * 0.25 +
            (ltv_ratios > 0.95) * 0.2 +
            (employment_years < 2) * 0.15 +
            np.random.normal(0, 0.1, n_samples)
        )
        
        default_probs = 1 / (1 + np.exp(-5 * (risk_scores - 0.5)))  # Sigmoid
        defaults = np.random.binomial(1, default_probs, n_samples)
        
        df = pd.DataFrame({
            'loan_amount': loan_amounts,
            'credit_score': credit_scores,
            'dti_ratio': dti_ratios,
            'employment_years': employment_years,
            'annual_income': annual_incomes,
            'property_value': property_values,
            'ltv_ratio': ltv_ratios,
            'defaulted': defaults
        })
        
        logger.info(f"Generated {len(df)} synthetic training samples")
        logger.info(f"Default rate: {df['defaulted'].mean():.2%}")
        return df
    
    def prepare_features(self, df):
        """Feature engineering and preprocessing"""
        # Create additional features
        df = df.copy()
        df['loan_to_income'] = df['loan_amount'] / df['annual_income']
        df['credit_score_normalized'] = (df['credit_score'] - 300) / (850 - 300)
        df['employment_stability'] = np.clip(df['employment_years'] / 10, 0, 1)
        
        # Select features for training
        feature_columns = [
            'loan_amount', 'credit_score_normalized', 'dti_ratio', 
            'ltv_ratio', 'loan_to_income', 'employment_stability'
        ]
        
        X = df[feature_columns]
        y = df['defaulted']
        
        return X, y, feature_columns
    
    def train_model(self, X, y):
        """Train Random Forest model with hyperparameter tuning"""
        logger.info("Starting model training...")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Train Random Forest with optimized parameters
        model = RandomForestClassifier(
            n_estimators=200,
            max_depth=15,
            min_samples_split=10,
            min_samples_leaf=5,
            max_features='sqrt',
            random_state=42,
            n_jobs=-1
        )
        
        model.fit(X_train_scaled, y_train)
        
        # Evaluate model
        train_score = model.score(X_train_scaled, y_train)
        test_score = model.score(X_test_scaled, y_test)
        
        # Cross-validation
        cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5)
        
        # ROC AUC
        y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
        auc_score = roc_auc_score(y_test, y_pred_proba)
        
        metrics = {
            'train_accuracy': float(train_score),
            'test_accuracy': float(test_score),
            'cv_mean_accuracy': float(cv_scores.mean()),
            'cv_std_accuracy': float(cv_scores.std()),
            'roc_auc_score': float(auc_score),
            'feature_importance': dict(zip(X.columns, model.feature_importances_))
        }
        
        logger.info(f"Model training completed:")
        logger.info(f"  Train Accuracy: {train_score:.4f}")
        logger.info(f"  Test Accuracy: {test_score:.4f}")
        logger.info(f"  CV Accuracy: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
        logger.info(f"  ROC AUC: {auc_score:.4f}")
        
        return model, scaler, metrics
    
    def save_model_to_s3(self, model, scaler, feature_columns, metrics):
        """Save trained model, scaler, and metadata to S3"""
        try:
            # Save model
            model_buffer = pickle.dumps(model)
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=self.model_key,
                Body=model_buffer,
                ContentType='application/octet-stream'
            )
            
            # Save scaler
            scaler_buffer = pickle.dumps(scaler)
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=self.scaler_key,
                Body=scaler_buffer,
                ContentType='application/octet-stream'
            )
            
            # Save metadata
            metadata = {
                'model_version': datetime.utcnow().strftime('%Y%m%d_%H%M%S'),
                'training_timestamp': datetime.utcnow().isoformat(),
                'feature_columns': feature_columns,
                'model_type': 'RandomForestClassifier',
                'model_parameters': model.get_params(),
                'performance_metrics': metrics,
                's3_paths': {
                    'model': f's3://{self.s3_bucket}/{self.model_key}',
                    'scaler': f's3://{self.s3_bucket}/{self.scaler_key}'
                }
            }
            
            import json
            metadata_buffer = json.dumps(metadata, indent=2)
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=self.metadata_key,
                Body=metadata_buffer,
                ContentType='application/json'
            )
            
            logger.info(f"Model artifacts saved to S3:")
            logger.info(f"  Model: s3://{self.s3_bucket}/{self.model_key}")
            logger.info(f"  Scaler: s3://{self.s3_bucket}/{self.scaler_key}")
            logger.info(f"  Metadata: s3://{self.s3_bucket}/{self.metadata_key}")
            
            return metadata['model_version']
            
        except Exception as e:
            logger.error(f"Failed to save model to S3: {e}")
            raise
    
    def train_and_deploy(self):
        """Complete training pipeline"""
        try:
            # Load and prepare data
            df = self.load_training_data()
            X, y, feature_columns = self.prepare_features(df)
            
            # Train model
            model, scaler, metrics = self.train_model(X, y)
            
            # Save to S3
            model_version = self.save_model_to_s3(model, scaler, feature_columns, metrics)
            
            # Optionally trigger model refresh in prediction services
            self._notify_services_of_new_model(model_version)
            
            return {
                'success': True,
                'model_version': model_version,
                'metrics': metrics
            }
            
        except Exception as e:
            logger.error(f"Training pipeline failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _notify_services_of_new_model(self, model_version):
        """Notify prediction services of new model availability"""
        # Publish event to EventBridge
        try:
            event_client = boto3.client('events')
            event_client.put_events(
                Entries=[{
                    'Source': 'model-training-service',
                    'DetailType': 'ModelUpdated',
                    'Detail': json.dumps({
                        'model_version': model_version,
                        'model_path': f's3://{self.s3_bucket}/{self.model_key}',
                        'scaler_path': f's3://{self.s3_bucket}/{self.scaler_key}'
                    }),
                    'EventBusName': 'mortgage-application-bus'
                }]
            )
            logger.info(f"Published ModelUpdated event for version {model_version}")
        except Exception as e:
            logger.warning(f"Failed to publish model update event: {e}")
