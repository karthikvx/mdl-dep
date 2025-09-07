# Enhanced Model Management Service with A/B Testing and Performance Monitoring
# app/services/enhanced_model_service.py
import json
import boto3
import pickle
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, mean_squared_error, r2_score
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger(__name__)

@dataclass
class ModelMetrics:
    accuracy: float = None
    precision: float = None
    recall: float = None
    f1_score: float = None
    mse: float = None
    r2_score: float = None
    cross_val_score: List[float] = None
    feature_importance: Dict[str, float] = None
    training_time: float = None
    model_size: int = None

@dataclass
class ModelVersion:
    version: str
    model_type: str
    s3_path: str
    created_at: datetime
    metrics: ModelMetrics
    status: str  # 'training', 'active', 'shadow', 'retired'
    traffic_percentage: float = 0.0

class EnhancedModelService:
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.dynamodb = boto3.resource('dynamodb')
        self.cloudwatch = boto3.client('cloudwatch')
        self.bucket_name = 'mortgage-ml-models'
        
        # DynamoDB tables for model metadata and experiment tracking
        self.model_registry = self.dynamodb.Table('ModelRegistry')
        self.experiment_results = self.dynamodb.Table('ExperimentResults')
        self.model_performance = self.dynamodb.Table('ModelPerformance')
        
        # In-memory model cache with version management
        self.model_cache = {}
        self.active_experiments = {}
        
    def train_enhanced_model(self, model_type: str, data_path: str, 
                           hyperparameters: Dict = None) -> ModelVersion:
        """Enhanced model training with comprehensive metrics and validation"""
        start_time = datetime.now()
        
        # Load and prepare data
        data = self._load_training_data(data_path)
        X, y = self._prepare_features(data, model_type)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Feature scaling
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Model training with hyperparameter optimization
        model = self._train_model_with_optimization(
            model_type, X_train_scaled, y_train, hyperparameters
        )
        
        # Comprehensive evaluation
        metrics = self._evaluate_model(model, X_test_scaled, y_test, model_type)
        metrics.cross_val_score = cross_val_score(model, X_train_scaled, y_train, cv=5).tolist()
        metrics.feature_importance = dict(zip(X.columns, model.feature_importances_))
        metrics.training_time = (datetime.now() - start_time).total_seconds()
        
        # Generate version and save model
        version = self._generate_version()
        model_version = ModelVersion(
            version=version,
            model_type=model_type,
            s3_path=f"models/{model_type}/{version}/",
            created_at=start_time,
            metrics=metrics,
            status='training'
        )
        
        # Save model artifacts to S3
        self._save_model_artifacts(model_version, model, scaler)
        
        # Register model in DynamoDB
        self._register_model(model_version)
        
        logger.info(f"Model {model_type} v{version} trained successfully")
        return model_version
    
    def _train_model_with_optimization(self, model_type: str, X_train: np.ndarray, 
                                     y_train: np.ndarray, hyperparameters: Dict) -> object:
        """Train model with hyperparameter optimization"""
        if hyperparameters is None:
            hyperparameters = self._get_default_hyperparameters(model_type)
        
        if model_type == 'default_prediction':
            model = RandomForestClassifier(**hyperparameters, random_state=42)
        else:  # loan_pricing
            model = RandomForestRegressor(**hyperparameters, random_state=42)
        
        model.fit(X_train, y_train)
        return model
    
    def _evaluate_model(self, model: object, X_test: np.ndarray, 
                       y_test: np.ndarray, model_type: str) -> ModelMetrics:
        """Comprehensive model evaluation"""
        predictions = model.predict(X_test)
        metrics = ModelMetrics()
        
        if model_type == 'default_prediction':
            # Classification metrics
            metrics.accuracy = accuracy_score(y_test, predictions)
            metrics.precision = precision_score(y_test, predictions, average='weighted')
            metrics.recall = recall_score(y_test, predictions, average='weighted')
            metrics.f1_score = f1_score(y_test, predictions, average='weighted')
        else:
            # Regression metrics
            metrics.mse = mean_squared_error(y_test, predictions)
            metrics.r2_score = r2_score(y_test, predictions)
        
        return metrics
    
    def deploy_model_with_ab_testing(self, model_version: ModelVersion, 
                                   traffic_percentage: float = 10.0,
                                   experiment_name: str = None) -> str:
        """Deploy model with A/B testing capabilities"""
        experiment_id = experiment_name or f"exp_{model_version.version}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Update model status and traffic allocation
        model_version.status = 'shadow'
        model_version.traffic_percentage = traffic_percentage
        
        # Store experiment configuration
        experiment_config = {
            'experiment_id': experiment_id,
            'model_version': model_version.version,
            'model_type': model_version.model_type,
            'traffic_percentage': traffic_percentage,
            'start_time': datetime.now().isoformat(),
            'status': 'active',
            'baseline_version': self._get_current_active_version(model_version.model_type)
        }
        
        self.experiment_results.put_item(Item=experiment_config)
        self.active_experiments[experiment_id] = experiment_config
        
        # Update model registry
        self._update_model_status(model_version)
        
        logger.info(f"A/B test started: {experiment_id} with {traffic_percentage}% traffic")
        return experiment_id
    
    def route_prediction_request(self, model_type: str, features: Dict) -> Tuple[Dict, str]:
        """Route prediction requests based on A/B testing configuration"""
        # Get active experiments for this model type
        active_experiments = self._get_active_experiments(model_type)
        
        if not active_experiments:
            # Use current active model
            model_version = self._get_current_active_version(model_type)
            model = self._load_model_from_cache(model_version)
        else:
            # Route based on experiment configuration
            experiment = self._select_experiment(active_experiments)
            if experiment and np.random.random() < experiment['traffic_percentage'] / 100:
                model_version = experiment['model_version']
                model = self._load_model_from_cache(model_version)
                # Log experiment participation
                self._log_experiment_request(experiment['experiment_id'], features)
            else:
                model_version = experiment['baseline_version']
                model = self._load_model_from_cache(model_version)
        
        # Make prediction
        prediction = self._make_prediction(model, features, model_type)
        
        return prediction, model_version
    
    def monitor_model_performance(self, model_version: str, actual_outcome: Dict,
                                predicted_outcome: Dict, request_features: Dict):
        """Monitor model performance in real-time"""
        timestamp = datetime.now()
        
        # Calculate prediction accuracy/error
        performance_metrics = self._calculate_real_time_metrics(
            actual_outcome, predicted_outcome, model_version
        )
        
        # Store performance data
        performance_record = {
            'model_version': model_version,
            'timestamp': timestamp.isoformat(),
            'prediction_accuracy': performance_metrics['accuracy'],
            'prediction_error': performance_metrics.get('error'),
            'feature_drift': self._detect_feature_drift(request_features, model_version),
            'request_features': json.dumps(request_features),
            'actual_outcome': json.dumps(actual_outcome),
            'predicted_outcome': json.dumps(predicted_outcome)
        }
        
        self.model_performance.put_item(Item=performance_record)
        
        # Send metrics to CloudWatch
        self._send_cloudwatch_metrics(model_version, performance_metrics)
        
        # Check for performance degradation
        self._check_performance_alerts(model_version, performance_metrics)
    
    def analyze_experiment_results(self, experiment_id: str) -> Dict:
        """Analyze A/B test experiment results"""
        # Get experiment configuration
        experiment = self.active_experiments.get(experiment_id)
        if not experiment:
            experiment = self._get_experiment_from_db(experiment_id)
        
        # Collect performance data for both variants
        baseline_metrics = self._get_model_performance_metrics(experiment['baseline_version'])
        test_metrics = self._get_model_performance_metrics(experiment['model_version'])
        
        # Statistical significance testing
        significance_results = self._perform_significance_tests(baseline_metrics, test_metrics)
        
        analysis = {
            'experiment_id': experiment_id,
            'duration_days': (datetime.now() - datetime.fromisoformat(experiment['start_time'])).days,
            'baseline_performance': baseline_metrics,
            'test_performance': test_metrics,
            'improvement': self._calculate_improvement(baseline_metrics, test_metrics),
            'statistical_significance': significance_results,
            'recommendation': self._generate_recommendation(significance_results, test_metrics, baseline_metrics)
        }
        
        return analysis
    
    def promote_model_to_production(self, model_version: str, experiment_id: str = None):
        """Promote a model version to full production traffic"""
        # Get current active model
        model_info = self._get_model_info(model_version)
        current_active = self._get_current_active_version(model_info['model_type'])
        
        # Update statuses
        if current_active:
            self._update_model_status_by_version(current_active, 'retired')
        
        self._update_model_status_by_version(model_version, 'active', traffic_percentage=100.0)
        
        # Close experiment if provided
        if experiment_id:
            self._close_experiment(experiment_id, 'promoted')
        
        # Send notification
        self._send_promotion_notification(model_version, model_info['model_type'])
        
        logger.info(f"Model {model_version} promoted to production")
    
    def automated_model_validation(self, model_version: str) -> bool:
        """Automated validation before deployment"""
        model_info = self._get_model_info(model_version)
        
        validation_checks = {
            'performance_threshold': self._check_performance_threshold(model_info),
            'feature_compatibility': self._check_feature_compatibility(model_info),
            'model_size_check': self._check_model_size(model_info),
            'bias_detection': self._detect_model_bias(model_info),
            'stability_check': self._check_model_stability(model_info)
        }
        
        # All checks must pass
        validation_passed = all(validation_checks.values())
        
        # Log validation results
        self._log_validation_results(model_version, validation_checks)
        
        return validation_passed
    
    def _detect_feature_drift(self, current_features: Dict, model_version: str) -> float:
        """Detect feature drift compared to training data"""
        # Get training data statistics for the model
        training_stats = self._get_training_statistics(model_version)
        if not training_stats:
            return 0.0
        
        drift_scores = []
        for feature, value in current_features.items():
            if feature in training_stats:
                # Calculate drift score (simplified)
                mean = training_stats[feature]['mean']
                std = training_stats[feature]['std']
                drift_score = abs(value - mean) / (std + 1e-6)
                drift_scores.append(drift_score)
        
        return np.mean(drift_scores) if drift_scores else 0.0
    
    def _send_cloudwatch_metrics(self, model_version: str, metrics: Dict):
        """Send metrics to CloudWatch"""
        namespace = 'MortgageApp/MLModels'
        
        for metric_name, value in metrics.items():
            if value is not None:
                self.cloudwatch.put_metric_data(
                    Namespace=namespace,
                    MetricData=[
                        {
                            'MetricName': metric_name,
                            'Dimensions': [
                                {
                                    'Name': 'ModelVersion',
                                    'Value': model_version
                                }
                            ],
                            'Value': float(value),
                            'Timestamp': datetime.now()
                        }
                    ]
                )
    
    def _check_performance_alerts(self, model_version: str, metrics: Dict):
        """Check for performance degradation alerts"""
        # Define thresholds
        thresholds = {
            'accuracy': 0.85,
            'error_rate': 0.15,
            'drift_threshold': 2.0
        }
        
        alerts = []
        
        if metrics.get('accuracy', 1.0) < thresholds['accuracy']:
            alerts.append(f"Low accuracy: {metrics['accuracy']:.3f}")
        
        if metrics.get('error', 0.0) > thresholds['error_rate']:
            alerts.append(f"High error rate: {metrics['error']:.3f}")
        
        if alerts:
            self._send_alert(model_version, alerts)
    
    def get_model_lineage(self, model_version: str) -> Dict:
        """Get complete model lineage and audit trail"""
        model_info = self._get_model_info(model_version)
        
        lineage = {
            'model_version': model_version,
            'model_type': model_info['model_type'],
            'created_at': model_info['created_at'],
            'training_data': self._get_training_data_info(model_version),
            'parent_models': self._get_parent_models(model_version),
            'deployment_history': self._get_deployment_history(model_version),
            'experiment_participation': self._get_experiment_history(model_version),
            'performance_history': self._get_performance_history(model_version),
            'validation_results': self._get_validation_history(model_version)
        }
        
        return lineage
