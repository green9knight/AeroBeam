"""
Input validation for AeroBeam
Ensures all user inputs are physically reasonable and within safe bounds.
"""

from __future__ import annotations
from typing import Dict, Any, List, Tuple


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


class ValidationWarning:
    """Non-critical validation warning."""
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message


def validate_inputs(inputs: Dict[str, Any]) -> Tuple[Dict[str, Any], List[ValidationWarning]]:
    """
    Validate all inputs and return sanitized inputs plus warnings.
    
    Raises ValidationError for critical issues.
    Returns (sanitized_inputs, warnings) for non-critical issues.
    """
    warnings = []
    sanitized = dict(inputs)
    
    # Geometry validation
    _validate_geometry(sanitized, warnings)
    
    # Loads validation
    _validate_loads(sanitized, warnings)
    
    # Material validation
    _validate_materials(sanitized, warnings)
    
    # Spar validation
    _validate_spars(sanitized, warnings)
    
    # Configuration validation
    _validate_configuration(sanitized, warnings)
    
    # Flight conditions validation
    _validate_flight(sanitized, warnings)
    
    return sanitized, warnings


def _validate_geometry(inputs: Dict[str, Any], warnings: List[ValidationWarning]) -> None:
    """Validate geometric inputs."""
    
    # Span
    b = float(inputs.get("b", 0))
    if b <= 0:
        raise ValidationError("Span (b) must be positive")
    if b > 2000:
        warnings.append(ValidationWarning("b", f"Span {b} in is very large (>166 ft). Verify units."))
    
    # Root attach location
    r = float(inputs.get("r", 0))
    if r < 0:
        raise ValidationError("Root attach BL (r) cannot be negative")
    if r >= b:
        raise ValidationError(f"Root attach BL ({r} in) must be less than span ({b} in)")
    
    # Chords
    root_chord = float(inputs.get("root_chord", 0))
    tip_chord = float(inputs.get("tip_chord", 0))
    if root_chord <= 0:
        raise ValidationError("Root chord must be positive")
    if tip_chord <= 0:
        raise ValidationError("Tip chord must be positive")
    if root_chord > 500:
        warnings.append(ValidationWarning("root_chord", f"Root chord {root_chord} in is very large. Verify units."))
    
    # Taper
    taper_start_bl = float(inputs.get("taper_start_bl", 0))
    if taper_start_bl < 0:
        raise ValidationError("Taper start BL cannot be negative")
    if taper_start_bl > b:
        raise ValidationError(f"Taper start BL ({taper_start_bl} in) cannot exceed span ({b} in)")
    
    # Rib spacing
    rib_spacing = float(inputs.get("rib_spacing", 12))
    if rib_spacing <= 0:
        raise ValidationError("Rib spacing must be positive")
    if rib_spacing < 3:
        warnings.append(ValidationWarning("rib_spacing", f"Rib spacing {rib_spacing} in is very small"))
    if rib_spacing > 36:
        warnings.append(ValidationWarning("rib_spacing", f"Rib spacing {rib_spacing} in is very large"))
    
    # Analysis points
    num_points = int(inputs.get("num_points", 201))
    if num_points < 10:
        raise ValidationError("num_points must be at least 10")
    if num_points > 1000:
        warnings.append(ValidationWarning("num_points", f"{num_points} analysis points may be slow"))
    
    # Spar positions
    front_pct = float(inputs.get("front_spar_percent", 0.05))
    rear_pct = float(inputs.get("rear_spar_percent", 0.85))
    if not (0 < front_pct < 1):
        raise ValidationError(f"Front spar position {front_pct} must be between 0 and 1")
    if not (0 < rear_pct < 1):
        raise ValidationError(f"Rear spar position {rear_pct} must be between 0 and 1")
    if front_pct >= rear_pct:
        raise ValidationError(f"Front spar ({front_pct}) must be ahead of rear spar ({rear_pct})")
    
    # Load share
    load_share = float(inputs.get("front_spar_load_share", 0.55))
    if load_share > 1:
        # Normalize if given as percentage
        load_share = load_share / 100.0
        inputs["front_spar_load_share"] = load_share
    if not (0 < load_share < 1):
        raise ValidationError(f"Front spar load share {load_share} must be between 0 and 1")


