import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px
import math

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
    
    # Sección destacada para el botón de corrección
    st.subheader("Opciones de Corrección")
    forzar_correccion = st.checkbox("Aplicar corrección de masas", value=False,
                                   help="Activar para aplicar corrección incluso con diferencias pequeñas")
    
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
tolerancia = 1.0  # Tolerancia absoluta de 1 gramo
aplicar_correccion = False

# Lógica de corrección
if abs(diferencia) > 0:  # Solo si hay diferencia
    if abs(diferencia) > tolerancia or forzar_correccion:
        aplicar_correccion = True
        st.warning(f"⚠️ La suma de masas retenidas ({sum_masa_retenida:.2f} gr) difiere de la masa total ({masa_total:.2f} gr) en {diferencia:.2f} gr")
        
        # Guardar masas originales
        df['Masa Ret. Original (gr)'] = df['Masa Ret. (gr)']
        
        # Calcular y aplicar corrección específica
        if sum_masa_retenida > 0:
            df['Masa Ret. (gr)'] = df['Masa Ret. (gr)'] + (df['Masa Ret. (gr)'] / sum_masa_retenida) * diferencia
        else:
            # Si no hay masas retenidas, distribuir uniformemente
            num_tamices = len(df[df['Tamiz'] != 'Fondo'])
            df.loc[df['Tamiz'] != 'Fondo', 'Masa Ret. (gr)'] = masa_total / num_tamices
        
        st.success(f"✅ Se aplicó corrección específica: Masa corregida total = {df['Masa Ret. (gr)'].sum():.2f} gr")
        
        # Mostrar tabla con comparación
        st.subheader("Comparación de Masas (Original vs Corregido)")
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

# Cálculos granulométricos con masas corregidas
df['Retenido (%)'] = (df['Masa Ret. (gr)'] / masa_total) * 100
df['Ret. Acum. (%)'] = df['Retenido (%)'].cumsum()
df['Pasa (%)'] = 100 - df['Ret. Acum. (%)']

# Crear tabla de resultados
st.subheader("Resultados del Análisis Granulométrico")
# Seleccionar columnas a mostrar basado en si se aplicó corrección
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

# Filtrar datos para la curva (excluyendo fondo y valores sin muestra)
curve_df = df[df['Abertura (mm)'] > 0].copy()
curve_df = curve_df[curve_df['Pasa (%)'] >= 0]

# Crear curva granulométrica con Plotly Express
st.subheader("CURVA DE DISTRIBUCIÓN GRANULOMÉTRICA")

# Función de interpolación lineal personalizada
def interpolar_lineal_log(x, y, valor_y):
    """
    Interpola en espacio logarítmico para encontrar x dado un valor_y
    x: tamaños de abertura (mm)
    y: porcentaje que pasa (%)
    valor_y: valor de porcentaje para el cual encontrar el tamaño correspondiente
    """
    # Convertir a arrays de numpy
    x = np.array(x)
    y = np.array(y)
    
    # Ordenar los datos por tamaño (de menor a mayor)
    sorted_indices = np.argsort(x)
    x_sorted = x[sorted_indices]
    y_sorted = y[sorted_indices]
    
    # Encontrar índices adyacentes
    for i in range(len(y_sorted) - 1):
        y0, y1 = y_sorted[i], y_sorted[i+1]
        if (y0 <= valor_y <= y1) or (y1 <= valor_y <= y0):
            # Trabajar en espacio logarítmico
            log_x0 = math.log10(x_sorted[i])
            log_x1 = math.log10(x_sorted[i+1])
            
            # Calcular pendiente
            m = (log_x1 - log_x0) / (y1 - y0) if y1 != y0 else 0
            
            # Interpolar
            log_x = log_x0 + m * (valor_y - y0)
            return 10**log_x
    
    # Si no se encuentra dentro del rango, extrapolar con los puntos más cercanos
    if valor_y < min(y_sorted):
        i = np.argmin(y_sorted)
        j = i+1 if i < len(y_sorted)-1 else i-1
    else:
        i = np.argmax(y_sorted)
        j = i-1 if i > 0 else i+1
    
    # Trabajar en espacio logarítmico
    log_x0 = math.log10(x_sorted[i])
    log_x1 = math.log10(x_sorted[j])
    
    # Calcular pendiente
    m = (log_x1 - log_x0) / (y_sorted[j] - y_sorted[i]) if y_sorted[j] != y_sorted[i] else 0
    
    # Extrapolar
    log_x = log_x0 + m * (valor_y - y_sorted[i])
    return 10**log_x

