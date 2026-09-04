"""
Fluid Registry for ChemEng Thermodynamic API
=============================================
Maps user-friendly fluid names and aliases to CoolProp internal names,
and records the governing international standard for each fluid.

All equations of state implemented here are published in peer-reviewed
journals and adopted by NIST, ASHRAE, IAPWS, or IUPAC.

Data source: CoolProp 6.x (open-source, NIST REFPROP-equivalent accuracy)
"""

from typing import Dict, Any, Optional


# ============================================================
# FLUID REGISTRY
# ============================================================
# Key: canonical display name
# Value: metadata dict including coolprop_name, aliases, standard, accuracy
# ============================================================

FLUID_REGISTRY: Dict[str, Dict[str, Any]] = {

    # ---- Water / Steam ---------------------------------------------------
    "Water": {
        "coolprop_name": "Water",
        "aliases": ["water", "steam", "H2O", "h2o", "Water/Steam", "IAPWS97", "iapws"],
        "standard": "IAPWS-IF97 (2007 revision) + IAPWS-95",
        "reference": "Wagner & Kruse, IAPWS, 2007; Wagner & Pruß, J. Phys. Chem. Ref. Data 31(2), 2002",
        "accuracy": "±0.001%",
        "category": "Classic Utility Fluid",
        "T_min_C": 0.01,
        "T_max_C": 1999.85,
        "P_max_MPa": 100.0,
        "note": "Industry-standard formulation for power generation, process steam, HVAC.",
    },

    # ---- Next-Gen: Supercritical CO₂ ------------------------------------
    "CO2": {
        "coolprop_name": "CO2",
        "aliases": [
            "CO2", "co2", "sCO2", "sco2", "supercritical_co2", "CarbonDioxide",
            "carbon_dioxide", "CO₂", "R744",
        ],
        "standard": "Span & Wagner Helmholtz EOS",
        "reference": "Span & Wagner, J. Phys. Chem. Ref. Data 25(6), 1509–1596, 1996",
        "accuracy": "±0.03–0.05%",
        "category": "Next-Gen: sCO₂ Power Cycles / Carbon Capture",
        "T_min_C": -56.56,   # Triple point
        "T_max_C": 826.85,
        "P_max_MPa": 800.0,
        "critical_T_C": 30.98,
        "critical_P_bar": 73.77,
        "note": (
            "Critical point: 31.0°C, 73.8 bar. Above these conditions → supercritical region. "
            "Used in sCO₂ Brayton cycles (efficiency >50%), direct air capture, EOR, CCUS."
        ),
    },

    # ---- Next-Gen: Green Hydrogen ----------------------------------------
    "Hydrogen": {
        "coolprop_name": "Hydrogen",
        "aliases": [
            "H2", "h2", "hydrogen", "NormalHydrogen", "normal_hydrogen",
            "GreenHydrogen", "green_hydrogen", "H₂",
        ],
        "standard": "Leachman, Jacobsen, Penoncello & Lemmon Helmholtz EOS",
        "reference": "Leachman et al., J. Phys. Chem. Ref. Data 38(3), 721–748, 2009",
        "accuracy": "±0.04%",
        "category": "Next-Gen: Green Hydrogen Energy",
        "T_min_C": -259.20,
        "T_max_C": 1226.85,
        "P_max_MPa": 2000.0,
        "critical_T_C": -240.00,
        "critical_P_bar": 13.15,
        "note": "Normal hydrogen (25% para, 75% ortho). For storage/transport at cryogenic temperatures, use ParaHydrogen.",
    },

    "ParaHydrogen": {
        "coolprop_name": "ParaHydrogen",
        "aliases": ["pH2", "parahydrogen", "para_hydrogen", "para-hydrogen", "pH₂"],
        "standard": "Leachman, Jacobsen, Penoncello & Lemmon Helmholtz EOS",
        "reference": "Leachman et al., J. Phys. Chem. Ref. Data 38(3), 721–748, 2009",
        "accuracy": "±0.04%",
        "category": "Next-Gen: Liquid Hydrogen Storage & Transport",
        "T_min_C": -271.15,
        "T_max_C": 726.85,
        "P_max_MPa": 2000.0,
        "note": "Equilibrium hydrogen at cryogenic temperatures (>99% para). Critical for LH₂ storage, fuel cell vehicles.",
    },

    # ---- Next-Gen: Ammonia / Green NH₃ ----------------------------------
    "Ammonia": {
        "coolprop_name": "Ammonia",
        "aliases": [
            "NH3", "nh3", "ammonia", "R717", "r717",
            "GreenAmmonia", "green_ammonia", "NH₃",
        ],
        "standard": "Gao, Wu, Bell & Lemmon Helmholtz EOS",
        "reference": "Gao et al., J. Phys. Chem. Ref. Data 52, 013102, 2023; "
                     "Tillner-Roth & Friend, J. Phys. Chem. Ref. Data 27(1), 63–96, 1998",
        "accuracy": "±0.02%",
        "category": "Next-Gen: Green NH₃ / Industrial Refrigeration (R717)",
        "T_min_C": -77.65,
        "T_max_C": 726.85,
        "P_max_MPa": 1000.0,
        "critical_T_C": 132.41,
        "critical_P_bar": 113.33,
        "note": (
            "Zero GWP, zero ODP. Used as green energy carrier, long-distance H₂ transport vector, "
            "and in industrial refrigeration (food, petrochemical). ASHRAE Safety Group B2/L2."
        ),
    },

    # ---- Low-GWP Refrigerants: HFOs -------------------------------------
    "R1234yf": {
        "coolprop_name": "R1234yf",
        "aliases": [
            "R1234yf", "r1234yf", "HFO1234yf", "HFO-1234yf",
            "2,3,3,3-Tetrafluoropropene", "R-1234yf",
        ],
        "standard": "Richter, McLinden & Lemmon Helmholtz EOS — ASHRAE 34",
        "reference": "Richter et al., Int. J. Refrig. 34(3), 715–728, 2011 | ASHRAE Standard 34-2022",
        "accuracy": "±0.05%",
        "category": "Low-GWP Refrigerant (GWP₁₀₀ = 4)",
        "T_min_C": -115.09,
        "T_max_C": 166.85,
        "P_max_MPa": 30.0,
        "critical_T_C": 94.70,
        "critical_P_bar": 33.82,
        "note": (
            "ASHRAE A2L (mildly flammable). Drop-in replacement for R-134a in mobile air conditioning (MAC). "
            "EU MAC Directive mandates GWP < 150. Adopted by automotive OEMs globally."
        ),
    },

    "R1234ze": {
        "coolprop_name": "R1234ze(E)",
        "aliases": [
            "R1234ze", "r1234ze", "HFO1234ze", "HFO-1234ze", "R1234ze(E)",
            "R-1234ze", "R-1234ze(E)", "trans-1234ze",
        ],
        "standard": "Thol & Lemmon Helmholtz EOS — ASHRAE 34",
        "reference": "Thol & Lemmon, Int. J. Thermophys. 37(3), 28, 2016 | ASHRAE Standard 34-2022",
        "accuracy": "±0.05%",
        "category": "Low-GWP Refrigerant (GWP₁₀₀ = 7)",
        "T_min_C": -114.55,
        "T_max_C": 161.85,
        "P_max_MPa": 25.0,
        "critical_T_C": 109.36,
        "critical_P_bar": 36.36,
        "note": (
            "ASHRAE A2L. Used in centrifugal chillers and foam blowing agents. "
            "Better thermodynamic properties than R-1234yf for large-tonnage commercial refrigeration."
        ),
    },

    # ---- Classic Refrigerants -------------------------------------------
    "R134a": {
        "coolprop_name": "R134a",
        "aliases": ["R134a", "r134a", "HFC134a", "HFC-134a", "R-134a", "1,1,1,2-Tetrafluoroethane"],
        "standard": "Tillner-Roth & Baehr Helmholtz EOS — ASHRAE 34",
        "reference": "Tillner-Roth & Baehr, J. Phys. Chem. Ref. Data 23(5), 657–729, 1994",
        "accuracy": "±0.02%",
        "category": "HFC Refrigerant (GWP₁₀₀ = 1430)",
        "T_min_C": -103.30,
        "T_max_C": 101.06,
        "P_max_MPa": 70.0,
        "note": "Being phased out under Kigali Amendment. Legacy systems only.",
    },

    "R410A": {
        "coolprop_name": "R410A",
        "aliases": ["R410A", "r410a", "R-410A", "AZ-20"],
        "standard": "Lemmon Pseudo-Pure Mixture EOS — ASHRAE 34",
        "reference": "Lemmon, Int. J. Thermophys. 24(4), 991–1006, 2003",
        "accuracy": "±0.1%",
        "category": "HFC Blend Refrigerant (GWP₁₀₀ = 2088)",
        "T_min_C": -72.56,
        "T_max_C": 71.85,
        "P_max_MPa": 50.0,
        "note": "Phase-out scheduled under Kigali Amendment by 2024–2030 (region-dependent). Being replaced by R-32, R-454B.",
    },

    "R32": {
        "coolprop_name": "R32",
        "aliases": ["R32", "r32", "R-32", "Difluoromethane", "HFC-32"],
        "standard": "Tillner-Roth Helmholtz EOS — ASHRAE 34",
        "reference": "Tillner-Roth, Int. J. Thermophys. 16(1), 91–100, 1995",
        "accuracy": "±0.03%",
        "category": "Lower-GWP HFC Refrigerant (GWP₁₀₀ = 675)",
        "T_min_C": -136.81,
        "T_max_C": 78.11,
        "P_max_MPa": 70.0,
        "note": "ASHRAE A2L. Increasingly used in residential heat pumps and split systems.",
    },

    "R22": {
        "coolprop_name": "R22",
        "aliases": ["R22", "r22", "R-22", "HCFC-22", "Chlorodifluoromethane"],
        "standard": "Kamei & Beyerlein Helmholtz EOS — ASHRAE 34",
        "reference": "Kamei & Beyerlein, Int. J. Refrig. 18(2), 80–92, 1995",
        "accuracy": "±0.03%",
        "category": "HCFC Refrigerant (ODP=0.055, GWP=1760) — Phase-Out Complete",
        "note": "Fully phased out in developed countries (Montreal Protocol). Legacy data only.",
    },

    # ---- Common Engineering Fluids --------------------------------------
    "Air": {
        "coolprop_name": "Air",
        "aliases": ["air", "Air", "drY_AIR", "dry_air"],
        "standard": "Lemmon, Jacobsen, Penoncello & Friend Pseudo-Pure EOS",
        "reference": "Lemmon et al., J. Phys. Chem. Ref. Data 29(3), 331–385, 2000",
        "accuracy": "±0.02%",
        "category": "Common Gas",
        "note": "Dry air treated as pseudo-pure fluid. Composition: 78.12% N₂, 20.96% O₂, 0.92% Ar.",
    },

    "Nitrogen": {
        "coolprop_name": "Nitrogen",
        "aliases": ["N2", "n2", "nitrogen", "N₂"],
        "standard": "Span, Lemmon, Jacobsen & Wagner Helmholtz EOS",
        "reference": "Span et al., J. Phys. Chem. Ref. Data 29(6), 1361–1433, 2000",
        "accuracy": "±0.02%",
        "category": "Common Gas",
    },

    "Oxygen": {
        "coolprop_name": "Oxygen",
        "aliases": ["O2", "o2", "oxygen", "O₂"],
        "standard": "Schmidt & Wagner Helmholtz EOS",
        "reference": "Schmidt & Wagner, Fluid Phase Equilib. 19(3), 175–200, 1985",
        "accuracy": "±0.02%",
        "category": "Common Gas",
    },

    "Methane": {
        "coolprop_name": "Methane",
        "aliases": ["CH4", "ch4", "methane", "natural_gas", "CH₄"],
        "standard": "Setzmann & Wagner Helmholtz EOS",
        "reference": "Setzmann & Wagner, J. Phys. Chem. Ref. Data 20(6), 1061–1155, 1991",
        "accuracy": "±0.02%",
        "category": "Hydrocarbon / Natural Gas",
    },

    "Propane": {
        "coolprop_name": "Propane",
        "aliases": ["C3H8", "c3h8", "propane", "R290", "r290", "C₃H₈"],
        "standard": "Lemmon, McLinden & Wagner Helmholtz EOS",
        "reference": "Lemmon et al., J. Phys. Chem. Ref. Data 38(4), 721–748, 2009",
        "accuracy": "±0.01%",
        "category": "Hydrocarbon / Low-GWP Refrigerant (R290, GWP=3)",
        "note": "Natural refrigerant. ASHRAE A3 (flammable). Used in domestic refrigerators, heat pumps.",
    },

    "Ethane": {
        "coolprop_name": "Ethane",
        "aliases": ["C2H6", "c2h6", "ethane", "R170", "C₂H₆"],
        "standard": "Bücker & Wagner Helmholtz EOS",
        "reference": "Bücker & Wagner, J. Phys. Chem. Ref. Data 35(2), 205–266, 2006",
        "accuracy": "±0.02%",
        "category": "Hydrocarbon / Cryogenic Refrigerant (R170)",
    },

    "n-Butane": {
        "coolprop_name": "n-Butane",
        "aliases": ["nC4H10", "butane", "n_butane", "R600", "nButane"],
        "standard": "Bücker & Wagner Helmholtz EOS",
        "reference": "Bücker & Wagner, J. Phys. Chem. Ref. Data 35(2), 929–1019, 2006",
        "accuracy": "±0.02%",
        "category": "Hydrocarbon / Low-GWP Refrigerant (R600, GWP=4)",
    },

    "IsoButane": {
        "coolprop_name": "IsoButane",
        "aliases": ["iC4H10", "isobutane", "iso_butane", "R600a", "R-600a"],
        "standard": "Bücker & Wagner Helmholtz EOS",
        "reference": "Bücker & Wagner, J. Phys. Chem. Ref. Data 35(2), 929–1019, 2006",
        "accuracy": "±0.02%",
        "category": "Low-GWP Refrigerant (R600a, GWP=3)",
        "note": "Natural refrigerant. ASHRAE A3. Used in domestic refrigerators, vending machines.",
    },

    "HydrogenSulfide": {
        "coolprop_name": "HydrogenSulfide",
        "aliases": ["H2S", "h2s", "hydrogen_sulfide", "H₂S"],
        "standard": "Lemmon & Span Short Helmholtz EOS",
        "reference": "Lemmon & Span, J. Chem. Eng. Data 51(3), 785–850, 2006",
        "accuracy": "±0.05%",
        "category": "Sour Gas / Acid Gas Processing",
    },

    "Toluene": {
        "coolprop_name": "Toluene",
        "aliases": ["toluene", "methylbenzene", "C7H8"],
        "standard": "Lemmon & Span Short Helmholtz EOS",
        "reference": "Lemmon & Span, J. Chem. Eng. Data 51(3), 785–850, 2006",
        "accuracy": "±0.05%",
        "category": "Organic Solvent / ORC Working Fluid",
        "note": "Common working fluid in Organic Rankine Cycles (ORC) for waste heat recovery.",
    },

    "Ethanol": {
        "coolprop_name": "Ethanol",
        "aliases": ["ethanol", "EtOH", "C2H5OH", "alcohol"],
        "standard": "Schroeder et al. Helmholtz EOS",
        "reference": "Schroeder et al., J. Phys. Chem. Ref. Data 43, 043102, 2014",
        "accuracy": "±0.05%",
        "category": "Biofuel / Solvent",
    },
}


