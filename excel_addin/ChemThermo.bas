Attribute VB_Name = "ChemThermo"
'==============================================================================
' ChemThermo.bas — Excel VBA Module for =THERMO() Worksheet Function
'==============================================================================
' Provides custom worksheet functions that call the ChemEng Thermodynamic API.
'
' INSTALLATION:
'   1. Run: python xlwings_server.py    (keeps a terminal window open)
'   2. In Excel: Developer tab → Visual Basic → Import File → select this .bas
'   3. Or: Tools → References → Browse → select ChemThermo.xlam
'
' USAGE (in any Excel cell):
'   =THERMO("sCO2",  "Density",   "T", 308.15, "P", 8000000)
'   =THERMO("Water", "Enthalpy",  "T", 373.15, "Q", 1)
'   =THERMO("NH3",   "Entropy",   "T", 263.15, "Q", 0)
'   =THERMO("R1234yf","Pressure", "T", 298.15, "Q", 1)
'   =THERMO_SAT("Water", "hfg",   "T_C", 100)
'
' NOTE: Input values must be in SI units (K, Pa, J/kg, J/kg/K).
'       Use helper functions T_C_to_K(), kPa_to_Pa() below for conversions.
'
' API ENDPOINT (configurable):
'   - Local (offline): http://localhost:8765   (xlwings_server.py)
'   - Cloud  (online): https://api.chemengcalc.io  (your deployed instance)
'==============================================================================

Option Explicit

' ---- Configuration ----------------------------------------------------------
Private Const LOCAL_API  As String = "http://127.0.0.1:8765"
Private Const CLOUD_API  As String = "https://api.chemengcalc.io"   ' Update with your URL
Private Const USE_CLOUD  As Boolean = False   ' Set True to use cloud API

Private Function API_BASE() As String
    If USE_CLOUD Then
        API_BASE = CLOUD_API
    Else
        API_BASE = LOCAL_API
    End If
End Function


'==============================================================================
' THERMO() — Main worksheet function
'
' Returns a single thermodynamic property for a given state.
'
' Parameters:
'   fluid  (String) : Fluid name or alias, e.g. "Water", "sCO2", "R1234yf"
'   prop   (String) : Property to return, e.g. "Density", "Enthalpy", "Entropy"
'   in1    (String) : First input type: "T", "P", "H", "S", or "Q"
'   v1     (Double) : Value of first input (SI units: K, Pa, J/kg, J/kg/K)
'   in2    (String) : Second input type
'   v2     (Double) : Value of second input (SI units)
'   unit   (String, Optional) : "SI" or "Imperial" (default "SI")
'
' Returns: Double — the requested property in SI (or Imperial) units
'
' Example:
'   =THERMO("Water", "Enthalpy", "T", 373.15, "Q", 1)     → 2675.57 kJ/kg
'   =THERMO("sCO2",  "Density",  "T", 308.15, "P", 8e6)   → 623.5 kg/m³
'==============================================================================
Public Function THERMO(fluid As String, prop As String, _
                        in1 As String, v1 As Double, _
                        in2 As String, v2 As Double, _
                        Optional unit As String = "SI") As Variant

    On Error GoTo ErrHandler

    Dim url As String
    url = API_BASE() & "/thermo" & _
          "?fluid=" & EncodeURL(fluid) & _
          "&prop="  & EncodeURL(prop)  & _
          "&in1="   & EncodeURL(in1)   & _
          "&v1="    & CStr(v1)          & _
          "&in2="   & EncodeURL(in2)   & _
          "&v2="    & CStr(v2)          & _
          "&unit="  & EncodeURL(unit)

    Dim http As Object
    Set http = CreateObject("MSXML2.XMLHTTP")
    http.Open "GET", url, False
    http.Send

    If http.Status = 200 Then
        THERMO = CDbl(http.responseText)
    Else
        THERMO = CVErr(xlErrValue)   ' Returns #VALUE! in cell
    End If

    Set http = Nothing
    Exit Function

