"""
Enhanced Pricing Service - Integrates with enhanced model service
"""

from app.services.enhanced_model_service import EnhancedModelService
from app.services.event_publisher import EventPublisher
import logging

logger = logging.getLogger(__name__)

class LoanPricingService:
    def __init__(self):
        self.enhanced_model_service = EnhancedModelService()
        self.event_publisher = EventPublisher()
    
    def calculate_loan_pricing(self, application_data: dict) -> dict:
        """Calculate loan pricing using enhanced ML service"""
        try:
            # Use enhanced model service for pricing with A/B testing
            pricing_result, model_version = self.enhanced_model_service.route_prediction_request(
                model_type='loan_pricing',
                features=application_data
            )
            
            # Publish pricing event
            self.event_publisher.publish_event(
                event_type='Loan Pricing Calculated',
                detail={
                    'application_id': application_data.get('application_id'),
                    'model_version': model_version,
                    'pricing': pricing_result
                }
            )
            
            return pricing_result
            
        except Exception as e:
            logger.error(f"Loan pricing calculation failed: {e}")
            raise
