import streamlit as st
import pandas as pd

st.set_page_config(page_title="HR Analytics Assistant - Demo", page_icon="📊", layout="wide")

# ==============================
# Datos simulados de empleados
# ==============================
data = {
    "Nombre": ["María López", "Juan Pérez", "Ana García", "Luis Martín"],
    "Nota360": [4.2, 3.5, 2.8, 4.6],
    "Salario Actual": [32000, 28000, 25000, 36000],
    "Banda Salarial": ["B2", "B1", "A3", "B3"],
    "Referencia Mercado": [35000, 30000, 27000, 38000],
}
df = pd.DataFrame(data)

# ==============================
# Lógica de recomendación simulada
# ==============================
def generar_recomendacion(nota360, salario, referencia):
    # Reglas ejemplo para la demo
    if nota360 >= 4.0 and salario < referencia:
        return "Recomendar subida salarial (+8%). Justificación: desempeño alto y gap vs mercado."
    elif nota360 >= 4.0 and salario >= referencia:
        return "Mantener salario. Justificación: desempeño alto, sin gap vs mercado."
    elif 3.0 <= nota360 < 4.0:
        return "Mantener salario. Plan de formación en liderazgo y comunicación (FUNDAE)."
    else:
        return "Plan intensivo de desarrollo en competencias técnicas y trabajo en equipo (FUNDAE)."

df["Recomendación"] = df.apply(
    lambda r: generar_recomendacion(r["Nota360"], r["Salario Actual"], r["Referencia Mercado"]),
    axis=1
)

# ==============================
# Interfaz Streamlit
# ==============================
st.title("HR Analytics Assistant - Demo")
st.markdown("""
Este prototipo muestra cómo funcionaría el sistema de analítica de RRHH sin base de datos.
Los datos están simulados para enseñar el flujo de recomendaciones y análisis.
""")

# Panel principal con tabla
st.subheader("Datos de empleados y recomendaciones")
st.dataframe(df, use_container_width=True)

# Filtros y detalle
st.subheader("Detalle por empleado")
col1, col2 = st.columns([1, 2])

with col1:
    empleado = st.selectbox("Selecciona un empleado", df["Nombre"])
    info = df[df["Nombre"] == empleado].iloc[0]
    st.metric(label="Nota360", value=info["Nota360"])
    st.metric(label="Salario Actual (€)", value=f"{info['Salario Actual']:,}".replace(",", "."))
    st.metric(label="Referencia Mercado (€)", value=f"{info['Referencia Mercado']:,}".replace(",", "."))
    st.write(f"**Banda Salarial:** {info['Banda Salarial']}")

with col2:
    st.write("**Recomendación:**")
    st.info(info["Recomendación"])

# Exportación a Excel (descarga)
st.subheader("Descargar Excel consolidado")
excel_buffer = df.to_excel(index=False, sheet_name="HR Analytics", engine="openpyxl")
# Nota: Para compatibilidad en Streamlit Cloud, usa bytes con to_excel en un buffer BytesIO
from io import BytesIO
bio = BytesIO()
with pd.ExcelWriter(bio, engine="openpyxl") as writer:
    df.to_excel(writer, index=False, sheet_name="HR Analytics")
bio.seek(0)

st.download_button(
    label="Descargar Excel",
    data=bio,
    file_name="hr_analytics_consolidado.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

st.caption("Demo sin base de datos: datos en memoria y lógica simplificada para mostrar el funcionamiento.")
