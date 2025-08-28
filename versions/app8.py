import pandas as pd
import numpy as np
import streamlit as st
from scipy.stats import linregress
import matplotlib.pyplot as plt

st.title("Análisis de PCR cuantitativa")

# Carga de archivo
uploaded_file = st.file_uploader("Sube tu archivo .xls", type="xls")
if uploaded_file:
    df = pd.read_excel(uploaded_file, skiprows=7)
    
    # Filtramos pacientes y estándares
    df_patients = df[df['Task'] == 'UNKNOWN']
    df_std = df[df['Task'] == 'STANDARD']
    
    # Convertir Quantity y Ct a numérico, NaN en los que no se pueda
    df_std['Quantity'] = pd.to_numeric(df_std['Quantity'], errors='coerce')
    df_std['Cт'] = pd.to_numeric(df_std['Cт'], errors='coerce')
    
    # Eliminamos filas no numéricas antes de análisis
    df_std_clean = df_std.dropna(subset=['Quantity', 'Cт'])
    
    # Selección de multiplicador de ratio
    multiplicador = st.selectbox("Multiplicador del ratio", [100, 10000])
    
    # Calcular rectas estándar por Target
    rectas = {}
    conversion_factors = {}
    avisos_ct = []
    
    for target in df_std_clean['Target Name'].unique():
        df_t = df_std_clean[df_std_clean['Target Name'] == target].copy()
        # Log de Quantity
        df_t['logQ'] = np.log10(df_t['Quantity'])
        # Agrupamos por Quantity si hay duplicados
        x = df_t['logQ'].values
        y = df_t['Cт'].values
        slope, intercept, r_value, p_value, std_err = linregress(x, y)
        rectas[target] = {'slope': slope, 'intercept': intercept}
        
        # Factor de conversión: por cada Quantity
        factors = []
        for q, ct in zip(df_t['Quantity'], df_t['Cт']):
            ct_pred = slope * np.log10(q) + intercept
            factor = q / (10 ** ((ct - intercept)/slope))
            factors.append(factor)
        conversion_factors[target] = factors
    
    # Tabla resumen
    summary = []
    for sample in df_patients['Sample Name'].unique():
        df_s = df_patients[df_patients['Sample Name'] == sample]
        abl1_mean = df_s[df_s['Target Name'] == 'ABL1']['Quantity Mean'].mean()
        targets = df_s['Target Name'].unique()
        
        for target in targets:
            if target == 'ABL1':
                continue
            df_target = df_s[df_s['Target Name'] == target]
            q_mean = df_target['Quantity Mean'].mean()
            
            # Control triplicados
            n_pos = df_target['Quantity'].gt(0).sum()
            aviso = ""
            if n_pos == 1:
                aviso = "Sólo 1/3 positivo"
            elif n_pos == 2:
                aviso = "2/3 positivo"
            
            ratio = (q_mean / abl1_mean) * multiplicador if abl1_mean > 0 else 0
            ratio = round(ratio, 4)
            
            # Factor de conversión: tomamos el más cercano log10(q_mean)
            if ratio > 0:
                factors = np.array(conversion_factors[target])
                logq = np.log10(q_mean)
                idx = np.argmin(np.abs(np.log10(factors) - logq))
                factor_conv = factors[idx]
                ratio_corr = ratio * factor_conv
            else:
                factor_conv = np.nan
                ratio_corr = 0.0
            
            # Interpretación
            if abl1_mean < 10000:
                interpretation = "No valorable"
            elif ratio_corr == 0:
                if abl1_mean < 32000:
                    interpretation = "Al menos MR4"
                elif abl1_mean < 100000:
                    interpretation = "Al menos MR4.5"
                else:
                    interpretation = "Al menos MR5"
            else:
                if ratio_corr > 0.1:
                    interpretation = "Ausencia de MR"
                elif 0.01 < ratio_corr <= 0.1:
                    interpretation = "MR3"
                elif 0.0032 < ratio_corr <= 0.01:
                    interpretation = "MR4"
                elif 0.001 < ratio_corr <= 0.0032:
                    interpretation = "MR4.5"
                else:
                    interpretation = "MR5"
            
            summary.append({
                'Paciente': sample,
                'Target': target,
                'Quantity Mean': round(q_mean,1),
                'ABL1 Mean': round(abl1_mean,1),
                'Ratio': round(ratio_corr,4),
                'Factor Conv': round(factor_conv,4),
                'Aviso': aviso,
                'Interpretación': interpretation
            })
    
    df_summary = pd.DataFrame(summary)
    df_summary = df_summary.sort_values(by='Ratio')
    
    st.subheader("Tabla resumen")
    st.dataframe(df_summary)
    
    # Gráficos de rectas estándar
    st.subheader("Curvas patrón")
    fig, ax = plt.subplots()
    for target, params in rectas.items():
        slope = params['slope']
        intercept = params['intercept']
        x_vals = np.linspace(0, max(df_std_clean['Quantity']), 100)
        y_vals = slope * np.log10(x_vals + 1e-9) + intercept  # evitar log(0)
        ax.plot(x_vals, y_vals, label=f'{target} recta')
        
        # Filtrar solo valores numéricos antes de scatter
        df_plot = df_std_clean[df_std_clean['Target Name'] == target]
        ax.scatter(df_plot['Quantity'], df_plot['Cт'], marker='o')
        
    ax.set_xlabel('Quantity')
    ax.set_ylabel('Ct')
    ax.legend()
    st.pyplot(fig)
