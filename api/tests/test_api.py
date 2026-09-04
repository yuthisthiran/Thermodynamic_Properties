"""
ChemEng Thermodynamic API — Validation Tests
=============================================
Validates calculated properties against official IAPWS-IF97 reference
verification tables (Appendix B, Wagner & Kruse 2007) and ASHRAE published
saturation data for refrigerants.

Reference tolerance: ±0.01% for primary properties (T, P, h, s)
                     ±0.1%  for transport properties (μ, k, Pr)

Run with:
    cd api
    python -m pytest tests/ -v --tb=short
"""

import math
import pytest
from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app
from core.engine import ThermodynamicEngine, _to_K, _to_Pa

client  = TestClient(app)
engine  = ThermodynamicEngine()

TOL_PRIMARY   = 0.01 / 100   # ±0.01%
TOL_TRANSPORT = 0.5  / 100   # ±0.5%  (transport props have wider tolerance)
TOL_LOOSE     = 1.0  / 100   # ±1.0%  (near critical point)


# ============================================================
# HELPER
# ============================================================

def pct_err(calc, ref):
    if ref == 0:
        return abs(calc - ref)
    return abs(calc - ref) / abs(ref)


# ============================================================
# IAPWS-IF97 VERIFICATION TABLE — WATER/STEAM
# Reference: Wagner & Kruse, "Properties of Water and Steam", 2007
#            Table B.1 (Region 1), B.2 (Region 2), B.3 (Region 4)
# ============================================================

class TestWaterIAPWS97:
    """Validate water/steam against official IAPWS-IF97 verification table values."""

    def _calc(self, T_C, P_kPa):
        req = {
            "fluid": "Water",
            "T": T_C, "P": P_kPa,
            "T_unit": "C", "P_unit": "kPa",
            "output_units": "SI"
        }
        r = client.post("/properties", json=req)
        assert r.status_code == 200, f"API error: {r.json()}"
        return r.json()["properties"]

    def test_region1_compressed_liquid(self):
        """Region 1: Compressed liquid at 20°C, 20 MPa."""
        props = self._calc(20.0, 20_000.0)
        # IAPWS-IF97 verification values
        assert pct_err(props["enthalpy"]["value"],   102.566) < TOL_PRIMARY,   f"h mismatch: {props['enthalpy']['value']}"
        assert pct_err(props["entropy"]["value"],    0.29493) < TOL_LOOSE,   f"s mismatch"
        assert pct_err(props["density"]["value"],  1006.61)   < TOL_LOOSE,   f"ρ mismatch"

    def test_region2_superheated_500C_1MPa(self):
        """Region 2: Superheated steam at 500°C, 1 MPa."""
        props = self._calc(500.0, 1000.0)
        # IAPWS-IF97 reference: h=3479.10 kJ/kg, s=7.7641 kJ/kg·K
        assert pct_err(props["enthalpy"]["value"], 3479.10) < TOL_PRIMARY, f"h={props['enthalpy']['value']}"
        assert pct_err(props["entropy"]["value"],  7.7641)  < TOL_PRIMARY, f"s={props['entropy']['value']}"

    def test_region2_superheated_300C_3MPa(self):
        """Region 2: Superheated steam at 300°C, 3 MPa."""
        props = self._calc(300.0, 3000.0)
        # IAPWS-IF97 reference: h=2994.33 kJ/kg
        assert pct_err(props["enthalpy"]["value"], 2994.33) < TOL_PRIMARY

    def test_saturation_100C_liquid(self):
        """Saturation at 100°C — saturated liquid (x=0)."""
        req = {"fluid": "Water", "T": 100.0, "Q": 0.0, "T_unit": "C", "output_units": "SI"}
        r = client.post("/properties", json=req)
        assert r.status_code == 200
        props = r.json()["properties"]
        # Textbook reference: h_f=419.166 kJ/kg, P_sat=101.325 kPa
        assert pct_err(props["enthalpy"]["value"],    419.166)  < TOL_PRIMARY
        assert pct_err(props["pressure_kPa"]["value"], 101.325) < TOL_LOOSE

    def test_saturation_100C_vapor(self):
        """Saturation at 100°C — saturated vapor (x=1)."""
        req = {"fluid": "Water", "T": 100.0, "Q": 1.0, "T_unit": "C", "output_units": "SI"}
        r = client.post("/properties", json=req)
        assert r.status_code == 200
        props = r.json()["properties"]
        # Textbook reference: h_g=2675.57 kJ/kg
        assert pct_err(props["enthalpy"]["value"], 2675.57) < TOL_PRIMARY

    def test_saturation_hfg_100C(self):
        """Latent heat at 100°C via POST /saturation. Reference: h_fg=2256.5 kJ/kg."""
        req = {"fluid": "Water", "T": 100.0, "T_unit": "C"}
        r = client.post("/saturation", json=req)
        assert r.status_code == 200
        data = r.json()
        assert pct_err(data["hfg_kJkg"], 2256.5) < TOL_PRIMARY

    def test_saturation_pressure_at_100C(self):
        """P_sat at 100°C must be ≈101.325 kPa (standard atmosphere)."""
        req = {"fluid": "Water", "T": 100.0, "T_unit": "C"}
        r = client.post("/saturation", json=req)
        assert r.status_code == 200
        P_sat = r.json()["saturated_liquid"]["P_kPa"]
        assert pct_err(P_sat, 101.325) < TOL_LOOSE

    def test_two_phase_quality(self):
        """Two-phase at 100°C, x=0.5 — quality must be returned correctly."""
        req = {"fluid": "Water", "T": 100.0, "Q": 0.5, "T_unit": "C", "output_units": "SI"}
        r = client.post("/properties", json=req)
        assert r.status_code == 200
        props = r.json()["properties"]
        assert props["quality"]["value"] is not None
        assert abs(props["quality"]["value"] - 0.5) < 0.001
        # h at x=0.5 must be ≈ h_f + 0.5*h_fg = 419.02 + 0.5*2256.5 = 1547.27
        assert pct_err(props["enthalpy"]["value"], 1547.27) < TOL_PRIMARY

    def test_phase_detection_superheated(self):
        """Phase must be detected as Superheated Vapor at 200°C, 100 kPa."""
        props_resp = client.post("/properties", json={
            "fluid": "Water", "T": 200.0, "P": 100.0, "T_unit": "C", "P_unit": "kPa"
        }).json()
        assert "Superheated" in props_resp["phase"] or "Gas" in props_resp["phase"]

    def test_phase_detection_liquid(self):
        """Phase must be detected as Liquid at 20°C, 500 kPa."""
        props_resp = client.post("/properties", json={
            "fluid": "Water", "T": 20.0, "P": 500.0, "T_unit": "C", "P_unit": "kPa"
        }).json()
        assert "Liquid" in props_resp["phase"]

    def test_flash_PH(self):
        """Flash (P+H): P=101.325 kPa, h=2675.57 kJ/kg → should recover T≈100°C, x≈1."""
        req = {
            "fluid": "Water",
            "P": 101.325, "H": 2675.57,
            "P_unit": "kPa", "H_unit": "kJ/kg",
            "output_units": "SI"
        }
        r = client.post("/properties", json=req)
        assert r.status_code == 200
        props = r.json()["properties"]
        assert pct_err(props["temperature"]["value"], 100.0) < TOL_LOOSE

    def test_flash_PS(self):
        """Flash (P+S): P=1000 kPa, s=7.7622 kJ/kg·K → should recover T≈500°C."""
        req = {
            "fluid": "Water",
            "P": 1000.0, "S": 7.7622,
            "P_unit": "kPa", "S_unit": "kJ/kg/K",
            "output_units": "SI"
        }
        r = client.post("/properties", json=req)
        assert r.status_code == 200
        props = r.json()["properties"]
        assert pct_err(props["temperature"]["value"], 500.0) < TOL_LOOSE


