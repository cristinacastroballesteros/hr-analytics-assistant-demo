# app.py
import os
import json
import io
import pandas as pd
import streamlit as st
from openai import OpenAI

# -----------------------------
# CONFIGURACIÓN
# -----------------------------
MODEL_NAME = "gpt-4o-mini"
PESOS_360 = {"manager": 0.4, "pares": 0.3, "clientes": 0.2, "auto": 0.1}

client = OpenAI()  # Requiere OPENAI_API_KEY en el entorno

PROMPT_BASE = """Eres un asistente experto en Recursos Humanos, especializado en compensación, evaluación del desempeño y formación corporativa en España.
Tu función es actuar como motor de recomendación para el departamento de Recursos Humanos de la empresa RHC, proporcionando decisiones objetivas, trazables y justificables a partir de datos estructurados.

REGLAS ESTRICTAS:
- No inventes proveedores, empresas, precios ni datos sensibles.
- No menciones marcas comerciales.
- Usa un lenguaje profesional, neutro y justificable ante RRHH.
- Si no hay subida salarial, debes recomendar un plan formativo tipo FUNDAE.
- Si hay subida salarial, NO recomiendes formación salvo que sea estrictamente necesaria.
- Basa siempre la decisión en Nota360, posición en la banda salarial y benchmark de mercado.

CONTEXTO DEL EMPLEADO:
Departamento: {departamento}
Posición: {posicion}
Nivel: {nivel}
Región: {region}
Antigüedad (años): {antiguedad}
Salario actual (€): {salario_actual}
Nota360 (0–5): {nota360}
Evaluación Manager: {eval_manager}
Evaluación Pares: {eval_pares}
Evaluación Clientes: {eval_clientes}
Autoevaluación: {eval_auto}
Competencias fuertes: {competencias_fuertes}
Competencias débiles: {competencias_debiles}
Benchmark mercado (% vs mercado): {benchmark}

CONTEXTO SALARIAL:
Rango mínimo (€): {rango_min}
Rango máximo (€): {rango_max}
Política de subida mínima (%): {politica_min}
Política de subida máxima (%): {politica_max}

TAREA:
Determina si el empleado debe recibir subida salarial.

Si procede subida:
- Indica el % recomendado.
- Calcula el nuevo salario.
- Justifica la decisión en 5–7 líneas.

Si NO procede subida:
- Explica brevemente por qué.
- Diseña un plan FUNDAE con 3–5 cursos genéricos.
  Para cada curso incluye:
  - Nombre del curso
  - Competencia a desarrollar
  - Duración en horas
  - Modalidad (online / presencial / mixta)
  - Justificación

FORMATO DE SALIDA (JSON ESTRICTO):
{
  "decision": "SUBIDA" | "NO_SUBIDA",
  "porcentaje_subida": number | null,
  "nuevo_salario": number | null,
  "justificacion": "texto",
  "plan_fundae": [
    {
      "curso": "string",
      "competencia": "string",
      "horas": number,
      "modalidad": "string",
      "justificacion": "string"
    }
  ] | null
}
"""

# -----------------------------
# UTILIDADES DE CARGA
# -----------------------------
@st.cache_data
def load_data_from_files(empleados_file: io.BytesIO, rangos_file: io.BytesIO):
    empleados = pd.read_excel(empleados_file, sheet_name="Empleados")
    rangos = pd.read_excel(rangos_file, sheet_name="Rangos")
    return empleados, rangos

@st.cache_data
def load_data_from_local():
    empleados = pd.read_excel("data/empleados.xlsx", sheet_name="Empleados")
    rangos = pd.read_excel("data/rangos.xlsx", sheet_name="Rangos")
    return empleados, rangos

# -----------------------------
# CÁLCULO NOTA 360
# -----------------------------
def calcular_nota_360(df: pd.DataFrame) -> pd.DataFrame:
    # Tus evaluaciones vienen en escala 0–100. Convertimos a 0–5 dividiendo por 20 tras ponderación.
    # Nueva columna Nota360_calc para no pisar la fuente original si ya trae "Nota360".
    df["Nota360_calc"] = (
        df["EvaluaciónManager"] * PESOS_360["manager"]
        + df["EvaluaciónPares"] * PESOS_360["pares"]
        + df["EvaluaciónClientes"] * PESOS_360["clientes"]
        + df["Autoevaluación"] * PESOS_360["auto"]
    ) / 20.0
    df["Nota360_calc"] = df["Nota360_calc"].round(2)
    return df

# -----------------------------
# MATCHING CON BANDAS
# -----------------------------
def match_rango_row(emp: pd.Series, rangos: pd.DataFrame):
    # Filtro por claves y por antigüedad dentro del intervalo
    candidates = rangos[
        (rangos["Departamento"] == emp["Departamento"])
        & (rangos["Posición"] == emp["Posición"])
        & (rangos["Nivel"] == emp["Nivel"])
        & (rangos["Región"] == emp["Región"])
        & (emp["Antigüedad"] >= rangos["Antigüedad_Mín"])
        & (emp["Antigüedad"] <= rangos["Antigüedad_Máx"])
    ]
    if candidates.empty:
        return None
    # Si hubiese varias coincidencias, tomamos la primera (las tablas de rangos suelen ser únicas)
    return candidates.iloc[0].to_dict()