ErrHandler:
    THERMO = CVErr(xlErrValue)
    Set http = Nothing
End Function


'==============================================================================
' THERMO_SAT() — Saturation property lookup
'
' Returns a saturation property (h_f, h_g, h_fg, s_f, s_g, P_sat, T_sat, etc.)
' at a given temperature or pressure.
'
' Parameters:
'   fluid    (String) : Fluid name or alias
'   prop     (String) : "h_f", "h_g", "h_fg", "s_f", "s_g", "s_fg",
'                       "v_f", "v_g", "P_sat", "T_sat", "hfg", etc.
'   input_by (String) : "T_C" (temperature in °C) or "P_kPa" (pressure in kPa)
'   value    (Double) : Temperature (°C) or Pressure (kPa)
'
' Example:
'   =THERMO_SAT("Water", "h_fg", "T_C", 100)   → 2256.5 kJ/kg
'   =THERMO_SAT("NH3",   "P_sat","T_C", -10)   → ~290 kPa
'==============================================================================
Public Function THERMO_SAT(fluid As String, prop As String, _
                            input_by As String, value As Double) As Variant

    On Error GoTo ErrHandler

    Dim url As String
    If UCase(input_by) = "T_C" Then
        url = API_BASE() & "/saturation" & _
              "?fluid=" & EncodeURL(fluid) & _
              "&T_C=" & CStr(value)
    ElseIf UCase(input_by) = "P_KPA" Then
        url = API_BASE() & "/saturation" & _
              "?fluid=" & EncodeURL(fluid) & _
              "&P_kPa=" & CStr(value)
    Else
        THERMO_SAT = CVErr(xlErrValue)
        Exit Function
    End If

    Dim http As Object
    Set http = CreateObject("MSXML2.XMLHTTP")
    http.Open "GET", url, False
    http.Send

    If http.Status <> 200 Then
        THERMO_SAT = CVErr(xlErrValue)
        Exit Function
    End If

    ' Parse JSON response using simple string search
    Dim json As String
    json = http.responseText

    Dim prop_lower As String
    prop_lower = LCase(prop)

    Select Case prop_lower
        Case "h_f", "hf"
            THERMO_SAT = ExtractJsonNumber(json, "h_kJkg", "saturated_liquid")
        Case "h_g", "hg"
            THERMO_SAT = ExtractJsonNumber(json, "h_kJkg", "saturated_vapor")
        Case "h_fg", "hfg", "latent_heat", "latent"
            THERMO_SAT = ExtractJsonNumber(json, "hfg_kJkg", "")
        Case "s_f", "sf"
            THERMO_SAT = ExtractJsonNumber(json, "s_kJkgK", "saturated_liquid")
        Case "s_g", "sg"
            THERMO_SAT = ExtractJsonNumber(json, "s_kJkgK", "saturated_vapor")
        Case "s_fg", "sfg"
            THERMO_SAT = ExtractJsonNumber(json, "sfg_kJkgK", "")
        Case "v_f", "vf"
            THERMO_SAT = ExtractJsonNumber(json, "v_m3kg", "saturated_liquid")
        Case "v_g", "vg"
            THERMO_SAT = ExtractJsonNumber(json, "v_m3kg", "saturated_vapor")
        Case "p_sat", "psat", "pressure"
            THERMO_SAT = ExtractJsonNumber(json, "P_kPa", "saturated_liquid")
        Case "t_sat", "tsat", "temperature"
            THERMO_SAT = ExtractJsonNumber(json, "T_C", "saturated_liquid")
        Case "u_f", "uf"
            THERMO_SAT = ExtractJsonNumber(json, "u_kJkg", "saturated_liquid")
        Case "u_g", "ug"
            THERMO_SAT = ExtractJsonNumber(json, "u_kJkg", "saturated_vapor")
        Case "u_fg", "ufg"
            THERMO_SAT = ExtractJsonNumber(json, "ufg_kJkg", "")
        Case Else
            THERMO_SAT = CVErr(xlErrValue)
    End Select

    Set http = Nothing
    Exit Function

