# PCR Quantitative Ratio Analyzer

Este proyecto es una aplicación **Streamlit** para analizar datos de PCR cuantitativa, calcular ratios entre distintos **Target Names** y ABL1, y aplicar factores de conversión basados en las curvas estándar (`STANDARD`).

La aplicación permite:  
- Calcular ratios Target/ABL1 con multiplicador configurable (100 o 10000).  
- Aplicar **factores de conversión** correctos basados en los pares de Quantity de las curvas estándar.  
- Generar interpretaciones MR según las reglas definidas.  
- Avisar si solo hay 1/3 o 2/3 positivos en los pocillos.  
- Mostrar gráficamente las rectas de regresión de las curvas estándar.  
- Descargar una tabla resumen en Excel.

---

## Requisitos

- Python 3.10+  
- Librerías:

```
streamlit
pandas
numpy
matplotlib
openpyxl
```

Puedes instalarlas con:

```bash
pip install -r requirements.txt
```

---

## Estructura del proyecto

```
PCR_Analyzer/
├─ pcr_ratio_streamlit_final.py   # Script principal de Streamlit
├─ requirements.txt               # Librerías necesarias
└─ README.md                      # Este archivo
```

---

## Uso

1. Clonar el repositorio:

```bash
git clone https://github.com/TU_USUARIO/PCR_Analyzer.git
cd PCR_Analyzer
```

2. (Opcional) Crear entorno virtual:

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate
```

3. Instalar dependencias:

```bash
pip install -r requirements.txt
```

4. Ejecutar la app:

```bash
streamlit run pcr_ratio_streamlit_final.py
```

5. Se abrirá en el navegador una interfaz donde podrás:  
   - Subir tus archivos `.xls` de PCR.  
   - Seleccionar multiplicador (100 o 10000).  
   - Visualizar la tabla resumen y descargarla en Excel.  
   - Ver los gráficos de las curvas estándar con las rectas de regresión.

---

## Notas importantes

- Las filas con `Task == UNKNOWN` son consideradas como pacientes reales.  
- Todas las muestras deben tener un ABL1 para calcular ratios.  
- Las curvas estándar (`STANDARD`) se usan para calcular factores de conversión por par de Quantity.  
- Las filas con `NTC` son ignoradas.  
- Si alguna medición tiene `Undetermined`, se generan avisos y se maneja según las reglas de cálculo.  

---

## Autor

- GenDoc94

