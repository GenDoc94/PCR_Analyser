import streamlit as st
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

st.title("Análisis de PCR cuantitativa")

# 1. Cargar archivo .xls
uploaded_file = st.file_uploader("Sube tu archivo .xls", type=["xls","xlsx"])

if uploaded_file:
    # Saltar las primeras 7 filas y leer Excel
    df = pd.read_excel(uploaded_file, skiprows=7)

    # Filtrar solo Task UNKNOWN para pacientes
    df_patients = df[df['Task'] == 'UNKNOWN'].copy()
    
    # Filtrar solo Task STANDARD para regresión
    df_standard = df[df['Task'] == 'STANDARD'].copy()
    
    # Multiplicador
    multiplicador = st.selectbox("Multiplicador del ratio", [100, 10000], index=0)

    # Factor de conversión por paciente
    pacientes = df_patients['Sample Name'].unique()
    conversion_factors = {}
    st.subheader("Factores de conversión por paciente")
    for p in pacientes:
        conversion_factors[p] = st.number_input(f"Factor para {p}", min_value=0.0, value=1.0, step=0.1)

    # Tabla resumen
    resumen = []

    for paciente in pacientes:
        df_p = df_patients[df_patients['Sample Name'] == paciente]
        # Obtener ABL1 Mean
        abl1_row = df_p[df_p['Target Name'] == 'ABL1']
        if abl1_row.empty or pd.isna(abl1_row['Quantity Mean'].values[0]):
            abl1_mean = None
        else:
            abl1_mean = abl1_row['Quantity Mean'].values[0]
        # Procesar otros targets
        targets = df_p['Target Name'].unique()
        for target in targets:
            if target == 'ABL1':
                continue
            df_t = df_p[df_p['Target Name'] == target]
            # Comprobar replicados
            n_replicas = df_t.shape[0]
            quantity_values = df_t['Quantity Mean'].values
            quantity_values_ct = df_t['Cт'].values
            # Revisar si hay Undetermined
            if all(str(ct) == 'Undetermined' or pd.isna(ct) for ct in quantity_values_ct):
                ratio = 0.0
                status = "NEGATIVO"
            else:
                # Comprobar si solo 1 positivo de 3
                n_positivos = sum([not (str(ct) == 'Undetermined' or pd.isna(ct)) for ct in quantity_values_ct])
                status = "OK"
                if n_positivos < n_replicas:
                    status = "Revisar"
                # Tomar la media de los positivos
                valid_quantities = [q for q, ct in zip(quantity_values, quantity_values_ct) if not (str(ct)=='Undetermined' or pd.isna(ct))]
                quantity_mean = np.mean(valid_quantities)
                ratio = (quantity_mean / abl1_mean) * multiplicador * conversion_factors[paciente]

            resumen.append({
                'Paciente': paciente,
                'Target': target,
                'Quantity Mean': round(np.mean(quantity_values) if len(quantity_values)>0 else 0,1),
                'ABL1 Mean': round(abl1_mean if abl1_mean else 0,1),
                'Ratio': round(ratio,4),
                'Estado': status
            })

    resumen_df = pd.DataFrame(resumen)
    resumen_df = resumen_df.sort_values(by='Paciente')
    
    # Interpretación
    def interpretar(row):
        ratio = row['Ratio']
        abl1 = row['ABL1 Mean']
        if row['Estado'] == 'NEGATIVO':
            if abl1 > 100000:
                mr = "Al menos MR5"
            elif abl1 >= 32000:
                mr = "Al menos MR4.5"
            elif abl1 >= 10000:
                mr = "Al menos MR4"
            else:
                mr = "Al menos MR?"
        else:
            if ratio > 0.1:
                mr = "Ausencia de MR"
            elif ratio >= 0.01:
                mr = "MR3"
            elif ratio >= 0.0032:
                mr = "MR4"
            elif ratio >= 0.001:
                mr = "MR4.5"
            else:
                mr = "MR5"
        return mr

    resumen_df['Interpretación'] = resumen_df.apply(interpretar, axis=1)

    st.subheader("Tabla resumen")
    st.dataframe(resumen_df)

    # ---- REGRESIÓN LINEAL para STANDARD ----
    st.subheader("Regresión lineal (STANDARD)")
    targets_standard = df_standard['Target Name'].unique()
    regresiones = []
    for target in targets_standard:
        df_t = df_standard[df_standard['Target Name']==target]
        # Ignorar NTC
        df_t = df_t[df_t['Task'] != 'NTC']
        # Preparar x y log(Quantity)
        x = []
        y = []
        for _, row in df_t.iterrows():
            if str(row['Cт']) == 'Undetermined' or pd.isna(row['Cт']):
                st.warning(f"Para Target {target}, Quantity {row['Quantity']} tiene Ct Undetermined, usando la otra determinación.")
                continue
            x.append(np.log10(row['Quantity']))
            y.append(row['Cт'])
        if len(x) >= 2:
            model = LinearRegression()
            x_arr = np.array(x).reshape(-1,1)
            y_arr = np.array(y)
            model.fit(x_arr, y_arr)
            a = model.intercept_
            b = model.coef_[0]
            regresiones.append({'Target': target, 'a': round(a,3), 'b': round(b,3)})
    
    regresion_df = pd.DataFrame(regresiones)
    st.dataframe(regresion_df)