# -----------------------------
# PROMPT BUILDER
# -----------------------------
def build_prompt(emp: pd.Series, rango: dict) -> str:
    return PROMPT_BASE.format(
        departamento=emp["Departamento"],
        posicion=emp["Posición"],
        nivel=emp["Nivel"],
        region=emp["Región"],
        antiguedad=emp["Antigüedad"],
        salario_actual=emp["SalarioActual"],
        nota360=emp.get("Nota360_calc", emp.get("Nota360", None)),
        eval_manager=emp["EvaluaciónManager"],
        eval_pares=emp["EvaluaciónPares"],
        eval_clientes=emp["EvaluaciónClientes"],
        eval_auto=emp["Autoevaluación"],
        competencias_fuertes=emp.get("CompetenciasFuertes", ""),
        competencias_debiles=emp.get("CompetenciasDébiles", ""),
        benchmark=emp.get("BenchmarkMercado", ""),
        rango_min=rango["Rango_Salarial_Mín"],
        rango_max=rango["Rango_Salarial_Máx"],
        politica_min=rango["Política_Subida_Mín"],
        politica_max=rango["Política_Subida_Máx"],
    )

# -----------------------------
# LLAMADA A IA
# -----------------------------
def call_ai(prompt: str) -> dict:
    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    content = resp.choices[0].message.content
    # El modelo devuelve JSON según el prompt. Parseamos.
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        # Fallback defensivo: intenta corregir formato mínimo
        parsed = {"decision": "NO_SUBIDA", "porcentaje_subida": None, "nuevo_salario": None, "justificacion": content, "plan_fundae": None}
    return parsed

# -----------------------------
# PIPELINE BACKEND (LOTE)
# -----------------------------
def run_backend(empleados: pd.DataFrame, rangos: pd.DataFrame) -> pd.DataFrame:
    empleados = calcular_nota_360(empleados)

    resultados = []
    for _, emp in empleados.iterrows():
        rango = match_rango_row(emp, rangos)
        if rango is None:
            continue
        prompt = build_prompt(emp, rango)
        ai_result = call_ai(prompt)

        row_out = {**emp.to_dict(), **ai_result}
        resultados.append(row_out)

    df_master = pd.DataFrame(resultados)
    return df_master

# -----------------------------
# STREAMLIT UI
# -----------------------------
st.set_page_config(page_title="HR Analytics Assistant", layout="wide")
st.title("HR Analytics Assistant - Recomendaciones RRHH (Compensación y Formación)")

# Subida interactiva de ficheros o carga local
st.sidebar.header("Carga de datos")
opt = st.sidebar.radio("Origen de datos", ["Subir Excel", "Usar carpeta local (data/)"])

empleados_df, rangos_df = None, None
if opt == "Subir Excel":
    empleados_file = st.sidebar.file_uploader("Sube empleados.xlsx (hoja: Empleados)", type=["xlsx"])
    rangos_file = st.sidebar.file_uploader("Sube rangos.xlsx (hoja: Rangos)", type=["xlsx"])
    if empleados_file and rangos_file:
        empleados_df, rangos_df = load_data_from_files(empleados_file, rangos_file)
elif opt == "Usar carpeta local (data/)"]:
    try:
        empleados_df, rangos_df = load_data_from_local()
        st.sidebar.success("Datos cargados desde data/empleados.xlsx y data/rangos.xlsx")
    except Exception as e:
        st.sidebar.error(f"No se pudo cargar desde carpeta local: {e}")

