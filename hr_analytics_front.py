import os
import io
import json
import pandas as pd
import streamlit as st
from openai import OpenAI

# -----------------------------
# CONFIGURACIÓN
# -----------------------------
MODEL_NAME = "gpt-4o-mini"
PESOS_360 = {"manager": 0.4, "pares": 0.3, "clientes": 0.2, "auto": 0.1}
client = OpenAI()  # requiere OPENAI_API_KEY en el entorno

PROMPT_BASE = """Eres un asistente experto en Recursos Humanos...
(usa aquí el prompt completo que definiste)
"""

# -----------------------------
# FUNCIONES BACKEND
# -----------------------------
def calcular_nota_360(df):
    df["Nota360_calc"] = (
        df["EvaluaciónManager"] * PESOS_360["manager"]
        + df["EvaluaciónPares"] * PESOS_360["pares"]
        + df["EvaluaciónClientes"] * PESOS_360["clientes"]
        + df["Autoevaluación"] * PESOS_360["auto"]
    ) / 20.0  # convertir a escala 0–5
    return df.round(2)

def match_rango(emp, rangos):
    filtro = (
        (rangos["Departamento"] == emp["Departamento"]) &
        (rangos["Posición"] == emp["Posición"]) &
        (rangos["Nivel"] == emp["Nivel"]) &
        (rangos["Región"] == emp["Región"]) &
        (emp["Antigüedad"] >= rangos["Antigüedad_Mín"]) &
        (emp["Antigüedad"] <= rangos["Antigüedad_Máx"])
    )
    match = rangos[filtro]
    return match.iloc[0].to_dict() if not match.empty else None

def build_prompt(emp, rango):
    return PROMPT_BASE.format(
        departamento=emp["Departamento"],
        posicion=emp["Posición"],
        nivel=emp["Nivel"],
        region=emp["Región"],
        antiguedad=emp["Antigüedad"],
        salario_actual=emp["SalarioActual"],
        nota360=emp["Nota360_calc"],
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

def call_ai(prompt):
    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    content = resp.choices[0].message.content
    try:
        return json.loads(content)
    except:
        return {"decision":"NO_SUBIDA","justificacion":content,"plan_fundae":None}

# -----------------------------
# STREAMLIT FRONTEND
# -----------------------------
st.title("HR Analytics Assistant")

empleados_file = st.file_uploader("Sube empleados.xlsx", type=["xlsx"])
rangos_file = st.file_uploader("Sube rangos.xlsx", type=["xlsx"])

if empleados_file and rangos_file:
    empleados = pd.read_excel(empleados_file, sheet_name="Empleados")
    rangos = pd.read_excel(rangos_file, sheet_name="Rangos")

    empleados = calcular_nota_360(empleados)

    st.subheader("Vista previa empleados")
    st.dataframe(empleados.head())

    emp_id = st.selectbox("Selecciona un empleado", empleados["EmployeeID"])
    if st.button("Generar recomendación IA"):
        emp = empleados[empleados["EmployeeID"] == emp_id].iloc[0]
        rango = match_rango(emp, rangos)
        if rango:
            prompt = build_prompt(emp, rango)
            result = call_ai(prompt)
            st.json(result)
        else:
            st.warning("No se encontró rango para este empleado")
