""" El modelo de regresión polinomial grado 2 se utiliza para ajustar una curva descendente a los datos
de factor f vs Sut. Shigley Diseño de ingenieria mecánica, 9na edición, pág. 272 gráfica 6-18"""
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.metrics import r2_score
from pandas import read_csv
import pickle

from scipy.optimize import curve_fit

def model_func(x, A, B, C, D, E):
    return (A*x - B)/(C*x - D) + E/x

def torsion_wahl_factor(x):
    return (4*x**2 - x - 1)/(4 * x * (x - 1))

# 1. Datos que forman una curva descendente
file = "/home/eavedillo/Desktop/djmenu/muelles/regresiones/Wahl Factor Torsion/Wahl factor vs index.csv"
pd = read_csv(file, header=0, skipinitialspace=True)  # skipinitialspace maneja espacios después de comas
X = pd["index"].values.reshape(-1, 1)  # Reshape para que sea una matriz de una columna
y = pd["Wahl_f"].values.reshape(-1, 1)  # Reshape para que sea una matriz de una columna
# X = np.log(X)  # Transformamos X para que sea una curva descendente
y_prima = np.log(y)  # Transformamos y para que sea una curva descendente
# 2. Transformamos X para que el modelo entienda curvas (grado 2)
# Esto convierte X en [X, X^2]
poly = PolynomialFeatures(degree=2)
X_poly = poly.fit_transform(X)

# 3. Entrenamos el modelo con los datos transformados
modelo_curvo = LinearRegression()
modelo_curvo.fit(X_poly, y_prima)

# Guardamos el modelo completo (modelo + transformador polinomial)
modelo_completo = {
    'modelo': modelo_curvo,
    'poly_transformer': poly,
    'info': {
        'descripcion': 'Modelo de regresión polinomial grado 2 para factor f vs Sut',
        'entrada': 'Sut (debe aplicarse log natural antes)',
        'salida': 'factor f'
    }
}

# Guardar en archivo pickle
output_file = "/home/eavedillo/Desktop/djmenu/muelles/regresiones/Wahl Factor Torsion/modelo_factor_f.pkl"
with open(output_file, 'wb') as f:
    pickle.dump(modelo_completo, f)

print(f"Modelo guardado exitosamente en '{output_file}'")

# 4. Predicción y Visualización
y_fit = np.exp(modelo_curvo.predict(poly.transform(X)))


# Calcular R² (coeficiente de determinación) como medida de precisión
r2 = r2_score(y, y_fit)

plt.scatter(X, y, color='blue', label='Datos reales')
plt.plot(X, y_fit, color='green', label=f'Regresión Polinomial (R² = {r2:.4f})')
plt.title('Ajuste de Curva Descendente')
plt.xlabel('log(Sut)')
plt.ylabel('factor f')
plt.legend()
plt.grid(True, alpha=0.3)
plt.show()

print(f"Precisión del modelo (R²): {r2:.4f} ({r2*100:.2f}%)")

popt, pcov = curve_fit(model_func, X.ravel(), y_prima.ravel(), p0=[1, 1, 1, 1, 1])

parametros_ajuste = {
    'popt': popt,
    'pcov': pcov,
    'param_names': ['A', 'B', 'C', 'D', 'E']
}
output_params_file = "/home/eavedillo/Desktop/djmenu/muelles/regresiones/Wahl Factor Torsion/parametros_popt.pkl"
with open(output_params_file, 'wb') as file_handle:
    pickle.dump(parametros_ajuste, file_handle)

print("Parámetros ajustados:", popt)
print(f"Parámetros guardados exitosamente en '{output_params_file}'")

""" El modelo de regresión polinomial grado 2 se utiliza para ajustar una curva descendente a los datos
de factor f vs Sut. Shigley Diseño de ingenieria mecánica, 9na edición, pág. 272 gráfica 6-18"""

with open(output_params_file, 'rb') as file_handle:
    data = pickle.load(file_handle)

popt = data["popt"]
pcov = data["pcov"]

# 4. Predicción y Visualización
y_fit = np.exp(model_func(X.ravel(), *popt))

# Calcular R² (coeficiente de determinación) como medida de precisión
r2 = r2_score(y.ravel(), y_fit)

plt.scatter(X.ravel(), y.ravel(), color='blue', label='Datos reales')
plt.plot(X, y_fit, color='green', label=f'Regresión Polinomial (R² = {r2:.4f})')
plt.title('Ajuste de Curva Descendente')
plt.xlabel('log(Sut)')
plt.ylabel('factor f')
plt.legend()
plt.grid(True, alpha=0.3)
plt.show()


y_fit = torsion_wahl_factor(X.ravel())
r2 = r2_score(y.ravel(), y_fit)
plt.scatter(X.ravel(), y.ravel(), color='blue', label='Datos reales')
plt.plot(X, y_fit, color='green', label=f'Regresión Polinomial (R² = {r2:.4f})')
plt.title('Ajuste de Curva Descendente')
plt.xlabel('log(Sut)')
plt.ylabel('factor f')
plt.legend()
plt.grid(True, alpha=0.3)
plt.show()
