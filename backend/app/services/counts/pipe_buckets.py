"""
Pipe bucket processing for depth-based count items.

Provides functions to flatten depth metrics into stable, price-able count lines
with CSI tags and depth bucket attributes.
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PipeBucketItem:
    """Individual pipe bucket count item."""
    category: str  # e.g., "pipe.sanitary.0_5"
    csi: str  # CSI code
    uom: str  # Unit of measure
    quantity: float  # Length in feet
    unit_price: Optional[float] = None
    total_price: Optional[float] = None
    attributes: Dict[str, Any] = None


@dataclass
class TrenchItem:
    """Trench excavation count item."""
    category: str  # "trench.excavation"
    csi: str  # CSI code
    uom: str  # Unit of measure (CY)
    quantity: float  # Volume in cubic yards
    unit_price: Optional[float] = None
    total_price: Optional[float] = None
    attributes: Dict[str, Any] = None


class PipeBucketProcessor:
    """Processes pipe depth buckets into count items."""
    
    def __init__(self, assemblies_config: str = "config/assemblies/pipes.json", 
                 pricing_config: str = "config/pricing/pipes_stub.json"):
        self.assemblies_config_path = Path(assemblies_config)
        self.pricing_config_path = Path(pricing_config)
        self.assemblies_config = self._load_assemblies_config()
        self.pricing_config = self._load_pricing_config()
    
    def _load_assemblies_config(self) -> Dict[str, Any]:
        """Load assemblies configuration."""
        try:
            if self.assemblies_config_path.exists():
                with open(self.assemblies_config_path, 'r') as f:
                    return json.load(f)
            else:
                logger.warning(f"Assemblies config not found: {self.assemblies_config_path}")
                return {}
        except Exception as e:
            logger.error(f"Failed to load assemblies config: {e}")
            return {}
    
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
    
    def process_pipe_buckets(self, pipes: List[Dict[str, Any]], discipline: str) -> List[PipeBucketItem]:
        """
        Process pipe depth buckets into count items.
        
        Args:
            pipes: List of pipe dictionaries with depth analysis
            discipline: Pipe discipline (sanitary, storm, water)
            
        Returns:
            List of PipeBucketItem objects
        """
        bucket_items = []
        
        for pipe in pipes:
            if "extra" not in pipe:
                continue
            
            extra = pipe["extra"]
            buckets_lf = extra.get("buckets_lf", {})
            
            # Process each depth bucket
            for bucket_name, length_ft in buckets_lf.items():
                if length_ft <= 0:
                    continue
                
                # Create bucket category
                category = f"pipe.{discipline}.{bucket_name}"
                
                # Get assembly config
                assembly_config = self.assemblies_config.get(category, {})
                csi = assembly_config.get("csi", "33 00 00")  # Default CSI
                uom = assembly_config.get("uom", "LF")
                
                # Get pricing config
                pricing_config = self.pricing_config.get(category, {})
                unit_price = pricing_config.get("unit_price")
                
                # Calculate total price if unit price available
                total_price = None
                if unit_price is not None:
                    total_price = round(unit_price * length_ft, 2)
                
                # Create attributes
                attributes = {
                    "diameter_in": pipe.get("dia_in"),
                    "material": pipe.get("mat"),
                    "avg_depth_ft": pipe.get("avg_depth_ft"),
                    "min_depth_ft": extra.get("min_depth_ft"),
                    "max_depth_ft": extra.get("max_depth_ft"),
                    "p95_depth_ft": extra.get("p95_depth_ft"),
                    "cover_ok": extra.get("cover_ok"),
                    "deep_excavation": extra.get("deep_excavation"),
                    "ground_source": extra.get("_ground_source"),
                    "pipe_id": pipe.get("id"),
                    "from_id": pipe.get("from_id"),
                    "to_id": pipe.get("to_id")
                }
                
                # Create bucket item
                bucket_item = PipeBucketItem(
                    category=category,
                    csi=csi,
                    uom=uom,
                    quantity=round(length_ft, 2),
                    unit_price=unit_price,
                    total_price=total_price,
                    attributes=attributes
                )
                
                bucket_items.append(bucket_item)
        
        return bucket_items
    
    def process_trench_excavation(self, pipes: List[Dict[str, Any]], discipline: str) -> List[TrenchItem]:
        """
        Process trench excavation volumes into count items.
        
        Args:
            pipes: List of pipe dictionaries with depth analysis
            discipline: Pipe discipline (sanitary, storm, water)
            
        Returns:
            List of TrenchItem objects
        """
        trench_items = []
        
        for pipe in pipes:
            if "extra" not in pipe:
                continue
            
            extra = pipe["extra"]
            trench_volume_cy = extra.get("trench_volume_cy", 0.0)
            
            if trench_volume_cy <= 0:
                continue
            
            # Get assembly config
            category = "trench.excavation"
            assembly_config = self.assemblies_config.get(category, {})
            csi = assembly_config.get("csi", "31 23 33")  # Default CSI for excavation
            uom = assembly_config.get("uom", "CY")
            
            # Get pricing config
            pricing_config = self.pricing_config.get(category, {})
            unit_price = pricing_config.get("unit_price")
            
            # Calculate total price if unit price available
            total_price = None
            if unit_price is not None:
                total_price = round(unit_price * trench_volume_cy, 2)
            
            # Create attributes
            attributes = {
                "discipline": discipline,
                "diameter_in": pipe.get("dia_in"),
                "material": pipe.get("mat"),
                "avg_depth_ft": pipe.get("avg_depth_ft"),
                "min_depth_ft": extra.get("min_depth_ft"),
                "max_depth_ft": extra.get("max_depth_ft"),
                "p95_depth_ft": extra.get("p95_depth_ft"),
                "cover_ok": extra.get("cover_ok"),
                "deep_excavation": extra.get("deep_excavation"),
                "ground_source": extra.get("_ground_source"),
                "pipe_id": pipe.get("id"),
                "from_id": pipe.get("from_id"),
                "to_id": pipe.get("to_id")
            }
            
            # Create trench item
            trench_item = TrenchItem(
                category=category,
                csi=csi,
                uom=uom,
                quantity=round(trench_volume_cy, 2),
                unit_price=unit_price,
                total_price=total_price,
                attributes=attributes
            )
            
            trench_items.append(trench_item)
        
        return trench_items
    
    def process_all_pipes(self, networks: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process all pipes from networks into count items.
        
        Args:
            networks: Networks dictionary with storm, sanitary, water pipes
            
        Returns:
            List of count item dictionaries
        """
        all_count_items = []
        
        # Process each discipline
        disciplines = {
            "storm": networks.get("storm", {}).get("pipes", []),
            "sanitary": networks.get("sanitary", {}).get("pipes", []),
            "water": networks.get("water", {}).get("pipes", [])
        }
        
        for discipline, pipes in disciplines.items():
            if not pipes:
                continue
            
            # Process pipe buckets
            bucket_items = self.process_pipe_buckets(pipes, discipline)
            for item in bucket_items:
                count_item = {
                    "category": item.category,
                    "csi": item.csi,
                    "uom": item.uom,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "total_price": item.total_price,
                    "attributes": item.attributes or {}
                }
                all_count_items.append(count_item)
            
            # Process trench excavation
            trench_items = self.process_trench_excavation(pipes, discipline)
            for item in trench_items:
                count_item = {
                    "category": item.category,
                    "csi": item.csi,
                    "uom": item.uom,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "total_price": item.total_price,
                    "attributes": item.attributes or {}
                }
                all_count_items.append(count_item)
        
        return all_count_items
    
    def get_assembly_summary(self, count_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get summary of assemblies and pricing.
        
        Args:
            count_items: List of count item dictionaries
            
        Returns:
            Summary dictionary with totals and breakdowns
        """
        summary = {
            "total_items": len(count_items),
            "total_quantity": 0.0,
            "total_price": 0.0,
            "by_category": {},
            "by_csi": {},
            "pricing_available": False
        }
        
        for item in count_items:
            category = item["category"]
            quantity = item["quantity"]
            total_price = item.get("total_price", 0.0)
            
            # Update totals
            summary["total_quantity"] += quantity
            if total_price:
                summary["total_price"] += total_price
                summary["pricing_available"] = True
            
            # By category
            if category not in summary["by_category"]:
                summary["by_category"][category] = {
                    "quantity": 0.0,
                    "total_price": 0.0,
                    "csi": item["csi"],
                    "uom": item["uom"]
                }
            
            summary["by_category"][category]["quantity"] += quantity
            if total_price:
                summary["by_category"][category]["total_price"] += total_price
            
            # By CSI
            csi = item["csi"]
            if csi not in summary["by_csi"]:
                summary["by_csi"][csi] = {
                    "quantity": 0.0,
                    "total_price": 0.0,
                    "categories": set()
                }
            
            summary["by_csi"][csi]["quantity"] += quantity
            if total_price:
                summary["by_csi"][csi]["total_price"] += total_price
            summary["by_csi"][csi]["categories"].add(category)
        
        # Convert sets to lists for JSON serialization
        for csi_data in summary["by_csi"].values():
            csi_data["categories"] = list(csi_data["categories"])
        
        return summary


def create_pipe_bucket_processor() -> PipeBucketProcessor:
    """Create a pipe bucket processor instance."""
    return PipeBucketProcessor()


def process_networks_to_count_items(networks: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Process networks into count items with depth buckets and pricing.
    
    Args:
        networks: Networks dictionary with storm, sanitary, water pipes
        
    Returns:
        List of count item dictionaries
    """
    processor = create_pipe_bucket_processor()
    return processor.process_all_pipes(networks)
