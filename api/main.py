"""
ChemEng Thermodynamic API — FastAPI Application
================================================
RESTful API providing accurate thermodynamic properties for chemical engineers.

Standards: IAPWS-IF97, Span & Wagner, Leachman et al., ASHRAE 34, NIST REFPROP-equivalent.
Engine:    CoolProp 6.x (open-source, NIST-validated)
Accuracy:  ±0.01–0.05% for most fluids and states.

Run locally:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Docker:
    docker build -t chemeng-api .
    docker run -p 8000:8000 chemeng-api
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import CoolProp as _CP_pkg          # top-level package — has __version__
import CoolProp.CoolProp as CP      # C extension module — calculation functions
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.engine import ThermodynamicEngine
from core.fluids import FLUID_REGISTRY
from core.models import (
    PropertyRequest,
    SaturationRequest,
    HealthResponse,
    ErrorResponse,
)

# ============================================================
# APP SETUP
# ============================================================

app = FastAPI(
    title="ChemEng Thermodynamic API",
    description=(
        "Accurate thermodynamic properties for chemical engineers. "
        "Powered by CoolProp and NIST/IAPWS international standards. "
        "Supports 20+ fluids including sCO₂, Green H₂, Ammonia (R717), "
        "R-1234yf, R-1234ze, and all common refrigerants and gases."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name":  "ChemEng Thermodynamic Calculator",
        "email": "contact@chemengcalc.io",
    },
    license_info={
        "name": "MIT",
        "url":  "https://opensource.org/licenses/MIT",
    },
)

# Allow cross-origin requests from React web app, Excel, etc.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # In production: restrict to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Singleton engine instance (CoolProp is stateless, so this is safe)
engine = ThermodynamicEngine()


# ============================================================
# MIDDLEWARE: Request timing
# ============================================================

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Process-Time-ms"] = f"{duration_ms:.2f}"
    return response


# ============================================================
# EXCEPTION HANDLERS
# ============================================================

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=422,
        content={
            "error":  "Validation Error",
            "detail": str(exc),
            "hint":   "GET /fluids for supported fluids. GET /docs for API reference.",
        },
    )


# ============================================================
# ROOT & HEALTH
# ============================================================

@app.get("/", tags=["Info"])
async def root() -> Dict[str, Any]:
    """API root — returns metadata and version info."""
    return {
        "name":         "ChemEng Thermodynamic API",
        "version":      "1.0.0",
        "description":  "Accurate thermodynamic properties for 20+ fluids",
        "engine":       f"CoolProp {_CP_pkg.__version__}",
        "standards":    [
            "IAPWS-IF97 / IAPWS-95  (Water/Steam)",
            "Span & Wagner EOS       (CO₂ / sCO₂)",
            "Leachman et al. EOS     (H₂ / Green Hydrogen)",
            "Gao et al. EOS          (Ammonia / R717)",
            "Richter et al. EOS      (R-1234yf, ASHRAE 34)",
            "Thol & Lemmon EOS       (R-1234ze, ASHRAE 34)",
            "NIST Helmholtz EOS      (all other fluids)",
        ],
        "accuracy":     "±0.01–0.05% (equivalent to NIST REFPROP 9.1+)",
        "total_fluids": len(FLUID_REGISTRY),
        "endpoints": {
            "docs":             "/docs",
            "fluids":           "/fluids",
            "properties":       "POST /properties",
            "single_property":  "GET  /property",
            "saturation":       "POST /saturation",
            "saturation_table": "GET  /saturation-table",
            "phase_curve":      "GET  /phase-curve",
            "health":           "GET  /health",
        },
    }


@app.get("/health", response_model=HealthResponse, tags=["Info"])
async def health() -> HealthResponse:
    """Health check — verifies CoolProp is functional."""
    # Quick sanity: saturation T of water at 100°C should be ~101.325 kPa
    try:
        P_check = CP.PropsSI("P", "T", 373.15, "Q", 0, "Water") / 1e3
        assert abs(P_check - 101.325) < 1.0, f"Unexpected P_sat: {P_check}"
        status = "healthy"
        msg    = f"CoolProp functional. Water P_sat(100°C) = {P_check:.3f} kPa ✓"
    except Exception as e:
        status = "degraded"
        msg    = f"CoolProp check failed: {e}"

    return HealthResponse(
        status=status,
        coolprop_version=_CP_pkg.__version__,
        supported_fluid_count=len(FLUID_REGISTRY),
        message=msg,
    )


# ============================================================
# FLUIDS
# ============================================================

@app.get("/fluids", tags=["Fluids"])
async def list_fluids() -> Dict[str, Any]:
    """
    List all supported fluids with their international standards,
    peer-reviewed references, accuracy ratings, and aliases.

    Use the `name` or any value from `aliases` in the `fluid` field
    of POST /properties.
    """
    return engine.get_fluid_list()


# ============================================================
# CORE: FULL PROPERTY SET
# ============================================================

@app.post("/properties", tags=["Thermodynamic Properties"])
async def get_properties(request: PropertyRequest) -> Dict[str, Any]:
    """
    **Primary endpoint.** Calculate all thermodynamic and transport properties
    for a fluid given exactly two independent intensive state variables.

    ### State Postulate
    Two independent intensive properties fix the thermodynamic state of a
    pure single-component system (Gibbs Phase Rule for single-phase).
    - Single-phase (superheated, compressed liquid): any 2 of {T, P, H, S}
    - Saturation / two-phase: T+Q or P+Q (where Q = vapor quality 0–1)
    - Flash: P+H or P+S or T+S

    ### Returns
    All of: T, P, h, s, v, ρ, u, x, Cₚ, Cᵥ, μ, k, Pr, Z, speed of sound,
    plus phase identification, governing standard, and accuracy rating.

    ### Example (sCO₂ in supercritical region)
    ```json
    {"fluid": "sCO2", "T": 35, "P": 80, "T_unit": "C", "P_unit": "bar"}
    ```
    """
    try:
        return engine.calculate(request)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Calculation failed: {str(e)}. Check that inputs are within the valid range for the fluid."
        )


# ============================================================
# EXCEL / SHEETS OPTIMIZED: SINGLE PROPERTY
# ============================================================

@app.get("/property", tags=["Spreadsheet Integration"])
async def get_single_property(
    fluid: str  = Query(...,    description="Fluid name or alias (e.g. 'sCO2', 'H2', 'R1234yf')"),
    prop:  str  = Query(...,    description="Property name: Density, Enthalpy, Entropy, Temperature, Pressure, Quality, Cp, Cv, Viscosity, Conductivity, Prandtl, Volume, InternalEnergy, SpeedOfSound, Compressibility"),
    in1:   str  = Query(...,    description="First input identifier: T, P, H, S, Q"),
    v1:    float= Query(...,    description="Value of first input (in SI units: K, Pa, J/kg, J/kg/K)"),
    in2:   str  = Query(...,    description="Second input identifier: T, P, H, S, Q"),
    v2:    float= Query(...,    description="Value of second input (in SI units)"),
    unit:  str  = Query("SI",   description="Output unit system: SI or Imperial"),
) -> Dict[str, Any]:
    """
    **Spreadsheet-optimized endpoint.** Returns a single scalar property value.
    This is called by the Excel `=THERMO()` add-in formula.

    ### Excel Formula Syntax
    ```
    =THERMO("sCO2",  "Density",  "T", A2, "P", B2)
    =THERMO("Water", "Enthalpy", "T", C5, "Q", 1)
    =THERMO("NH3",   "Entropy",  "P", D3, "H", E3)
    ```

    ### Input Units (always SI for the API; Excel add-in converts)
    - T → Kelvin [K]
    - P → Pascal [Pa]
    - H → J/kg
    - S → J/kg/K
    - Q → dimensionless [0–1]
    """
    try:
        value = engine.get_single_property(fluid, prop, in1, v1, in2, v2, unit)
        return {
            "fluid":    fluid,
            "property": prop,
            "value":    value,
            "inputs":   {in1: v1, in2: v2},
        }
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation error: {e}")


# ============================================================
# SATURATION
# ============================================================

@app.post("/saturation", tags=["Saturation Properties"])
async def get_saturation(request: SaturationRequest) -> Dict[str, Any]:
    """
    Get saturated liquid **and** saturated vapor properties at a given
    temperature **or** pressure.

    Also returns:
    - h_fg  (latent heat of vaporization, kJ/kg)
    - s_fg  (entropy of vaporization, kJ/kg·K)
    - u_fg  (internal energy of vaporization, kJ/kg)

    ### Example
    ```json
    {"fluid": "Water", "T": 100, "T_unit": "C"}
    ```
    Expected: h_fg ≈ 2256.5 kJ/kg (matches textbook steam tables)
    """
    try:
        return engine.calculate_saturation(request)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Saturation calculation failed: {e}")


@app.get("/saturation-table", tags=["Saturation Properties"])
async def saturation_table(
    fluid:       str   = Query("Water", description="Fluid name or alias"),
    by_pressure: bool  = Query(False, description="Generate table by pressure increments instead of temperature"),
    start_val:   float = Query(0.0, description="Start value (C or F for Temp, kPa or psi for Pressure)"),
    end_val:     float = Query(200.0, description="End value"),
    n_points:    int   = Query(20, description="Number of rows", ge=5, le=200),
    T_unit:      str   = Query("C", description="Temperature unit"),
    output_units:str   = Query("SI", description="SI or Imperial")
) -> Dict[str, Any]:
    """
    Generate a **textbook-style saturation property table** like the appendices
    in Çengel & Boles, Perry's Handbook, or CRC Handbook.
    """
    try:
        is_si = (output_units.upper() == "SI")
        if by_pressure:
            P_start_Pa = start_val * 1e3 if is_si else start_val * 6894.757
            P_end_Pa   = end_val * 1e3 if is_si else end_val * 6894.757
            return engine.generate_saturation_table(
                fluid_str=fluid, T_start_K=None, T_end_K=None, n_points=n_points,
                by_pressure=True, P_start_Pa=P_start_Pa, P_end_Pa=P_end_Pa, si=is_si
            )
        else:
            T_start_K = start_val + 273.15 if is_si else (start_val + 459.67) * 5/9
            T_end_K   = end_val   + 273.15 if is_si else (end_val   + 459.67) * 5/9
            return engine.generate_saturation_table(
                fluid_str=fluid, T_start_K=T_start_K, T_end_K=T_end_K, n_points=n_points,
                by_pressure=False, P_start_Pa=None, P_end_Pa=None, si=is_si
            )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Table generation failed: {e}")


# ============================================================
# PHASE CURVE (for React charts)
# ============================================================

@app.get("/phase-curve", tags=["Phase Diagrams"])
async def phase_curve(
    fluid:    str = Query("Water", description="Fluid name or alias"),
    n_points: int = Query(150,     description="Number of saturation curve points", ge=20, le=500),
) -> Dict[str, Any]:
    """
    Return the **saturation dome** coordinates for plotting T-s and P-h diagrams.
    Used by the Phase 3 React web canvas to draw interactive phase diagrams.

    Returns arrays for:
    - T-s diagram: T_C, s_liq_kJkgK, s_vap_kJkgK
    - P-h diagram: P_sat_kPa, h_liq_kJkg, h_vap_kJkg
    - Critical point coordinates

    Drag a state point on the chart → frontend calls POST /properties with
    the dragged coordinates → sidebar updates in real time.
    """
    try:
        return engine.get_phase_curve(fluid, n_points)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Phase curve generation failed: {e}")


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

@app.get("/superheated-table", tags=["Superheated Properties"])
async def superheated_table(
    fluid:       str   = Query("Water", description="Fluid name or alias"),
    P_val:       float = Query(100.0, description="Fixed pressure (kPa or psi)"),
    T_start:     float = Query(100.0, description="Start temperature (C or F)"),
    T_end:       float = Query(500.0, description="End temperature (C or F)"),
    n_points:    int   = Query(20, description="Number of rows", ge=5, le=200),
    output_units:str   = Query("SI", description="SI or Imperial")
) -> Dict[str, Any]:
    is_si = (output_units.upper() == "SI")
    P_Pa = P_val * 1e3 if is_si else P_val * 6894.757
    T_start_K = T_start + 273.15 if is_si else (T_start + 459.67) * 5/9
    T_end_K   = T_end   + 273.15 if is_si else (T_end   + 459.67) * 5/9
    
    return engine.generate_superheated_table(
        fluid_str=fluid,
        P_Pa=P_Pa,
        T_start_K=T_start_K,
        T_end_K=T_end_K,
        n_points=n_points,
        si=is_si
    )
