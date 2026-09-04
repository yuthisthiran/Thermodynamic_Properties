import re

with open(r"d:\Downloads\ChemEng\api\main.py", "r", encoding="utf-8") as f:
    main_code = f.read()

# Replace the saturation_table endpoint to include by_pressure and fix inputs
old_sat_endpoint = """@app.get("/saturation-table", tags=["Saturation Properties"])
async def saturation_table(
    fluid:    str   = Query("Water",  description="Fluid name or alias"),
    T_start:  float = Query(0.0,      description="Start temperature (°C)"),
    T_end:    float = Query(200.0,    description="End temperature (°C)"),
    n_points: int   = Query(20,       description="Number of rows", ge=5, le=200),
    si:       bool  = Query(True,     description="True = SI units, False = Imperial"),
) -> Dict[str, Any]:"""

new_sat_endpoint = """@app.get("/saturation-table", tags=["Saturation Properties"])
async def saturation_table(
    fluid:       str   = Query("Water", description="Fluid name or alias"),
    by_pressure: bool  = Query(False, description="Generate table by pressure increments instead of temperature"),
    start_val:   float = Query(0.0, description="Start value (C or F for Temp, kPa or psi for Pressure)"),
    end_val:     float = Query(200.0, description="End value"),
    n_points:    int   = Query(20, description="Number of rows", ge=5, le=200),
    T_unit:      str   = Query("C", description="Temperature unit"),
    output_units:str   = Query("SI", description="SI or Imperial")
) -> Dict[str, Any]:"""

# We also need to fix how saturation_table calls engine.generate_saturation_table
old_sat_body = """    # Convert T_start/T_end to Kelvin
    T_start_K = T_start + 273.15 if si else (T_start + 459.67) * 5/9
    T_end_K   = T_end   + 273.15 if si else (T_end   + 459.67) * 5/9

    return engine.generate_saturation_table(
        fluid_str=fluid,
        T_start_K=T_start_K,
        T_end_K=T_end_K,
        n_points=n_points,
        si=si
    )"""

new_sat_body = """    is_si = (output_units.upper() == "SI")
    
    if by_pressure:
        # Convert start/end to Pa
        P_start_Pa = start_val * 1e3 if is_si else start_val * 6894.757
        P_end_Pa   = end_val * 1e3 if is_si else end_val * 6894.757
        return engine.generate_saturation_table(
            fluid_str=fluid, T_start_K=None, T_end_K=None, n_points=n_points,
            by_pressure=True, P_start_Pa=P_start_Pa, P_end_Pa=P_end_Pa, si=is_si
        )
    else:
        # Convert start/end to Kelvin
        T_start_K = start_val + 273.15 if is_si else (start_val + 459.67) * 5/9
        T_end_K   = end_val   + 273.15 if is_si else (end_val   + 459.67) * 5/9
        return engine.generate_saturation_table(
            fluid_str=fluid, T_start_K=T_start_K, T_end_K=T_end_K, n_points=n_points,
            by_pressure=False, P_start_Pa=None, P_end_Pa=None, si=is_si
        )"""

if old_sat_endpoint in main_code:
    main_code = main_code.replace(old_sat_endpoint, new_sat_endpoint)
    main_code = main_code.replace(old_sat_body, new_sat_body)
    
superheated_endpoint = """
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
"""

if "@app.get(\"/superheated-table\"" not in main_code:
    main_code += superheated_endpoint

with open(r"d:\Downloads\ChemEng\api\main.py", "w", encoding="utf-8") as f:
    f.write(main_code)
    
print("Patched main.py")
