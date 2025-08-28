# pcr_analysis_app.py

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import linregress

st.set_page_config(page_title="Análisis de PCR cuantitativa", layout="wide")
st.title("Análisis de PCR cuantitativa con ratios y factores de conversión")

uploaded_file = st.file_uploader("Sube tu archivo .xls", type=["xls", "xlsx"])
multiplier = st.selectbox("Multiplicador del ratio", [100, 10000], index=0)

if uploaded_file:
    df = pd.read_excel(uploaded_file, skiprows=7)
    df_unknown = df[df['Task'] == 'UNKNOWN'].copy()
    df_standard = df[df['Task'] == 'STANDARD'].copy()
    
    # --- Curvas estándar ---
    st.subheader("Curvas patrón y regresión lineal")
    curves = {}
    conversion_factors = {}  # Almacenaremos factor por cada target y cada Quantity
    fig, ax = plt.subplots(figsize=(8,5))
    
    for target, group in df_standard.groupby('Target Name'):
        group = group.copy()
        group['Ct'] = pd.to_numeric(group['Cт'], errors='coerce')
        group['Quantity'] = pd.to_numeric(group['Quantity'], errors='coerce')
        group = group.dropna(subset=['Quantity'])
        
        # Agrupar por Quantity para manejar duplicados
        factors_list = []
        for q_val, subgrp in group.groupby('Quantity'):
            cts = subgrp['Ct'].values
            if len(cts) > 1 and np.isnan(cts).any():
                st.warning(f"Target {target}, Quantity {q_val}: una determinación es Undetermined, se usa la otra.")
            ct_mean = np.nanmean(cts)
            factors_list.append((q_val, ct_mean))
        
        # Regresión lineal
        x_log = np.log10([f[0] for f in factors_list])
        y_ct = [f[1] for f in factors_list]
        slope, intercept, r_value, p_value, std_err = linregress(x_log, y_ct)
        curves[target] = (slope, intercept)
        ax.scatter(x_log, y_ct, label=f"{target} puntos")
        ax.plot(x_log, slope*x_log + intercept, label=f"{target} fit")
        
        # Calcular factor de conversión por cada Quantity de la curva
        conversion_factors[target] = {}
        for q_val, ct_val in factors_list:
            # x_expected = log10(Quantity) desde Ct usando la recta
            x_expected = (ct_val - intercept) / slope
            q_expected = 10**x_expected
            factor = q_val / q_expected
            conversion_factors[target][q_val] = factor
    
    ax.set_xlabel("log10(Quantity)")
    ax.set_ylabel("Ct")
    ax.legend()
    st.pyplot(fig)
    
    st.write("Rectas de regresión (y = a*x + b)")
    for target, (a,b) in curves.items():
        st.write(f"{target}: pendiente={a:.3f}, intercept={b:.3f}")
    
    # --- Tabla resumen de ratios ---
    summary_rows = []
    
    for patient, group in df_unknown.groupby('Sample Name'):
        abl1_row = group[group['Target Name'] == 'ABL1']
        if abl1_row.empty:
            st.warning(f"Paciente {patient} no tiene ABL1, se omite")
            continue
        abl1_mean = abl1_row['Quantity Mean'].mean()
        
        for target in group['Target Name'].unique():
            if target == 'ABL1':
                continue
            target_rows = group[group['Target Name'] == target]
            
            # Revisar replicados
            if target_rows['Quantity'].notna().sum() < len(target_rows):
                warning_replicates = "Revisar replicados"
            else:
                warning_replicates = ""
            
            if target_rows['Quantity Mean'].isna().all():
                quantity_mean = 0.0
                ratio = 0.0
                interpretation = "NEGATIVO"
                factor_used = np.nan
            else:
                quantity_mean = target_rows['Quantity Mean'].mean()
                ratio = (quantity_mean / abl1_mean) * multiplier
                
                # Aplicar factor de conversión más cercano
                if target in conversion_factors and ratio > 0:
                    q_log = np.log10(quantity_mean)
                    closest_q = min(conversion_factors[target].keys(), key=lambda q: abs(np.log10(q) - q_log))
                    factor_used = conversion_factors[target][closest_q]
                    ratio *= factor_used
                else:
                    factor_used = np.nan
                
                ratio = round(ratio, 4)
                
                # Interpretación
                if abl1_mean < 10000:
                    interpretation = "No valorable"
                elif ratio == 0.0:
                    if 10000 <= abl1_mean < 32000:
                        interpretation = "Al menos MR4"
                    elif 32000 <= abl1_mean <= 100000:
                        interpretation = "Al menos MR4.5"
                    else:
                        interpretation = "Al menos MR5"
                else:
                    if ratio > 0.1:
                        interpretation = "Ausencia de MR"
                    elif 0.1 >= ratio > 0.01:
                        interpretation = "MR3"
                    elif 0.01 >= ratio > 0.0032:
                        interpretation = "MR4"
                    elif 0.0032 >= ratio > 0.001:
                        interpretation = "MR4.5"
                    else:
                        interpretation = "MR5"
            
            summary_rows.append({
                "Paciente": patient,
                "Target": target,
                "Quantity Mean": round(quantity_mean, 1),
                "ABL1 Mean": round(abl1_mean, 1),
                "Ratio": ratio,
                "Factor de conversión": round(factor_used, 3) if not np.isnan(factor_used) else "",
                "Advertencia": warning_replicates,
                "Interpretación": interpretation
            })
    
    summary_df = pd.DataFrame(summary_rows)
    summary_df = summary_df.sort_values(by='Ratio')
    
    st.subheader("Tabla resumen de ratios con factor de conversión")
    st.dataframe(summary_df)
