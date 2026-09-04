/**
 * ChemThermo — Google Sheets Custom Functions
 * ============================================
 * Provides =THERMO() and =THERMO_SAT() worksheet functions in Google Sheets.
 * Calls the deployed ChemEng Thermodynamic API (Phase 1).
 *
 * INSTALLATION:
 *   1. Open any Google Sheet
 *   2. Extensions → Apps Script → paste this code → Save
 *   3. Run setupMenu() once to create the "ChemThermo" menu
 *   4. Set API_URL below to your deployed API URL
 *
 * USAGE:
 *   =THERMO("sCO2",  "Density",  "T", 308.15, "P", 8000000)
 *   =THERMO("Water", "Enthalpy", "T", 373.15, "Q", 1)
 *   =THERMO_SAT("Water", "h_fg", "T_C", 100)
 *   =THERMO_TABLE("Water", 0, 200, 20)      ← Generates saturation table
 *
 * @author ChemEng Thermodynamic Calculator
 * @version 1.0.0
 */

// ============================================================
// CONFIGURATION
// ============================================================

/** Your deployed Phase 1 API URL. Update this after deployment. */
const API_URL = "https://api.chemengcalc.io";   // or "http://localhost:8000"

/** Default output unit system */
const DEFAULT_UNIT_SYSTEM = "SI";

/** Cache timeout in seconds (Google Apps Script cache max = 6 hours) */
const CACHE_SECONDS = 3600;


// ============================================================
// THERMO() — Main worksheet function
// ============================================================

/**
 * Returns a single thermodynamic property for a given fluid state.
 *
 * @param {string} fluid  Fluid name or alias (e.g. "Water", "sCO2", "R1234yf")
 * @param {string} prop   Property: "Density", "Enthalpy", "Entropy", "Cp", "Viscosity", etc.
 * @param {string} in1    First input type: "T", "P", "H", "S", or "Q"
 * @param {number} v1     Value of first input (SI units: K, Pa, J/kg, J/kg/K)
 * @param {string} in2    Second input type
 * @param {number} v2     Value of second input (SI units)
 * @param {string} [unit] Output unit system: "SI" or "Imperial" (default: "SI")
 * @return {number}       The requested thermodynamic property
 * @customfunction
 */
function THERMO(fluid, prop, in1, v1, in2, v2, unit) {
  unit = unit || DEFAULT_UNIT_SYSTEM;

  const cacheKey = `thermo_${fluid}_${prop}_${in1}_${v1}_${in2}_${v2}_${unit}`;
  const cache = CacheService.getScriptCache();
  const cached = cache.get(cacheKey);
  if (cached) return parseFloat(cached);

  const url = `${API_URL}/property?fluid=${encodeURIComponent(fluid)}&prop=${encodeURIComponent(prop)}&in1=${in1}&v1=${v1}&in2=${in2}&v2=${v2}&unit=${unit}`;

  try {
    const response = UrlFetchApp.fetch(url, {
      method: "GET",
      headers: { "Accept": "application/json" },
      muteHttpExceptions: true,
    });

    if (response.getResponseCode() !== 200) {
      const err = JSON.parse(response.getContentText());
      throw new Error(err.detail || "API error");
    }

    const data = JSON.parse(response.getContentText());
    const value = data.value;

    cache.put(cacheKey, String(value), CACHE_SECONDS);
    return value;

  } catch (e) {
    return `ERROR: ${e.message}`;
  }
}


// ============================================================
// THERMO_SAT() — Saturation property lookup
// ============================================================

/**
 * Returns a saturation property at a given temperature or pressure.
 *
 * @param {string} fluid     Fluid name or alias
 * @param {string} prop      Saturation property: "h_f", "h_g", "h_fg", "s_f", "s_g",
 *                           "s_fg", "v_f", "v_g", "P_sat", "T_sat", "u_f", "u_fg", "u_g"
 * @param {string} input_by  "T_C" (temperature in °C) or "P_kPa" (pressure in kPa)
 * @param {number} value     Temperature (°C) or Pressure (kPa)
 * @return {number}          The saturation property value in SI units
 * @customfunction
 */