# ============================================================
# ALIAS MAP (built at import time)
# ============================================================
def _build_alias_map() -> Dict[str, str]:
    """Build a flat alias → CoolProp fluid name dictionary."""
    alias_map: Dict[str, str] = {}
    for canonical, info in FLUID_REGISTRY.items():
        cp_name = info["coolprop_name"]
        alias_map[canonical.lower()] = cp_name
        alias_map[cp_name.lower()] = cp_name
        for alias in info.get("aliases", []):
            alias_map[alias.lower()] = cp_name
    return alias_map


ALIAS_MAP: Dict[str, str] = _build_alias_map()


def resolve_fluid(fluid_str: str) -> str:
    """
    Resolve any fluid name/alias to the CoolProp fluid name.

    Args:
        fluid_str: Any supported name or alias (e.g. 'sCO2', 'H2O', 'R717')

    Returns:
        CoolProp internal fluid name (e.g. 'CO2', 'Water', 'Ammonia')

    Raises:
        ValueError: If the fluid is not recognized
    """
    resolved = ALIAS_MAP.get(fluid_str.lower())
    if resolved is None:
        raise ValueError(
            f"Unknown fluid: '{fluid_str}'. "
            f"Supported fluids: {', '.join(FLUID_REGISTRY.keys())}. "
            f"GET /fluids for the full list with aliases."
        )
    return resolved


