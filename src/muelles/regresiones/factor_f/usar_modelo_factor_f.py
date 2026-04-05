import os
import pickle
import numpy as np

# Use a package-relative path so the model loads correctly regardless of user home
MODELO = os.path.join(os.path.dirname(__file__), 'modelo_factor_f.pkl')

class ModeloFactorF:
    def __init__(self, modelo_completo:str=MODELO):
        self.cargar_modelo_factor_f(modelo_completo)
        self.poly_transformer = self.modelo_completo['poly_transformer']
        self.info = self.modelo_completo['info']
    
    def predecir(self, sut_valor):
        """
        Predice el factor f dado un valor de Sut
        Fuera del rango variable, entre N=10³ y N=10⁶, se asignan valores f=0.9 y f=0.76 respectivamente,
        según la gráfica 6-18 de Shigley Diseño de ingenieria mecánica, 9na edición, pág. 272.
        
        Args:
            sut_valor: Valor de resistencia última a tracción (Sut)
        
        Returns:
            factor_f: Valor predicho del factor f
        """
        if sut_valor <= 480:
            return 0.9
        elif sut_valor >= 1380:
            return 0.76
        
        # Aplicar logaritmo natural como en el entrenamiento
        sut_log = np.log([[sut_valor]])
        
        # Transformar con el polinomio
        sut_poly = self.poly_transformer.transform(sut_log)
        
        # Predecir
        factor_f = self.modelo_completo['modelo'].predict(sut_poly)[0][0]

        factor_f = np.exp(factor_f)  # Convertir de logaritmo a valor real
        
        return factor_f
    
    def cargar_modelo_factor_f(self, modelo_path):
        """
        Carga el modelo entrenado para calcular el factor f
        """
        with open(modelo_path, 'rb') as f:
            self.modelo_completo = pickle.load(f)
        return 

# Ejemplo de uso
if __name__ == "__main__":
    # Cargar modelo
    modelo = ModeloFactorF(MODELO)
    
    # Mostrar información del modelo
    print("Información del modelo:")
    print(f"Descripción: {modelo.info['descripcion']}")
    print(f"Entrada: {modelo.info['entrada']}")
    print(f"Salida: {modelo.info['salida']}")
    print()
    
    # Ejemplos de predicción
    valores_sut = [300,500, 600, 700, 800, 1200, 1500]  # Valores de Sut para probar
    
    print("Predicciones:")
    for sut in valores_sut:
        factor_f = modelo.predecir(sut)
        print(f"Sut = {sut} MPa → factor f = {factor_f:.4f}")