# Mostrar y preparar datos
if empleados_df is not None and rangos_df is not None:
    # Normalizamos tipos
    for col in ["Antigüedad", "SalarioActual", "EvaluaciónManager", "EvaluaciónPares", "EvaluaciónClientes", "Autoevaluación"]:
        if col in empleados_df.columns:
            empleados_df[col] = pd.to_numeric(empleados_df[col], errors="coerce")

    empleados_df = calcular_nota_360(empleados_df)

    st.subheader("Vista previa de Empleados")
    st.dataframe(empleados_df.head(20), use_container_width=True)

    st.subheader("Vista previa de Rangos")
    st.dataframe(rangos_df.head(20), use_container_width=True)

    # Filtros
    st.sidebar.header("Filtros")
    dep_sel = st.sidebar.multiselect("Departamento", sorted(empleados_df["Departamento"].unique()))
    pos_sel = st.sidebar.multiselect("Posición", sorted(empleados_df["Posición"].unique()))
    niv_sel = st.sidebar.multiselect("Nivel", sorted(empleados_df["Nivel"].unique()))
    reg_sel = st.sidebar.multiselect("Región", sorted(empleados_df["Región"].unique()))

    filtered = empleados_df.copy()
    if dep_sel:
        filtered = filtered[filtered["Departamento"].isin(dep_sel)]
    if pos_sel:
        filtered = filtered[filtered["Posición"].isin(pos_sel)]
    if niv_sel:
        filtered = filtered[filtered["Nivel"].isin(niv_sel)]
    if reg_sel:
        filtered = filtered[filtered["Región"].isin(reg_sel)]

    # Buscador por ID
    st.sidebar.header("Búsqueda")
    search_id = st.sidebar.text_input("Buscar por EmployeeID")
    if search_id:
        filtered = filtered[filtered["EmployeeID"].astype(str).str.contains(search_id, case=False, na=False)]

    st.subheader("Empleados filtrados")
    st.dataframe(
        filtered[[
            "EmployeeID","Departamento","Posición","Nivel","Región","Antigüedad","SalarioActual",
            "EvaluaciónManager","EvaluaciónPares","EvaluaciónClientes","Autoevaluación","Nota360_calc"
        ]],
        use_container_width=True
    )

    st.markdown("---")
    st.subheader("Evaluación por IA (individual)")
    col1, col2 = st.columns([1,1])
    with col1:
        emp_choice = st.selectbox("Selecciona un empleado", filtered["EmployeeID"])
    with col2:
        run_one = st.button("Generar recomendación IA para el empleado seleccionado")

    if run_one and emp_choice:
        emp_row = filtered[filtered["EmployeeID"] == emp_choice].iloc[0]
        rango = match_rango_row(emp_row, rangos_df)
        if rango is None:
            st.warning("No se encontró rango coincidente para este empleado (revisa claves y antigüedad).")
        else:
            prompt = build_prompt(emp_row, rango)
            with st.spinner("Llamando a IA…"):
                result = call_ai(prompt)
            st.write("Salida (JSON):")
            st.json(result, expanded=True)

            # Render amigable
            if result.get("decision") == "SUBIDA":
                st.success(f"SUBIDA recomendada: +{result.get('porcentaje_subida')}% → Nuevo salario: {result.get('nuevo_salario')} €")
            else:
                st.info("NO SUBIDA. Recomendación de plan FUNDAE.")
            st.write("Justificación:")
            st.write(result.get("justificacion", ""))

            if result.get("plan_fundae"):
                st.write("Plan FUNDAE sugerido:")
                st.table(pd.DataFrame(result["plan_fundae"]))

    st.markdown("---")
    st.subheader("Evaluación por IA (lote)")
    run_batch = st.button("Generar recomendaciones IA para todos los empleados filtrados")
    if run_batch:
        out_rows = []
        progress = st.progress(0)
        total = len(filtered)
        for i, (_, emp_row) in enumerate(filtered.iterrows(), start=1):
            rango = match_rango_row(emp_row, rangos_df)
            if rango is None:
                continue
            prompt = build_prompt(emp_row, rango)
            result = call_ai(prompt)
            out_rows.append({**emp_row.to_dict(), **result})
            progress.progress(min(i / total, 1.0))

        if not out_rows:
            st.warning("No se generaron resultados (posible ausencia de rangos coincidentes).")
        else:
            df_out = pd.DataFrame(out_rows)

            # Vistas separadas
            df_subida = df_out[df_out["decision"] == "SUBIDA"].copy()
            df_formacion = df_out[df_out["decision"] == "NO_SUBIDA"].copy()

            st.success(f"Generadas {len(df_out)} recomendaciones.")
            st.write("Resultados completos:")
            st.dataframe(
                df_out[[
                    "EmployeeID","Departamento","Posición","Nivel","Región",
                    "Antigüedad","SalarioActual","Nota360_calc","decision","porcentaje_subida","nuevo_salario"
                ]],
                use_container_width=True
            )

            st.write("Empleados con SUBIDA recomendada:")
            st.dataframe(
                df_subida[[
                    "EmployeeID","Departamento","Posición","Nivel","Región",
                    "Antigüedad","SalarioActual","Nota360_calc","porcentaje_subida","nuevo_salario","justificacion"
                ]],
                use_container_width=True
            )

            st.write("Empleados con plan FUNDAE (NO SUBIDA):")
            st.dataframe(
                df_formacion[[
                    "EmployeeID","Departamento","Posición","Nivel","Región",
                    "Antigüedad","SalarioActual","Nota360_calc","justificacion"
                ]],
                use_container_width=True
            )

            # Descarga Excel
            to_excel = st.button("Descargar resultados en Excel")
            if to_excel:
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                    df_out.to_excel(writer, sheet_name="Resultados", index=False)
                    df_subida.to_excel(writer, sheet_name="Subidas", index=False)
                    df_formacion.to_excel(writer, sheet_name="Formacion", index=False)
                output.seek(0)
                st.download_button(
                    label="Descargar Resultados_Completos.xlsx",
                    data=output,
                    file_name="Resultados_Completos.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

else:
    st.info("Sube ambos Excel o usa la carga local para empezar.")

# -----------------------------
# Nota de uso
# -----------------------------
st.caption("Asegúrate de definir OPENAI_API_KEY en tu entorno antes de ejecutar: export OPENAI_API_KEY='tu_api_key'")
