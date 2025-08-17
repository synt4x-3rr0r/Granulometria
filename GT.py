import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Configuración de la página
st.set_page_config(page_title="Análisis Granulométrico", layout="wide")
st.title("Análisis Granulométrico de Suelos")

# Datos de tamices estandarizados
tamices_data = {
    "Tamiz": ['3"', '2 1/2"', '2"', '1 1/2"', '1"', '3/4"', '1/2"', '3/8"', '1/4"', 
             'N°4', 'N°10', 'N°20', 'N°40', 'N°60', 'N°100', 'N°200', 'Fondo'],
    "Abertura (mm)": [76.2, 63.5, 50.8, 38.1, 25.4, 19.1, 12.7, 9.52, 6.35, 
                      4.75, 2.00, 0.85, 0.425, 0.25, 0.150, 0.075, 0]
}

# Crear DataFrame inicial
df = pd.DataFrame(tamices_data)

# Entrada de datos en el sidebar
with st.sidebar:
    st.header("Datos de Entrada")
    
    st.subheader("Opciones de Corrección")
    forzar_correccion = st.checkbox("Aplicar corrección de masas", value=False)
    
    masa_total = st.number_input("Masa Total de la Muestra (gr):", min_value=0.1, value=1000.0)
    
    st.subheader("Masa Retenida por Tamiz (gr):")
    masa_retenida = []
    for tamiz in df['Tamiz']:
        masa = st.number_input(f"{tamiz}:", min_value=0.0, value=0.0, key=tamiz)
        masa_retenida.append(masa)
    
    df['Masa Ret. (gr)'] = masa_retenida

# Verificar consistencia de datos
sum_masa_retenida = df['Masa Ret. (gr)'].sum()
diferencia = masa_total - sum_masa_retenida
tolerancia = 1.0  
aplicar_correccion = False

if abs(diferencia) > 0:
    if abs(diferencia) > tolerancia or forzar_correccion:
        aplicar_correccion = True
        st.warning(f"La suma de masas retenidas ({sum_masa_retenida:.2f} gr) difiere de la masa total ({masa_total:.2f} gr) en {diferencia:.2f} gr")
        
        df['Masa Ret. Original (gr)'] = df['Masa Ret. (gr)']
        
        if sum_masa_retenida > 0:
            df['Masa Ret. (gr)'] = df['Masa Ret. (gr)'] + (df['Masa Ret. (gr)'] / sum_masa_retenida) * diferencia
        else:
            num_tamices = len(df[df['Tamiz'] != 'Fondo'])
            df.loc[df['Tamiz'] != 'Fondo', 'Masa Ret. (gr)'] = masa_total / num_tamices
        
        st.success(f"Se aplicó corrección específica: Masa corregida total = {df['Masa Ret. (gr)'].sum():.2f} gr")
        
        correccion_df = df[['Tamiz', 'Masa Ret. Original (gr)', 'Masa Ret. (gr)']].copy()
        correccion_df['Diferencia (gr)'] = correccion_df['Masa Ret. (gr)'] - correccion_df['Masa Ret. Original (gr)']
        correccion_df['Corrección (%)'] = (correccion_df['Diferencia (gr)'] / correccion_df['Masa Ret. Original (gr)']).replace(np.inf, 0) * 100
        
        st.dataframe(correccion_df.style.format({
            'Masa Ret. Original (gr)': '{:.2f}',
            'Masa Ret. (gr)': '{:.2f}',
            'Diferencia (gr)': '{:.2f}',
            'Corrección (%)': '{:.2f}%'
        }))
    else:
        st.success("✅ La suma de masas retenidas coincide con la masa total (diferencia ≤ 1g)")
else:
    st.success("✅ La suma de masas retenidas coincide exactamente con la masa total")

# Cálculos granulométricos
df['Retenido (%)'] = (df['Masa Ret. (gr)'] / masa_total) * 100
df['Ret. Acum. (%)'] = df['Retenido (%)'].cumsum()
df['Pasa (%)'] = 100 - df['Ret. Acum. (%)']

