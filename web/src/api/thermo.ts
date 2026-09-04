import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface PropertyRequest {
    fluid: string;
    T?: number;
    P?: number;
    H?: number;
    S?: number;
    Q?: number;
    T_unit: string;
    P_unit: string;
    H_unit: string;
    S_unit: string;
    output_units: string;
}

export const fetchProperties = async (req: PropertyRequest) => {
    const res = await axios.post(`${API_URL}/properties`, req);
    return res.data.properties;
};

export const fetchPhaseCurve = async (fluid: string) => {
    const res = await axios.get(`${API_URL}/phase-curve`, { params: { fluid, n_points: 50 } });
    return res.data;
};

export const fetchFluids = async () => {
    const res = await axios.get(`${API_URL}/fluids`);
    return res.data.fluids;
};

export const fetchSaturationTable = async (fluid: string, by_pressure: boolean, start_val: number, end_val: number, n_points: number, units: string) => {
    const res = await axios.get(`${API_URL}/saturation-table`, { 
        params: { fluid, by_pressure, start_val, end_val, n_points, T_unit: units === 'SI' ? 'C' : 'F', output_units: units } 
    });
    return res.data;
};

export const fetchSuperheatedTable = async (fluid: string, P_val: number, T_start: number, T_end: number, n_points: number, units: string) => {
    const res = await axios.get(`${API_URL}/superheated-table`, { 
        params: { fluid, P_val, T_start, T_end, n_points, output_units: units } 
    });
    return res.data;
};
