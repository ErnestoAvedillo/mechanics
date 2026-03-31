from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from muelles.pymodels.material import Material
from muelles.lineal.compresion import MuelleCompresion



@require_http_methods(["POST"])
def calculate_pitch(request):
    """
    Calcula el paso de un muelle de compresión.
    
    Recibe por POST:
    - material: código del material
    - diametro_hilo: diámetro del hilo en mm
    - numero_espiras: número total de espiras
    
    Retorna JSON con:
    - pitch: paso del muelle en mm
    - error: mensaje de error si ocurre
    """
    try:
        material_code = request.POST.get('material', '').strip()
        diametro_hilo = request.POST.get('diametro_hilo', '').strip()
        numero_espiras = request.POST.get('numero_espiras', '').strip()
        longitud_libre = request.POST.get('longitud_libre', '').strip()
        
        # Validar que están presentes
        if not material_code:
            return JsonResponse({
                'error': 'Material no seleccionado'
            }, status=400)
        
        if not diametro_hilo:
            return JsonResponse({
                'error': 'Diámetro del hilo no proporcionado'
            }, status=400)
        
        if not numero_espiras:
            return JsonResponse({
                'error': 'Número de espiras no proporcionado'
            }, status=400)
        
        if not longitud_libre:
            return JsonResponse({
                'error': 'Longitud libre no proporcionada'
            }, status=400)

        # Convertir a números
        try:
            diametro_hilo = float(diametro_hilo)
            numero_espiras = float(numero_espiras)
            longitud_libre = float(longitud_libre)
        except ValueError:
            return JsonResponse({
                'error': 'Valores numéricos no válidos'
            }, status=400)
        
        # Crear objeto Material y Muelle
        material_obj = Material(nombre_material=material_code)
        muelle = MuelleCompresion(
            material=material_obj,
            diametro_hilo=diametro_hilo
        )
        
        # Calcular el pitch para devolverlo también (opcional, pero útil para validación)
        muelle.numero_espiras = numero_espiras
        muelle.longitud_libre = longitud_libre
        pitch = muelle.calcular_paso()

        # Convertir a float si es una Quantity
        pitch_value = float(pitch.magnitude) if hasattr(pitch, 'magnitude') else float(pitch)
        
        return JsonResponse({
            'pitch': pitch_value
        })
    
    except Exception as e:
        return JsonResponse({
            'error': f'Error al calcular pitch: {str(e)}'
        }, status=500)
