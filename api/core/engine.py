"""
Thermodynamic Calculation Engine — ChemEng API
===============================================
Core CoolProp wrapper that handles:
  - Unit conversion (any unit → SI for CoolProp → any unit for output)
  - All input mode combinations (T+P, T+Q, P+Q, P+H, P+S, T+S, ...)
  - Full property extraction (T, P, h, s, v, ρ, u, x, Cp, Cv, μ, k, Pr, Z, c)
  - Saturation property tables
  - Phase curve generation for charting
  - Compressibility factor Z calculation
  - Graceful error handling (CoolProp can raise on invalid states)

Standards basis:
  All calculations use CoolProp 6.x, which implements the same
  Helmholtz-energy equations of state as NIST REFPROP 9.1.
  Accuracy: ±0.01–0.05% for most fluids and states.

Author: ChemEng Thermodynamic Calculator
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import CoolProp.CoolProp as CP

from .fluids import FLUID_REGISTRY, resolve_fluid, get_fluid_metadata, get_registry_response
from .models import (
    PropertyRequest,
    SaturationRequest,
    UnitSystem,
    TemperatureUnit,
    PressureUnit,
    EnthalpyUnit,
    EntropyUnit,
)

# ============================================================
# PHASE NAME MAP (CoolProp phase index → human label)
# ============================================================
PHASE_NAMES: Dict[int, str] = {
    0: "Liquid (Compressed / Subcooled)",
    1: "Supercritical",
    2: "Supercritical Gas",
    3: "Supercritical Liquid",
    4: "Critical Point",
    5: "Superheated Vapor / Gas",
    6: "Two-Phase Mixture (Wet / Quality Region)",
    7: "Unknown",
    8: "Not Imposed",
}

# ============================================================
# UNIT CONVERSION HELPERS
# ============================================================

def _to_K(value: float, unit: str) -> float:
    """Convert temperature to Kelvin."""
    u = unit.upper().strip().replace("°", "")
    if u in ("C", "CELSIUS", "DEGC"):
        return value + 273.15
    if u in ("F", "FAHRENHEIT", "DEGF"):
        return (value - 32.0) * 5.0 / 9.0 + 273.15
    # Default: assume K
    return value


def _to_Pa(value: float, unit: str) -> float:
    """Convert pressure to Pascal."""
    factors: Dict[str, float] = {
        "PA": 1.0,
        "KPA": 1e3,
        "MPA": 1e6,
        "BAR": 1e5,
        "PSI": 6894.757293168,
        "ATM": 101325.0,
    }
    key = unit.upper().replace("/", "").strip()
    factor = factors.get(key)
    if factor is None:
        raise ValueError(f"Unknown pressure unit: '{unit}'. Use Pa, kPa, MPa, bar, psi, or atm.")
    return value * factor


def _to_Jkg(value: float, unit: str) -> float:
    """Convert specific enthalpy to J/kg."""
    factors: Dict[str, float] = {
        "J/KG":   1.0,
        "KJ/KG":  1e3,
        "BTU/LB": 2326.0,
    }
    key = unit.upper().strip()
    factor = factors.get(key)
    if factor is None:
        raise ValueError(f"Unknown enthalpy unit: '{unit}'. Use J/kg, kJ/kg, or BTU/lb.")
    return value * factor


def _to_JkgK(value: float, unit: str) -> float:
    """Convert specific entropy to J/kg/K."""
    factors: Dict[str, float] = {
        "J/KG/K":   1.0,
        "KJ/KG/K":  1e3,
        "BTU/LB/R": 4186.8,
    }
    key = unit.upper().strip().replace("°", "")
    factor = factors.get(key)
    if factor is None:
        raise ValueError(f"Unknown entropy unit: '{unit}'. Use J/kg/K, kJ/kg/K, or BTU/lb/R.")
    return value * factor


def _safe_prop(cp_prop: str, in1: str, v1: float, in2: str, v2: float, fluid: str) -> Optional[float]:
    """Safely call CoolProp PropsSI, returning None on error or NaN."""
    try:
        val = CP.PropsSI(cp_prop, in1, v1, in2, v2, fluid)
        return val if math.isfinite(val) else None
    except Exception:
        return None


# ============================================================
# MAIN ENGINE CLASS
# ============================================================

class ThermodynamicEngine:
    """
    Central calculation engine. Wraps CoolProp with:
      - fluid aliasing
      - unit conversion
      - full property extraction
      - saturation tables
      - phase curve generation
    """

    # ---- Property extraction ----------------------------------------

    def _extract_all(
        self,
        fluid_cp: str,
        in1: str,
        v1: float,
        in2: str,
        v2: float,
    ) -> Dict[str, Any]:
        """
        Extract all thermodynamic and transport properties from CoolProp.
        All values returned in SI units.
        Returns a flat dict; missing/failed properties are None.
        """
        raw: Dict[str, Any] = {}

        # Phase first (determines downstream logic)
        phase_val = _safe_prop("Phase", in1, v1, in2, v2, fluid_cp)
        raw["phase_index"] = int(phase_val) if phase_val is not None else 7

        # Core thermodynamic properties
        for cp_name, key in [
            ("T", "T_K"),
            ("P", "P_Pa"),
            ("H", "h_Jkg"),
            ("S", "s_JkgK"),
            ("D", "rho_kgm3"),
            ("U", "u_Jkg"),
            ("Q", "quality"),
        ]:
            raw[key] = _safe_prop(cp_name, in1, v1, in2, v2, fluid_cp)

        # Quality: only meaningful in [0, 1]
        q = raw.get("quality")
        if q is not None and not (0.0 <= q <= 1.0):
            raw["quality"] = None

        # Transport properties
        for cp_name, key in [
            ("Cpmass",       "cp_JkgK"),
            ("Cvmass",       "cv_JkgK"),
            ("viscosity",    "mu_Pas"),
            ("conductivity", "k_WmK"),
            ("Prandtl",      "Pr"),
            ("speed_of_sound", "speed_of_sound_ms"),
        ]:
            raw[key] = _safe_prop(cp_name, in1, v1, in2, v2, fluid_cp)

        # Compressibility factor Z = P / (ρ R_specific T)
        T_K   = raw.get("T_K")
        P_Pa  = raw.get("P_Pa")
        rho   = raw.get("rho_kgm3")
        raw["Z"] = None
        if T_K and P_Pa and rho and rho > 0:
            try:
                M = CP.PropsSI("M", fluid_cp)          # kg/mol
                R_spec = 8.314462618 / M               # J/kg/K
                raw["Z"] = P_Pa / (rho * R_spec * T_K)
            except Exception:
                pass

        return raw

    # ---- Unit conversion for output -------------------------------------

    @staticmethod
    def _format_si(raw: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Format raw SI values into output property dict (SI output)."""
        T_K  = raw.get("T_K")
        P_Pa = raw.get("P_Pa")

        def fv(val: Optional[float], factor: float = 1.0) -> Optional[float]:
            return val / factor if val is not None else None

        def vf(val: Optional[float]) -> Optional[float]:  # specific volume
            return 1.0 / val if val and val > 0 else None

        return {
            "temperature":          {"value": fv(T_K, 1) - 273.15 if T_K else None,  "unit": "°C",      "si_value": T_K,            "si_unit": "K"},
            "temperature_K":        {"value": T_K,                                     "unit": "K"},
            "pressure_kPa":         {"value": fv(P_Pa, 1e3),                           "unit": "kPa",     "si_value": P_Pa,           "si_unit": "Pa"},
            "pressure_MPa":         {"value": fv(P_Pa, 1e6),                           "unit": "MPa"},
            "pressure_bar":         {"value": fv(P_Pa, 1e5),                           "unit": "bar"},
            "enthalpy":             {"value": fv(raw.get("h_Jkg"),  1e3),              "unit": "kJ/kg"},
            "entropy":              {"value": fv(raw.get("s_JkgK"), 1e3),              "unit": "kJ/kg·K"},
            "density":              {"value": raw.get("rho_kgm3"),                     "unit": "kg/m³"},
            "specific_volume":      {"value": vf(raw.get("rho_kgm3")),                 "unit": "m³/kg"},
            "internal_energy":      {"value": fv(raw.get("u_Jkg"),  1e3),              "unit": "kJ/kg"},
            "quality":              {"value": raw.get("quality"),                       "unit": "—"},
            "cp":                   {"value": fv(raw.get("cp_JkgK"), 1e3),             "unit": "kJ/kg·K"},
            "cv":                   {"value": fv(raw.get("cv_JkgK"), 1e3),             "unit": "kJ/kg·K"},
            "dynamic_viscosity_Pas":{"value": raw.get("mu_Pas"),                       "unit": "Pa·s"},
            "dynamic_viscosity_cP": {"value": fv(raw.get("mu_Pas"), 1e-3),            "unit": "cP (mPa·s)"},
            "thermal_conductivity": {"value": raw.get("k_WmK"),                        "unit": "W/m·K"},
            "prandtl":              {"value": raw.get("Pr"),                            "unit": "—"},
            "speed_of_sound":       {"value": raw.get("speed_of_sound_ms"),             "unit": "m/s"},
            "compressibility_Z":    {"value": raw.get("Z"),                             "unit": "—"},
        }

    @staticmethod
    def _format_imperial(raw: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Format raw SI values into output property dict (Imperial output)."""
        T_K  = raw.get("T_K")
        P_Pa = raw.get("P_Pa")

        def vf(val: Optional[float]) -> Optional[float]:
            return 1.0 / val * 16.01846 if val and val > 0 else None

        return {
            "temperature":          {"value": T_K * 9/5 - 459.67 if T_K else None,              "unit": "°F"},
            "pressure_psi":         {"value": P_Pa / 6894.757 if P_Pa else None,                 "unit": "psi"},
            "pressure_psia":        {"value": P_Pa / 6894.757 if P_Pa else None,                 "unit": "psia"},
            "enthalpy":             {"value": raw.get("h_Jkg")  / 2326.0 if raw.get("h_Jkg")    else None, "unit": "BTU/lb"},
            "entropy":              {"value": raw.get("s_JkgK") / 4186.8 if raw.get("s_JkgK")   else None, "unit": "BTU/lb·°R"},
            "density":              {"value": raw.get("rho_kgm3") * 0.0624279 if raw.get("rho_kgm3") else None, "unit": "lb/ft³"},
            "specific_volume":      {"value": vf(raw.get("rho_kgm3")),                            "unit": "ft³/lb"},
            "internal_energy":      {"value": raw.get("u_Jkg")  / 2326.0 if raw.get("u_Jkg")    else None, "unit": "BTU/lb"},
            "quality":              {"value": raw.get("quality"),                                  "unit": "—"},
            "cp":                   {"value": raw.get("cp_JkgK") / 4186.8 if raw.get("cp_JkgK") else None, "unit": "BTU/lb·°R"},
            "cv":                   {"value": raw.get("cv_JkgK") / 4186.8 if raw.get("cv_JkgK") else None, "unit": "BTU/lb·°R"},
            "dynamic_viscosity_Pas":{"value": raw.get("mu_Pas"),                                  "unit": "Pa·s"},
            "dynamic_viscosity_cP": {"value": raw.get("mu_Pas") / 1e-3 if raw.get("mu_Pas") else None, "unit": "cP"},
            "thermal_conductivity": {"value": raw.get("k_WmK"),                                   "unit": "W/m·K"},
            "prandtl":              {"value": raw.get("Pr"),                                       "unit": "—"},
            "speed_of_sound":       {"value": raw.get("speed_of_sound_ms") / 0.3048 if raw.get("speed_of_sound_ms") else None, "unit": "ft/s"},
            "compressibility_Z":    {"value": raw.get("Z"),                                        "unit": "—"},
        }

    # ---- Public API methods ---------------------------------------------

    def calculate(self, request: PropertyRequest) -> Dict[str, Any]:
        """
        Main calculation: returns all thermodynamic properties for a given state.
        Called by POST /properties.
        """
        fluid_cp = resolve_fluid(request.fluid)
        meta     = get_fluid_metadata(request.fluid)

        # Convert inputs to SI
        inputs: Dict[str, float] = {}
        if request.T is not None:
            inputs["T"] = _to_K(request.T,    request.T_unit.value)
        if request.P is not None:
            inputs["P"] = _to_Pa(request.P,   request.P_unit.value)
        if request.H is not None:
            inputs["H"] = _to_Jkg(request.H,  request.H_unit.value)
        if request.S is not None:
            inputs["S"] = _to_JkgK(request.S, request.S_unit.value)
        if request.Q is not None:
            inputs["Q"] = float(request.Q)

        keys = list(inputs.keys())
        in1, in2 = keys[0], keys[1]
        v1,  v2  = inputs[in1], inputs[in2]

        # Run calculation
        raw = self._extract_all(fluid_cp, in1, v1, in2, v2)

        # Format output
        if request.output_units == UnitSystem.SI:
            props = self._format_si(raw)
        else:
            props = self._format_imperial(raw)

        phase_idx = raw.get("phase_index", 7)

        # Build warnings
        warnings: List[str] = []
        if raw.get("quality") is None and phase_idx == 6:
            warnings.append("Phase detected as two-phase but quality could not be computed.")
        if raw.get("mu_Pas") is None:
            warnings.append("Transport properties (viscosity, conductivity) unavailable for this state.")
        T_K = raw.get("T_K")
        if T_K and meta.get("T_max_C") and T_K > meta["T_max_C"] + 273.15:
            warnings.append(f"Temperature may exceed the valid range for {fluid_cp}.")

        return {
            "fluid":            fluid_cp,
            "fluid_alias_used": request.fluid,
            "phase":            PHASE_NAMES.get(phase_idx, "Unknown"),
            "phase_index":      phase_idx,
            "standard":         meta.get("standard",  "CoolProp Helmholtz EOS"),
            "reference":        meta.get("reference", ""),
            "accuracy":         meta.get("accuracy",  "±0.05%"),
            "unit_system":      request.output_units.value,
            "properties":       props,
            "warnings":         warnings,
        }

    def calculate_saturation(self, request: SaturationRequest) -> Dict[str, Any]:
        """
        Get saturated liquid + saturated vapor properties at a given T or P.
        Called by POST /saturation.
        """
        fluid_cp = resolve_fluid(request.fluid)
        meta     = get_fluid_metadata(request.fluid)

        if request.T is not None:
            in_name = "T"
            in_val  = _to_K(request.T, request.T_unit.value)
        else:
            in_name = "P"
            in_val  = _to_Pa(request.P, request.P_unit.value)

        def sat_row(x_val: float) -> Dict[str, Any]:
            raw = self._extract_all(fluid_cp, in_name, in_val, "Q", x_val)
            return raw

        liq_raw = sat_row(0.0)
        vap_raw = sat_row(1.0)

        def to_out(raw: Dict) -> Dict[str, Any]:
            T  = raw.get("T_K")
            P  = raw.get("P_Pa")
            h  = raw.get("h_Jkg")
            s  = raw.get("s_JkgK")
            rho = raw.get("rho_kgm3")
            u  = raw.get("u_Jkg")
            return {
                "T_C":       T - 273.15     if T   else None,
                "T_K":       T,
                "P_kPa":     P / 1e3        if P   else None,
                "P_MPa":     P / 1e6        if P   else None,
                "h_kJkg":    h / 1e3        if h   else None,
                "s_kJkgK":   s / 1e3        if s   else None,
                "v_m3kg":    1.0/rho        if rho and rho > 0 else None,
                "rho_kgm3":  rho,
                "u_kJkg":    u / 1e3        if u   else None,
                "cp_kJkgK":  raw.get("cp_JkgK", 0) / 1e3   if raw.get("cp_JkgK") else None,
                "mu_Pas":    raw.get("mu_Pas"),
                "k_WmK":     raw.get("k_WmK"),
                "Pr":        raw.get("Pr"),
            }

        liq = to_out(liq_raw)
        vap = to_out(vap_raw)

        h_fg = (vap["h_kJkg"] - liq["h_kJkg"]) if vap.get("h_kJkg") and liq.get("h_kJkg") else None
        s_fg = (vap["s_kJkgK"] - liq["s_kJkgK"]) if vap.get("s_kJkgK") and liq.get("s_kJkgK") else None
        u_fg = (vap["u_kJkg"] - liq["u_kJkg"]) if vap.get("u_kJkg") and liq.get("u_kJkg") else None

        return {
            "fluid":            fluid_cp,
            "standard":         meta.get("standard", "CoolProp EOS"),
            "saturated_liquid": liq,
            "saturated_vapor":  vap,
            "hfg_kJkg":         h_fg,
            "sfg_kJkgK":        s_fg,
            "ufg_kJkg":         u_fg,
        }

    def generate_saturation_table(
        self,
        fluid_str: str,
        T_start_K: float,
        T_end_K:   float,
        n_points:  int,
        by_pressure: bool = False,
        P_start_Pa: float = None,
        P_end_Pa:   float = None,
        si: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate a textbook-style saturation property table.
        Columns: T, P_sat, h_f, h_fg, h_g, s_f, s_fg, s_g, v_f, v_g, u_f, u_fg, u_g
        Called by GET /saturation-table.
        """
        fluid_cp = resolve_fluid(fluid_str)
        meta     = get_fluid_metadata(fluid_str)

        if by_pressure and P_start_Pa and P_end_Pa:
            range_vals = np.linspace(P_start_Pa, P_end_Pa, n_points)
            in_name    = "P"
        else:
            range_vals = np.linspace(T_start_K, T_end_K, n_points)
            in_name    = "T"

        rows: List[Dict[str, Any]] = []

        for val in range_vals:
            try:
                def sp(prop: str, x: float) -> Optional[float]:
                    return _safe_prop(prop, in_name, val, "Q", x, fluid_cp)

                T_K = sp("T", 0.0)
                P   = sp("P", 0.0)
                hl  = sp("H", 0.0); hg = sp("H", 1.0)
                sl  = sp("S", 0.0); sg = sp("S", 1.0)
                vl_ = sp("D", 0.0); vg_ = sp("D", 1.0)
                ul  = sp("U", 0.0); ug = sp("U", 1.0)

                def safe_1_over(d): return 1.0/d if d and d > 0 else None
                def safe_div(v, f): return v / f if v is not None else None
                def safe_sub(a, b): return a - b if a is not None and b is not None else None

                if si:
                    rows.append({
                        "T_C":           round(T_K - 273.15, 4)               if T_K else None,
                        "P_sat_kPa":     round(safe_div(P, 1e3), 4)            if P   else None,
                        "h_f_kJkg":      round(safe_div(hl, 1e3), 4)           if hl  else None,
                        "h_fg_kJkg":     round(safe_div(safe_sub(hg, hl), 1e3), 4) if hg and hl else None,
                        "h_g_kJkg":      round(safe_div(hg, 1e3), 4)           if hg  else None,
                        "s_f_kJkgK":     round(safe_div(sl, 1e3), 6)           if sl  else None,
                        "s_fg_kJkgK":    round(safe_div(safe_sub(sg, sl), 1e3), 6) if sg and sl else None,
                        "s_g_kJkgK":     round(safe_div(sg, 1e3), 6)           if sg  else None,
                        "v_f_m3kg":      round(safe_1_over(vl_), 8)            if vl_ else None,
                        "v_g_m3kg":      round(safe_1_over(vg_), 6)            if vg_ else None,
                        "u_f_kJkg":      round(safe_div(ul, 1e3), 4)           if ul  else None,
                        "u_fg_kJkg":     round(safe_div(safe_sub(ug, ul), 1e3), 4) if ug and ul else None,
                        "u_g_kJkg":      round(safe_div(ug, 1e3), 4)           if ug  else None,
                    })
                else:
                    rows.append({
                        "T_F":           round(T_K * 9/5 - 459.67, 4)          if T_K else None,
                        "P_sat_psi":     round(safe_div(P, 6894.757), 4)        if P   else None,
                        "h_f_BTUlb":     round(safe_div(hl,  2326.0), 4)        if hl  else None,
                        "h_fg_BTUlb":    round(safe_div(safe_sub(hg, hl), 2326.0), 4) if hg and hl else None,
                        "h_g_BTUlb":     round(safe_div(hg,  2326.0), 4)        if hg  else None,
                        "s_f_BTUlbR":    round(safe_div(sl,  4186.8), 6)        if sl  else None,
                        "s_fg_BTUlbR":   round(safe_div(safe_sub(sg, sl), 4186.8), 6) if sg and sl else None,
                        "s_g_BTUlbR":    round(safe_div(sg,  4186.8), 6)        if sg  else None,
                        "v_f_ft3lb":     round(safe_1_over(vl_) * 16.01846, 8) if vl_ else None,
                        "v_g_ft3lb":     round(safe_1_over(vg_) * 16.01846, 6) if vg_ else None,
                    })
            except Exception:
                continue

        columns_si = {
            "T_C": "°C", "P_sat_kPa": "kPa",
            "h_f_kJkg": "kJ/kg", "h_fg_kJkg": "kJ/kg", "h_g_kJkg": "kJ/kg",
            "s_f_kJkgK": "kJ/kg·K", "s_fg_kJkgK": "kJ/kg·K", "s_g_kJkgK": "kJ/kg·K",
            "v_f_m3kg": "m³/kg", "v_g_m3kg": "m³/kg",
            "u_f_kJkg": "kJ/kg", "u_fg_kJkg": "kJ/kg", "u_g_kJkg": "kJ/kg",
        }
        columns_imp = {
            "T_F": "°F", "P_sat_psi": "psi",
            "h_f_BTUlb": "BTU/lb", "h_fg_BTUlb": "BTU/lb", "h_g_BTUlb": "BTU/lb",
            "s_f_BTUlbR": "BTU/lb·°R", "s_fg_BTUlbR": "BTU/lb·°R", "s_g_BTUlbR": "BTU/lb·°R",
            "v_f_ft3lb": "ft³/lb", "v_g_ft3lb": "ft³/lb",
        }

        return {
            "fluid":    fluid_cp,
            "standard": meta.get("standard", "CoolProp EOS"),
            "units":    "SI" if si else "Imperial",
            "columns":  columns_si if si else columns_imp,
            "rows":     rows,
            "n_rows":   len(rows),
        }

    def get_phase_curve(self, fluid_str: str, n_points: int = 150) -> Dict[str, Any]:
        """
        Return saturation dome (T-s and P-h) coordinates for interactive charts.
        Called by GET /phase-curve.
        """
        fluid_cp = resolve_fluid(fluid_str)
        meta     = get_fluid_metadata(fluid_str)

        T_crit_K = CP.PropsSI("Tcrit", fluid_cp)
        P_crit   = CP.PropsSI("pcrit", fluid_cp)

        try:
            T_triple = CP.PropsSI("T_triple", fluid_cp)
            T_start  = T_triple + 0.5
        except Exception:
            T_start = CP.PropsSI("Tmin", fluid_cp) + 0.5

        T_range = np.linspace(T_start, T_crit_K - 0.01, n_points)

        result: Dict[str, Any] = {
            "fluid":        fluid_cp,
            "T_crit_C":     T_crit_K - 273.15,
            "P_crit_kPa":   P_crit / 1e3,
            "T_C":          [],
            "s_liq_kJkgK":  [],
            "s_vap_kJkgK":  [],
            "h_liq_kJkg":   [],
            "h_vap_kJkg":   [],
            "P_sat_kPa":    [],
            "rho_liq_kgm3": [],
            "rho_vap_kgm3": [],
            "critical_point": {},
        }

        for T_K in T_range:
            try:
                sl  = _safe_prop("S", "T", T_K, "Q", 0, fluid_cp)
                sv  = _safe_prop("S", "T", T_K, "Q", 1, fluid_cp)
                hl  = _safe_prop("H", "T", T_K, "Q", 0, fluid_cp)
                hv  = _safe_prop("H", "T", T_K, "Q", 1, fluid_cp)
                P   = _safe_prop("P", "T", T_K, "Q", 0, fluid_cp)
                dl  = _safe_prop("D", "T", T_K, "Q", 0, fluid_cp)
                dv  = _safe_prop("D", "T", T_K, "Q", 1, fluid_cp)

                if all(v is not None for v in (sl, sv, hl, hv, P)):
                    result["T_C"].append(round(T_K - 273.15, 4))
                    result["s_liq_kJkgK"].append(round(sl / 1e3, 6))
                    result["s_vap_kJkgK"].append(round(sv / 1e3, 6))
                    result["h_liq_kJkg"].append(round(hl / 1e3, 4))
                    result["h_vap_kJkg"].append(round(hv / 1e3, 4))
                    result["P_sat_kPa"].append(round(P / 1e3, 4))
                    result["rho_liq_kgm3"].append(round(dl, 4) if dl else None)
                    result["rho_vap_kgm3"].append(round(dv, 6) if dv else None)
            except Exception:
                continue

        # Critical point
        try:
            s_cp = _safe_prop("S", "T", T_crit_K, "Q", 0, fluid_cp)
            h_cp = _safe_prop("H", "T", T_crit_K, "Q", 0, fluid_cp)
            result["critical_point"] = {
                "T_C":      T_crit_K - 273.15,
                "P_kPa":    P_crit / 1e3,
                "s_kJkgK":  s_cp / 1e3 if s_cp else None,
                "h_kJkg":   h_cp / 1e3 if h_cp else None,
            }
        except Exception:
            pass

        return result

    def get_single_property(
        self,
        fluid_str: str,
        prop:  str,
        in1:   str,
        v1:    float,
        in2:   str,
        v2:    float,
        unit:  str = "SI",
    ) -> float:
        """
        Return a single scalar property. Designed for Excel/Sheets formula calls.
        GET /property?fluid=sCO2&prop=Density&in1=T&v1=308.15&in2=P&v2=8e6

        Prop aliases: Density, Enthalpy, Entropy, Temperature, Pressure, Quality,
                      Cp, Cv, Viscosity, Conductivity, Prandtl, Volume, InternalEnergy,
                      SpeedOfSound, Compressibility
        """
        fluid_cp = resolve_fluid(fluid_str)

        PROP_MAP: Dict[str, str] = {
            "density":          "D",
            "rho":              "D",
            "enthalpy":         "H",
            "h":                "H",
            "entropy":          "S",
            "s":                "S",
            "temperature":      "T",
            "t":                "T",
            "pressure":         "P",
            "p":                "P",
            "quality":          "Q",
            "x":                "Q",
            "cp":               "Cpmass",
            "specificheatp":    "Cpmass",
            "cv":               "Cvmass",
            "specificheatv":    "Cvmass",
            "viscosity":        "viscosity",
            "mu":               "viscosity",
            "conductivity":     "conductivity",
            "k":                "conductivity",
            "thermalconductivity": "conductivity",
            "prandtl":          "Prandtl",
            "pr":               "Prandtl",
            "volume":           "D",   # returns 1/D
            "specificvolume":   "D",
            "v":                "D",
            "internalenergy":   "U",
            "u":                "U",
            "speedofsound":     "speed_of_sound",
            "c":                "speed_of_sound",
            "sonicvelocity":    "speed_of_sound",
            "compressibility":  "__Z",
            "z":                "__Z",
        }

        prop_key  = prop.lower().replace(" ", "").replace("_", "")
        cp_prop   = PROP_MAP.get(prop_key)
        if cp_prop is None:
            raise ValueError(
                f"Unknown property '{prop}'. "
                f"Valid options: {', '.join(sorted(set(PROP_MAP.keys())))}"
            )

        # Special case: compressibility Z
        if cp_prop == "__Z":
            raw = self._extract_all(fluid_cp, in1, v1, in2, v2)
            return raw.get("Z") or float("nan")

        val = _safe_prop(cp_prop, in1, v1, in2, v2, fluid_cp)
        if val is None:
            raise ValueError(f"Could not compute '{prop}' for {fluid_cp} at given state.")

        # Convert to engineering units
        if cp_prop == "D" and prop_key in ("volume", "specificvolume", "v"):
            return 1.0 / val  # m³/kg
        if cp_prop == "T":
            return val - 273.15 if unit == "SI" else val * 9/5 - 459.67
        if cp_prop == "P":
            return val / 1e3 if unit == "SI" else val / 6894.757
        if cp_prop in ("H", "U"):
            return val / 1e3 if unit == "SI" else val / 2326.0
        if cp_prop == "S":
            return val / 1e3 if unit == "SI" else val / 4186.8
        if cp_prop in ("Cpmass", "Cvmass"):
            return val / 1e3 if unit == "SI" else val / 4186.8

        return val  # dimensionless or already in natural units

    def get_fluid_list(self) -> Dict[str, Any]:
        """Return the full fluid registry. Called by GET /fluids."""
        return get_registry_response()


    def generate_superheated_table(
        self,
        fluid_str: str,
        P_Pa: float,
        T_start_K: float,
        T_end_K: float,
        n_points: int,
        si: bool = True
    ) -> Dict[str, Any]:
        fluid_cp = resolve_fluid(fluid_str)
        T_sat = _safe_prop("T", "P", P_Pa, "Q", 0.0, fluid_cp)
        
        range_vals = np.linspace(T_start_K, T_end_K, n_points)
        
        rows = []
        # Optionally insert saturation row if T_sat falls in or near range
        if T_sat is not None and T_start_K <= T_sat <= T_end_K:
            range_vals = sorted(list(set(list(range_vals) + [T_sat + 0.01]))) # slightly above sat

        for T in range_vals:
            try:
                def sp(prop): return _safe_prop(prop, "P", P_Pa, "T", T, fluid_cp)
                
                vl = sp("D")
                ul = sp("U")
                hl = sp("H")
                sl = sp("S")
                
                def safe_1_over(d): return 1.0/d if d and d > 0 else None
                def safe_div(v, f): return v / f if v is not None else None
                
                if si:
                    rows.append({
                        "T_C": round(T - 273.15, 4),
                        "v_m3kg": round(safe_1_over(vl), 6) if vl else None,
                        "u_kJkg": round(safe_div(ul, 1e3), 4) if ul else None,
                        "h_kJkg": round(safe_div(hl, 1e3), 4) if hl else None,
                        "s_kJkgK": round(safe_div(sl, 1e3), 6) if sl else None,
                    })
                else:
                    rows.append({
                        "T_F": round(T * 9/5 - 459.67, 4),
                        "v_ft3lbm": round(safe_1_over(vl) * 16.01846, 6) if vl else None,
                        "u_BTUlb": round(safe_div(ul, 2326.0), 4) if ul else None,
                        "h_BTUlb": round(safe_div(hl, 2326.0), 4) if hl else None,
                        "s_BTUlbR": round(safe_div(sl, 4186.8), 6) if sl else None,
                    })
            except:
                pass
                
        # Also return T_sat for UI reference
        T_sat_out = None
        if T_sat:
            T_sat_out = round(T_sat - 273.15, 4) if si else round(T_sat * 9/5 - 459.67, 4)
            
        return {
            "fluid": fluid_str,
            "P_fixed": round(P_Pa/1e3, 4) if si else round(P_Pa/6894.757, 4),
            "T_sat": T_sat_out,
            "n_rows": len(rows),
            "rows": rows
        }
