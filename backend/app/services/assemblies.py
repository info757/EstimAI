"""
Assemblies mapping service for construction takeoff.

Maps pipe buckets, trench CY, and other quantities to count items
with stable CSI (Construction Specifications Institute) tags for pricing.
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class AssemblyType(str, Enum):
    """Assembly types for construction takeoff."""
    PIPE = "pipe"
    TRENCH = "trench"
    STRUCTURE = "structure"
    SITEWORK = "sitework"
    EARTHWORK = "earthwork"


@dataclass
class AssemblyMapping:
    """Mapping from count item to assembly."""
    csi_code: str
    assembly_type: AssemblyType
    description: str
    unit: str
    quantity: float
    attributes: Dict[str, Any]
    pricing_key: str


@dataclass
class PricingItem:
    """Pricing item with unit cost and total."""
    csi_code: str
    description: str
    unit: str
    quantity: float
    unit_cost: Optional[float] = None
    total_cost: Optional[float] = None
    attributes: Dict[str, Any] = None


class AssembliesMapper:
    """Maps count items to construction assemblies with CSI codes."""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.pricing_config = self._load_pricing_config()
        self.assembly_mappings = self._load_assembly_mappings()
    
    def _load_pricing_config(self) -> Dict[str, Any]:
        """Load pricing configuration from JSON file."""
        pricing_file = self.config_dir / "pricing" / "assemblies.json"
        
        if not pricing_file.exists():
            logger.warning(f"Pricing config not found at {pricing_file}, using defaults")
            return self._get_default_pricing_config()
        
        try:
            with open(pricing_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading pricing config: {e}")
            return self._get_default_pricing_config()
    
    def _load_assembly_mappings(self) -> Dict[str, Dict[str, Any]]:
        """Load assembly mappings from JSON file."""
        mappings_file = self.config_dir / "assemblies" / "mappings.json"
        
        if not mappings_file.exists():
            logger.warning(f"Assembly mappings not found at {mappings_file}, using defaults")
            return self._get_default_assembly_mappings()
        
        try:
            with open(mappings_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading assembly mappings: {e}")
            return self._get_default_assembly_mappings()
    
    def _get_default_pricing_config(self) -> Dict[str, Any]:
        """Get default pricing configuration."""
        return {
            "unit_costs": {
                "33-1000": {"description": "Storm Pipe - 12\" Concrete", "unit": "LF", "cost": 45.00},
                "33-1001": {"description": "Storm Pipe - 15\" Concrete", "unit": "LF", "cost": 55.00},
                "33-1002": {"description": "Storm Pipe - 18\" Concrete", "unit": "LF", "cost": 65.00},
                "33-2000": {"description": "Sanitary Pipe - 8\" PVC", "unit": "LF", "cost": 25.00},
                "33-2001": {"description": "Sanitary Pipe - 10\" PVC", "unit": "LF", "cost": 30.00},
                "33-3000": {"description": "Water Pipe - 6\" Ductile Iron", "unit": "LF", "cost": 35.00},
                "33-3001": {"description": "Water Pipe - 8\" Ductile Iron", "unit": "LF", "cost": 40.00},
                "33-4000": {"description": "Trench Excavation - 0-5ft", "unit": "CY", "cost": 15.00},
                "33-4001": {"description": "Trench Excavation - 5-8ft", "unit": "CY", "cost": 18.00},
                "33-4002": {"description": "Trench Excavation - 8-12ft", "unit": "CY", "cost": 22.00},
                "33-4003": {"description": "Trench Excavation - 12+ft", "unit": "CY", "cost": 28.00},
                "33-5000": {"description": "Manhole - 4ft Diameter", "unit": "EA", "cost": 2500.00},
                "33-5001": {"description": "Inlet - Type A", "unit": "EA", "cost": 800.00},
                "33-6000": {"description": "Curb - Concrete", "unit": "LF", "cost": 12.00},
                "33-6001": {"description": "Sidewalk - Concrete", "unit": "SF", "cost": 8.50},
                "33-6002": {"description": "Silt Fence", "unit": "LF", "cost": 3.50}
            },
            "markup_percent": 15.0,
            "labor_factor": 1.25,
            "equipment_factor": 1.15
        }
    
    def _get_default_assembly_mappings(self) -> Dict[str, Dict[str, Any]]:
        """Get default assembly mappings."""
        return {
            "pipe_mappings": {
                "storm": {
                    "12": "33-1000",
                    "15": "33-1001", 
                    "18": "33-1002",
                    "21": "33-1003",
                    "24": "33-1004"
                },
                "sanitary": {
                    "8": "33-2000",
                    "10": "33-2001",
                    "12": "33-2002",
                    "15": "33-2003"
                },
                "water": {
                    "6": "33-3000",
                    "8": "33-3001",
                    "10": "33-3002",
                    "12": "33-3003"
                }
            },
            "trench_mappings": {
                "0-5": "33-4000",
                "5-8": "33-4001",
                "8-12": "33-4002",
                "12+": "33-4003"
            },
            "structure_mappings": {
                "manhole": "33-5000",
                "inlet": "33-5001",
                "valve": "33-5002",
                "hydrant": "33-5003"
            },
            "sitework_mappings": {
                "curb": "33-6000",
                "sidewalk": "33-6001",
                "silt_fence": "33-6002"
            }
        }
    
    def map_pipe_to_assemblies(self, pipe_data: Dict[str, Any]) -> List[AssemblyMapping]:
        """Map pipe data to assembly mappings."""
        assemblies = []
        
        # Extract pipe information
        pipe_type = pipe_data.get('type', 'unknown')
        diameter = pipe_data.get('dia_in', 0)
        length_ft = pipe_data.get('length_ft', 0)
        material = pipe_data.get('mat', 'unknown')
        extra = pipe_data.get('extra', {})
        
        # Map main pipe assembly
        csi_code = self._get_pipe_csi_code(pipe_type, diameter)
        if csi_code:
            assemblies.append(AssemblyMapping(
                csi_code=csi_code,
                assembly_type=AssemblyType.PIPE,
                description=f"{pipe_type.title()} Pipe - {diameter}\" {material.title()}",
                unit="LF",
                quantity=length_ft,
                attributes={
                    "diameter_in": diameter,
                    "material": material,
                    "pipe_type": pipe_type,
                    "length_ft": length_ft
                },
                pricing_key=f"{pipe_type}_{diameter}_{material}"
            ))
        
        # Map trench assemblies by depth buckets
        buckets_lf = extra.get('buckets_lf', {})
        for bucket, lf in buckets_lf.items():
            if lf > 0:
                trench_csi = self._get_trench_csi_code(bucket)
                if trench_csi:
                    # Convert LF to CY using trench volume
                    trench_volume_cy = extra.get('trench_volume_cy', 0)
                    if trench_volume_cy > 0:
                        # Estimate CY per LF for this bucket
                        cy_per_lf = trench_volume_cy / length_ft if length_ft > 0 else 0
                        trench_cy = lf * cy_per_lf
                        
                        assemblies.append(AssemblyMapping(
                            csi_code=trench_csi,
                            assembly_type=AssemblyType.TRENCH,
                            description=f"Trench Excavation - {bucket}ft depth",
                            unit="CY",
                            quantity=trench_cy,
                            attributes={
                                "depth_bucket": bucket,
                                "length_lf": lf,
                                "trench_cy": trench_cy,
                                "pipe_type": pipe_type,
                                "diameter_in": diameter
                            },
                            pricing_key=f"trench_{bucket}"
                        ))
        
        return assemblies
    
    def map_sitework_to_assemblies(self, sitework_data: Dict[str, Any]) -> List[AssemblyMapping]:
        """Map sitework data to assembly mappings."""
        assemblies = []
        
        # Map curb
        curb_lf = sitework_data.get('curb_lf', 0)
        if curb_lf > 0:
            assemblies.append(AssemblyMapping(
                csi_code="33-6000",
                assembly_type=AssemblyType.SITEWORK,
                description="Concrete Curb",
                unit="LF",
                quantity=curb_lf,
                attributes={"type": "curb", "material": "concrete"},
                pricing_key="curb_concrete"
            ))
        
        # Map sidewalk
        sidewalk_sf = sitework_data.get('sidewalk_sf', 0)
        if sidewalk_sf > 0:
            assemblies.append(AssemblyMapping(
                csi_code="33-6001",
                assembly_type=AssemblyType.SITEWORK,
                description="Concrete Sidewalk",
                unit="SF",
                quantity=sidewalk_sf,
                attributes={"type": "sidewalk", "material": "concrete"},
                pricing_key="sidewalk_concrete"
            ))
        
        # Map silt fence
        silt_fence_lf = sitework_data.get('silt_fence_lf', 0)
        if silt_fence_lf > 0:
            assemblies.append(AssemblyMapping(
                csi_code="33-6002",
                assembly_type=AssemblyType.SITEWORK,
                description="Silt Fence",
                unit="LF",
                quantity=silt_fence_lf,
                attributes={"type": "silt_fence"},
                pricing_key="silt_fence"
            ))
        
        return assemblies
    
    def map_structures_to_assemblies(self, structures_data: List[Dict[str, Any]]) -> List[AssemblyMapping]:
        """Map structure data to assembly mappings."""
        assemblies = []
        
        for structure in structures_data:
            structure_type = structure.get('type', 'unknown')
            count = structure.get('count', 1)
            
            csi_code = self._get_structure_csi_code(structure_type)
            if csi_code:
                assemblies.append(AssemblyMapping(
                    csi_code=csi_code,
                    assembly_type=AssemblyType.STRUCTURE,
                    description=f"{structure_type.title()} Structure",
                    unit="EA",
                    quantity=count,
                    attributes={
                        "structure_type": structure_type,
                        "count": count
                    },
                    pricing_key=f"structure_{structure_type}"
                ))
        
        return assemblies
    
    def _get_pipe_csi_code(self, pipe_type: str, diameter: float) -> Optional[str]:
        """Get CSI code for pipe based on type and diameter."""
        pipe_mappings = self.assembly_mappings.get('pipe_mappings', {})
        type_mappings = pipe_mappings.get(pipe_type, {})
        
        # Find closest diameter match
        diameter_str = str(int(diameter))
        if diameter_str in type_mappings:
            return type_mappings[diameter_str]
        
        # Find closest match
        available_diameters = [int(d) for d in type_mappings.keys()]
        if available_diameters:
            closest = min(available_diameters, key=lambda x: abs(x - diameter))
            return type_mappings[str(closest)]
        
        return None
    
    def _get_trench_csi_code(self, depth_bucket: str) -> Optional[str]:
        """Get CSI code for trench based on depth bucket."""
        trench_mappings = self.assembly_mappings.get('trench_mappings', {})
        return trench_mappings.get(depth_bucket)
    
    def _get_structure_csi_code(self, structure_type: str) -> Optional[str]:
        """Get CSI code for structure based on type."""
        structure_mappings = self.assembly_mappings.get('structure_mappings', {})
        return structure_mappings.get(structure_type)
    
    def calculate_pricing(self, assemblies: List[AssemblyMapping]) -> List[PricingItem]:
        """Calculate pricing for assemblies."""
        pricing_items = []
        unit_costs = self.pricing_config.get('unit_costs', {})
        
        for assembly in assemblies:
            # Get unit cost
            unit_cost = None
            if assembly.csi_code in unit_costs:
                unit_cost = unit_costs[assembly.csi_code]['cost']
            
            # Calculate total cost if unit cost is available
            total_cost = None
            if unit_cost is not None:
                total_cost = assembly.quantity * unit_cost
            
            pricing_item = PricingItem(
                csi_code=assembly.csi_code,
                description=assembly.description,
                unit=assembly.unit,
                quantity=assembly.quantity,
                unit_cost=unit_cost,
                total_cost=total_cost,
                attributes=assembly.attributes
            )
            
            pricing_items.append(pricing_item)
        
        return pricing_items
    
    def generate_assembly_summary(self, assemblies: List[AssemblyMapping]) -> Dict[str, Any]:
        """Generate summary of assemblies by type."""
        summary = {
            "total_assemblies": len(assemblies),
            "by_type": {},
            "by_csi_code": {},
            "total_quantities": {}
        }
        
        for assembly in assemblies:
            # By type
            assembly_type = assembly.assembly_type.value
            if assembly_type not in summary["by_type"]:
                summary["by_type"][assembly_type] = 0
            summary["by_type"][assembly_type] += 1
            
            # By CSI code
            if assembly.csi_code not in summary["by_csi_code"]:
                summary["by_csi_code"][assembly.csi_code] = {
                    "description": assembly.description,
                    "unit": assembly.unit,
                    "quantity": 0
                }
            summary["by_csi_code"][assembly.csi_code]["quantity"] += assembly.quantity
            
            # Total quantities by unit
            unit = assembly.unit
            if unit not in summary["total_quantities"]:
                summary["total_quantities"][unit] = 0
            summary["total_quantities"][unit] += assembly.quantity
        
        return summary


# Global mapper instance
_assemblies_mapper = None


def get_assemblies_mapper() -> AssembliesMapper:
    """Get global assemblies mapper instance."""
    global _assemblies_mapper
    if _assemblies_mapper is None:
        _assemblies_mapper = AssembliesMapper()
    return _assemblies_mapper


def map_count_items_to_assemblies(count_items: List[Dict[str, Any]]) -> Tuple[List[AssemblyMapping], List[PricingItem]]:
    """
    Map count items to assemblies and calculate pricing.
    
    Args:
        count_items: List of count item dictionaries
        
    Returns:
        Tuple of (assemblies, pricing_items)
    """
    mapper = get_assemblies_mapper()
    all_assemblies = []
    
    # Group count items by type
    pipe_items = []
    sitework_items = []
    structure_items = []
    
    for item in count_items:
        item_type = item.get('type', '')
        attributes = item.get('attributes', {})
        
        if 'pipe' in item_type.lower():
            pipe_items.append({
                'type': item_type,
                'dia_in': attributes.get('diameter_in', 0),
                'length_ft': item.get('quantity', 0),
                'mat': attributes.get('material', 'unknown'),
                'extra': attributes
            })
        elif 'curb' in item_type.lower() or 'sidewalk' in item_type.lower() or 'silt' in item_type.lower():
            sitework_items.append({
                f"{item_type.lower()}_lf" if 'curb' in item_type.lower() or 'silt' in item_type.lower() else f"{item_type.lower()}_sf": item.get('quantity', 0)
            })
        elif 'manhole' in item_type.lower() or 'inlet' in item_type.lower():
            structure_items.append({
                'type': item_type,
                'count': item.get('quantity', 1)
            })
    
    # Map pipes to assemblies
    for pipe_data in pipe_items:
        pipe_assemblies = mapper.map_pipe_to_assemblies(pipe_data)
        all_assemblies.extend(pipe_assemblies)
    
    # Map sitework to assemblies
    if sitework_items:
        sitework_data = {}
        for item in sitework_items:
            sitework_data.update(item)
        sitework_assemblies = mapper.map_sitework_to_assemblies(sitework_data)
        all_assemblies.extend(sitework_assemblies)
    
    # Map structures to assemblies
    if structure_items:
        structure_assemblies = mapper.map_structures_to_assemblies(structure_items)
        all_assemblies.extend(structure_assemblies)
    
    # Calculate pricing
    pricing_items = mapper.calculate_pricing(all_assemblies)
    
    return all_assemblies, pricing_items
