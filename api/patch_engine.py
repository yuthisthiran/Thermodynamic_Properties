import re

with open(r"d:\Downloads\ChemEng\api\core\engine.py", "r", encoding="utf-8") as f:
    engine_code = f.read()

superheated_method = """
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
"""

if "def generate_superheated_table" not in engine_code:
    engine_code = engine_code + "\n" + superheated_method
    with open(r"d:\Downloads\ChemEng\api\core\engine.py", "w", encoding="utf-8") as f:
        f.write(engine_code)
    print("Added generate_superheated_table to engine.py")
