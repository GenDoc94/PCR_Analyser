# pcr_ratio_streamlit.py
import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
from io import BytesIO

st.set_page_config(page_title="PCR Ratio Analyzer", layout="wide")

st.title("PCR Quantitative Ratio Analyzer")

# Upload Excel file
uploaded_file = st.file_uploader("Sube tu archivo .xls", type=["xls","xlsx"])
multiplicador = st.selectbox("Multiplicar ratio por:", [100, 10000])

if uploaded_file:
    # Cargar Excel ignorando primeras 7 filas
    df = pd.read_excel(uploaded_file, skiprows=7)
    
    # Filtrar pacientes reales
    df_patients = df[df["Task"] == "UNKNOWN"].copy()
    
    # Eliminar posibles NaN en Quantity Mean y ABL1
    df_patients["Quantity Mean"] = pd.to_numeric(df_patients["Quantity Mean"], errors='coerce')
    
    # Preparar tabla resumen
    summary_list = []
    
    # Obtener pacientes únicos
    patients = df_patients["Sample Name"].unique()
    
    for patient in patients:
        patient_df = df_patients[df_patients["Sample Name"] == patient]
        abl1_mean = patient_df[patient_df["Target Name"]=="ABL1"]["Quantity Mean"].mean()
        
        # Todos los Target excepto ABL1
        targets = patient_df[patient_df["Target Name"]!="ABL1"]["Target Name"].unique()
        
        for target in targets:
            target_df = patient_df[patient_df["Target Name"]==target]
            quantity_mean = target_df["Quantity Mean"].mean()
            
            # Comprobar cuántos positivos
            n_positive = target_df["Quantity"].notna().sum()
            if n_positive == 1:
                aviso = "Sólo 1/3 positivo"
                interpretacion_extra = "Repetir"
            elif n_positive == 2:
                aviso = "Sólo 2/3 positivo"
                interpretacion_extra = ""
            else:
                aviso = ""
                interpretacion_extra = ""
            
            # Calcular ratio
            ratio = 0.0
            if quantity_mean > 0 and abl1_mean > 0:
                ratio = (quantity_mean / abl1_mean) * multiplicador
            
            # Interpretación
            if abl1_mean < 10000:
                interpretacion = "No valorable"
            elif ratio == 0.0:
                if abl1_mean < 32000:
                    interpretacion = "Al menos MR4"
                elif abl1_mean < 100000:
                    interpretacion = "Al menos MR4.5"
                else:
                    interpretacion = "Al menos MR5"
            else:
                if ratio > 0.1:
                    interpretacion = "Ausencia de MR"
                elif 0.01 < ratio <= 0.1:
                    interpretacion = "MR3"
                elif 0.0032 < ratio <= 0.01:
                    interpretacion = "MR4"
                elif 0.001 < ratio <= 0.0032:
                    interpretacion = "MR4.5"
                else:
                    interpretacion = "MR5"
            if interpretacion_extra:
                interpretacion += f" ({interpretacion_extra})"
            
            summary_list.append({
                "Paciente": patient,
                "Target": target,
                "Quantity Mean": round(quantity_mean,1),
                "ABL1 Mean": round(abl1_mean,1),
                "Ratio": round(ratio,4),
                "Aviso": aviso,
                "Interpretación": interpretacion
            })
    
    summary_df = pd.DataFrame(summary_list)
    summary_df = summary_df.sort_values(by="Ratio")
    
    st.subheader("Tabla Resumen de Ratios")
    st.dataframe(summary_df)
    
    # Descargar Excel
    towrite = BytesIO()
    summary_df.to_excel(towrite, index=False, engine='openpyxl')
    towrite.seek(0)
    st.download_button(label="Descargar tabla resumen", data=towrite, file_name="tabla_resumen.xlsx", mime="application/vnd.ms-excel")
    
    # Curvas patrón
    st.subheader("Curvas patrón y factores de conversión")
    df_standard = df[df["Task"]=="STANDARD"].copy()
    df_standard["Quantity"] = pd.to_numeric(df_standard["Quantity"], errors='coerce')
    df_standard["Cт"] = pd.to_numeric(df_standard["Cт"], errors='coerce')
    
    # Generar gráfico
    targets_standard = df_standard["Target Name"].unique()
    
    fig, ax = plt.subplots(figsize=(8,6))
    for target in targets_standard:
        t_df = df_standard[df_standard["Target Name"]==target]
        
        # Agrupar por Quantity para pares
        t_groups = t_df.groupby("Quantity")
        x_vals, y_vals = [], []
        for qty, group in t_groups:
            ct_values = group["Cт"].dropna()
            if len(ct_values) == 0:
                st.warning(f"Target {target}, Quantity {qty}: Ningún Cт disponible para la pareja")
            elif len(ct_values) == 1:
                st.warning(f"Target {target}, Quantity {qty}: Sólo un Cт disponible, otro 'Undetermined'")
                x_vals.append(np.log10(qty))
                y_vals.append(ct_values.iloc[0])
            else:
                # Tomar la media de los dos Ct
                x_vals.append(np.log10(qty))
                y_vals.append(ct_values.mean())
        
        if len(x_vals) > 1:
            # Regresión lineal
            coeffs = np.polyfit(x_vals, y_vals, 1)
            a,b = coeffs
            st.write(f"Target {target}: Ct = {a:.3f}*log10(Quantity) + {b:.3f}")
            
            # Graficar
            x_plot = np.linspace(min(x_vals), max(x_vals), 100)
            y_plot = a*x_plot + b
            ax.plot(x_plot, y_plot, label=f"{target} (fit)")
            ax.scatter(x_vals, y_vals, s=50)
    
    ax.set_xlabel("log10(Quantity)")
    ax.set_ylabel("Cт")
    ax.set_title("Curvas patrón de cada Target")
    ax.legend()
    st.pyplot(fig)
