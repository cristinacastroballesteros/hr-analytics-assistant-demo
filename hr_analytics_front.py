import streamlit as st
import pandas as pd

st.title("HR Analytics Assistant - Multi Excel")

# Subir archivos
empleados_file = st.file_uploader("Sube el Excel de empleados", type=["xlsx"])
rangos_file = st.file_uploader("Sube el Excel de rangos", type=["xlsx"])

if empleados_file and rangos_file:
    # Leer los datos
    empleados = pd.read_excel(empleados_file, sheet_name="Empleados")
    rangos = pd.read_excel(rangos_file, sheet_name="Rangos")

    # Unir empleados con rangos según Departamento, Posición, Nivel y Región
    df = empleados.merge(
        rangos,
        on=["Departamento", "Posición", "Nivel", "Región"],
        how="left"
    )

    # Función de recomendación
    def generar_recomendacion(row):
        # Condición subida salarial: buen desempeño y salario por debajo del rango
        if row["Nota360"] >= 75 and row["SalarioActual"] < row["Rango_Salarial_Mín"]:
            return "✅ Subida salarial recomendada (+{}%)".format(int(row["Política_Subida_Mín"]*100))
        elif row["Nota360"] >= 70:
            return "📈 Mantener salario, plan de formación en liderazgo (FUNDAE)"
        else:
            return "📚 Plan intensivo de desarrollo en competencias básicas (FUNDAE)"

    # Crear columna de recomendación
    df["Recomendación"] = df.apply(generar_recomendacion, axis=1)

    # Filtros interactivos
    st.sidebar.header("Filtros")
    depto = st.sidebar.selectbox("Departamento", ["Todos"] + sorted(df["Departamento"].unique()))
    region = st.sidebar.selectbox("Región", ["Todos"] + sorted(df["Región"].unique()))
    nivel = st.sidebar.selectbox("Nivel", ["Todos"] + sorted(df["Nivel"].unique()))

    filtrado = df.copy()
    if depto != "Todos":
        filtrado = filtrado[filtrado["Departamento"] == depto]
    if region != "Todos":
        filtrado = filtrado[filtrado["Región"] == region]
    if nivel != "Todos":
        filtrado = filtrado[filtrado["Nivel"] == nivel]

    # Mostrar resultados
    st.subheader("Resultados con recomendaciones")
    st.dataframe(filtrado[[
        "EmployeeID","Departamento","Posición","Nivel","Región",
        "Antigüedad","SalarioActual","Nota360","Recomendación"
    ]])

    # Selección de empleado para ver detalle
    empleado = st.selectbox("Selecciona un empleado", filtrado["EmployeeID"])
    info = filtrado[filtrado["EmployeeID"] == empleado].iloc[0]

    st.write(f"**Departamento:** {info['Departamento']}")
    st.write(f"**Posición:** {info['Posición']}")
    st.write(f"**Nivel:** {info['Nivel']}")
    st.write(f"**Región:** {info['Región']}")
    st.write(f"**Antigüedad:** {info['Antigüedad']} años")
    st.write(f"**Salario Actual:** {info['SalarioActual']} €")
    st.write(f"**Rango Salarial:** {info['Rango_Salarial_Mín']} € - {info['Rango_Salarial_Máx']} €")
    st.write(f"**Nota360:** {info['Nota360']}")
    st.write(f"**Recomendación:** {info['Recomendación']}")
