import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import linregress
import math

st.title("Análisis de PCR cuantitativa")

# Subida de archivo
uploaded_file = st.file_uploader("Sube tu archivo .xls", type=["xls", "xlsx"])
if uploaded_file:
    # Leemos el Excel ignorando las primeras 7 filas
    df = pd.read_excel(uploaded_file, skiprows=7)

    # Filtramos solo las filas de pacientes (Task UNKNOWN)
    df_patients = df[df['Task'] == 'UNKNOWN']

    # Filtramos también los estándares
    df_standards = df[df['Task'] == 'STANDARD']

    # Creamos lista de pacientes únicos
    patients = df_patients['Sample Name'].unique()

    # Selección de multiplicador de ratio
    mult_factor = st.selectbox("Multiplicador de ratio", [100, 10000], index=0)

    # Diccionario para almacenar factores de conversión manuales
    conv_factors = {}
    st.subheader("Introduce factor de conversión por paciente (opcional)")
    for p in patients:
        conv_factors[p] = st.number_input(f"Factor de conversión para paciente {p}", value=1.0, step=0.1)

    # Lista para almacenar resultados finales
    summary_data = []

    for p in patients:
        df_patient = df_patients[df_patients['Sample Name'] == p]
        # Tomamos ABL1 Quantity Mean
        abl1_row = df_patient[df_patient['Target Name'] == 'ABL1']
        if not abl1_row.empty:
            abl1_mean = abl1_row['Quantity Mean'].values[0]
        else:
            abl1_mean = np.nan

        targets = df_patient['Target Name'].unique()
        for t in targets:
            if t == 'ABL1':
                continue
            df_target = df_patient[df_patient['Target Name'] == t]
            # Revisamos si hay Quantity Mean
            if df_target['Quantity Mean'].isna().all():
                quantity_mean = "NEGATIVO"
                ratio = 0.0
                warning = ""
            else:
                quantity_mean = df_target['Quantity Mean'].values[0]
                # Revisamos si hay solo una de tres repeticiones positiva
                pos_count = df_target['Quantity'].count()
                warning = ""
                if pos_count == 1:
                    warning = "Revisar: solo 1/3 positivo"
                ratio = (quantity_mean / abl1_mean) * mult_factor * conv_factors[p]

            summary_data.append({
                "Paciente": p,
                "Target": t,
                "Quantity Mean": round(quantity_mean, 1) if quantity_mean != "NEGATIVO" else quantity_mean,
                "ABL1 Mean": round(abl1_mean, 1) if not np.isnan(abl1_mean) else "NA",
                "Ratio": round(ratio, 4) if quantity_mean != "NEGATIVO" else 0.0,
                "Warning": warning
            })

    # Convertimos a DataFrame y ordenamos por paciente
    summary_df = pd.DataFrame(summary_data)
    summary_df = summary_df.sort_values(by=['Paciente', 'Target'])

    # Interpretación según reglas
    def interpret(row):
        abl1 = row['ABL1 Mean']
        ratio = row['Ratio']
        if abl1 == "NA" or abl1 < 10000:
            return "No valorable"
        if row['Quantity Mean'] == "NEGATIVO":
            if abl1 < 32000:
                return "Al menos MR4"
            elif abl1 <= 100000:
                return "Al menos MR4.5"
            else:
                return "Al menos MR5"
        # Positivo
        if ratio > 0.1:
            return "Ausencia de MR"
        elif 0.1 >= ratio > 0.01:
            return "MR3"
        elif 0.01 >= ratio > 0.0032:
            return "MR4"
        elif 0.0032 >= ratio > 0.001:
            return "MR4.5"
        else:
            return "MR5"

    summary_df['Interpretación'] = summary_df.apply(interpret, axis=1)

    st.subheader("Tabla resumen de pacientes")
    st.dataframe(summary_df)

    st.subheader("Regresión lineal de estándares")
    reg_results = []
    for t in df_standards['Target Name'].unique():
        df_std_target = df_standards[df_standards['Target Name'] == t]
        # Eliminamos NTC
        df_std_target = df_std_target[df_std_target['Task'] != 'NTC']
        # Log de Quantity
        df_std_target = df_std_target[df_std_target['Quantity'].notna()]
        x = np.log10(df_std_target['Quantity'].values)
        y = df_std_target['Cт'].apply(lambda v: np.nan if v == "Undetermined" else v).values
        # Aviso si hay Undetermined
        if np.isnan(y).any():
            undet_idx = np.where(np.isnan(y))[0]
            for idx in undet_idx:
                qty = df_std_target['Quantity'].values[idx]
                st.warning(f"Undetermined Ct para Quantity={qty} en Target {t}")
            # Quitamos los NaN
            x = x[~np.isnan(y)]
            y = y[~np.isnan(y)]
        if len(x) > 1:
            slope, intercept, r_value, p_value, std_err = linregress(x, y)
            reg_results.append({
                "Target": t,
                "a (intercept)": round(intercept, 3),
                "b (slope)": round(slope, 3)
            })

    st.subheader("Resultados regresión lineal")
    st.dataframe(pd.DataFrame(reg_results))