# Calcular D10, D30, D60 mediante interpolación personalizada
try:
    # Preparar datos para interpolación
    x = curve_df['Abertura (mm)'].values
    y = curve_df['Pasa (%)'].values
    
    # Calcular diámetros efectivos
    D10 = interpolar_lineal_log(x, y, 10)
    D30 = interpolar_lineal_log(x, y, 30)
    D60 = interpolar_lineal_log(x, y, 60)
    
    # Calcular coeficientes
    Cu = D60 / D10
    Cc = (D30**2) / (D10 * D60)
    
    # Crear figura con Plotly Express
    fig = px.line(curve_df, x='Abertura (mm)', y='Pasa (%)', 
                  log_x=True, 
                  markers=True,
                  title='CURVA DE DISTRIBUCIÓN GRANULOMÉTRICA',
                  labels={'Abertura (mm)': 'Abertura de tamices (mm) - Escala Logarítmica'})
    
    # Personalizar gráfica
    fig.update_layout(
        xaxis_title="Abertura de tamices (mm)",
        yaxis_title="% Pasa",
        title_font=dict(size=18, family="Arial", color="black"),
        xaxis=dict(
            type='log',
            autorange='reversed',  # Invertir eje X
            tickvals=[0.01, 0.1, 1, 10, 100],
            showgrid=True,
            gridcolor='lightgray'
        ),
        yaxis=dict(
            range=[0, 100],
            tickvals=list(range(0, 101, 10)),
            showgrid=True,
            gridcolor='lightgray'
        ),
        plot_bgcolor='white'
    )
    
    # Agregar líneas horizontales
    for pct, color, name in zip([10, 30, 60], ['red', 'green', 'blue'], ['D10', 'D30', 'D60']):
        fig.add_hline(y=pct, line_dash="dash", line_color=color, opacity=0.7)
    
    # Agregar líneas verticales y puntos
    for pct, diam, color, label in zip([10, 30, 60], [D10, D30, D60], 
                                      ['red', 'green', 'blue'], ['D10', 'D30', 'D60']):
        fig.add_vline(x=diam, line_dash="dash", line_color=color, opacity=0.7)
        fig.add_scatter(x=[diam], y=[pct], mode='markers', 
                       marker=dict(size=10, color=color, symbol='circle-open'),
                       name=label)
        fig.add_annotation(x=diam, y=pct, 
                          text=f"{label} = {diam:.3f} mm",
                          showarrow=True,
                          arrowhead=1,
                          ax=20,
                          ay=-30,
                          font=dict(size=10, color=color))
    
    # Mostrar gráfica
    st.plotly_chart(fig, use_container_width=True)
    
    # Mostrar resultados
    st.success("Parámetros granulométricos calculados:")
    col1, col2, col3 = st.columns(3)
    col1.metric("D10 (mm)", f"{D10:.4f}")
    col2.metric("D30 (mm)", f"{D30:.4f}")
    col3.metric("D60 (mm)", f"{D60:.4f}")
    
    col1, col2 = st.columns(2)
    col1.metric("Coeficiente de Uniformidad (Cu)", f"{Cu:.2f}")
    col2.metric("Coeficiente de Curvatura (Cc)", f"{Cc:.2f}")
    
    # Clasificación según el tipo de suelo
    pasa_N4 = df.loc[df['Tamiz'] == 'N°4', 'Pasa (%)'].values[0]
    pasa_N200 = df.loc[df['Tamiz'] == 'N°200', 'Pasa (%)'].values[0]
    
    # Determinar si es grava o arena
    if pasa_N4 < 50:  # Menos del 50% pasa el tamiz N°4 (4.75 mm)
        tipo_suelo = "GRAVA"
        bien_gradada = (Cu >= 4) and (1 < Cc < 3)
    else:
        tipo_suelo = "ARENA"
        bien_gradada = (Cu >= 6) and (1 < Cc < 3)
    
    # Mostrar clasificación
    st.subheader("Clasificación del Suelo")
    st.info(f"**Tipo predominante:** {tipo_suelo}")
    st.info(f"**Porcentaje que pasa el tamiz N°4 (4.75 mm):** {pasa_N4:.2f}%")
    st.info(f"**Porcentaje que pasa el tamiz N°200 (0.075 mm):** {pasa_N200:.2f}%")
    
    # Mostrar resultado de la clasificación
    if bien_gradada:
        st.success(f"**CLASIFICACIÓN:** El suelo es una {tipo_suelo} BIEN GRADADA")
        st.markdown(f"**Criterio cumplido:** Cu ≥ {'4' if tipo_suelo == 'GRAVA' else '6'} y 1 < Cc < 3")
    else:
        st.warning("**CLASIFICACIÓN:** El suelo es MAL GRADADO")
        if tipo_suelo == "GRAVA":
            st.markdown("**Criterio para grava bien gradada:** Cu ≥ 4 y 1 < Cc < 3")
            if Cu < 4:
                st.markdown(f"- ✖ Cu = {Cu:.2f} < 4")
            else:
                st.markdown(f"- ✔ Cu = {Cu:.2f} ≥ 4")
            if not (1 < Cc < 3):
                st.markdown(f"- ✖ Cc = {Cc:.2f} no está entre 1 y 3")
            else:
                st.markdown(f"- ✔ Cc = {Cc:.2f} entre 1 y 3")
        else:
            st.markdown("**Criterio para arena bien gradada:** Cu ≥ 6 y 1 < Cc < 3")
            if Cu < 6:
                st.markdown(f"- ✖ Cu = {Cu:.2f} < 6")
            else:
                st.markdown(f"- ✔ Cu = {Cu:.2f} ≥ 6")
            if not (1 < Cc < 3):
                st.markdown(f"- ✖ Cc = {Cc:.2f} no está entre 1 y 3")
            else:
                st.markdown(f"- ✔ Cc = {Cc:.2f} entre 1 y 3")
    
