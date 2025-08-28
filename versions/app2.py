import pandas as pd
import streamlit as st

# Título de la app
st.title("Cálculo de ratios de PCR cuantitativa")

# Subida de archivo
uploaded_file = st.file_uploader("Sube tu archivo .xls", type=["xls", "xlsx"])

if uploaded_file:
    # Lectura del archivo, saltando las primeras 7 filas
    df = pd.read_excel(uploaded_file, skiprows=7)

    # Mostramos las primeras filas para verificar
    st.write("Vista previa de los datos:")
    st.dataframe(df.head())

    # Pedimos al usuario el multiplicador para el ratio
    multiplicador = st.number_input(
        "Multiplicar cada ratio por:", value=100.0, step=1.0
    )

    # Factor de conversión manual por paciente
    st.write("Opcional: introducir factores de conversión para cada paciente")
    pacientes = df['Sample Name'].unique()
    conversion_factors = {}
    for paciente in pacientes:
        factor = st.number_input(f"Factor para {paciente}", value=1.0, step=0.1)
        conversion_factors[paciente] = factor

    # Filtramos columnas necesarias
    df_needed = df[['Sample Name', 'Target Name', 'Quantity Mean', 'Cт']]

    # Creamos lista para resultados
    resultados = []

    for paciente in pacientes:
        df_paciente = df_needed[df_needed['Sample Name'] == paciente]

        # Tomamos Quantity Mean de ABL1
        abl1 = df_paciente[df_paciente['Target Name'] == 'ABL1']['Quantity Mean'].values
        if len(abl1) == 0 or pd.isna(abl1[0]):
            st.warning(f"Paciente {paciente} no tiene ABL1 o está NEGATIVO")
            continue
        abl1_value = abl1[0]

        # Analizamos los otros targets
        targets = df_paciente[df_paciente['Target Name'] != 'ABL1']['Target Name'].unique()

        for target in targets:
            df_target = df_paciente[df_paciente['Target Name'] == target]
            
            # Revisión de pocillos
            pos_count = df_target['Cт'].count()
            if pos_count == 0:
                quantity_mean = "NEGATIVO"
                ratio = 0.0
            else:
                quantity_mean = df_target['Quantity Mean'].values[0]
                ratio = (quantity_mean / abl1_value) * multiplicador * conversion_factors[paciente]

            # Aviso si solo hay un pocillo positivo de 3
            revisar = ""
            if pos_count == 1:
                revisar = "Revisar (solo 1 de 3 positivos)"

            resultados.append({
                'Paciente': paciente,
                'Target': target,
                'Quantity Mean': quantity_mean if quantity_mean != "NEGATIVO" else "NEGATIVO",
                'ABL1 Mean': round(abl1_value, 1),
                'Ratio': round(ratio, 4) if quantity_mean != "NEGATIVO" else 0.0000,
                'Aviso': revisar
            })

    # Convertimos a DataFrame y ordenamos
    df_result = pd.DataFrame(resultados)
    df_result.sort_values(by=['Paciente', 'Target'], inplace=True)

    st.write("Tabla resumen de ratios:")
    st.dataframe(df_result)
