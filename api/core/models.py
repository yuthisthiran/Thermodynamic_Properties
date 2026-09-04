"""
Pydantic Models — ChemEng Thermodynamic API
============================================
Request and response schemas for all API endpoints.
Includes input validation, unit handling, and API documentation.
"""

from __future__ import annotations
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Dict, Any, List
from enum import Enum


# ============================================================
# ENUMS
# ============================================================

class TemperatureUnit(str, Enum):
    K = "K"
    C = "C"
    F = "F"

class PressureUnit(str, Enum):
    Pa  = "Pa"
    kPa = "kPa"
    MPa = "MPa"
    bar = "bar"
    psi = "psi"
    atm = "atm"

class EnthalpyUnit(str, Enum):
    Jkg    = "J/kg"
    kJkg   = "kJ/kg"
    BTUlb  = "BTU/lb"

class EntropyUnit(str, Enum):
    JkgK   = "J/kg/K"
    kJkgK  = "kJ/kg/K"
    BTUlbR = "BTU/lb/R"

class UnitSystem(str, Enum):
    SI       = "SI"
    Imperial = "Imperial"


# ============================================================
# REQUEST MODELS
# ============================================================

class PropertyRequest(BaseModel):
    """
    Request body for POST /properties.
    Provide exactly two independent intensive properties to fix the thermodynamic state.

    State Postulate: Two independent intensive properties uniquely determine the state
    of a single-component, single-phase system.
    """

    fluid: str = Field(
        ...,
        description=(
            "Fluid name or alias. Examples: 'Water', 'sCO2', 'H2', 'NH3', "
            "'R1234yf', 'R134a', 'Propane'. GET /fluids for all options."
        ),
        examples=["sCO2", "Water", "Ammonia", "R1234yf"],
    )

    # ---- Input state variables (provide exactly 2) ----
    T: Optional[float] = Field(None, description="Temperature")
    P: Optional[float] = Field(None, description="Pressure (absolute, not gauge)")
    H: Optional[float] = Field(None, description="Specific enthalpy")
    S: Optional[float] = Field(None, description="Specific entropy")
    Q: Optional[float] = Field(None, ge=0.0, le=1.0, description="Vapor quality (0=sat. liquid, 1=sat. vapor)")

    # ---- Input units ----
    T_unit: TemperatureUnit = Field(TemperatureUnit.C,   description="Temperature unit")
    P_unit: PressureUnit    = Field(PressureUnit.kPa,    description="Pressure unit")
    H_unit: EnthalpyUnit    = Field(EnthalpyUnit.kJkg,   description="Enthalpy unit")
    S_unit: EntropyUnit     = Field(EntropyUnit.kJkgK,   description="Entropy unit")

    # ---- Output unit system ----
    output_units: UnitSystem = Field(
        UnitSystem.SI,
        description="Unit system for all output properties (SI or Imperial)",
    )

    @model_validator(mode="after")
    def check_exactly_two_inputs(self) -> "PropertyRequest":
        provided = [k for k in ("T", "P", "H", "S", "Q") if getattr(self, k) is not None]
        if len(provided) < 2:
            raise ValueError(
                f"Provide exactly 2 independent state variables. Got: {provided}. "
                "Examples: T+P (superheated), T+Q or P+Q (saturation), P+H (flash)."
            )
        if len(provided) > 2:
            raise ValueError(
                f"Provide exactly 2 independent state variables. Got {len(provided)}: {provided}. "
                "Remove the extra inputs."
            )
        return self

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "summary": "Supercritical CO₂ at 35°C, 80 bar",
                    "value": {"fluid": "sCO2", "T": 35, "P": 80, "T_unit": "C", "P_unit": "bar"},
                },
                {
                    "summary": "Superheated steam at 500°C, 10 MPa",
                    "value": {"fluid": "Water", "T": 500, "P": 10, "T_unit": "C", "P_unit": "MPa"},
                },
                {
                    "summary": "Saturated ammonia vapor at -10°C",
                    "value": {"fluid": "NH3", "T": -10, "Q": 1.0, "T_unit": "C"},
                },
                {
                    "summary": "Flash: R-1234yf at 10 bar, h=250 kJ/kg",
                    "value": {"fluid": "R1234yf", "P": 1000, "H": 250, "P_unit": "kPa"},
                },
            ]
        }
    }


class SaturationRequest(BaseModel):
    """Request for POST /saturation — sat. liquid + vapor at a given T or P."""
    fluid: str = Field(..., description="Fluid name or alias")
    T: Optional[float] = Field(None, description="Saturation temperature")
    P: Optional[float] = Field(None, description="Saturation pressure")
    T_unit: TemperatureUnit = Field(TemperatureUnit.C)
    P_unit: PressureUnit    = Field(PressureUnit.kPa)
    output_units: UnitSystem = Field(UnitSystem.SI)

    @model_validator(mode="after")
    def check_T_or_P(self) -> "SaturationRequest":
        if self.T is None and self.P is None:
            raise ValueError("Provide either T or P for saturation calculation.")
        if self.T is not None and self.P is not None:
            raise ValueError("Provide either T or P, not both.")
        return self


# ============================================================
# RESPONSE MODELS
# ============================================================

class PropertyValue(BaseModel):
    """A single property with its value and unit."""
    value: Optional[float] = None
    unit: str = ""
    si_value: Optional[float] = Field(None, description="Value in SI units (always provided)")
    si_unit: str = ""


class PropertyResponse(BaseModel):
    """Full thermodynamic state response."""
    fluid: str
    fluid_alias_used: str
    phase: str
    phase_index: int
    standard: str
    reference: str
    accuracy: str
    unit_system: str
    properties: Dict[str, PropertyValue]
    warnings: List[str] = []


class SaturationRow(BaseModel):
    """One row of a saturation property table."""
    T_C: Optional[float] = None
    P_sat_kPa: Optional[float] = None
    h_f: Optional[float] = None
    h_fg: Optional[float] = None
    h_g: Optional[float] = None
    s_f: Optional[float] = None
    s_fg: Optional[float] = None
    s_g: Optional[float] = None
    v_f: Optional[float] = None
    v_g: Optional[float] = None
    u_f: Optional[float] = None
    u_fg: Optional[float] = None
    u_g: Optional[float] = None


class SaturationTableResponse(BaseModel):
    fluid: str
    standard: str
    units: str
    columns: Dict[str, str]   # column_name → unit string
    rows: List[Dict[str, Any]]
    n_rows: int


class PhaseCurveResponse(BaseModel):
    """Saturation dome data for frontend charting."""
    fluid: str
    T_crit_C: float
    P_crit_kPa: float
    T_C: List[float]
    s_liq_kJkgK: List[float]
    s_vap_kJkgK: List[float]
    h_liq_kJkg: List[float]
    h_vap_kJkg: List[float]
    P_sat_kPa: List[float]
    critical_point: Dict[str, float]


class FluidInfo(BaseModel):
    name: str
    coolprop_name: str
    aliases: List[str]
    standard: str
    reference: str
    accuracy: str
    category: str
    note: str = ""
    T_min_C: Optional[float] = None
    T_max_C: Optional[float] = None
    P_max_MPa: Optional[float] = None


class FluidListResponse(BaseModel):
    engine: str
    engine_accuracy: str
    total_fluids: int
    standards_bodies: List[str]
    fluids: List[FluidInfo]


class HealthResponse(BaseModel):
    status: str
    coolprop_version: str
    supported_fluid_count: int
    message: str


class ErrorResponse(BaseModel):
    error: str
    detail: str
    hint: str = ""