ErrHandler:
    THERMO_SAT = CVErr(xlErrValue)
    Set http = Nothing
End Function


'==============================================================================
' UNIT CONVERSION HELPERS (use in formulas alongside THERMO)
'==============================================================================

' Convert °C to Kelvin
Public Function T_C_TO_K(T_C As Double) As Double
    T_C_TO_K = T_C + 273.15
End Function

' Convert °F to Kelvin
Public Function T_F_TO_K(T_F As Double) As Double
    T_F_TO_K = (T_F - 32) * 5 / 9 + 273.15
End Function

' Convert kPa to Pa
Public Function KPA_TO_PA(P_kPa As Double) As Double
    KPA_TO_PA = P_kPa * 1000#
End Function

' Convert MPa to Pa
Public Function MPA_TO_PA(P_MPa As Double) As Double
    MPA_TO_PA = P_MPa * 1000000#
End Function

' Convert bar to Pa
Public Function BAR_TO_PA(P_bar As Double) As Double
    BAR_TO_PA = P_bar * 100000#
End Function

' Convert psi to Pa
Public Function PSI_TO_PA(P_psi As Double) As Double
    PSI_TO_PA = P_psi * 6894.757293168
End Function

' Convert kJ/kg to J/kg
Public Function KJKG_TO_JKG(h As Double) As Double
    KJKG_TO_JKG = h * 1000#
End Function

' Convert kJ/kg/K to J/kg/K
Public Function KJKGK_TO_JKGK(s As Double) As Double
    KJKGK_TO_JKGK = s * 1000#
End Function


'==============================================================================
' PRIVATE HELPERS
'==============================================================================

Private Function EncodeURL(s As String) As String
    ' Simple URL encoding for fluid names and property names
    EncodeURL = s
    EncodeURL = Replace(EncodeURL, " ", "%20")
    EncodeURL = Replace(EncodeURL, "/", "%2F")
End Function

Private Function ExtractJsonNumber(json As String, key As String, section As String) As Variant
    ' Minimal JSON number extractor. Works for flat and one-level nested JSON.
    Dim search_area As String
    Dim pos1 As Long, pos2 As Long, pos3 As Long

    If section <> "" Then
        ' Find the section first
        pos1 = InStr(json, """" & section & """")
        If pos1 = 0 Then
            ExtractJsonNumber = CVErr(xlErrNA)
            Exit Function
        End If
        search_area = Mid(json, pos1)
    Else
        search_area = json
    End If

    ' Find the key
    pos1 = InStr(search_area, """" & key & """")
    If pos1 = 0 Then
        ExtractJsonNumber = CVErr(xlErrNA)
        Exit Function
    End If

    pos2 = InStr(pos1, search_area, ":")
    If pos2 = 0 Then
        ExtractJsonNumber = CVErr(xlErrNA)
        Exit Function
    End If

    ' Extract number (until comma or closing brace)
    Dim start_pos As Long
    start_pos = pos2 + 1
    ' Skip whitespace
    Do While Mid(search_area, start_pos, 1) = " " Or Mid(search_area, start_pos, 1) = Chr(10) Or Mid(search_area, start_pos, 1) = Chr(13)
        start_pos = start_pos + 1
    Loop

    pos3 = start_pos
    Do While Mid(search_area, pos3, 1) <> "," And _
             Mid(search_area, pos3, 1) <> "}" And _
             Mid(search_area, pos3, 1) <> "]" And _
             pos3 < Len(search_area)
        pos3 = pos3 + 1
    Loop

    Dim num_str As String
    num_str = Trim(Mid(search_area, start_pos, pos3 - start_pos))

    If num_str = "null" Or num_str = "" Then
        ExtractJsonNumber = CVErr(xlErrNA)
    Else
        On Error Resume Next
        ExtractJsonNumber = CDbl(num_str)
        If Err.Number <> 0 Then ExtractJsonNumber = CVErr(xlErrValue)
        On Error GoTo 0
    End If
End Function
