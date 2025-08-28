# app.py
import streamlit as st
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import math
import os

st.set_page_config(page_title="Análisis PCR cuantitativa", layout="wide")

st.title("Análisis de Ratios de PCR cuantitativa")

# Cargar archivo
uploaded_file = st.file_uploader("Sube tu archivo .xls", type=["xls", "xlsx"])
if uploaded_file:
    # Leer Excel ignorando primeras 7 filas
    df = pd.read_excel(uploaded_file, skiprows=7)
    
    # Filtrar solo pacientes y standards
    df_patients = df[df['Task'] == 'UNKNOWN'].copy()
    df_standards = df[df['Task'] == 'STANDARD'].copy()
    
    # Filtrar NTC en pacientes de forma segura
    df_patients = df_patients[~df_patients['Sample Name'].fillna('').str.upper().eq('NTC')]
    
    # Opciones multiplicador
    multiplicador = st.selectbox("Multiplicador del ratio", [100, 10000])
    
    # Preparar tabla resumen
    resumen = []
    
    for paciente in df_patients['Sample Name'].unique():
        df_p = df_patients[df_patients['Sample Name'] == paciente]
        
        # ABL1 del paciente
        abl1_row = df_p[df_p['Target Name'] == 'ABL1']
        if abl1_row.empty or abl1_row['Quantity Mean'].isna().all():
            abl1_mean = np.nan
        else:
            abl1_mean = abl1_row['Quantity Mean'].values[0]
        
        # Factor de conversión manual
        factor_conv = st.number_input(f"Factor de conversión paciente {paciente}", value=1.0, step=0.01)
        
        for target in df_p['Target Name'].unique():
            if target == 'ABL1':
                continue
            df_t = df_p[df_p['Target Name'] == target]
            
            # Comprobar cuántas positivas
            positive_count = df_t['Quantity'].notna().sum()
            revisable = positive_count == 1
            
            # Quantity Mean
            quantity_mean = df_t['Quantity Mean'].values[0] if not df_t['Quantity Mean'].isna().all() else "NEGATIVO"
            
            # Calcular ratio
            if quantity_mean == "NEGATIVO" or pd.isna(abl1_mean):
                ratio = 0
            else:
                ratio = (quantity_mean / abl1_mean) * multiplicador * factor_conv
            
            # Interpretación
            if pd.isna(abl1_mean) or abl1_mean < 10000:
                interpretacion = "No valorable"
            elif quantity_mean == "NEGATIVO":
                if abl1_mean < 32000:
                    mr = 4
                elif abl1_mean < 100000:
                    mr = 4.5
                else:
                    mr = 5
                interpretacion = f"Al menos MR{mr}"
            else:
                if ratio > 0.1:
                    interpretacion = "Ausencia de MR"
                elif ratio > 0.01:
                    interpretacion = "MR3"
                elif ratio > 0.0032:
                    interpretacion = "MR4"
                elif ratio > 0.001:
                    interpretacion = "MR4.5"
                else:
                    interpretacion = "MR5"
            
            resumen.append({
                "Paciente": paciente,
                "Target": target,
                "Quantity Mean": quantity_mean if isinstance(quantity_mean, str) else round(quantity_mean,1),
                "ABL1 Mean": round(abl1_mean,1) if not pd.isna(abl1_mean) else "NA",
                "Ratio": round(ratio,4),
                "Revisar": "Sí" if revisable else "No",
                "Interpretación": interpretacion
            })
    
    df_resumen = pd.DataFrame(resumen)
    df_resumen = df_resumen.sort_values(by='Ratio')
    
    st.subheader("Tabla resumen de ratios")
    st.dataframe(df_resumen)
    
    # Calcular rectas de regresión por Target
    st.subheader("Rectas de regresión lineal por Target (Task=STANDARD)")
    rectas = []
    for target in df_standards['Target Name'].unique():
        df_std = df_standards[df_standards['Target Name'] == target]
        
        # Filtrar NTC en standards de forma segura
        df_std = df_std[~df_std['Sample Name'].fillna('').str.upper().eq('NTC')]
        
        x_list, y_list = [], []
        avisos = []
        for qty in df_std['Quantity'].unique():
            df_qty = df_std[df_std['Quantity'] == qty]
            cts = df_qty['Cт']
            
            # Manejar Undetermined
            ct_vals = []
            for idx, ct in enumerate(cts):
                if isinstance(ct, str) and ct.upper() == "UNDETERMINED":
                    avisos.append(f"{target} Quantity {qty} tiene un Cт undetermined en fila {df_qty.index[idx]}")
                else:
                    ct_vals.append(float(ct))
            if ct_vals:
                x_list.append(math.log10(qty))
                y_list.append(np.mean(ct_vals))
        
        if len(x_list) > 1:
            X = np.array(x_list).reshape(-1,1)
            y = np.array(y_list)
            model = LinearRegression()
            model.fit(X, y)
            b = round(model.coef_[0], 3)
            a = round(model.intercept_, 3)
            rectas.append({"Target": target, "b": b, "a": a, "Avisos": "; ".join(avisos)})
    
    df_rectas = pd.DataFrame(rectas)
    st.dataframe(df_rectas)
