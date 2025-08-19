import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# --- Configuración de la Página ---
st.set_page_config(
    page_title="Análisis Granulométrico",
    page_icon="grain",
    layout="wide"
)

# --- Datos Constantes ---
TAMICES = {
    "3\"": 76.2,
    "2\"": 50.8,
    "1 1/2\"": 38.1,
    "1\"": 25.4,
    "3/4\"": 19.05,
    "1/2\"": 12.7,
    "3/8\"": 9.525,
    "1/4\"": 6.35,
    "No. 4": 4.75,
    "No. 10": 2.00,
    "No. 20": 0.850,
    "No. 40": 0.425,
    "No. 60": 0.250,
    "No. 100": 0.150,
    "No. 200": 0.075,
    "Fondo": 0.00
}

# --- Funciones de Cálculo ---

def calcular_granulometria(masas_retenidas, masa_inicial):
    """
    Realiza todos los cálculos del análisis granulométrico con el método de corrección
    aditivo y proporcional.
    """
    
    # 1. Crear DataFrame inicial
    data = []
    for nombre, apertura in TAMICES.items():
        data.append({
            "Tamiz": nombre,
            "Apertura (mm)": apertura,
            "Masa Retenida (g)": masas_retenidas.get(nombre, 0.0)
        })
    df = pd.DataFrame(data)

    # 2. Corrección de Masas (MÉTODO CORREGIDO)
    masa_final_medida = df["Masa Retenida (g)"].sum()
    mensaje_correccion = ""
    
    # Se aplica corrección si la diferencia es significativa (ej. > 0.01g)
    if masa_final_medida > 0 and abs(masa_inicial - masa_final_medida) > 0.01:
        diferencia_neta = masa_inicial - masa_final_medida
        
        # Calcular el % de aporte de cada tamiz sobre la masa total medida
        df["% Aporte Inicial"] = (df["Masa Retenida (g)"] / masa_final_medida) * 100
        
        # Calcular el ajuste para cada tamiz basado en su aporte proporcional al error
        df["Ajuste (g)"] = (df["% Aporte Inicial"] / 100) * diferencia_neta
        
        # Aplicar el ajuste para obtener la masa corregida
        df["Masa Corregida (g)"] = df["Masa Retenida (g)"] + df["Ajuste (g)"]
        
        mensaje_correccion = (
            f"La masa final medida ({masa_final_medida:.2f} g) no coincide con la inicial ({masa_inicial:.2f} g). "
            f"Se ha distribuido una diferencia de {diferencia_neta:.2f} g proporcionalmente al aporte de cada tamiz."
        )
    else:
        # Si no se necesita corrección, la masa corregida es la misma que la retenida
        df["Masa Corregida (g)"] = df["Masa Retenida (g)"]
        mensaje_correccion = "La masa final coincide con la inicial. No se aplicó corrección."

    # 3. Cálculos de Porcentajes
    # Después de la corrección, la suma de "Masa Corregida" debe ser igual a "masa_inicial"
    # Por lo tanto, usamos masa_inicial como la base para los porcentajes.
    df["% Retenido"] = (df["Masa Corregida (g)"] / masa_inicial) * 100
    df["% Ret. Acumulado"] = df["% Retenido"].cumsum()
    df["% Pasa"] = 100 - df["% Ret. Acumulado"]
    
    # Asegurar que el % Pasa del fondo sea exactamente 0 y el acumulado 100
    df.loc[df["Tamiz"] == "Fondo", "% Pasa"] = 0.0
    df.loc[df["% Ret. Acumulado"] > 99.99, "% Ret. Acumulado"] = 100.0 # Ajuste final por precisión
    df.loc[df["% Pasa"] < 0.01, "% Pasa"] = 0.0
    
    # Seleccionar y reordenar columnas para la visualización final
    columnas_finales = [
        "Tamiz", "Apertura (mm)", "Masa Retenida (g)", "Masa Corregida (g)",
        "% Retenido", "% Ret. Acumulado", "% Pasa"
    ]
    df_final = df[columnas_finales]

    return df_final, mensaje_correccion


