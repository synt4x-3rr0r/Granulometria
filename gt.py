import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px

# Título de la app
st.title("Ejemplo sencillo con Streamlit, Numpy, Pandas y Plotly")

# Generar datos con numpy
x = np.linspace(0, 10, 50)
y = np.sin(x)

# Crear DataFrame con pandas
df = pd.DataFrame({"x": x, "y = sin(x)": y})

# Mostrar tabla en Streamlit
st.subheader("Tabla de Datos")
st.dataframe(df)

# Graficar con Plotly
fig = px.line(df, x="x", y="y = sin(x)", markers=True, title="Gráfica de y = sin(x)")

# Mostrar gráfica en Streamlit
st.subheader("Gráfica")
st.plotly_chart(fig)
