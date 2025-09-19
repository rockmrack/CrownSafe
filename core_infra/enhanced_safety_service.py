"""
Enhanced Safety Service for comprehensive safety reports
Combines recall data with supplemental data sources
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from core_infra.supplemental_data_service import supplemental_data_service
from core_infra.database import get_db
from api.models.supplemental_models import (
    EnhancedSafetyReport, 
    FoodDataResponse, 
    CosmeticDataResponse, 
    ChemicalDataResponse,
    NutritionalInfo,
    CosmeticIngredient,
    ChemicalSafetyLimits
)

logger = logging.getLogger(__name__)

class EnhancedSafetyService:
    """Service for generating comprehensive safety reports"""
    
    def __init__(self):
        self.supplemental_service = supplemental_data_service
        logger.info("EnhancedSafetyService initialized")
    
    async def generate_enhanced_safety_report(
        self, 
        product_identifier: str,
        product_name: Optional[str] = None,
        product_type: Optional[str] = None,
        include_food_data: bool = True,
        include_cosmetic_data: bool = True,
        include_chemical_data: bool = True
    ) -> EnhancedSafetyReport:
        """Generate comprehensive safety report with supplemental data"""
        
        start_time = time.time()
        logger.info(f"Generating enhanced safety report for: {product_identifier}")
        
        # Initialize report
        report = EnhancedSafetyReport(
            product_identifier=product_identifier,
            product_name=product_name,
            product_type=product_type or "unknown"
        )
        
        # Get recall data
        recall_data = await self._get_recall_data(product_identifier)
        report.recall_status = recall_data.get("status", "no_recalls")
        report.recall_count = recall_data.get("count", 0)
        report.recent_recalls = recall_data.get("recalls", [])
        
        # Get supplemental data based on product type
        if include_food_data and (product_type == "food" or product_type is None):
            report.food_data = await self._get_food_data(product_identifier, product_name)
        
        if include_cosmetic_data and (product_type == "cosmetic" or product_type is None):
            report.cosmetic_data = await self._get_cosmetic_data(product_identifier, product_name)
        
        if include_chemical_data and (product_type == "chemical" or product_type is None):
            report.chemical_data = await self._get_chemical_data(product_identifier, product_name)
        
        # Calculate overall safety score
        report.overall_safety_score = self._calculate_overall_safety_score(report)
        
        # Generate recommendations and risk factors
        report.safety_recommendations = self._generate_safety_recommendations(report)
        report.risk_factors = self._identify_risk_factors(report)
        
        # Set metadata
        report.data_sources = self._get_data_sources(report)
        report.confidence_level = self._calculate_confidence_level(report)
        
        processing_time = int((time.time() - start_time) * 1000)
        logger.info(f"Enhanced safety report generated in {processing_time}ms")
        
        return report
    
    async def _get_recall_data(self, product_identifier: str) -> Dict[str, Any]:
        """Get recall data for the product"""
        try:
            # This would integrate with your existing recall database
            # For now, returning mock data structure
            return {
                "status": "no_recalls",
                "count": 0,
                "recalls": []
            }
        except Exception as e:
            logger.error(f"Error getting recall data: {e}")
            return {"status": "error", "count": 0, "recalls": []}
    
    async def _get_food_data(self, product_identifier: str, product_name: Optional[str]) -> Optional[FoodDataResponse]:
        """Get food data from supplemental sources"""
        try:
            search_term = product_name or product_identifier
            food_data = await self.supplemental_service.get_food_data(search_term, product_identifier)
            
            if not food_data.name:
                return None
            
            # Convert to response model
            nutritional_info = None
            if food_data.nutritional_info:
                nutritional_info = NutritionalInfo(
                    calories=food_data.nutritional_info.get("energy", {}).get("amount"),
                    protein=food_data.nutritional_info.get("protein", {}).get("amount"),
                    carbohydrates=food_data.nutritional_info.get("carbohydrate, by difference", {}).get("amount"),
                    fat=food_data.nutritional_info.get("total lipid (fat)", {}).get("amount"),
                    fiber=food_data.nutritional_info.get("fiber, total dietary", {}).get("amount"),
                    sugar=food_data.nutritional_info.get("sugars, total including nse", {}).get("amount"),
                    sodium=food_data.nutritional_info.get("sodium, na", {}).get("amount"),
                    cholesterol=food_data.nutritional_info.get("cholesterol", {}).get("amount")
                )
            
            return FoodDataResponse(
                fdc_id=food_data.fdc_id,
                name=food_data.name,
                ingredients=food_data.ingredients or [],
                allergens=food_data.allergens or [],
                nutritional_info=nutritional_info,
                safety_score=food_data.safety_score,
                source=food_data.source
            )
        except Exception as e:
            logger.error(f"Error getting food data: {e}")
            return None
    
    async def _get_cosmetic_data(self, product_identifier: str, product_name: Optional[str]) -> Optional[CosmeticDataResponse]:
        """Get cosmetic data from supplemental sources"""
        try:
            search_term = product_name or product_identifier
            logger.info(f"Getting cosmetic data for search term: {search_term}")
            
            cosmetic_data = await self.supplemental_service.get_cosmetic_data(search_term)
            logger.info(f"Got cosmetic data: {cosmetic_data}")
            
            if not cosmetic_data.product_name:
                logger.warning("No product name in cosmetic data, returning None")
                return None
            
            # Convert ingredients to response model
            ingredients = []
            for ingredient_name in cosmetic_data.ingredients or []:
                # Skip ingredients with empty or None names
                if not ingredient_name or not ingredient_name.strip():
                    continue
                    
                try:
                    ingredient = CosmeticIngredient(
                        name=ingredient_name.strip(),
                        functions=["emollient"],  # Mock function
                        restrictions=[],
                        safety_assessment="pending"
                    )
                    ingredients.append(ingredient)
                except Exception as e:
                    logger.error(f"Error creating ingredient '{ingredient_name}': {e}")
                    continue
            
            logger.info(f"Created {len(ingredients)} ingredients")
            
            try:
                response = CosmeticDataResponse(
                    product_name=cosmetic_data.product_name,
                    ingredients=ingredients,
                    regulatory_status=cosmetic_data.regulatory_status or {},
                    safety_concerns=cosmetic_data.safety_concerns or [],
                    safety_score=cosmetic_data.safety_score,
                    source=cosmetic_data.source
                )
                logger.info(f"Created CosmeticDataResponse successfully")
                return response
            except Exception as e:
                logger.error(f"Error creating CosmeticDataResponse: {e}", exc_info=True)
                return None
                
        except Exception as e:
            logger.error(f"Error getting cosmetic data: {e}", exc_info=True)
            return None
    
    async def _get_chemical_data(self, product_identifier: str, product_name: Optional[str]) -> Optional[ChemicalDataResponse]:
        """Get chemical data from supplemental sources"""
        try:
            search_term = product_name or product_identifier
            chemical_data = await self.supplemental_service.get_chemical_data(search_term)
            
            if not chemical_data.chemical_name:
                return None
            
            # Convert safety limits to response model
            safety_limits = None
            if chemical_data.safety_limits:
                safety_limits = ChemicalSafetyLimits(
                    osha_pel=chemical_data.safety_limits.get("OSHA_PEL"),
                    acgih_tlv=chemical_data.safety_limits.get("ACGIH_TLV"),
                    niosh_rel=chemical_data.safety_limits.get("NIOSH_REL"),
                    idlh=chemical_data.safety_limits.get("IDLH")
                )
            
            return ChemicalDataResponse(
                chemical_name=chemical_data.chemical_name,
                cas_number=chemical_data.cas_number,
                safety_limits=safety_limits,
                health_effects=chemical_data.health_effects or [],
                exposure_guidelines=chemical_data.exposure_guidelines or {},
                safety_score=chemical_data.safety_score,
                source=chemical_data.source
            )
        except Exception as e:
            logger.error(f"Error getting chemical data: {e}")
            return None
    
    def _calculate_overall_safety_score(self, report: EnhancedSafetyReport) -> float:
        """Calculate overall safety score based on all available data"""
        scores = []
        weights = []
        
        # Recall data weight (40%)
        if report.recall_count > 0:
            recall_score = max(0.0, 1.0 - (report.recall_count * 0.2))
            scores.append(recall_score)
            weights.append(0.4)
        
        # Food data weight (30%)
        if report.food_data and report.food_data.safety_score:
            scores.append(report.food_data.safety_score)
            weights.append(0.3)
        
        # Cosmetic data weight (20%)
        if report.cosmetic_data and report.cosmetic_data.safety_score:
            scores.append(report.cosmetic_data.safety_score)
            weights.append(0.2)
        
        # Chemical data weight (10%)
        if report.chemical_data and report.chemical_data.safety_score:
            scores.append(report.chemical_data.safety_score)
            weights.append(0.1)
        
        # Calculate weighted average
        if scores and weights:
            total_weight = sum(weights)
            weighted_score = sum(score * weight for score, weight in zip(scores, weights)) / total_weight
            return min(max(weighted_score, 0.0), 1.0)
        
        return 0.5  # Default neutral score
    
    def _generate_safety_recommendations(self, report: EnhancedSafetyReport) -> List[str]:
        """Generate safety recommendations based on the report data"""
        recommendations = []
        
        # Recall-based recommendations
        if report.recall_count > 0:
            recommendations.append("[WARNING] This product has been recalled. Avoid use and check for updates.")
        
        # Food-based recommendations
        if report.food_data:
            if report.food_data.allergens:
                recommendations.append(f"[FOOD] Contains allergens: {', '.join(report.food_data.allergens)}")
            
            if report.food_data.nutritional_info:
                if report.food_data.nutritional_info.sodium and report.food_data.nutritional_info.sodium > 500:
                    recommendations.append("[SODIUM] High sodium content - consume in moderation")
                
                if report.food_data.nutritional_info.sugar and report.food_data.nutritional_info.sugar > 20:
                    recommendations.append("[SUGAR] High sugar content - limit consumption")
        
        # Cosmetic-based recommendations
        if report.cosmetic_data:
            if report.cosmetic_data.safety_concerns:
                recommendations.append(f"[COSMETIC] Safety concerns: {', '.join(report.cosmetic_data.safety_concerns)}")
            
            if any(ingredient.restrictions for ingredient in report.cosmetic_data.ingredients):
                recommendations.append("[WARNING] Some ingredients have usage restrictions")
        
        # Chemical-based recommendations
        if report.chemical_data:
            if report.chemical_data.health_effects:
                recommendations.append(f"[CHEMICAL] Health effects: {', '.join(report.chemical_data.health_effects)}")
            
            if report.chemical_data.exposure_guidelines:
                for exposure_type, guideline in report.chemical_data.exposure_guidelines.items():
                    recommendations.append(f"[PROTECTION] {exposure_type.title()} exposure: {guideline}")
        
        # Overall safety recommendations
        if report.overall_safety_score < 0.3:
            recommendations.append("[HIGH RISK] High risk - exercise extreme caution")
        elif report.overall_safety_score < 0.6:
            recommendations.append("[MODERATE RISK] Moderate risk - use with caution")
        else:
            recommendations.append("[SAFE] Generally safe for intended use")
        
        return recommendations
    
    def _identify_risk_factors(self, report: EnhancedSafetyReport) -> List[str]:
        """Identify risk factors from the report data"""
        risk_factors = []
        
        # Recall risks
        if report.recall_count > 0:
            risk_factors.append("Product recalls")
        
        # Food risks
        if report.food_data:
            if report.food_data.allergens:
                risk_factors.append("Allergen exposure")
            
            if report.food_data.nutritional_info:
                if report.food_data.nutritional_info.sodium and report.food_data.nutritional_info.sodium > 1000:
                    risk_factors.append("High sodium content")
                
                if report.food_data.nutritional_info.sugar and report.food_data.nutritional_info.sugar > 30:
                    risk_factors.append("High sugar content")
        
        # Cosmetic risks
        if report.cosmetic_data:
            if report.cosmetic_data.safety_concerns:
                risk_factors.extend(report.cosmetic_data.safety_concerns)
        
        # Chemical risks
        if report.chemical_data:
            if report.chemical_data.health_effects:
                risk_factors.extend(report.chemical_data.health_effects)
        
        return list(set(risk_factors))  # Remove duplicates
    
    def _get_data_sources(self, report: EnhancedSafetyReport) -> List[str]:
        """Get list of data sources used in the report"""
        sources = ["recall_database"]
        
        if report.food_data:
            sources.append(report.food_data.source)
        
        if report.cosmetic_data:
            sources.append(report.cosmetic_data.source)
        
        if report.chemical_data:
            sources.append(report.chemical_data.source)
        
        return list(set(sources))  # Remove duplicates
    
    def _calculate_confidence_level(self, report: EnhancedSafetyReport) -> float:
        """Calculate confidence level based on data availability"""
        confidence = 0.0
        
        # Base confidence from recall data
        if report.recall_count >= 0:  # Even 0 recalls is data
            confidence += 0.3
        
        # Additional confidence from supplemental data
        if report.food_data:
            confidence += 0.3
        
        if report.cosmetic_data:
            confidence += 0.2
        
        if report.chemical_data:
            confidence += 0.2
        
        return min(confidence, 1.0)

# Global instance
enhanced_safety_service = EnhancedSafetyService()
