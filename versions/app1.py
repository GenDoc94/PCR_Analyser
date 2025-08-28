import streamlit as st
import pandas as pd

st.set_page_config(page_title="PCR Ratio Calculator", layout="wide")

st.title("Calculadora de ratios de PCR")

# Subida del archivo
uploaded_file = st.file_uploader("Sube tu archivo .xls", type=["xls", "xlsx"])
if uploaded_file is not None:
    # Leer el Excel ignorando las 7 primeras filas
    df = pd.read_excel(uploaded_file, skiprows=7)
    
    # Filtramos las columnas necesarias
    cols_needed = ['Sample Name', 'Target Name', 'Cт', 'Quantity Mean']
    df = df[cols_needed]

    # Input para multiplicar los ratios
    multiplicador = st.number_input("Multiplicar ratio por:", value=100)
    factor_conversion = st.number_input("Factor de conversión manual:", value=1.0, format="%.4f")
    
    resumen = []

    for sample in df['Sample Name'].unique():
        df_sample = df[df['Sample Name'] == sample]
        df_abl1 = df_sample[df_sample['Target Name'] == 'ABL1']

        if df_abl1.empty or df_abl1['Quantity Mean'].isna().all():
            st.warning(f"Paciente {sample} no tiene ABL1 válido")
            continue

        abl1_mean = df_abl1['Quantity Mean'].mean()
        
        targets = df_sample['Target Name'].unique()
        targets = [t for t in targets if t != 'ABL1']
        
        for target in targets:
            df_target = df_sample[df_sample['Target Name'] == target]
            
            # Verificar positivos
            positivos = df_target['Quantity Mean'].notna().sum()
            total_replicas = len(df_target)
            status = ""
            if positivos == 0:
                ratio = "NEGATIVO"
                status = "NEGATIVO"
            else:
                ratio = (df_target['Quantity Mean'].mean() / abl1_mean) * multiplicador * factor_conversion
                if positivos == 1:
                    status = "Revisar: sólo 1 positivo de 3"
                elif positivos < total_replicas:
                    status = f"Revisar: {positivos}/{total_replicas} positivos"

            resumen.append({
                "Paciente": sample,
                "Target": target,
                "Ratio": ratio,
                "Estado": status
            })
    
    df_resumen = pd.DataFrame(resumen)
    st.subheader("Resumen de ratios")
    st.dataframe(df_resumen)

    # Descargar Excel
    st.download_button(
        label="Descargar resumen como Excel",
        data=df_resumen.to_excel(index=False, engine='openpyxl'),
        file_name="resumen_ratios.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
