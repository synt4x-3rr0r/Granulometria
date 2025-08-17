import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Título de la app
st.title("Ejemplo sencillo con Streamlit, Numpy, Pandas y Matplotlib")

# Generar datos con numpy
x = np.linspace(0, 10, 50)
y = np.sin(x)

# Crear un DataFrame con pandas
df = pd.DataFrame({"x": x, "y = sin(x)": y})

# Mostrar la tabla en streamlit
st.subheader("Tabla de Datos")
st.dataframe(df)

# Graficar con matplotlib
fig, ax = plt.subplots()
ax.plot(x, y, marker="o", linestyle="-", color="blue")
ax.set_title("Gráfica de y = sin(x)")
ax.set_xlabel("x")
ax.set_ylabel("y")

# Mostrar la gráfica en streamlit
st.subheader("Gráfica")
st.pyplot(fig)
