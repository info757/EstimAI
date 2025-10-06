"""
Pricing stub service for construction takeoff.

Provides basic pricing calculations when unit prices are available.
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PricingSummary:
    """Summary of pricing calculations."""
    total_cost: float
    currency: str
    item_count: int
    priced_items: int
    unpriced_items: int
    by_category: Dict[str, Dict[str, Any]]
    by_csi: Dict[str, Dict[str, Any]]


class PricingStub:
    """Stub pricing service for basic cost calculations."""
    
    def __init__(self, pricing_config: str = "config/pricing/pipes_stub.json"):
        self.pricing_config_path = Path(pricing_config)
        self.pricing_config = self._load_pricing_config()
    
    def _load_pricing_config(self) -> Dict[str, Any]:
        """Load pricing configuration."""
        try:
            if self.pricing_config_path.exists():
                with open(self.pricing_config_path, 'r') as f:
                    return json.load(f)
            else:
                logger.warning(f"Pricing config not found: {self.pricing_config_path}")
                return {}
        except Exception as e:
            logger.error(f"Failed to load pricing config: {e}")
            return {}
    
    def calculate_totals(self, count_items: List[Dict[str, Any]]) -> PricingSummary:
        """
        Calculate pricing totals for count items.
        
        Args:
            count_items: List of count item dictionaries
            
        Returns:
            PricingSummary with totals and breakdowns
        """
        total_cost = 0.0
        item_count = len(count_items)
        priced_items = 0
        unpriced_items = 0
        
        by_category = {}
        by_csi = {}
        currency = "USD"  # Default currency
        
        for item in count_items:
            category = item["category"]
            csi = item["csi"]
            quantity = item["quantity"]
            unit_price = item.get("unit_price")
            total_price = item.get("total_price", 0.0)
            
            # Track pricing status
            if unit_price is not None and total_price is not None:
                priced_items += 1
                total_cost += total_price
            else:
                unpriced_items += 1
            
            # By category
            if category not in by_category:
                by_category[category] = {
                    "quantity": 0.0,
                    "unit_price": unit_price,
                    "total_cost": 0.0,
                    "csi": csi,
                    "uom": item["uom"]
                }
            
            by_category[category]["quantity"] += quantity
            if total_price:
                by_category[category]["total_cost"] += total_price
            
            # By CSI
            if csi not in by_csi:
                by_csi[csi] = {
                    "quantity": 0.0,
                    "total_cost": 0.0,
                    "categories": set()
                }
            
            by_csi[csi]["quantity"] += quantity
            if total_price:
                by_csi[csi]["total_cost"] += total_price
            by_csi[csi]["categories"].add(category)
        
        # Convert sets to lists for JSON serialization
        for csi_data in by_csi.values():
            csi_data["categories"] = list(csi_data["categories"])
        
        return PricingSummary(
            total_cost=round(total_cost, 2),
            currency=currency,
            item_count=item_count,
            priced_items=priced_items,
            unpriced_items=unpriced_items,
            by_category=by_category,
            by_csi=by_csi
        )
    
    def get_unit_price(self, category: str) -> Optional[float]:
        """
        Get unit price for a category.
        
        Args:
            category: Category name (e.g., "pipe.sanitary.0_5")
            
        Returns:
            Unit price or None if not available
        """
        pricing_data = self.pricing_config.get(category, {})
        return pricing_data.get("unit_price")
    
    def get_currency(self, category: str) -> str:
        """
        Get currency for a category.
        
        Args:
            category: Category name
            
        Returns:
            Currency code (default: USD)
        """
        pricing_data = self.pricing_config.get(category, {})
        return pricing_data.get("currency", "USD")
    
    def is_pricing_available(self) -> bool:
        """
        Check if pricing configuration is available.
        
        Returns:
            True if pricing config is loaded and has data
        """
        return bool(self.pricing_config)
    
    def get_available_categories(self) -> List[str]:
        """
        Get list of categories with pricing data.
        
        Returns:
            List of category names
        """
        return list(self.pricing_config.keys())
    
    def get_pricing_summary(self) -> Dict[str, Any]:
        """
        Get summary of available pricing data.
        
        Returns:
            Dictionary with pricing summary
        """
        if not self.pricing_config:
            return {
                "available": False,
                "categories": 0,
                "currency": "USD"
            }
        
        categories = list(self.pricing_config.keys())
        currencies = set()
        
        for category_data in self.pricing_config.values():
            if "currency" in category_data:
                currencies.add(category_data["currency"])
        
        return {
            "available": True,
            "categories": len(categories),
            "currency": list(currencies)[0] if currencies else "USD",
            "sample_categories": categories[:5]  # First 5 categories as sample
        }


def create_pricing_stub() -> PricingStub:
    """Create a pricing stub instance."""
    return PricingStub()


def calculate_pricing_totals(count_items: List[Dict[str, Any]]) -> PricingSummary:
    """
    Calculate pricing totals for count items.
    
    Args:
        count_items: List of count item dictionaries
        
    Returns:
        PricingSummary with totals and breakdowns
    """
    pricing_stub = create_pricing_stub()
    return pricing_stub.calculate_totals(count_items)