def calcular_diametros(df):
    """Calcula D10, D30, D60 por interpolación logarítmica."""
    df_interp = df[df["Tamiz"] != "Fondo"].copy()
    log_apertura = np.log10(df_interp["Apertura (mm)"])
    porcentaje_pasa = df_interp["% Pasa"]
    y_interp = porcentaje_pasa.values[::-1]
    x_interp = log_apertura.values[::-1]
    
    try:
        log_d10 = np.interp(10, y_interp, x_interp)
        log_d30 = np.interp(30, y_interp, x_interp)
        log_d60 = np.interp(60, y_interp, x_interp)
        d10 = 10**log_d10
        d30 = 10**log_d30
        d60 = 10**log_d60
        return d10, d30, d60
    except Exception as e:
        st.error(f"No se pudieron calcular los diámetros. Verifica que los datos cubran los rangos de 10%, 30% y 60% que pasa. Error: {e}")
        return None, None, None

def calcular_coeficientes(d10, d30, d60):
    """Calcula los coeficientes de Uniformidad y Curvatura."""
    cu = cc = None
    if d10 and d10 > 0:
        cu = d60 / d10
        if d60 > 0:
            cc = (d30**2) / (d10 * d60)
    return cu, cc

def clasificar_suelo(df, cu, cc):
    """Clasifica el suelo según su granulometría (basado en USCS)."""
    try:
        pasa_n4 = df.loc[df["Tamiz"] == "No. 4", "% Pasa"].iloc[0]
        pasa_n200 = df.loc[df["Tamiz"] == "No. 200", "% Pasa"].iloc[0]
    except IndexError:
        st.error("No se encontraron los tamices No. 4 o No. 200 en los datos para la clasificación.")
        return None, None, None, "Error en clasificación"
        
    porc_grava = 100 - pasa_n4
    porc_arena = pasa_n4 - pasa_n200
    porc_finos = pasa_n200
    
    gradacion = "No aplica (Suelo con alto contenido de finos)"
    if porc_finos < 5: # Criterio para suelos limpios
        fraccion_gruesa = porc_grava + porc_arena
        if porc_grava > porc_arena: # Suelo predominantemente grava
            if cu and cc and cu >= 4 and 1 <= cc <= 3:
                gradacion = "Suelo Bien Gradado (GW - Grava bien gradada)"
            else:
                gradacion = "Suelo Mal Gradado (GP - Grava mal gradada)"
        else: # Suelo predominantemente arena
            if cu and cc and cu >= 6 and 1 <= cc <= 3:
                gradacion = "Suelo Bien Gradado (SW - Arena bien gradada)"
            else:
                gradacion = "Suelo Mal Gradado (SP - Arena mal gradada)"
    elif porc_finos > 12:
        gradacion = "Suelo con alto contenido de finos (SM, SC, GM, GC). Se requiere análisis de plasticidad."
    else: # Entre 5% y 12% de finos
        gradacion = "Suelo con gradación de frontera. Se requiere análisis de plasticidad para una clasificación completa."
    
    return porc_grava, porc_arena, porc_finos, gradacion


def generar_grafica(df):
    """Genera la curva granulométrica."""
    df_plot = df[df['Apertura (mm)'] > 0]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(df_plot["Apertura (mm)"], df_plot["% Pasa"], marker='o', linestyle='-', color='b')
    ax.set_xscale('log')
    ax.set_xlabel("Apertura del Tamiz (mm) - Escala Logarítmica", fontsize=12)
    ax.set_ylabel("% Que Pasa", fontsize=12)
    ax.set_title("Curva Granulométrica", fontsize=14, fontweight='bold')
    ax.grid(True, which="both", linestyle='--', linewidth=0.5)
    plt.gca().invert_xaxis()
    
    return fig

# --- Interfaz de la Aplicación ---

st.title("Análisis Granulométrico - Geotecnia I")
st.markdown("""
Esta aplicación realiza un análisis granulométrico completo a partir de la masa retenida en cada tamiz.
**El método de corrección de masas ha sido actualizado para distribuir el error proporcionalmente**, como es estándar en la práctica de laboratorio.
""")

