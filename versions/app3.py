# pcr_analysis_app.py
import streamlit as st
import pandas as pd
import numpy as np
from math import log10
from sklearn.linear_model import LinearRegression

st.title("Análisis de PCR cuantitativa")

# Cargar archivo
uploaded_file = st.file_uploader("Sube tu archivo .xls", type=["xls", "xlsx"])
multiplicador = st.number_input("Multiplicador de ratios (ej. 100, 10000)", value=100)
factor_conversion = st.number_input("Factor de conversión para ratios", value=1.0, format="%.4f")

if uploaded_file:
    # Leer archivo y eliminar primeras 7 filas
    df = pd.read_excel(uploaded_file, skiprows=7)
    
    # Filtrar solo los pacientes reales
    pacientes = df[df['Task'] == 'UNKNOWN'].copy()
    abl1_df = pacientes[pacientes['Target Name'] == 'ABL1']
    
    # Preparar lista para resultados
    resultados = []

    for paciente in pacientes['Sample Name'].unique():
        sub_df = pacientes[pacientes['Sample Name'] == paciente]
        abl1_quantity = sub_df[sub_df['Target Name'] == 'ABL1']['Quantity Mean'].values
        if len(abl1_quantity) == 0:
            st.warning(f"Paciente {paciente} no tiene ABL1, se saltará.")
            continue
        abl1_mean = np.mean(abl1_quantity)

        # Analizar cada target que no sea ABL1
        targets = sub_df[sub_df['Target Name'] != 'ABL1']['Target Name'].unique()
        for target in targets:
            target_df = sub_df[sub_df['Target Name'] == target]
            
            # Revisar cantidad de determinaciones
            positive_count = target_df['Quantity'].notna().sum()
            if positive_count < len(target_df):
                warning_text = "Revisar: sólo una casilla positiva de 3" if positive_count == 1 else ""
            else:
                warning_text = ""
            
            quantity_mean = target_df['Quantity Mean'].mean() if positive_count > 0 else np.nan
            ratio = (quantity_mean / abl1_mean) if positive_count > 0 else 0
            
            resultados.append({
                'Paciente': paciente,
                'Target': target,
                'Quantity Mean': round(quantity_mean, 1) if not np.isnan(quantity_mean) else "NEGATIVO",
                'ABL1 Mean': round(abl1_mean, 1),
                'Ratio': round(ratio * multiplicador * factor_conversion, 4) if positive_count > 0 else 0.0000,
                'Advertencia': warning_text
            })

    # Crear tabla resumen
    resumen_df = pd.DataFrame(resultados)
    resumen_df.sort_values(by=['Paciente', 'Target'], inplace=True)
    st.subheader("Tabla resumen de ratios")
    st.dataframe(resumen_df)

    # Análisis de rectas de regresión
    st.subheader("Rectas de regresión lineal (Task STANDARD)")
    standar_df = df[df['Task'] == 'STANDARD']
    regression_results = []

    for target in standar_df['Target Name'].unique():
        target_std = standar_df[standar_df['Target Name'] == target]
        x = []
        y = []
        for q in target_std['Quantity'].unique():
            q_rows = target_std[target_std['Quantity'] == q]
            ct_vals = []
            for ct in q_rows['Cт']:
                if ct != 'Undetermined':
                    ct_vals.append(ct)
                else:
                    st.warning(f"Para Target {target}, Quantity {q}, Cт Undetermined en una determinación.")
            if ct_vals:
                x.append(log10(q))
                y.append(np.mean(ct_vals))
        if len(x) >= 2:
            model = LinearRegression().fit(np.array(x).reshape(-1,1), y)
            regression_results.append({
                'Target': target,
                'Pendiente (b)': round(model.coef_[0], 4),
                'Intercepto (a)': round(model.intercept_, 4)
            })

    reg_df = pd.DataFrame(regression_results)
    st.dataframe(reg_df)