def _validate_loads(inputs: Dict[str, Any], warnings: List[ValidationWarning]) -> None:
    """Validate load inputs."""
    
    # Load factors
    n = float(inputs.get("n", 6.0))
    n_neg = float(inputs.get("n_neg", -3.0))
    
    if n <= 0:
        raise ValidationError("Positive load factor (n) must be positive")
    if n < 2:
        warnings.append(ValidationWarning("n", f"Load factor {n}g is very low for aircraft"))
    if n > 12:
        warnings.append(ValidationWarning("n", f"Load factor {n}g is very high. Verify design category."))
    
    if n_neg >= 0:
        raise ValidationError("Negative load factor (n_neg) must be negative")
    if n_neg < -6:
        warnings.append(ValidationWarning("n_neg", f"Negative load factor {n_neg}g is very high"))
    
    # Weights
    weight = float(inputs.get("Weight", 0))
    wing_weight = float(inputs.get("Wing_Weight", 0))
    
    if weight <= 0:
        raise ValidationError("Gross weight must be positive")
    if wing_weight < 0:
        raise ValidationError("Wing weight cannot be negative")
    if wing_weight > weight:
        raise ValidationError(f"Wing weight ({wing_weight} lb) cannot exceed gross weight ({weight} lb)")
    
    # Design lift
    ng_lift = float(inputs.get("ng_lift", 0))
    if ng_lift <= 0:
        raise ValidationError("Design semi-span lift must be positive")
    
    # Sanity check: lift should be roughly half of n*Weight
    expected_lift = n * weight / 2
    if ng_lift < expected_lift * 0.5 or ng_lift > expected_lift * 2:
        warnings.append(ValidationWarning("ng_lift", 
            f"Design lift {ng_lift} lb seems inconsistent with {n}g × {weight} lb. Expected ~{expected_lift:.0f} lb"))


def _validate_materials(inputs: Dict[str, Any], warnings: List[ValidationWarning]) -> None:
    """Validate material selections."""
    from spar_sections import MATERIAL_DB, STRUT_MATERIALS
    
    # Check spar materials exist
    for prefix in ["front_spar", "rear_spar"]:
        mat = inputs.get(f"{prefix}_mat")
        if mat and mat not in MATERIAL_DB:
            raise ValidationError(f"{prefix} material '{mat}' not found in database")
        
        cap_mat = inputs.get(f"{prefix}_cap_mat")
        if cap_mat and cap_mat not in MATERIAL_DB:
            raise ValidationError(f"{prefix} cap material '{cap_mat}' not found in database")
        
        web_mat = inputs.get(f"{prefix}_web_mat")
        if web_mat and web_mat not in MATERIAL_DB:
            raise ValidationError(f"{prefix} web material '{web_mat}' not found in database")
    
    # Check strut material
    strut_mat = inputs.get("strut_mat")
    if strut_mat and strut_mat not in STRUT_MATERIALS:
        raise ValidationError(f"Strut material '{strut_mat}' not found in database")


def _validate_spars(inputs: Dict[str, Any], warnings: List[ValidationWarning]) -> None:
    """Validate spar geometry."""
    
    for prefix in ["front_spar", "rear_spar"]:
        spar_type = inputs.get(f"{prefix}_type", "Round Tube")
        
        if spar_type == "Round Tube":
            od = float(inputs.get(f"{prefix}_od", 0))
            wall = float(inputs.get(f"{prefix}_wall", 0))
            
            if od <= 0:
                raise ValidationError(f"{prefix} OD must be positive")
            if wall <= 0:
                raise ValidationError(f"{prefix} wall thickness must be positive")
            if wall >= od / 2:
                raise ValidationError(f"{prefix} wall ({wall}) must be less than OD/2 ({od/2})")
            if wall < 0.020:
                warnings.append(ValidationWarning(f"{prefix}_wall", 
                    f"{prefix} wall {wall} in is very thin"))
        
        elif spar_type in ["I-Beam", "C-Channel", "Double I-Beam", "Aluminum I-Beam", "Aluminum C-Spar"]:
            h_web = float(inputs.get(f"{prefix}_h_web", 0))
            t_web = float(inputs.get(f"{prefix}_t_web", 0))
            
            if h_web <= 0:
                raise ValidationError(f"{prefix} web height must be positive")
            if t_web <= 0:
                raise ValidationError(f"{prefix} web thickness must be positive")
            if t_web > h_web:
                warnings.append(ValidationWarning(f"{prefix}_t_web", 
                    f"{prefix} web thickness {t_web} exceeds height {h_web}"))
            
            # Cap dimensions
            for cap in ["top", "bot"]:
                b = float(inputs.get(f"{prefix}_b_{cap}", 0))
                t = float(inputs.get(f"{prefix}_t_{cap}", 0))
                if b <= 0:
                    raise ValidationError(f"{prefix} {cap} cap width must be positive")
                if t <= 0:
                    raise ValidationError(f"{prefix} {cap} cap thickness must be positive")
                if t > b:
                    warnings.append(ValidationWarning(f"{prefix}_t_{cap}", 
                        f"{prefix} {cap} cap thickness {t} exceeds width {b}"))
        
        elif spar_type == "Box Spar":
            b_outer = float(inputs.get(f"{prefix}_b_outer", 0))
            h_outer = float(inputs.get(f"{prefix}_h_outer", 0))
            t_web = float(inputs.get(f"{prefix}_t_web", 0))
            t_cap = float(inputs.get(f"{prefix}_t_cap", 0))
            
            if b_outer <= 0 or h_outer <= 0:
                raise ValidationError(f"{prefix} box dimensions must be positive")
            if t_web <= 0 or t_cap <= 0:
                raise ValidationError(f"{prefix} box thicknesses must be positive")
            if t_web >= b_outer / 2 or t_cap >= h_outer / 2:
                raise ValidationError(f"{prefix} box wall thicknesses too large for outer dimensions")