# --- Barra Lateral para Entradas ---
with st.sidebar:
    st.header("1. Datos de Entrada")
    masa_inicial = st.number_input("Masa Inicial Total de la Muestra (g)", min_value=0.1, value=500.0, step=10.0)
    
    st.header("2. Masa Retenida en Tamices (g)")
    masas_retenidas_input = {}
    with st.expander("Ingresar Masas Retenidas", expanded=True):
        for tamiz_nombre in TAMICES.keys():
            # Excluimos "Fondo" del bucle principal para manejarlo por separado
            if tamiz_nombre != "Fondo":
                masas_retenidas_input[tamiz_nombre] = st.number_input(
                    f"Tamiz {tamiz_nombre}", min_value=0.0, value=0.0, key=tamiz_nombre
                )
    
    # Se calcula una sugerencia para el fondo, pero el usuario puede modificarla
    suma_parcial = sum(masas_retenidas_input.values())
    masa_fondo_sugerida = masa_inicial - suma_parcial if masa_inicial >= suma_parcial else 0.0
    masas_retenidas_input["Fondo"] = st.number_input(
        "Fondo", min_value=0.0, value=masa_fondo_sugerida, key="Fondo",
        help="Puede ajustar este valor. Si la suma total no coincide con la masa inicial, se aplicará una corrección."
    )

    boton_calcular = st.button("📊 Calcular Análisis", type="primary")

# --- Área Principal para Resultados ---
if boton_calcular:
    if masa_inicial <= 0 or sum(masas_retenidas_input.values()) <= 0:
        st.error("La masa inicial y la suma de masas retenidas deben ser mayores que cero.")
    else:
        st.header("Resultados del Análisis")
        
        df_resultados, mensaje = calcular_granulometria(masas_retenidas_input, masa_inicial)
        
        st.info(mensaje)

        st.subheader("Tabla de Datos y Cálculos")
        st.dataframe(df_resultados.style.format({
            "Apertura (mm)": "{:.3f}",
            "Masa Retenida (g)": "{:.2f}",
            "Masa Corregida (g)": "{:.2f}",
            "% Retenido": "{:.2f}%",
            "% Ret. Acumulado": "{:.2f}%",
            "% Pasa": "{:.2f}%"
        }))
        
        d10, d30, d60 = calcular_diametros(df_resultados)
        
        if d10 is not None:
            cu, cc = calcular_coeficientes(d10, d30, d60)

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Diámetros Característicos")
                st.metric("D10 (mm)", f"{d10:.3f}")
                st.metric("D30 (mm)", f"{d30:.3f}")
                st.metric("D60 (mm)", f"{d60:.3f}")

            with col2:
                st.subheader("Coeficientes Geotécnicos")
                if cu is not None: st.metric("Coeficiente de Uniformidad (Cu)", f"{cu:.2f}")
                else: st.warning("No se pudo calcular Cu.")
                
                if cc is not None: st.metric("Coeficiente de Curvatura (Cc)", f"{cc:.2f}")
                else: st.warning("No se pudo calcular Cc.")
            
            st.subheader("Clasificación del Suelo")
            grava, arena, finos, gradacion = clasificar_suelo(df_resultados, cu, cc)
            
            c3, c4, c5 = st.columns(3)
            c3.metric("% Grava (> 4.75mm)", f"{grava:.2f}%")
            c4.metric("% Arena (4.75mm a 0.075mm)", f"{arena:.2f}%")
            c5.metric("% Finos (< 0.075mm)", f"{finos:.2f}%")
            
            st.markdown(f"**Análisis de Gradación:**")
            if "Bien Gradado" in gradacion: st.success(f"✔️ {gradacion}")
            elif "Mal Gradado" in gradacion: st.warning(f"⚠️ {gradacion}")
            else: st.info(f"ℹ️ {gradacion}")
            st.caption("Nota: La clasificación de gradación es una simplificación del Sistema Unificado de Clasificación de Suelos (USCS). Una clasificación completa para suelos con más de 5% de finos requiere conocer los límites de Atterberg.")

        st.subheader("Curva Granulométrica")
        grafica = generar_grafica(df_resultados)
        st.pyplot(grafica)