function THERMO_SAT(fluid, prop, input_by, value) {
  const cacheKey = `sat_${fluid}_${prop}_${input_by}_${value}`;
  const cache = CacheService.getScriptCache();
  const cached = cache.get(cacheKey);
  if (cached) return parseFloat(cached);

  let url;
  if (input_by.toUpperCase() === "T_C") {
    url = `${API_URL}/saturation?fluid=${encodeURIComponent(fluid)}&T_C=${value}`;
  } else if (input_by.toUpperCase() === "P_KPA") {
    url = `${API_URL}/saturation?fluid=${encodeURIComponent(fluid)}&P_kPa=${value}`;
  } else {
    return "ERROR: input_by must be 'T_C' or 'P_kPa'";
  }

  try {
    const response = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
    if (response.getResponseCode() !== 200) return `ERROR: ${response.getResponseCode()}`;

    const data = JSON.parse(response.getContentText());
    const prop_lower = prop.toLowerCase();
    let result;

    // Map property names to JSON paths
    const propMap = {
      "h_f": ["saturated_liquid", "h_kJkg"],
      "hf":  ["saturated_liquid", "h_kJkg"],
      "h_g": ["saturated_vapor",  "h_kJkg"],
      "hg":  ["saturated_vapor",  "h_kJkg"],
      "h_fg": ["hfg_kJkg"],
      "hfg":  ["hfg_kJkg"],
      "latent_heat": ["hfg_kJkg"],
      "s_f": ["saturated_liquid", "s_kJkgK"],
      "sf":  ["saturated_liquid", "s_kJkgK"],
      "s_g": ["saturated_vapor",  "s_kJkgK"],
      "sg":  ["saturated_vapor",  "s_kJkgK"],
      "s_fg": ["sfg_kJkgK"],
      "sfg":  ["sfg_kJkgK"],
      "v_f": ["saturated_liquid", "v_m3kg"],
      "vf":  ["saturated_liquid", "v_m3kg"],
      "v_g": ["saturated_vapor",  "v_m3kg"],
      "vg":  ["saturated_vapor",  "v_m3kg"],
      "p_sat":  ["saturated_liquid", "P_kPa"],
      "psat":   ["saturated_liquid", "P_kPa"],
      "pressure": ["saturated_liquid", "P_kPa"],
      "t_sat":  ["saturated_liquid", "T_C"],
      "tsat":   ["saturated_liquid", "T_C"],
      "temperature": ["saturated_liquid", "T_C"],
      "u_f": ["saturated_liquid", "u_kJkg"],
      "uf":  ["saturated_liquid", "u_kJkg"],
      "u_g": ["saturated_vapor",  "u_kJkg"],
      "ug":  ["saturated_vapor",  "u_kJkg"],
      "u_fg": ["ufg_kJkg"],
      "ufg":  ["ufg_kJkg"],
      "rho_f": ["saturated_liquid", "rho_kgm3"],
      "rho_g": ["saturated_vapor",  "rho_kgm3"],
    };

    const path = propMap[prop_lower];
    if (!path) return `ERROR: Unknown prop '${prop}'`;

    if (path.length === 1) {
      result = data[path[0]];
    } else {
      result = data[path[0]] && data[path[0]][path[1]];
    }

    if (result === null || result === undefined) return "N/A";

    cache.put(cacheKey, String(result), CACHE_SECONDS);
    return result;

  } catch (e) {
    return `ERROR: ${e.message}`;
  }
}


// ============================================================
// THERMO_TABLE() — Generate saturation table in a range
// ============================================================

/**
 * Generates a saturation property table starting from the current cell.
 * Use as an array formula: select a range, type the formula, press Ctrl+Shift+Enter.
 *
 * @param {string} fluid     Fluid name or alias
 * @param {number} T_start   Start temperature (°C)
 * @param {number} T_end     End temperature (°C)
 * @param {number} n_points  Number of rows
 * @param {boolean} [si]     True = SI units (default), False = Imperial
 * @return {Array}           2D array: rows × columns of saturation data
 * @customfunction
 */
function THERMO_TABLE(fluid, T_start, T_end, n_points, si) {
  si = (si === undefined) ? true : si;
  n_points = Math.min(Math.max(n_points, 5), 100);

  const url = `${API_URL}/saturation-table?fluid=${encodeURIComponent(fluid)}&T_start=${T_start}&T_end=${T_end}&n_points=${n_points}&si=${si}`;

  try {
    const response = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
    if (response.getResponseCode() !== 200) return [["API Error: " + response.getResponseCode()]];

    const data = JSON.parse(response.getContentText());
    if (!data.rows || data.rows.length === 0) return [["No data returned"]];

    const columns = Object.keys(data.rows[0]);

    // Build 2D array: header row + data rows
    const output = [columns];  // Header
    for (const row of data.rows) {
      output.push(columns.map(col => row[col] !== null ? row[col] : ""));
    }

    return output;

  } catch (e) {
    return [["ERROR: " + e.message]];
  }
}