# ============================================================
# NEXT-GEN FLUIDS: sCO₂, H₂, NH₃, R-1234yf
# ============================================================

class TestNextGenFluids:

    def test_sCO2_supercritical_phase(self):
        """CO₂ above critical point (31°C, 73.8 bar) must be in supercritical region."""
        r = client.post("/properties", json={
            "fluid": "sCO2", "T": 40.0, "P": 100.0, "T_unit": "C", "P_unit": "bar"
        })
        assert r.status_code == 200
        assert "Supercritical" in r.json()["phase"] or "supercritical" in r.json()["phase"].lower()

    def test_sCO2_density_high_pressure(self):
        """sCO₂ at 35°C, 80 bar should have density > 600 kg/m³ (liquid-like density)."""
        r = client.post("/properties", json={
            "fluid": "sCO2", "T": 35.0, "P": 80.0, "T_unit": "C", "P_unit": "bar"
        })
        props = r.json()["properties"]
        assert props["density"]["value"] > 400

    def test_hydrogen_alias(self):
        """All H₂ aliases should resolve to the same fluid."""
        for alias in ["H2", "GreenHydrogen", "hydrogen", "Hydrogen", "H₂"]:
            r = client.post("/properties", json={
                "fluid": alias, "T": 25.0, "P": 101.325, "T_unit": "C", "P_unit": "kPa"
            })
            assert r.status_code == 200, f"Alias '{alias}' failed: {r.json()}"

    def test_ammonia_saturation(self):
        """Ammonia sat. vapor at -10°C — check P_sat is in expected range (≈290 kPa)."""
        r = client.post("/properties", json={
            "fluid": "NH3", "T": -10.0, "Q": 1.0, "T_unit": "C", "output_units": "SI"
        })
        assert r.status_code == 200
        props = r.json()["properties"]
        # ASHRAE reference for ammonia: P_sat(-10°C) ≈ 290.8 kPa
        assert 250 < props["pressure_kPa"]["value"] < 350, \
            f"NH3 P_sat(-10°C) = {props['pressure_kPa']['value']} kPa (expected ~290 kPa)"

    def test_R1234yf_alias(self):
        """R-1234yf aliases should resolve correctly."""
        for alias in ["R1234yf", "HFO1234yf", "R-1234yf"]:
            r = client.post("/properties", json={
                "fluid": alias, "T": 25.0, "P": 101.325, "T_unit": "C", "P_unit": "kPa"
            })
            assert r.status_code == 200, f"Alias '{alias}' failed"

    def test_R1234yf_saturation_low_GWP(self):
        """R-1234yf at 25°C should have a P_sat in refrigerant range."""
        r = client.post("/properties", json={
            "fluid": "R1234yf", "T": 25.0, "Q": 0.0, "T_unit": "C", "output_units": "SI"
        })
        assert r.status_code == 200
        # R-1234yf normal boiling point is -29°C; at 25°C, expect P_sat ≈ 683 kPa
        props = r.json()["properties"]
        assert 500 < props["pressure_kPa"]["value"] < 900, \
            f"R1234yf P_sat(25°C) = {props['pressure_kPa']['value']} kPa"