# Resultados
st.subheader("Resultados del Análisis Granulométrico")
display_columns = ['Tamiz', 'Abertura (mm)', 'Masa Ret. (gr)', 'Retenido (%)', 'Ret. Acum. (%)', 'Pasa (%)']
if 'Masa Ret. Original (gr)' in df.columns:
    display_columns.insert(3, 'Masa Ret. Original (gr)')

st.dataframe(df[display_columns].style.format({
    'Abertura (mm)': '{:.2f}',
    'Masa Ret. Original (gr)': '{:.2f}',
    'Masa Ret. (gr)': '{:.2f}',
    'Retenido (%)': '{:.2f}',
    'Ret. Acum. (%)': '{:.2f}',
    'Pasa (%)': '{:.2f}'
}))

# Filtrar datos para curva
curve_df = df[df['Abertura (mm)'] > 0].copy()
curve_df = curve_df[curve_df['Pasa (%)'] >= 0]

# Gráfica
st.subheader("CURVA DE DISTRIBUCIÓN GRANULOMÉTRICA")
fig, ax = plt.subplots(figsize=(10, 6))
ax.set_xscale('log')
ax.set_xlabel('Abertura de tamices (mm)', fontsize=12)
ax.set_ylabel('% Pasa', fontsize=12)
ax.set_title('CURVA DE DISTRIBUCIÓN GRANULOMÉTRICA', fontsize=14, fontweight='bold')
ax.set_xlim(100, 0.01)  
ax.set_xticks([0.01, 0.1, 1, 10, 100])
ax.set_yticks(range(0, 101, 10))
ax.grid(True, which='both', linestyle='--', alpha=0.5)
ax.plot(curve_df['Abertura (mm)'], curve_df['Pasa (%)'], 'b-', linewidth=1.5)

# Interpolación en log
def interpolar_lineal_log(x, y, valor_y):
    x = np.array(x)
    y = np.array(y)
    sorted_indices = np.argsort(x)
    x_sorted, y_sorted = x[sorted_indices], y[sorted_indices]
    for i in range(len(y_sorted) - 1):
        y0, y1 = y_sorted[i], y_sorted[i+1]
        if (y0 <= valor_y <= y1) or (y1 <= valor_y <= y0):
            log_x0, log_x1 = np.log10(x_sorted[i]), np.log10(x_sorted[i+1])
            m = (log_x1 - log_x0) / (y1 - y0) if y1 != y0 else 0
            log_x = log_x0 + m * (valor_y - y0)
            return 10**log_x
    return None

try:
    x, y = curve_df['Abertura (mm)'].values, curve_df['Pasa (%)'].values
    D10, D30, D60 = interpolar_lineal_log(x, y, 10), interpolar_lineal_log(x, y, 30), interpolar_lineal_log(x, y, 60)
    if D10 and D30 and D60:
        Cu, Cc = D60 / D10, (D30**2) / (D10 * D60)
        for pct, diam, color, label in zip([10, 30, 60], [D10, D30, D60], ['red', 'green', 'blue'], ['D10', 'D30', 'D60']):
            ax.axhline(y=pct, color=color, linestyle='--', alpha=0.7)
            ax.axvline(x=diam, color=color, linestyle='--', alpha=0.7)
            ax.plot(diam, pct, 'o', markersize=8, color=color, fillstyle='none', markeredgewidth=1.5)
            ax.annotate(f'{label} = {diam:.3f} mm', xy=(diam, pct), xytext=(diam*1.2, pct+3), fontsize=10,
                        arrowprops=dict(arrowstyle='->', color=color))
        
        st.success("Parámetros granulométricos calculados:")
        col1, col2, col3 = st.columns(3)
        col1.metric("D10 (mm)", f"{D10:.4f}")
        col2.metric("D30 (mm)", f"{D30:.4f}")
        col3.metric("D60 (mm)", f"{D60:.4f}")
        col1, col2 = st.columns(2)
        col1.metric("Cu", f"{Cu:.2f}")
        col2.metric("Cc", f"{Cc:.2f}")
except Exception as e:
    st.error(f"Error en interpolación: {e}")

st.pyplot(fig)