except Exception as e:
    st.error(f"Error en interpolación: {str(e)}. Verifique los datos de entrada. Asegúrese de que los datos de porcentaje que pasa sean adecuados para la interpolación.")

# Instrucciones de uso
with st.expander("Instrucciones de Uso"):
    st.markdown("""
    ## Método de Corrección de Masas
    Cuando la suma de masas retenidas no coincide con la masa total, aplicamos el siguiente método de corrección:
    
    ```
    Diferencia = Masa Total - Σ(Masas Retenidas)
    Masa Corregida = Masa Original + (Masa Original / Σ(Masas Retenidas)) * Diferencia
    ```
    
    **Ejemplo:**
    - Masa total: 500 gr
    - Suma de masas retenidas: 497.5 gr
    - Diferencia: 500 - 497.5 = 2.5 gr
    
    Para un tamiz con masa retenida de 18 gr:
    ```
    Corrección = (18 / 497.5) * 2.5 = 0.0905 gr
    Masa Corregida = 18 + 0.0905 = 18.0905 gr
    ```
    
    Para un tamiz con masa retenida de 90 gr:
    ```
    Corrección = (90 / 497.5) * 2.5 = 0.4523 gr
    Masa Corregida = 90 + 0.4523 = 90.4523 gr
    ```
    
    La suma de todas las masas corregidas será exactamente 500 gr.
    
    ## Control de Corrección
    - **Diferencias > 1g**: Se aplica corrección automáticamente
    - **Diferencias ≤ 1g**: 
        - Por defecto no se aplica corrección
        - Active la casilla "Aplicar corrección de masas" para forzar la corrección
    
    ## Pasos del Análisis
    1. Ingrese la **masa total** de la muestra en gramos
    2. Ingrese las **masas retenidas** en cada tamiz
    3. Si la suma difiere de la masa total:
       - Se mostrará advertencia y opción de corrección
       - Active "Aplicar corrección de masas" si desea corregir diferencias pequeñas
    4. Los resultados se calcularán con las masas corregidas (si se aplicó)
    5. La curva mostrará las líneas para D₁₀, D₃₀ y D₆₀
    6. Se calcularán los coeficientes de uniformidad (Cu) y curvatura (Cc)
    7. Clasificación según:
        - **Grava bien gradada:** Cu ≥ 4 y 1 < Cc < 3
        - **Arena bien gradada:** Cu ≥ 6 y 1 < Cc < 3
        - **Mal gradado:** No cumple los criterios anteriores
    
    **Fórmulas:**
    - Cu = D₆₀/D₁₀
    - Cc = (D₃₀)²/(D₁₀·D₆₀)
    
    ## Características de la Gráfica
    - Eje X invertido (de mayor a menor tamaño)
    - Valores en formato decimal (sin exponentes)
    - Líneas de referencia para D10, D30, D60
    - Gráfica interactiva: puede hacer zoom y desplazarse
    """)
