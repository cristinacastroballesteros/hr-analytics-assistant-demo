import streamlit as st
import pandas as pd

st.title("HR Analytics Assistant - Multi-Excel Demo")

# Subir varios archivos Excel
uploaded_files = st.file_uploader(
    "Sube uno o varios Excel con datos de empleados", 
    type=["xlsx"], 
    accept_multiple_files=True
)

if uploaded_files:
    # Leer y concatenar todos los archivos
    dfs = []
    for file in uploaded_files:
        df_temp = pd.read_excel(file)
        dfs.append(df_temp)
    df = pd.concat(dfs, ignore_index=True)

    # Función de recomendación
    def generar_recomendacion(nota360, salario, referencia):
        if nota360 >= 4.0 and salario < referencia:
            return "✅ Subida salarial recomendada (+8%) - Alto desempeño con salario por debajo del mercado"
        elif nota360 >= 3.0:
            return "📈 Mantener salario, plan de formación en liderazgo (FUNDAE)"
        else:
            return "📚 Plan intensivo de desarrollo en competencias básicas (FUNDAE)"

    # Crear columna de recomendación
    df["Recomendación"] = df.apply(
        lambda row: generar_recomendacion(
            row["Nota360"], 
            row["Salario Actual"], 
            row["Referencia Mercado"]
        ),
        axis=1
    )

    # Mostrar tabla con recomendaciones
    st.subheader("Resultados con recomendaciones")
    st.dataframe(df)

    # Filtrar empleados según recomendación
    subida = df[df["Recomendación"].str.contains("Subida salarial")]
    formacion = df[df["Recomendación"].str.contains("Plan")]

    st.subheader("📊 Empleados que merecen subida salarial")
    st.dataframe(subida[["Nombre","Departamento","Nota360","Salario Actual","Referencia Mercado","Recomendación"]])

    st.subheader("📚 Empleados que necesitan formación")
    st.dataframe(formacion[["Nombre","Departamento","Nota360","Recomendación"]])

    # Selección de empleado para ver detalle
    empleado = st.selectbox("Selecciona un empleado", df["Nombre"])
    info = df[df["Nombre"] == empleado].iloc[0]

    st.write(f"**Nota360:** {info['Nota360']}")
    st.write(f"**Salario Actual:** {info['Salario Actual']} €")
    st.write(f"**Referencia Mercado:** {info['Referencia Mercado']} €")
    st.write(f"**Recomendación:** {info['Recomendación']}")
