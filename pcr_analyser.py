# pcr_analyser.py
import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
from io import BytesIO

st.set_page_config(page_title="PCR Analyzer", layout="wide")
st.title("PCR Analyzer")

uploaded_file = st.file_uploader("Sube tu archivo .xls", type=["xls","xlsx"])
multiplicador = st.selectbox("Multiplicar ratio por:", [100, 10000])

if uploaded_file:
    df = pd.read_excel(uploaded_file, skiprows=7)
    
    # Pacientes reales
    df_patients = df[df["Task"]=="UNKNOWN"].copy()
    df_patients["Quantity Mean"] = pd.to_numeric(df_patients["Quantity Mean"], errors='coerce')
    
    # Curvas estándar
    df_standard = df[df["Task"]=="STANDARD"].copy()
    df_standard["Quantity"] = pd.to_numeric(df_standard["Quantity"], errors='coerce')
    df_standard["Cт"] = pd.to_numeric(df_standard["Cт"], errors='coerce')
    
    # Calcular rectas de regresión y factores de conversión por par
    regression_dict = {}
    pair_factors_dict = {}  # Target -> lista de dicts {Quantity, Factor}
    st.subheader("Rectas de regresión")
    
    for target in df_standard["Target Name"].unique():
        t_df = df_standard[df_standard["Target Name"]==target]
        grouped = t_df.groupby("Quantity")
        x_vals, y_vals = [], []
        pair_factors = []
        
        for qty, group in grouped:
            ct_vals = group["Cт"].dropna().values
            if len(ct_vals) == 0:
                st.warning(f"{target}, Quantity {qty}: Ningún Ct disponible para la pareja")
                continue
            elif len(ct_vals) == 1:
                st.warning(f"{target}, Quantity {qty}: Sólo un Ct disponible, otro 'Undetermined'")
                x_vals.append(np.log10(qty))
                y_vals.append(ct_vals[0])
                # provisional factor
                pair_factors.append({"Quantity": qty, "Ct_pair": ct_vals})
            else:
                x_vals.append(np.log10(qty))
                y_vals.append(ct_vals.mean())
                pair_factors.append({"Quantity": qty, "Ct_pair": ct_vals})
        
        if len(x_vals) > 1:
            a, b = np.polyfit(x_vals, y_vals, 1)
            regression_dict[target] = {"a": a, "b": b, "x_vals": x_vals, "y_vals": y_vals}
            
            # Calcular factor de conversión real por par usando la recta
            for pf in pair_factors:
                ct_pair = pf["Ct_pair"]
                expected_qties = [10**((ct - b)/a) for ct in ct_pair]
                pf["Factor"] = pf["Quantity"] / np.mean(expected_qties)
                pf.pop("Ct_pair")
            pair_factors_dict[target] = pair_factors
            st.write(f"{target}: Ct = {a:.3f}*log10(Quantity) + {b:.3f}")
    
# Tabla resumen con ratios y factor de conversión
    summary_list = []
    for patient in df_patients["Sample Name"].unique():
        patient_df = df_patients[df_patients["Sample Name"]==patient]
        abl1_mean = patient_df[patient_df["Target Name"]=="ABL1"]["Quantity Mean"].mean()
        targets = [t for t in patient_df["Target Name"].unique() if t!="ABL1"]
        
        for target in targets:
            target_df = patient_df[patient_df["Target Name"]==target]
            quantity_mean = target_df["Quantity Mean"].mean()
            n_positive = target_df["Quantity"].notna().sum()
            
            if n_positive == 1:
                aviso = "Sólo 1/3 positivo"
                extra = "Repetir"
            elif n_positive == 2:
                aviso = "Sólo 2/3 positivo"
                extra = ""
            else:
                aviso = ""
                extra = ""
            
            ratio = 0.0
            if quantity_mean>0 and abl1_mean>0:
                ratio = (quantity_mean / abl1_mean) * multiplicador
            
            # Aplicar factor de conversión
            fc = 1.0
            if ratio>0 and target in pair_factors_dict:
                pf_list = pair_factors_dict[target]
                log_q_patient = np.log10(quantity_mean)
                diffs = [abs(np.log10(pf["Quantity"]) - log_q_patient) for pf in pf_list]
                idx = np.argmin(diffs)
                fc = pf_list[idx]["Factor"]
                ratio *= fc
            
            # Interpretación
            if abl1_mean<10000:
                interpretacion = "No valorable"
            elif ratio==0:
                if abl1_mean<32000:
                    interpretacion="Al menos MR4"
                elif abl1_mean<100000:
                    interpretacion="Al menos MR4.5"
                else:
                    interpretacion="Al menos MR5"
            else:
                if ratio>0.1:
                    interpretacion="Ausencia de MR"
                elif 0.01<ratio<=0.1:
                    interpretacion="MR3"
                elif 0.0032<ratio<=0.01:
                    interpretacion="MR4"
                elif 0.001<ratio<=0.0032:
                    interpretacion="MR4.5"
                else:
                    interpretacion="MR5"
            if extra:
                interpretacion += f" ({extra})"
            
            summary_list.append({
                "Paciente": patient,
                "Target": target,
                "Quantity Mean": round(quantity_mean,1),
                "ABL1 Mean": round(abl1_mean,1),
                "Ratio": round(ratio,4),
                "Factor de Conversión": round(fc,3),
                "Aviso": aviso,
                "Interpretación": interpretacion
            })
    
    summary_df = pd.DataFrame(summary_list).sort_values("Ratio")
    st.subheader("Tabla Resumen")
    st.dataframe(summary_df)
    
    # Descargar Excel
    towrite = BytesIO()
    summary_df.to_excel(towrite, index=False, engine='openpyxl')
    towrite.seek(0)
    st.download_button(label="Descargar tabla resumen", data=towrite, file_name="tabla_resumen_final.xlsx", mime="application/vnd.ms-excel")

    # Graficar curvas estándar
    fig, ax = plt.subplots(figsize=(8,6))
    for target, reg in regression_dict.items():
        x_plot = np.linspace(min(reg["x_vals"]), max(reg["x_vals"]), 100)
        y_plot = reg["a"]*x_plot + reg["b"]
        ax.plot(x_plot, y_plot, label=f"{target} (fit)")
        ax.scatter(reg["x_vals"], reg["y_vals"], s=50)
    ax.set_xlabel("log10(Quantity)")
    ax.set_ylabel("Ct")
    ax.set_title("Curvas patrón de cada Target")
    ax.legend()
    st.pyplot(fig)
    
    