// ============================================================
// UNIT CONVERSION HELPERS (usable as Sheets formulas)
// ============================================================

/** Convert °C to K  @customfunction */
function T_C_TO_K(T_C) { return T_C + 273.15; }

/** Convert °F to K  @customfunction */
function T_F_TO_K(T_F) { return (T_F - 32) * 5 / 9 + 273.15; }

/** Convert kPa to Pa  @customfunction */
function KPA_TO_PA(P_kPa) { return P_kPa * 1000; }

/** Convert MPa to Pa  @customfunction */
function MPA_TO_PA(P_MPa) { return P_MPa * 1e6; }

/** Convert bar to Pa  @customfunction */
function BAR_TO_PA(P_bar) { return P_bar * 1e5; }

/** Convert psi to Pa  @customfunction */
function PSI_TO_PA(P_psi) { return P_psi * 6894.757293168; }

/** Convert kJ/kg to J/kg  @customfunction */
function KJKG_TO_JKG(h_kJkg) { return h_kJkg * 1000; }

/** Convert kJ/kg/K to J/kg/K  @customfunction */
function KJKGK_TO_JKGK(s) { return s * 1000; }


// ============================================================
// MENU & SETUP
// ============================================================

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu("⚗️ ChemThermo")
    .addItem("📋 Insert THERMO formula", "insertThermoFormula")
    .addItem("📊 Generate Steam Table", "generateSteamTable")
    .addItem("🔧 Test API Connection", "testConnection")
    .addItem("📚 View Supported Fluids", "showFluids")
    .addSeparator()
    .addItem("⚙️ Settings", "showSettings")
    .addToUi();
}

function setupMenu() { onOpen(); }

function testConnection() {
  try {
    const r = UrlFetchApp.fetch(API_URL + "/health");
    const data = JSON.parse(r.getContentText());
    SpreadsheetApp.getUi().alert(
      "✅ API Connected!\n\n" +
      "Status: " + data.status + "\n" +
      "CoolProp: " + data.coolprop_version + "\n" +
      "Fluids: " + data.supported_fluid_count
    );
  } catch (e) {
    SpreadsheetApp.getUi().alert("❌ Connection failed: " + e.message + "\n\nURL: " + API_URL);
  }
}

function showFluids() {
  try {
    const r = UrlFetchApp.fetch(API_URL + "/fluids");
    const data = JSON.parse(r.getContentText());
    const list = data.fluids.map(f => `${f.name} (${f.category})`).join("\n");
    SpreadsheetApp.getUi().alert("Supported Fluids (" + data.total_fluids + " total):\n\n" + list);
  } catch (e) {
    SpreadsheetApp.getUi().alert("Error: " + e.message);
  }
}

function insertThermoFormula() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const cell  = sheet.getActiveCell();
  cell.setFormula('=THERMO("Water","Enthalpy","T",T_C_TO_K(100),"Q",1)');
  SpreadsheetApp.getUi().alert(
    "Formula inserted!\n\n" +
    "Edit fluid, property, and input values.\n" +
    "Input values must be in SI units (K, Pa, J/kg, J/kg/K).\n\n" +
    "Use helper functions:\n" +
    "  T_C_TO_K(°C)  →  Kelvin\n" +
    "  KPA_TO_PA(kPa) → Pascal"
  );
}

function generateSteamTable() {
  const ui = SpreadsheetApp.getUi();
  const fluidResp = ui.prompt("Fluid", "Enter fluid name (e.g. Water, Ammonia, R1234yf):", ui.ButtonSet.OK_CANCEL);
  if (fluidResp.getSelectedButton() !== ui.Button.OK) return;

  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const cell  = sheet.getActiveCell();
  cell.setFormula(`=THERMO_TABLE("${fluidResp.getResponseText()}", 0, 200, 20)`);
  ui.alert("Saturation table formula inserted.\nPress Ctrl+Shift+Enter to expand as array formula.");
}

function showSettings() {
  SpreadsheetApp.getUi().alert(
    "Current Settings:\n\n" +
    "API URL:       " + API_URL + "\n" +
    "Unit System:   " + DEFAULT_UNIT_SYSTEM + "\n" +
    "Cache timeout: " + CACHE_SECONDS + " seconds\n\n" +
    "To change: open Apps Script editor and edit the constants at the top of Code.gs."
  );
}
