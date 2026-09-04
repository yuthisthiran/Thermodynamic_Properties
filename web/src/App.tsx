import { useState, useEffect } from 'react';
import { fetchProperties, fetchPhaseCurve, fetchFluids, fetchSaturationTable, fetchSuperheatedTable } from './api/thermo';
import PlotlyChart from 'react-plotly.js';

export default function App() {
  const [activeTab, setActiveTab] = useState<'calculator' | 'tables'>('calculator');

  // Shared state
  const [fluids, setFluids] = useState<any[]>([]);
  const [fluid, setFluid] = useState('Water');
  const [units, setUnits] = useState('SI');
  
  // Calculator state
  const [in1Type, setIn1Type] = useState<'T'|'P'>('T');
  const [in1Val, setIn1Val] = useState<number>(100);
  const [in2Type, setIn2Type] = useState<'Q'|'P'|'H'|'S'>('Q');
  const [in2Val, setIn2Val] = useState<number>(1);
  const [results, setResults] = useState<any>(null);
  const [error, setError] = useState<string>('');
  const [phaseData, setPhaseData] = useState<any>(null);

  // Table state
  const [tableType, setTableType] = useState<'sat_t' | 'sat_p' | 'super'>('sat_t');
  const [tStart, setTStart] = useState<number>(0);
  const [tEnd, setTEnd] = useState<number>(200);
  const [pStart, setPStart] = useState<number>(100);
  const [pEnd, setPEnd] = useState<number>(5000);
  const [pFixed, setPFixed] = useState<number>(1000);
  const [nPoints, setNPoints] = useState<number>(20);
  const [tableData, setTableData] = useState<any>(null);
  const [tableError, setTableError] = useState<string>('');

  // Interpolation state
  const [interpXKey, setInterpXKey] = useState<string>('');
  const [interpYKey, setInterpYKey] = useState<string>('');
  const [interpXValue, setInterpXValue] = useState<string>('');

  useEffect(() => {
    fetchFluids().then(setFluids).catch(console.error);
  }, []);

  useEffect(() => {
    if (activeTab === 'calculator') {
      fetchPhaseCurve(fluid).then(setPhaseData).catch(console.error);
    }
  }, [fluid, activeTab]);

  const handleCalculate = async () => {
    setError('');
    try {
      const req = {
        fluid,
        [in1Type]: in1Val,
        [in2Type]: in2Val,
        T_unit: units === 'SI' ? 'C' : 'F',
        P_unit: units === 'SI' ? 'kPa' : 'psi',
        H_unit: units === 'SI' ? 'kJ/kg' : 'BTU/lb',
        S_unit: units === 'SI' ? 'kJ/kg/K' : 'BTU/lb/R',
        output_units: units
      };
      const data = await fetchProperties(req);
      setResults(data);
    } catch (err: any) {
      setError(err.response?.data?.detail?.[0]?.msg || err.response?.data?.detail || err.message);
    }
  };

  const handleGenerateTable = async () => {
    setTableError('');
    setTableData(null);
    try {
      let data;
      if (tableType === 'sat_t') {
        data = await fetchSaturationTable(fluid, false, tStart, tEnd, nPoints, units);
        data.type = 'sat';
      } else if (tableType === 'sat_p') {
        data = await fetchSaturationTable(fluid, true, pStart, pEnd, nPoints, units);
        data.type = 'sat';
      } else {
        data = await fetchSuperheatedTable(fluid, pFixed, tStart, tEnd, nPoints, units);
        data.type = 'super';
      }
      setTableData(data);
      
      // Auto-set default interpolation keys when table generates
      if (data && data.rows && data.rows.length > 0) {
        const keys = Object.keys(data.rows[0]);
        if (keys.length >= 2) {
          setInterpXKey(keys[0]);
          setInterpYKey(keys[1]);
        }
      }
    } catch (err: any) {
      setTableError(err.response?.data?.detail?.[0]?.msg || err.response?.data?.detail || err.message);
    }
  };

  // Automatic Table Interpolation Logic
  let yTarget = "—";
  if (tableData && tableData.rows && interpXKey && interpYKey && interpXValue !== '') {
    const xT = Number(interpXValue);
    const rows = tableData.rows;
    let found = false;
    
    // Check exact match first
    for (let i = 0; i < rows.length; i++) {
        if (rows[i][interpXKey] === xT) {
            yTarget = Number(rows[i][interpYKey]).toPrecision(6);
            found = true;
            break;
        }
    }
    
    if (!found) {
        // Find bounding rows
        for (let i = 0; i < rows.length - 1; i++) {
            const x1 = rows[i][interpXKey];
            const x2 = rows[i+1][interpXKey];
            const y1 = rows[i][interpYKey];
            const y2 = rows[i+1][interpYKey];
            
            if (x1 !== null && x2 !== null && y1 !== null && y2 !== null) {
                if ((x1 <= xT && xT <= x2) || (x1 >= xT && xT >= x2)) {
                    const dx = x2 - x1;
                    if (dx !== 0) {
                        const val = y1 + ((xT - x1) * (y2 - y1)) / dx;
                        yTarget = val.toPrecision(6);
                        found = true;
                        break;
                    }
                }
            }
        }
    }
    
    if (!found) {
        yTarget = "Out of bounds";
    }
  }

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col font-sans text-gray-900 pb-10">
      
      {/* HEADER */}
      <header className="bg-blue-600 text-white p-4 shadow-md">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row gap-4 md:gap-0 justify-between items-center">
          <h1 className="text-xl font-bold">Chemical Engineering Thermodynamic Calculator</h1>
          <div className="flex bg-blue-700 rounded overflow-hidden shadow-inner">
            <button 
              className={`px-4 py-2 text-sm font-semibold transition-colors ${activeTab === 'calculator' ? 'bg-white text-blue-700' : 'text-blue-100 hover:bg-blue-600'}`}
              onClick={() => setActiveTab('calculator')}
            >
              State Calculator
            </button>
            <button 
              className={`px-4 py-2 text-sm font-semibold transition-colors ${activeTab === 'tables' ? 'bg-white text-blue-700' : 'text-blue-100 hover:bg-blue-600'}`}
              onClick={() => setActiveTab('tables')}
            >
              Standard Tables
            </button>
          </div>
        </div>
      </header>

      {/* MAIN CONTENT */}
      <main className="max-w-7xl mx-auto w-full p-4 flex flex-col md:flex-row gap-6 mt-4">
        
        {activeTab === 'calculator' ? (
            <>
                <aside className="w-full md:w-1/3 bg-white p-6 rounded shadow border border-gray-200 self-start">
                <h2 className="text-lg font-semibold border-b pb-2 mb-4">Define State</h2>

                <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-1">Fluid</label>
                    <select className="w-full border border-gray-300 p-2 rounded bg-gray-50 outline-none focus:ring-2 focus:ring-blue-500" value={fluid} onChange={(e) => setFluid(e.target.value)}>
                    {fluids.map(f => (
                        <option key={f.name} value={f.name}>{f.name} ({f.standard})</option>
                    ))}
                    </select>
                </div>

                <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-1">Unit System</label>
                    <select className="w-full border border-gray-300 p-2 rounded bg-gray-50 outline-none focus:ring-2 focus:ring-blue-500" value={units} onChange={(e) => setUnits(e.target.value)}>
                    <option value="SI">SI (C, kPa, m³/kg, kJ/kg)</option>
                    <option value="Imperial">Imperial (F, psia, ft³/lbm, BTU/lb)</option>
                    </select>
                </div>

                <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-1">Property 1</label>
                    <div className="flex gap-2">
                    <select className="w-1/3 border border-gray-300 p-2 rounded bg-gray-50" value={in1Type} onChange={(e: any) => setIn1Type(e.target.value)}>
                        <option value="T">Temp</option>
                        <option value="P">Pressure</option>
                    </select>
                    <input type="number" step="any" className="w-2/3 border border-gray-300 p-2 rounded focus:ring-2 focus:ring-blue-500 outline-none" value={in1Val} onChange={(e) => setIn1Val(parseFloat(e.target.value))} />
                    </div>
                </div>

                <div className="mb-6">
                    <label className="block text-sm font-medium text-gray-700 mb-1">Property 2</label>
                    <div className="flex gap-2">
                    <select className="w-1/3 border border-gray-300 p-2 rounded bg-gray-50" value={in2Type} onChange={(e: any) => setIn2Type(e.target.value)}>
                        <option value="P">Pressure</option>
                        <option value="Q">Quality (0-1)</option>
                        <option value="H">Enthalpy</option>
                        <option value="S">Entropy</option>
                    </select>
                    <input type="number" step="any" className="w-2/3 border border-gray-300 p-2 rounded focus:ring-2 focus:ring-blue-500 outline-none" value={in2Val} onChange={(e) => setIn2Val(parseFloat(e.target.value))} />
                    </div>
                </div>

                <button onClick={handleCalculate} className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded transition-colors">
                    Calculate Exact State
                </button>

                {error && <div className="mt-4 p-3 bg-red-50 border-l-4 border-red-500 text-red-700 text-sm"><strong>Error:</strong> {error}</div>}
                </aside>

                <section className="w-full md:w-2/3 flex flex-col gap-6">
                
                <div className="bg-white p-6 rounded shadow border border-gray-200">
                    <h2 className="text-lg font-semibold border-b pb-2 mb-4">Calculated Properties</h2>
                    {results ? (
                    <div className="overflow-x-auto">
                        <table className="min-w-full border-collapse">
                        <thead>
                            <tr className="bg-gray-100 border-y border-gray-300 text-left">
                            <th className="py-2 px-4 font-semibold border-r border-gray-200">Property</th>
                            <th className="py-2 px-4 font-semibold text-right border-r border-gray-200">Value</th>
                            <th className="py-2 px-4 font-semibold">Unit</th>
                            </tr>
                        </thead>
                        <tbody>
                            {Object.entries(results).map(([key, obj]: any, i) => (
                            <tr key={key} className={`border-b border-gray-200 ${i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}`}>
                                <td className="py-1.5 px-4 capitalize font-medium text-gray-700 border-r border-gray-200">{key.replace('_', ' ')}</td>
                                <td className="py-1.5 px-4 font-mono text-right border-r border-gray-200">{obj.value !== null ? Number(obj.value).toPrecision(6) : '-'}</td>
                                <td className="py-1.5 px-4 text-gray-600">{obj.unit}</td>
                            </tr>
                            ))}
                        </tbody>
                        </table>
                    </div>
                    ) : (
                    <p className="text-gray-500 italic text-center py-8">Click calculate to see results.</p>
                    )}
                </div>

                <div className="bg-white p-6 rounded shadow border border-gray-200">
                    <h2 className="text-lg font-semibold border-b pb-2 mb-4">T-s Diagram</h2>
                    {phaseData ? (
                    <div className="w-full overflow-hidden flex justify-center">
                        <PlotlyChart
                        data={[
                            { x: phaseData.s_liq_kJkgK, y: phaseData.T_C, type: 'scatter', mode: 'lines', name: 'Saturated Liquid', line: { color: 'blue' } },
                            { x: phaseData.s_vap_kJkgK, y: phaseData.T_C, type: 'scatter', mode: 'lines', name: 'Saturated Vapor', line: { color: 'red' } },
                            ...(results && results.entropy && results.temperature ? [{
                            x: [results.entropy.value], y: [results.temperature.value], type: 'scatter', mode: 'markers', name: 'State Point', marker: { size: 12, color: 'black', symbol: 'x' }
                            }] : [])
                        ]}
                        layout={{ width: 700, height: 400, margin: { t: 20, l: 50, r: 20, b: 40 }, xaxis: { title: 'Entropy' }, yaxis: { title: 'Temperature' } }}
                        />
                    </div>
                    ) : <p className="text-gray-500 italic text-center py-8">Loading phase curve...</p>}
                </div>
                </section>
            </>
        ) : (
            <div className="w-full flex flex-col gap-6">
                
                {/* TOP ROW: TABLE CONTROLS & INTERPOLATION */}
                <div className="flex flex-col lg:flex-row gap-6">
                  
                  {/* TABLE TYPE CONTROLS */}
                  <div className="w-full lg:w-2/3 bg-white p-6 rounded shadow border border-gray-200 flex flex-col gap-4">
                      <h2 className="text-lg font-semibold border-b pb-2">Table Generation Parameters</h2>
                      
                      <div className="flex gap-6 mb-2 flex-wrap bg-gray-50 p-4 rounded border border-gray-200">
                          <div className="flex items-center gap-2">
                              <label className="font-semibold text-gray-700">Fluid:</label>
                              <select className="border border-gray-300 p-1.5 rounded bg-white outline-none min-w-[150px]" value={fluid} onChange={(e) => setFluid(e.target.value)}>
                              {fluids.filter(f => !['Air', 'Oxygen', 'Nitrogen', 'Helium', 'Hydrogen', 'Argon'].includes(f.name)).map(f => (
                                  <option key={f.name} value={f.name}>{f.name} ({f.standard})</option>
                              ))}
                              </select>
                          </div>
                          <div className="flex items-center gap-2">
                              <label className="font-semibold text-gray-700">Units:</label>
                              <select className="border border-gray-300 p-1.5 rounded bg-white outline-none" value={units} onChange={(e) => setUnits(e.target.value)}>
                              <option value="SI">SI (C, kPa, m³, kJ)</option>
                              <option value="Imperial">Imperial (F, psia, ft³, BTU)</option>
                              </select>
                          </div>
                      </div>
                      
                      <div className="flex gap-4 mb-2 flex-wrap">
                        <label className="flex items-center gap-2 cursor-pointer">
                          <input type="radio" name="ttype" checked={tableType === 'sat_t'} onChange={() => setTableType('sat_t')} className="w-4 h-4 text-blue-600" />
                          <span className="font-medium">Saturated (Temp)</span>
                        </label>
                        <label className="flex items-center gap-2 cursor-pointer">
                          <input type="radio" name="ttype" checked={tableType === 'sat_p'} onChange={() => setTableType('sat_p')} className="w-4 h-4 text-blue-600" />
                          <span className="font-medium">Saturated (Press.)</span>
                        </label>
                        <label className="flex items-center gap-2 cursor-pointer">
                          <input type="radio" name="ttype" checked={tableType === 'super'} onChange={() => setTableType('super')} className="w-4 h-4 text-blue-600" />
                          <span className="font-medium">Superheated / Comp.</span>
                        </label>
                      </div>

                      <div className="flex gap-6 items-end flex-wrap">
                          {tableType === 'super' && (
                              <div>
                                  <label className="block text-sm font-medium text-gray-700 mb-1">Fixed Press. ({units === 'SI' ? 'kPa' : 'psia'})</label>
                                  <input type="number" className="border border-gray-300 p-2 rounded w-28 outline-none focus:ring-2 focus:ring-blue-500" value={pFixed} onChange={e => setPFixed(parseFloat(e.target.value))} />
                              </div>
                          )}
                          
                          {tableType === 'sat_p' ? (
                              <>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Start P. ({units === 'SI' ? 'kPa' : 'psia'})</label>
                                    <input type="number" className="border border-gray-300 p-2 rounded w-28 outline-none focus:ring-2 focus:ring-blue-500" value={pStart} onChange={e => setPStart(parseFloat(e.target.value))} />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">End P. ({units === 'SI' ? 'kPa' : 'psia'})</label>
                                    <input type="number" className="border border-gray-300 p-2 rounded w-28 outline-none focus:ring-2 focus:ring-blue-500" value={pEnd} onChange={e => setPEnd(parseFloat(e.target.value))} />
                                </div>
                              </>
                          ) : (
                              <>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Start T. ({units === 'SI' ? '°C' : '°F'})</label>
                                    <input type="number" className="border border-gray-300 p-2 rounded w-28 outline-none focus:ring-2 focus:ring-blue-500" value={tStart} onChange={e => setTStart(parseFloat(e.target.value))} />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">End T. ({units === 'SI' ? '°C' : '°F'})</label>
                                    <input type="number" className="border border-gray-300 p-2 rounded w-28 outline-none focus:ring-2 focus:ring-blue-500" value={tEnd} onChange={e => setTEnd(parseFloat(e.target.value))} />
                                </div>
                              </>
                          )}
                          
                          <div>
                              <label className="block text-sm font-medium text-gray-700 mb-1">Rows</label>
                              <input type="number" className="border border-gray-300 p-2 rounded w-20 outline-none focus:ring-2 focus:ring-blue-500" value={nPoints} onChange={e => setNPoints(parseInt(e.target.value))} />
                          </div>
                          <button onClick={handleGenerateTable} className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-6 rounded transition-colors">
                              Generate Table
                          </button>
                      </div>
                  </div>

                  {/* LINEAR INTERPOLATION UTILITY */}
                  <div className="w-full lg:w-1/3 bg-white p-6 rounded shadow border border-gray-200 flex flex-col">
                    <h2 className="text-lg font-semibold border-b pb-2 mb-4">Auto-Interpolation</h2>
                    
                    {!tableData || !tableData.rows || tableData.rows.length === 0 ? (
                        <p className="text-gray-500 italic text-sm text-center py-8">Generate a table first to use the auto-interpolator.</p>
                    ) : (
                        <>
                            <div className="grid grid-cols-1 gap-3 mb-4">
                              <div>
                                <label className="block text-xs font-semibold text-gray-600 mb-1">Input Variable (X)</label>
                                <select className="w-full border border-gray-300 p-1.5 rounded outline-none focus:border-blue-500 text-sm" value={interpXKey} onChange={e => setInterpXKey(e.target.value)}>
                                  {Object.keys(tableData.rows[0]).map(k => (
                                      <option key={k} value={k}>{k.replace(/_/g, ' ')}</option>
                                  ))}
                                </select>
                              </div>
                              <div>
                                <label className="block text-xs font-semibold text-gray-600 mb-1">Target Variable to Calculate (Y)</label>
                                <select className="w-full border border-gray-300 p-1.5 rounded outline-none focus:border-blue-500 text-sm" value={interpYKey} onChange={e => setInterpYKey(e.target.value)}>
                                  {Object.keys(tableData.rows[0]).map(k => (
                                      <option key={k} value={k}>{k.replace(/_/g, ' ')}</option>
                                  ))}
                                </select>
                              </div>
                            </div>
                            
                            <div className="border-t border-gray-200 pt-4 flex gap-3 items-end">
                              <div className="w-1/2">
                                <label className="block text-xs font-bold text-blue-700 mb-1">Target X Value</label>
                                <input type="number" step="any" placeholder="Enter X..." className="w-full border-2 border-blue-300 p-2 rounded outline-none focus:border-blue-600 font-semibold" value={interpXValue} onChange={e => setInterpXValue(e.target.value)} />
                              </div>
                              <div className="w-1/2">
                                <label className="block text-xs font-bold text-gray-600 mb-1">Calculated Y</label>
                                <div className="w-full bg-gray-100 border border-gray-300 p-2 rounded font-mono text-gray-800 font-semibold text-center overflow-hidden h-11 flex items-center justify-center">
                                  {yTarget}
                                </div>
                              </div>
                            </div>
                        </>
                    )}
                  </div>
                </div>

                {tableError && <div className="p-3 bg-red-50 border-l-4 border-red-500 text-red-700"><strong>Error:</strong> {tableError}</div>}

                {tableData && tableData.type === 'sat' && (
                    <div className="bg-white p-0 rounded shadow border border-gray-300 overflow-x-auto">
                        <table className="min-w-full border-collapse text-sm">
                            <thead className="bg-gray-200 text-gray-800">
                                <tr>
                                    <th className="py-2 px-3 border border-gray-300 text-center align-middle" rowSpan={2}>Temp<br/><span className="font-normal text-xs">{units === 'SI' ? '°C' : '°F'}</span></th>
                                    <th className="py-2 px-3 border border-gray-300 text-center align-middle" rowSpan={2}>Press.<br/><span className="font-normal text-xs">{units === 'SI' ? 'kPa' : 'psia'}</span></th>
                                    <th className="py-1 px-3 border border-gray-300 text-center" colSpan={2}>Specific Vol. ({units === 'SI' ? 'm³/kg' : 'ft³/lbm'})</th>
                                    <th className="py-1 px-3 border border-gray-300 text-center" colSpan={3}>Int. Energy ({units === 'SI' ? 'kJ/kg' : 'Btu/lbm'})</th>
                                    <th className="py-1 px-3 border border-gray-300 text-center" colSpan={3}>Enthalpy ({units === 'SI' ? 'kJ/kg' : 'Btu/lbm'})</th>
                                    <th className="py-1 px-3 border border-gray-300 text-center" colSpan={3}>Entropy ({units === 'SI' ? 'kJ/kg·K' : 'Btu/lbm·R'})</th>
                                </tr>
                                <tr className="text-xs">
                                    <th className="py-1 px-2 border border-gray-300 text-center italic font-medium">Sat. liq. (v_f)</th>
                                    <th className="py-1 px-2 border border-gray-300 text-center italic font-medium">Sat. vap. (v_g)</th>
                                    <th className="py-1 px-2 border border-gray-300 text-center italic font-medium">Sat. liq. (u_f)</th>
                                    <th className="py-1 px-2 border border-gray-300 text-center italic font-medium">Evap. (u_fg)</th>
                                    <th className="py-1 px-2 border border-gray-300 text-center italic font-medium">Sat. vap. (u_g)</th>
                                    <th className="py-1 px-2 border border-gray-300 text-center italic font-medium">Sat. liq. (h_f)</th>
                                    <th className="py-1 px-2 border border-gray-300 text-center italic font-medium">Evap. (h_fg)</th>
                                    <th className="py-1 px-2 border border-gray-300 text-center italic font-medium">Sat. vap. (h_g)</th>
                                    <th className="py-1 px-2 border border-gray-300 text-center italic font-medium">Sat. liq. (s_f)</th>
                                    <th className="py-1 px-2 border border-gray-300 text-center italic font-medium">Evap. (s_fg)</th>
                                    <th className="py-1 px-2 border border-gray-300 text-center italic font-medium">Sat. vap. (s_g)</th>
                                </tr>
                            </thead>
                            <tbody>
                                {tableData.rows.map((row: any, idx: number) => {
                                    const T = units === 'SI' ? row.T_C : row.T_F;
                                    const P = units === 'SI' ? row.P_sat_kPa : row.P_sat_psi;
                                    const vf = units === 'SI' ? row.v_f_m3kg : row.v_f_ft3lbm;
                                    const vg = units === 'SI' ? row.v_g_m3kg : row.v_g_ft3lbm;
                                    const uf = units === 'SI' ? row.u_f_kJkg : row.u_f_BTUlb;
                                    const ufg = units === 'SI' ? row.u_fg_kJkg : row.u_fg_BTUlb;
                                    const ug = units === 'SI' ? row.u_g_kJkg : row.u_g_BTUlb;
                                    const hf = units === 'SI' ? row.h_f_kJkg : row.h_f_BTUlb;
                                    const hfg = units === 'SI' ? row.h_fg_kJkg : row.h_fg_BTUlb;
                                    const hg = units === 'SI' ? row.h_g_kJkg : row.h_g_BTUlb;
                                    const sf = units === 'SI' ? row.s_f_kJkgK : row.s_f_BTUlbR;
                                    const sfg = units === 'SI' ? row.s_fg_kJkgK : row.s_fg_BTUlbR;
                                    const sg = units === 'SI' ? row.s_g_kJkgK : row.s_g_BTUlbR;
                                    
                                    return (
                                        <tr key={idx} className={`hover:bg-blue-50 ${idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}`}>
                                            <td className="py-1.5 px-3 border border-gray-300 text-center font-semibold">{T !== null ? T.toFixed(1) : '-'}</td>
                                            <td className="py-1.5 px-3 border border-gray-300 text-right font-mono text-gray-700">{P !== null ? P.toPrecision(6) : '-'}</td>
                                            <td className="py-1.5 px-3 border border-gray-300 text-right font-mono">{vf !== null ? vf.toPrecision(5) : '-'}</td>
                                            <td className="py-1.5 px-3 border border-gray-300 text-right font-mono">{vg !== null ? vg.toPrecision(5) : '-'}</td>
                                            <td className="py-1.5 px-3 border border-gray-300 text-right font-mono">{uf !== null ? uf.toFixed(2) : '-'}</td>
                                            <td className="py-1.5 px-3 border border-gray-300 text-right font-mono text-gray-500">{ufg !== null ? ufg.toFixed(2) : '-'}</td>
                                            <td className="py-1.5 px-3 border border-gray-300 text-right font-mono">{ug !== null ? ug.toFixed(2) : '-'}</td>
                                            <td className="py-1.5 px-3 border border-gray-300 text-right font-mono">{hf !== null ? hf.toFixed(2) : '-'}</td>
                                            <td className="py-1.5 px-3 border border-gray-300 text-right font-mono text-gray-500">{hfg !== null ? hfg.toFixed(2) : '-'}</td>
                                            <td className="py-1.5 px-3 border border-gray-300 text-right font-mono">{hg !== null ? hg.toFixed(2) : '-'}</td>
                                            <td className="py-1.5 px-3 border border-gray-300 text-right font-mono">{sf !== null ? sf.toFixed(4) : '-'}</td>
                                            <td className="py-1.5 px-3 border border-gray-300 text-right font-mono text-gray-500">{sfg !== null ? sfg.toFixed(4) : '-'}</td>
                                            <td className="py-1.5 px-3 border border-gray-300 text-right font-mono">{sg !== null ? sg.toFixed(4) : '-'}</td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                )}

                {tableData && tableData.type === 'super' && (
                    <div className="bg-white p-0 rounded shadow border border-gray-300 overflow-x-auto">
                        <div className="p-3 bg-blue-50 border-b border-gray-300 text-blue-900 font-semibold">
                            Table at Fixed Pressure: {tableData.P_fixed} {units === 'SI' ? 'kPa' : 'psia'} 
                            {tableData.T_sat !== null && <span className="text-sm font-normal text-blue-700 ml-4"> (Saturation Temp: {tableData.T_sat} {units === 'SI' ? '°C' : '°F'})</span>}
                        </div>
                        <table className="min-w-full border-collapse text-sm">
                            <thead className="bg-gray-200 text-gray-800">
                                <tr>
                                    <th className="py-2 px-3 border border-gray-300 text-center">Temp<br/><span className="font-normal text-xs">{units === 'SI' ? '°C' : '°F'}</span></th>
                                    <th className="py-2 px-3 border border-gray-300 text-center">Spec. Vol. (v)<br/><span className="font-normal text-xs">{units === 'SI' ? 'm³/kg' : 'ft³/lbm'}</span></th>
                                    <th className="py-2 px-3 border border-gray-300 text-center">Int. Energy (u)<br/><span className="font-normal text-xs">{units === 'SI' ? 'kJ/kg' : 'Btu/lbm'}</span></th>
                                    <th className="py-2 px-3 border border-gray-300 text-center">Enthalpy (h)<br/><span className="font-normal text-xs">{units === 'SI' ? 'kJ/kg' : 'Btu/lbm'}</span></th>
                                    <th className="py-2 px-3 border border-gray-300 text-center">Entropy (s)<br/><span className="font-normal text-xs">{units === 'SI' ? 'kJ/kg·K' : 'Btu/lbm·R'}</span></th>
                                </tr>
                            </thead>
                            <tbody>
                                {tableData.rows.map((row: any, idx: number) => {
                                    const T = units === 'SI' ? row.T_C : row.T_F;
                                    const v = units === 'SI' ? row.v_m3kg : row.v_ft3lbm;
                                    const u = units === 'SI' ? row.u_kJkg : row.u_BTUlb;
                                    const h = units === 'SI' ? row.h_kJkg : row.h_BTUlb;
                                    const s = units === 'SI' ? row.s_kJkgK : row.s_BTUlbR;
                                    
                                    const isSat = tableData.T_sat && Math.abs(T - tableData.T_sat) < 0.02;

                                    return (
                                        <tr key={idx} className={`hover:bg-blue-50 ${isSat ? 'bg-blue-100 font-medium' : (idx % 2 === 0 ? 'bg-white' : 'bg-gray-50')}`}>
                                            <td className="py-1.5 px-3 border border-gray-300 text-center">{T !== null ? T.toFixed(2) : '-'} {isSat && '(Sat)'}</td>
                                            <td className="py-1.5 px-3 border border-gray-300 text-right font-mono">{v !== null ? v.toPrecision(5) : '-'}</td>
                                            <td className="py-1.5 px-3 border border-gray-300 text-right font-mono">{u !== null ? u.toFixed(2) : '-'}</td>
                                            <td className="py-1.5 px-3 border border-gray-300 text-right font-mono">{h !== null ? h.toFixed(2) : '-'}</td>
                                            <td className="py-1.5 px-3 border border-gray-300 text-right font-mono">{s !== null ? s.toFixed(4) : '-'}</td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                )}

            </div>
        )}
      </main>
    </div>
  )
}
