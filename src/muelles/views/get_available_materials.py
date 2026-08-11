import pandas as pd
from django.utils.translation import gettext as _
from springcalc import get_materials_dataframe

def get_available_materials():
    """Gets the list of available materials from springcalc"""
    try:
        df = get_materials_dataframe()

        materials = []
        for index, row in df.iterrows():
            denomination = str(row['denomination']).strip()
            # Use the description from the CSV, stripping quotes if present
            description = str(row.get('description', denomination)).strip().strip("'\"")

            materials.append({
                'code': denomination,
                'name': description,
                'shear_modulus': str(row.get('shear_modulus', '')).strip() if pd.notna(row.get('shear_modulus')) else '',
                'elastic_factor': str(row.get('elastic_limit_factor', '')).strip() if pd.notna(row.get('elastic_limit_factor')) else '',
            })

        return materials
    except Exception as e:
        print(f"Error loading materials: {e}")
        # Default materials if reading the CSV fails
        return [
            {'code': 'SL', 'name': _('SL - Acero de alto carbono'), 'shear_modulus': '81500', 'elastic_factor': '0.5'},
            {'code': 'SM', 'name': _('SM - Acero medio carbono'), 'shear_modulus': '81500', 'elastic_factor': '0.5'},
            {'code': 'SH', 'name': _('SH - Acero duro'), 'shear_modulus': '81500', 'elastic_factor': '0.5'},
        ]