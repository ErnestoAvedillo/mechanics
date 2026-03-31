import pandas as pd
from django.conf import settings

def get_available_materials():
    """Obtiene la lista de materiales disponibles desde materials.csv"""
    try:
        csv_path = settings.MUELLES_MATERIALS_CSV

        df = pd.read_csv(csv_path)
        # Limpiar espacios en nombres de columnas
        df.columns = df.columns.str.strip()

        materials = []
        for index, row in df.iterrows():
            denomination = str(row['denomination']).strip()
            # Usar la descripción del CSV, limpiando comillas si las hay
            description = str(row.get('descripcion', denomination)).strip().strip("'\"")

            materials.append({
                'code': denomination,
                'name': description,
                'shear_modulus': str(row.get('shear_modulus', '')).strip() if pd.notna(row.get('shear_modulus')) else '',
                'elastic_factor': str(row.get('factor_limite_elástico', '')).strip() if pd.notna(row.get('factor_limite_elástico')) else '',
            })
        
        return materials
    except Exception as e:
        print(f"Error al cargar materiales: {e}")
        # Materiales por defecto si falla la lectura del CSV
        return [
            {'code': 'SL', 'name': 'SL - Acero de alto carbono', 'shear_modulus': '81500', 'elastic_factor': '0.5'},
            {'code': 'SM', 'name': 'SM - Acero medio carbono', 'shear_modulus': '81500', 'elastic_factor': '0.5'},
            {'code': 'SH', 'name': 'SH - Acero duro', 'shear_modulus': '81500', 'elastic_factor': '0.5'},
        ]