def get_fluid_metadata(fluid_str: str) -> Dict[str, Any]:
    """Return the full metadata dict for a given fluid name/alias."""
    cp_name = resolve_fluid(fluid_str)
    for info in FLUID_REGISTRY.values():
        if info["coolprop_name"] == cp_name:
            return info
    return {}


def get_registry_response() -> Dict[str, Any]:
    """Return the full fluid registry formatted for the /fluids API endpoint."""
    return {
        "engine": "CoolProp 6.x",
        "engine_accuracy": "Equivalent to NIST REFPROP 9.1+ (±0.01–0.05% for most properties)",
        "total_fluids": len(FLUID_REGISTRY),
        "standards_bodies": ["IAPWS", "NIST", "ASHRAE", "IUPAC", "ISO"],
        "fluids": [
            {
                "name": canonical,
                "coolprop_name": info["coolprop_name"],
                "aliases": info.get("aliases", []),
                "standard": info.get("standard", ""),
                "reference": info.get("reference", ""),
                "accuracy": info.get("accuracy", ""),
                "category": info.get("category", ""),
                "note": info.get("note", ""),
                "T_min_C": info.get("T_min_C"),
                "T_max_C": info.get("T_max_C"),
                "P_max_MPa": info.get("P_max_MPa"),
            }
            for canonical, info in FLUID_REGISTRY.items()
        ],
    }
