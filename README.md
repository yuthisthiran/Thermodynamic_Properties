# ⚗️ ChemEng Thermodynamic Platform

> Accurate thermodynamic properties for chemical engineers — powered by **CoolProp** and **NIST/IAPWS international standards**.

[![Standards](https://img.shields.io/badge/Standard-IAPWS--IF97%20%7C%20NIST%20EOS-blue)](http://www.iapws.org/)
[![Accuracy](https://img.shields.io/badge/Accuracy-±0.01--0.05%25-green)](http://coolprop.org/)
[![Fluids](https://img.shields.io/badge/Fluids-20%2B-orange)](./api/core/fluids.py)
[![License](https://img.shields.io/badge/License-MIT-lightgrey)](./LICENSE)

---

## 🗂️ Project Structure

```
ChemEng/
├── api/                        # Phase 1 — FastAPI Thermodynamic Engine
│   ├── main.py                 #   FastAPI app (all endpoints)
│   ├── requirements.txt        #   Python dependencies
│   ├── Dockerfile              #   Docker container config
│   ├── core/
│   │   ├── engine.py           #   CoolProp calculation engine
│   │   ├── fluids.py           #   Fluid registry + international standards
│   │   └── models.py           #   Pydantic request/response models
│   └── tests/
│       └── test_api.py         #   IAPWS-IF97 validation tests
│
├── excel_addin/                # Phase 2 — Spreadsheet Integration
│   ├── xlwings_server.py       #   Local Python server for offline Excel use
│   ├── ChemThermo.bas          #   Excel VBA module (=THERMO() formula)
│   └── google_sheets/
│       └── Code.gs             #   Google Sheets Apps Script
│
└── README.md
```

---

## 🌐 Supported Fluids & International Standards

| Fluid | Standard | Body | Accuracy |
|---|---|---|---|
| **Water / Steam** | IAPWS-IF97 + IAPWS-95 | IAPWS | ±0.001% |
| **sCO₂ / CO₂** | Span & Wagner EOS | NIST (1996) | ±0.03% |
| **Green H₂** | Leachman et al. EOS | NIST (2009) | ±0.04% |
| **Ammonia (R717)** | Gao et al. EOS | NIST (2023) | ±0.02% |
| **R-1234yf** | Richter et al. EOS | ASHRAE 34 (2011) | ±0.05% |
| **R-1234ze(E)** | Thol & Lemmon EOS | ASHRAE 34 (2016) | ±0.05% |
| **R-134a, R-410A, R-32, R-22** | NIST Helmholtz EOS | ASHRAE 34 | ±0.02–0.1% |
| **Air, N₂, O₂, H₂S** | NIST Helmholtz EOS | NIST | ±0.02% |
| **Methane, Propane, Ethane, Butane** | NIST Helmholtz EOS | NIST | ±0.01–0.02% |

**Engine:** [CoolProp 6.x](http://coolprop.org/) — Open-source, equivalent accuracy to NIST REFPROP 9.1+

---

## 🚀 Phase 1 — FastAPI Backend

### Quick Start (Local)

```bash
cd api
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

API available at **http://localhost:8000**
Interactive docs at **http://localhost:8000/docs**

### Docker (Offline / On-Prem)

```bash
cd api
docker build -t chemeng-api .
docker run -p 8000:8000 chemeng-api
```

### API Examples

```bash
# Full property set — sCO₂ at 35°C, 80 bar (supercritical)
curl -X POST http://localhost:8000/properties \
  -H "Content-Type: application/json" \
  -d '{"fluid": "sCO2", "T": 35, "P": 80, "T_unit": "C", "P_unit": "bar"}'

# Saturated steam at 100°C
curl -X POST http://localhost:8000/properties \
  -d '{"fluid": "Water", "T": 100, "Q": 1.0, "T_unit": "C"}'

# Flash: R-1234yf at 10 bar, h = 250 kJ/kg
curl -X POST http://localhost:8000/properties \
  -d '{"fluid": "R1234yf", "P": 1000, "H": 250, "P_unit": "kPa", "H_unit": "kJ/kg"}'

# Single property (Excel formula endpoint)
curl "http://localhost:8000/property?fluid=Water&prop=Enthalpy&in1=T&v1=373.15&in2=Q&v2=1"

# Saturation table: water 0–200°C, 20 rows
curl "http://localhost:8000/saturation-table?fluid=Water&T_start=0&T_end=200&n_points=20"

# Phase curve (for T-s and P-h diagrams)
curl "http://localhost:8000/phase-curve?fluid=Ammonia&n_points=100"

# List all supported fluids
curl "http://localhost:8000/fluids"
```

### Key Endpoints

| Method | Route | Description |
|---|---|---|
| `POST` | `/properties` | All props from any 2 state variables |
| `GET` | `/property` | Single prop — Excel formula optimized |
| `POST` | `/saturation` | Sat. liquid + vapor at T or P |
| `GET` | `/saturation-table` | Textbook-style saturation table |
| `GET` | `/phase-curve` | Saturation dome for T-s / P-h charts |
| `GET` | `/fluids` | Supported fluids + standards |
| `GET` | `/health` | API health check |

### Input Modes (State Postulate)

| Inputs | Use Case |
|---|---|
| `T` + `P` | Superheated vapor, compressed liquid, supercritical |
| `T` + `Q` | Saturated / two-phase at given temperature |
| `P` + `Q` | Saturated / two-phase at given pressure |
| `P` + `H` | Flash (isenthalpic: throttling valves) |
| `P` + `S` | Flash (isentropic: turbines, compressors) |
| `T` + `S` | Flash (general two-property specification) |

### Run Tests

```bash
cd api
python -m pytest tests/ -v
```

Validates against IAPWS-IF97 Appendix B reference tables (±0.01% tolerance).

---

## 📊 Phase 2 — Excel & Google Sheets Integration

### Excel Add-in (Offline)

**Step 1: Start the local server**
```bash
cd excel_addin
pip install fastapi uvicorn CoolProp
python xlwings_server.py
# Keep this terminal open
```

**Step 2: Install VBA module**
1. Open Excel → `Alt+F11` → Visual Basic Editor
2. `File` → `Import File` → select `ChemThermo.bas`
3. Close VBA editor

**Step 3: Use in any cell**
```
=THERMO("sCO2",  "Density",   "T", T_C_TO_K(35),    "P", MPA_TO_PA(8))
=THERMO("Water", "Enthalpy",  "T", T_C_TO_K(100),   "Q", 1)
=THERMO("NH3",   "Entropy",   "T", T_C_TO_K(-10),   "Q", 0)
=THERMO("R1234yf","Pressure", "T", T_C_TO_K(25),    "Q", 1)

=THERMO_SAT("Water", "h_fg", "T_C", A2)   ← drag down 1000 rows ✓
=THERMO_SAT("NH3",   "P_sat","T_C", B2)
```

### Google Sheets

1. Open your Sheet → `Extensions` → `Apps Script`
2. Paste the contents of `excel_addin/google_sheets/Code.gs`
3. Update `API_URL` at the top to your deployed API URL
4. Save and reload the sheet
5. Use the same `=THERMO()` formula syntax as Excel

---

## 🔬 Property Reference

| Symbol | Property | SI Unit | Imperial Unit |
|---|---|---|---|
| T | Temperature | °C (K internally) | °F |
| P | Pressure | kPa | psi |
| h | Specific enthalpy | kJ/kg | BTU/lb |
| s | Specific entropy | kJ/kg·K | BTU/lb·°R |
| v | Specific volume | m³/kg | ft³/lb |
| ρ | Density | kg/m³ | lb/ft³ |
| u | Internal energy | kJ/kg | BTU/lb |
| x | Vapor quality | — (0–1) | — |
| Cₚ | Specific heat (const. P) | kJ/kg·K | BTU/lb·°R |
| Cᵥ | Specific heat (const. V) | kJ/kg·K | BTU/lb·°R |
| μ | Dynamic viscosity | Pa·s / cP | cP |
| k | Thermal conductivity | W/m·K | W/m·K |
| Pr | Prandtl number | — | — |
| Z | Compressibility factor | — | — |
| c | Speed of sound | m/s | ft/s |

---

## ☁️ Deployment

### Render (Free tier, 1-click)
```bash
# render.yaml (include in repo root):
services:
  - type: web
    name: chemeng-api
    env: python
    buildCommand: "pip install -r api/requirements.txt"
    startCommand: "uvicorn api.main:app --host 0.0.0.0 --port $PORT"
```

### Railway
```bash
railway init
railway link
railway up --service api
```

### AWS ECS / GCP Cloud Run
```bash
docker build -t chemeng-api ./api
docker tag chemeng-api gcr.io/YOUR_PROJECT/chemeng-api
docker push gcr.io/YOUR_PROJECT/chemeng-api
gcloud run deploy chemeng-api --image gcr.io/YOUR_PROJECT/chemeng-api --platform managed
```

---

## 📐 Phase 3 — React Web Canvas (Coming Next)

Interactive web application with:
- **Drag-and-drop state points** on T-s and P-h diagrams
- **60fps real-time updates** via Plotly.js + debounced API calls
- **Cycle analysis** (Rankine, Refrigeration, sCO₂ Brayton)
- **React + Vite** frontend connected to the Phase 1 API

---

## 📜 License

MIT License — free for personal, academic, and commercial use.

---

## 📚 References

1. Wagner & Kruse, *Properties of Water and Steam (IAPWS-IF97)*, Springer, 2007
2. Span & Wagner, *J. Phys. Chem. Ref. Data* 25(6), 1509–1596, 1996 (CO₂)
3. Leachman et al., *J. Phys. Chem. Ref. Data* 38(3), 721–748, 2009 (H₂)
4. Gao et al., *J. Phys. Chem. Ref. Data* 52, 013102, 2023 (NH₃)
5. Richter et al., *Int. J. Refrig.* 34(3), 715–728, 2011 (R-1234yf)
6. Bell et al., *Ind. Eng. Chem. Res.* 53(6), 2498–2508, 2014 (CoolProp)
