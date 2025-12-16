import streamlit as st
import pandas as pd

st.title("HR Analytics Assistant - Demo")

# Subir archivo Excel
uploaded_file = st.file_uploader("Sube el Excel con datos de empleados", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    # Función de recomendación
    def generar_recomendacion(nota360, salario, referencia):
        if nota360 >= 4.0 and salario < referencia:
            return "✅ Subida salarial recomendada (+8%)"
        elif nota360 >= 3.0:
            return "📈 Mantener salario, plan de formación en liderazgo (FUNDAE)"
        else:
            return "📚 Plan intensivo de desarrollo en competencias básicas (FUNDAE)"

    # Crear columna de recomendación
    df["Recomendación"] = df.apply(
        lambda row: generar_recomendacion(row["Nota360"], row["Salario Actual"], row["Referencia Mercado"]),
        axis=1
    )

    # Mostrar tabla con recomendaciones
    st.subheader("Resultados con recomendaciones")
    st.dataframe(df)

    # Selección de empleado para ver detalle
    empleado = st.selectbox("Selecciona un empleado", df["Nombre"])
    info = df[df["Nombre"] == empleado].iloc[0]

    st.write(f"**Nota360:** {info['Nota360']}")
    st.write(f"**Salario Actual:** {info['Salario Actual']} €")
    st.write(f"**Referencia Mercado:** {info['Referencia Mercado']} €")
    st.write(f"**Recomendación:** {info['Recomendación']}")
