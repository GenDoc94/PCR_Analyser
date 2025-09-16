# pcr_analyser.py
import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
from io import BytesIO

st.set_page_config(page_title="PCR Analyzer", layout="wide")

# Título centrado
st.markdown(
    "<h1 style='text-align: center;'>PCR Analyzer</h1>",
    unsafe_allow_html=True
)

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

    # Calcular rectas de regresión y factores de conversión
    regression_dict = {}
    pair_factors_dict = {}

    with st.expander("Rectas de regresión"):
        for target in df_standard["Target Name"].unique():
            t_df = df_standard[df_standard["Target Name"]==target]
            grouped = t_df.groupby("Quantity")
            x_vals, y_vals = [], []
            pair_factors = []

            for qty, group in grouped:
                ct_vals = group["Cт"].values
                # Detectar Undetermined
                n_undetermined = np.sum(pd.isna(ct_vals))
                if n_undetermined > 0:
                    if n_undetermined == 1:
                        st.warning(f"{target}, Quantity {qty}: 1 Ct de 2 está 'Undetermined'")
                    else:
                        st.warning(f"{target}, Quantity {qty}: Ambos Ct están 'Undetermined'")
                    ct_vals = [ct for ct in ct_vals if pd.notna(ct)]  # ignorar NaN

                if len(ct_vals) == 0:
                    continue
                elif len(ct_vals) == 1:
                    x_vals.append(np.log10(qty))
                    y_vals.append(ct_vals[0])
                    pair_factors.append({"Quantity": qty, "Ct_pair": ct_vals})
                else:
                    x_vals.append(np.log10(qty))
                    y_vals.append(ct_vals.mean())
                    pair_factors.append({"Quantity": qty, "Ct_pair": ct_vals})

            if len(x_vals) > 1:
                a, b = np.polyfit(x_vals, y_vals, 1)
                regression_dict[target] = {
                    "a": a, "b": b,
                    "x_vals": x_vals, "y_vals": y_vals,
                    "raw_points": t_df
                }

                for pf in pair_factors:
                    ct_pair = pf["Ct_pair"]
                    expected_qties = [10**((ct - b)/a) for ct in ct_pair]
                    pf["Factor"] = round(pf["Quantity"] / np.mean(expected_qties), 2)
                    pf.pop("Ct_pair")
                pair_factors_dict[target] = pair_factors
                st.write(f"{target}: Ct = {a:.3f}*log10(Quantity) + {b:.3f}")

    with st.expander("Factores de conversión"):
        targets = list(pair_factors_dict.keys())
        for i in range(0, len(targets), 2):
            cols = st.columns(2)
            for j, col in enumerate(cols):
                if i+j < len(targets):
                    target = targets[i+j]
                    pf_list = pair_factors_dict[target]
                    if pf_list:
                        table = pd.DataFrame(pf_list)
                        table = table.rename(columns={
                            "Quantity": "Quantity (par)",
                            "Factor": "Factor de Conversión"
                        })
                        col.markdown(f"**{target}**")
                        col.dataframe(table)

    with st.expander("Curvas patrón de cada Target"):
        fig, ax = plt.subplots(figsize=(8,6))
        for target, reg in regression_dict.items():
            x_plot = np.linspace(min(reg["x_vals"]), max(reg["x_vals"]), 100)
            y_plot = reg["a"]*x_plot + reg["b"]
            ax.plot(x_plot, y_plot, label=f"{target}")

            raw_points = reg["raw_points"]
            ax.scatter(np.log10(raw_points["Quantity"]), raw_points["Cт"], s=10, alpha=0.7)
        ax.set_xlabel("log10(Quantity)")
        ax.set_ylabel("Ct")
        ax.set_title("Curvas patrón de cada Target")
        ax.legend()
        st.pyplot(fig)

    # ==========================
    # TABLA 1: con Quantity
    # ==========================
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
                aviso, extra = "Sólo 1/3 positivo", "Repetir"
            elif n_positive == 2:
                aviso, extra = "Sólo 2/3 positivo", ""
            else:
                aviso, extra = "", ""

            ratio, fc = 0.0, 1.0
            if quantity_mean>0 and abl1_mean>0:
                ratio = (quantity_mean / abl1_mean) * multiplicador

            if ratio>0 and target in pair_factors_dict:
                pf_list = pair_factors_dict[target]
                log_q_patient = np.log10(quantity_mean)
                diffs = [abs(np.log10(pf["Quantity"]) - log_q_patient) for pf in pf_list]
                idx = np.argmin(diffs)
                fc = pf_list[idx]["Factor"]
                ratio *= fc

            if abl1_mean<10000:
                interpretacion = "No valorable"
            elif ratio==0:
                if abl1_mean<32000: interpretacion="Al menos MR4"
                elif abl1_mean<100000: interpretacion="Al menos MR4.5"
                else: interpretacion="Al menos MR5"
            else:
                if ratio>0.1: interpretacion="Ausencia de MR"
                elif 0.01<ratio<=0.1: interpretacion="MR3"
                elif 0.0032<ratio<=0.01: interpretacion="MR4"
                elif 0.001<ratio<=0.0032: interpretacion="MR4.5"
                else: interpretacion="MR5"
            if extra: interpretacion += f" ({extra})"

            summary_list.append({
                "Interpretación": interpretacion,
                "Paciente": patient,
                "Target": target,
                "Quantity Mean": round(quantity_mean,1),
                "ABL1 Mean": round(abl1_mean,1),
                "Ratio": round(ratio,4),
                "FC": round(fc,2),
                "Aviso": aviso
            })

    summary_df = pd.DataFrame(summary_list).sort_values("Ratio")
    st.subheader("Tabla Resumen (Quantity/ABL1)")
    st.dataframe(summary_df)

    towrite = BytesIO()
    summary_df.to_excel(towrite, index=False, engine='openpyxl')
    towrite.seek(0)
    st.download_button("Descargar tabla resumen", towrite, "tabla_resumen_final.xlsx")

    # ==========================
    # TABLA 2: con ΔCt
    # ==========================
    summary_ct_list = []
    for patient in df_patients["Sample Name"].unique():
        patient_df = df_patients[df_patients["Sample Name"]==patient]
        abl1_mean = patient_df[patient_df["Target Name"]=="ABL1"]["Quantity Mean"].mean()
        abl1_ct_mean = pd.to_numeric(patient_df[patient_df["Target Name"]=="ABL1"]["Cт Mean"], errors='coerce').mean()
        targets = [t for t in patient_df["Target Name"].unique() if t!="ABL1"]

        for target in targets:
            target_ct_mean = pd.to_numeric(patient_df[patient_df["Target Name"]==target]["Cт Mean"], errors='coerce').mean()
            
            aviso, extra = "", ""
            n_positive = patient_df[patient_df["Target Name"]==target]["Quantity"].notna().sum()
            if n_positive == 1:
                aviso, extra = "Sólo 1/3 positivo", "Repetir"
            elif n_positive == 2:
                aviso, extra = "Sólo 2/3 positivo", ""

            ratio_ct, delta_ct = 0.0, None
            if pd.notna(abl1_ct_mean) and pd.notna(target_ct_mean):
                delta_ct = abl1_ct_mean - target_ct_mean
                ratio_ct = (2 ** delta_ct) * multiplicador

            if abl1_mean < 10000:
                interpretacion = "No valorable"
            elif ratio_ct==0:
                if abl1_mean<32000: interpretacion="Al menos MR4"
                elif abl1_mean<100000: interpretacion="Al menos MR4.5"
                else: interpretacion="Al menos MR5"
            else:
                if ratio_ct>0.1: interpretacion="Ausencia de MR"
                elif 0.01<ratio_ct<=0.1: interpretacion="MR3"
                elif 0.0032<ratio_ct<=0.01: interpretacion="MR4"
                elif 0.001<ratio_ct<=0.0032: interpretacion="MR4.5"
                else: interpretacion="MR5"
            if extra: interpretacion += f" ({extra})"

            summary_ct_list.append({
                "Interpretación": interpretacion,
                "Paciente": patient,
                "Target": target,
                "Ct Mean Target": round(target_ct_mean,2) if pd.notna(target_ct_mean) else None,
                "Ct Mean ABL1": round(abl1_ct_mean,2) if pd.notna(abl1_ct_mean) else None,
                "ΔCt (ABL1-Target)": round(delta_ct,2) if delta_ct is not None else None,
                "Ratio (2^ΔCt)": round(ratio_ct,4),
                "Aviso": aviso
            })

    summary_ct_df = pd.DataFrame(summary_ct_list).sort_values("Ratio (2^ΔCt)")
    st.subheader("Tabla Resumen basada en ΔCt")
    st.dataframe(summary_ct_df)

    towrite_ct = BytesIO()
    summary_ct_df.to_excel(towrite_ct, index=False, engine='openpyxl')
    towrite_ct.seek(0)
    st.download_button("Descargar tabla ΔCt", towrite_ct, "tabla_resumen_ct.xlsx")

# Footer
st.markdown(
    """
    <div style='text-align: center; font-size: 12px;'>
        Created by 
        <a href="https://github.com/GenDoc94" target="_blank" style="text-decoration: none; color: inherit;">
            GenDoc94
            <img src="https://raw.githubusercontent.com/GenDoc94/PCR_Analyser/main/logo_hem.png"
                 style="height: 1em; vertical-align: middle; margin-left: 4px;"/>
        </a>
        &nbsp;|&nbsp;
        <a href="https://buymeacoffee.com/gendoc94" target="_blank" style="text-decoration: none; color: inherit;">
            Buy me a coffee
            <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png"
                 style="height: 1em; vertical-align: middle; margin-left: 4px;"/>
        </a>
    </div>
    """,
    unsafe_allow_html=True
)
