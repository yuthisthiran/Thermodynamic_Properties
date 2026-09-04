# Chemical Engineering Thermodynamic Calculator

![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)

A full-stack, highly accurate thermodynamic property calculator designed as a modern replacement for printed engineering tables (e.g., Çengel & Boles, Moran & Shapiro).

Unlike basic lookup tools, this application computes thermodynamic states dynamically by solving exact **Helmholtz Energy Equations of State** (such as the IAPWS-95 standard for Water) using the open-source [CoolProp](http://www.coolprop.org/) engine.

## Features

* **The State Calculator:** Input any two independent intensive properties (e.g., Temperature & Pressure, or Pressure & Enthalpy) to instantly calculate all remaining thermodynamic state variables.
* **Standard Table Generator:** Generates textbook-perfect property grids (matching Tables A-4, A-5, and A-6):
  * Saturated (Temperature-based)
  * Saturated (Pressure-based)
  * Superheated / Compressed Liquid
* **Auto-Interpolator:** A smart utility that automatically scans generated tables and performs precise linear interpolation between rows.
* **Phase Envelope Plotting:** Live generation of T-s (Temperature-Entropy) diagrams with the saturation dome and calculated state points.
* **Excel Integration:** Includes a local proxy server and VBA macro allowing engineers to pull live thermodynamic data directly into spreadsheet cells using formulas like `=THERMO("Water", "Enthalpy", "T", 100, "Q", 1)`.

## Tech Stack
* **Backend:** Python, FastAPI, CoolProp
* **Frontend:** React, TypeScript, Vite, TailwindCSS, Plotly.js
* **Integrations:** xlwings (Excel)

---

## How to Run Locally

This application is designed to be run offline. It requires Python 3.12+ and Node.js.

### 1. Start the Data Engine (Backend)
Open a terminal, navigate to the `api` folder, and start the FastAPI server:
```bash
cd api
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```
*The API will be available at `http://localhost:8000`. You can view the interactive API documentation at `http://localhost:8000/docs`.*

### 2. Start the Web Dashboard (Frontend)
Open a **new** terminal, navigate to the `web` folder, and start the Vite development server:
```bash
cd web
npm install
npm run dev
```
*The application will be accessible in your web browser at `http://localhost:5173`.*

---
*Disclaimer: This tool is intended for educational and engineering design estimates. Always verify safety-critical calculations against certified industrial software.*