def _validate_configuration(inputs: Dict[str, Any], warnings: List[ValidationWarning]) -> None:
    """Validate strut/jury configuration."""
    
    config = inputs.get("config", "cantilever")
    
    if config in ["strut_braced", "single_strut"]:
        b = float(inputs.get("b", 306))
        strut_bl = float(inputs.get("strut_bl", 0))
        strut_vert = float(inputs.get("strut_vert", 0))
        strut_fuse_bl = float(inputs.get("strut_fuse_bl", 0))
        
        if strut_bl <= 0:
            raise ValidationError("Strut BL must be positive for strut-braced configuration")
        if strut_bl > b:
            raise ValidationError(f"Strut BL ({strut_bl}) cannot exceed span ({b})")
        if strut_vert <= 0:
            raise ValidationError("Strut vertical rise must be positive")
        if strut_fuse_bl < 0:
            raise ValidationError("Strut fuselage BL cannot be negative")
        
        # Strut tube
        strut_od = float(inputs.get("strut_tube_od", 0))
        strut_wall = float(inputs.get("strut_tube_wall", 0))
        if strut_od <= 0:
            raise ValidationError("Strut tube OD must be positive")
        if strut_wall <= 0:
            raise ValidationError("Strut tube wall must be positive")
        if strut_wall >= strut_od / 2:
            raise ValidationError(f"Strut wall ({strut_wall}) must be less than OD/2 ({strut_od/2})")
    
    # Jury strut
    if inputs.get("jury_strut", False):
        jury_bl = float(inputs.get("jury_spar_bl", 0))
        if jury_bl <= 0:
            raise ValidationError("Jury spar BL must be positive when jury strut enabled")
        
        jury_od = float(inputs.get("jury_tube_od", 0))
        jury_wall = float(inputs.get("jury_tube_wall", 0))
        if jury_od <= 0:
            raise ValidationError("Jury tube OD must be positive")
        if jury_wall <= 0:
            raise ValidationError("Jury tube wall must be positive")
        if jury_wall >= jury_od / 2:
            raise ValidationError(f"Jury wall ({jury_wall}) must be less than OD/2 ({jury_od/2})")


def _validate_flight(inputs: Dict[str, Any], warnings: List[ValidationWarning]) -> None:
    """Validate flight conditions."""
    
    # Speeds
    for speed_key, name in [("Vd_mph", "Dive"), ("Vc_mph", "Cruise"), ("Va_mph", "Maneuver")]:
        speed = float(inputs.get(speed_key, 0))
        if speed <= 0:
            raise ValidationError(f"{name} speed must be positive")
        if speed > 500:
            warnings.append(ValidationWarning(speed_key, f"{name} speed {speed} mph is very high"))
    
    # Speed relationships
    Vd = float(inputs.get("Vd_mph", 200))
    Vc = float(inputs.get("Vc_mph", 150))
    Va = float(inputs.get("Va_mph", 100))
    
    if Vd < Vc:
        warnings.append(ValidationWarning("Vd_mph", f"Dive speed ({Vd}) should exceed cruise speed ({Vc})"))
    if Vc < Va:
        warnings.append(ValidationWarning("Vc_mph", f"Cruise speed ({Vc}) should exceed maneuver speed ({Va})"))
    
    # Altitude
    altitude = float(inputs.get("altitude_ft", 0))
    if altitude < 0:
        raise ValidationError("Altitude cannot be negative")
    if altitude > 50000:
        warnings.append(ValidationWarning("altitude_ft", f"Altitude {altitude} ft is very high"))
    
    # Airfoil
    t_c = float(inputs.get("airfoil_t_c", 0.12))
    if t_c <= 0:
        raise ValidationError("Airfoil thickness ratio must be positive")
    if t_c > 0.30:
        warnings.append(ValidationWarning("airfoil_t_c", f"Airfoil t/c {t_c} is very thick"))
    
    Cl_alpha = float(inputs.get("Cl_alpha", 5.73))
    if Cl_alpha <= 0:
        raise ValidationError("Cl_alpha must be positive")
    if Cl_alpha > 8:
        warnings.append(ValidationWarning("Cl_alpha", f"Cl_alpha {Cl_alpha} /rad is unusually high"))


def sanitize_error_message(error: Exception) -> str:
    """
    Convert technical error to user-friendly message.
    Removes stack traces and technical jargon.
    """
    msg = str(error)
    
    # Common error patterns
    if "KeyError" in type(error).__name__:
        return f"Missing required input field. Please check all required fields are filled."
    
    if "ValueError" in type(error).__name__:
        if "could not convert" in msg:
            return "Invalid number format. Please enter numeric values only."
        return f"Invalid value: {msg}"
    
    if "ZeroDivisionError" in type(error).__name__:
        return "Division by zero detected. Check for zero dimensions or properties."
    
    if "ValidationError" in type(error).__name__:
        return msg  # Already user-friendly
    
    # Generic fallback
    return f"Analysis error: {msg}. Please verify all inputs are reasonable."

# Made with Bob
