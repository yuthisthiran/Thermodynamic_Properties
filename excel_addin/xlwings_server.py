"""
ChemEng Thermodynamic API — Excel Add-in Backend
=================================================
xlwings-based local Python server that powers the =THERMO() Excel UDF.

This server runs locally on the engineer's machine. Excel VBA calls it
via localhost HTTP. No internet connection required — it talks directly
to CoolProp.

For cloud-connected mode: engineers can point the VBA module at the
deployed Phase 1 API URL instead.

Usage:
    pip install xlwings CoolProp fastapi uvicorn
    python xlwings_server.py

Then in Excel: enable the ChemThermo.xlam add-in and use:
    =THERMO("sCO2", "Density", "T", 308.15, "P", 8000000)
    =THERMO("Water", "Enthalpy", "T", 373.15, "Q", 1)
    =THERMO_FULL("NH3", "T", -10, "Q", 1, "C")  → JSON string of all props

Author: ChemEng Thermodynamic Calculator
"""

from __future__ import annotations

import json
import sys
import os

# Add parent directory to path so we can import the core engine
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
import uvicorn

from core.engine import ThermodynamicEngine
from core.fluids import resolve_fluid

# ============================================================
# LOCAL SERVER APP (separate from the main API for Excel use)
# ============================================================

app = FastAPI(
    title="ChemEng Excel Add-in Server",
    description=(
        "Local server powering the =THERMO() Excel UDF. "
        "Runs on localhost:8765. Called by ChemThermo.xlam VBA."
    ),
    version="1.0.0",
    docs_url="/docs",
)

engine = ThermodynamicEngine()

LOCAL_PORT = 8765   # Fixed port that VBA module expects


# ============================================================
# EXCEL UDF ENDPOINTS
# ============================================================

@app.get("/thermo")
async def thermo_formula(
    fluid:  str   = Query(..., description="Fluid alias"),
    prop:   str   = Query(..., description="Property name"),
    in1:    str   = Query(..., description="Input 1 type (T/P/H/S/Q)"),
    v1:     float = Query(..., description="Input 1 value (SI units)"),
    in2:    str   = Query(..., description="Input 2 type"),
    v2:     float = Query(..., description="Input 2 value (SI units)"),
    unit:   str   = Query("SI"),
) -> float:
    """
    Single-value endpoint for the Excel =THERMO() formula.

    The VBA function converts from user units → SI before calling this endpoint,
    and converts the result back to the requested output unit.

    Returns a plain float (no JSON wrapper) for fast Excel parsing.
    """
    try:
        val = engine.get_single_property(fluid, prop, in1, v1, in2, v2, unit)
        return val
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.get("/thermo_full")
async def thermo_full(
    fluid:    str   = Query(...),
    in1:      str   = Query(...),
    v1:       float = Query(...),
    in2:      str   = Query(...),
    v2:       float = Query(...),
    v1_unit:  str   = Query("SI"),
    v2_unit:  str   = Query("SI"),
    out_unit: str   = Query("SI"),
) -> str:
    """
    Full property set as a compact JSON string.
    Used by the Excel =THERMO_FULL() formula to populate a 2-column range.
    """
    from core.models import PropertyRequest, TemperatureUnit, PressureUnit, UnitSystem

    req = PropertyRequest(
        fluid=fluid,
        **{in1: v1, in2: v2},
        output_units=UnitSystem(out_unit),
    )
    result = engine.calculate(req)
    props  = result["properties"]

    # Return compact flat dict: {prop_name: value, ...}
    flat = {k: v.get("value") for k, v in props.items() if v.get("value") is not None}
    flat["phase"] = result["phase"]
    flat["standard"] = result["standard"]

    return json.dumps(flat, ensure_ascii=False)


@app.get("/saturation")
async def saturation(
    fluid:  str   = Query("Water"),
    T_C:    float = Query(None),
    P_kPa:  float = Query(None),
) -> dict:
    """Saturation properties for Excel. Returns sat. liquid + vapor dict."""
    from core.models import SaturationRequest, TemperatureUnit, PressureUnit

    if T_C is not None:
        req = SaturationRequest(fluid=fluid, T=T_C, T_unit=TemperatureUnit.C)
    elif P_kPa is not None:
        req = SaturationRequest(fluid=fluid, P=P_kPa, P_unit=PressureUnit.kPa)
    else:
        raise HTTPException(422, "Provide T_C or P_kPa")

    return engine.calculate_saturation(req)


@app.get("/ping")
async def ping():
    """Used by Excel VBA to check if the server is running."""
    return {"status": "ok", "port": LOCAL_PORT}


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  ChemEng Excel Add-in Server")
    print(f"  Running at: http://localhost:{LOCAL_PORT}")
    print(f"  Docs:       http://localhost:{LOCAL_PORT}/docs")
    print()
    print("  Keep this window open while using =THERMO() in Excel.")
    print("  To stop: Ctrl+C")
    print("=" * 60)

    uvicorn.run(
        "xlwings_server:app",
        host="127.0.0.1",
        port=LOCAL_PORT,
        log_level="warning",
        reload=False,
    )
