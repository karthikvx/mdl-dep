"""
Enhanced Prediction Service - Integrates with enhanced model service
"""

from app.services.enhanced_model_service import EnhancedModelService
from app.services.event_publisher import EventPublisher
import logging

logger = logging.getLogger(__name__)

class DefaultPredictionService:
    def __init__(self):
        self.enhanced_model_service = EnhancedModelService()
        self.event_publisher = EventPublisher()
    
    def predict_default_risk(self, application_data: dict) -> dict:
        """Predict default risk using enhanced ML service"""
        try:
            # Use enhanced model service for prediction with A/B testing
            prediction_result, model_version = self.enhanced_model_service.route_prediction_request(
                model_type='default_prediction',
                features=application_data
            )
            
            # Publish prediction event
            self.event_publisher.publish_event(
                event_type='Default Risk Prediction',
                detail={
                    'application_id': application_data.get('application_id'),
                    'model_version': model_version,
                    'prediction': prediction_result
                }
            )
            
            return prediction_result
            
        except Exception as e:
            logger.error(f"Default prediction failed: {e}")
            raise