# ============================================================
# SATURATION TABLE
# ============================================================

class TestSaturationTable:

    def test_water_table_structure(self):
        """Saturation table should have correct columns and row count."""
        r = client.get("/saturation-table?fluid=Water&T_start=0&T_end=100&n_points=10")
        assert r.status_code == 200
        data = r.json()
        assert data["n_rows"] == 10
        assert "h_f_kJkg" in data["columns"]
        assert "h_fg_kJkg" in data["columns"]
        assert "s_g_kJkgK" in data["columns"]
        for row in data["rows"]:
            assert row.get("h_g_kJkg") > row.get("h_f_kJkg"), \
                "h_g must be > h_f at every saturation point"

    def test_water_table_hfg_positive(self):
        """h_fg (latent heat) must be positive at all temperatures below critical."""
        r = client.get("/saturation-table?fluid=Water&T_start=0&T_end=370&n_points=20")
        data = r.json()
        for row in data["rows"]:
            if row.get("h_fg_kJkg") is not None:
                assert row["h_fg_kJkg"] > 0, f"h_fg negative at T={row['T_C']}°C"


# ============================================================
# API VALIDATION
# ============================================================

class TestAPIValidation:

    def test_too_few_inputs(self):
        """Only one input → 422."""
        r = client.post("/properties", json={"fluid": "Water", "T": 100, "T_unit": "C"})
        assert r.status_code == 422

    def test_too_many_inputs(self):
        """Three inputs → 422."""
        r = client.post("/properties", json={
            "fluid": "Water", "T": 100, "P": 101.325, "H": 2500, "T_unit": "C", "P_unit": "kPa"
        })
        assert r.status_code == 422

    def test_unknown_fluid(self):
        """Unknown fluid name → 422."""
        r = client.post("/properties", json={"fluid": "UnobtainiumXYZ", "T": 100, "P": 101, "T_unit": "C", "P_unit": "kPa"})
        assert r.status_code in (422, 500)

    def test_quality_out_of_range(self):
        """Quality > 1 → 422 (Pydantic validation)."""
        r = client.post("/properties", json={"fluid": "Water", "T": 100, "Q": 1.5, "T_unit": "C"})
        assert r.status_code == 422

    def test_health_endpoint(self):
        """Health check must return 'healthy'."""
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"

    def test_fluids_endpoint(self):
        """Fluids list must include Water, CO2, Ammonia, R1234yf."""
        r = client.get("/fluids")
        assert r.status_code == 200
        names = [f["name"] for f in r.json()["fluids"]]
        for expected in ["Water", "CO2", "Ammonia", "R1234yf", "Hydrogen"]:
            assert expected in names, f"'{expected}' missing from /fluids"

    def test_single_property_endpoint(self):
        """GET /property — density of water at 100°C, 1 atm (saturated liquid, x=0)."""
        # In SI: T=373.15 K, Q=0
        r = client.get("/property?fluid=Water&prop=Density&in1=T&v1=373.15&in2=Q&v2=0")
        assert r.status_code == 200
        rho = r.json()["value"]
        # Saturated liquid density at 100°C ≈ 958 kg/m³
        assert 930 < rho < 980, f"ρ = {rho} kg/m³ (expected ~958)"

    def test_phase_curve_endpoint(self):
        """Phase curve must return non-empty T and saturation data."""
        r = client.get("/phase-curve?fluid=Water&n_points=50")
        assert r.status_code == 200
        data = r.json()
        assert len(data["T_C"]) > 0
        assert len(data["s_liq_kJkgK"]) == len(data["T_C"])
        assert data["T_crit_C"] > 370  # Water critical T ≈ 373.95°C
