from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import gettext as _
from springcalc import Material, CompressionSpring



@csrf_exempt
@require_http_methods(["POST"])
def calculate_blocking_length(request):
    """
    Calculates the solid (blocking) length of a compression spring.

    Receives via POST:
    - material: material code
    - diametro_hilo: wire diameter in mm
    - numero_espiras: total number of coils

    Returns JSON with:
    - longitud_bloqueo: solid length in mm
    - error: error message if one occurs
    """
    try:
        material_code = request.POST.get('material', '').strip()
        diametro_hilo = request.POST.get('diametro_hilo', '').strip()
        numero_espiras = request.POST.get('numero_espiras', '').strip()

        # Validate that they are present
        if not material_code:
            return JsonResponse({
                'error': _('Material no seleccionado')
            }, status=400)

        if not diametro_hilo:
            return JsonResponse({
                'error': _('Diámetro del hilo no proporcionado')
            }, status=400)

        if not numero_espiras:
            return JsonResponse({
                'error': _('Número de espiras no proporcionado')
            }, status=400)

        # Convert to numbers
        try:
            diametro_hilo = float(diametro_hilo)
            numero_espiras = float(numero_espiras)
        except ValueError:
            return JsonResponse({
                'error': _('Valores numéricos no válidos')
            }, status=400)

        # Create the Material and Spring objects
        material_obj = Material(material_name=material_code)
        muelle = CompressionSpring(
            material=material_obj,
            wire_diameter=diametro_hilo
        )

        # Assign the number of coils and calculate the solid length
        muelle.nr_coils = numero_espiras
        longitud_bloqueo = muelle.calculate_solid_length()

        # Also calculate the pitch to return it (optional, but useful for validation)
        pitch = muelle.calculate_pitch()

        # Convert to float if it's a Quantity
        longitud_bloqueo_value = float(longitud_bloqueo.magnitude) if hasattr(longitud_bloqueo, 'magnitude') else float(longitud_bloqueo)
        pitch_value = float(pitch.magnitude) if hasattr(pitch, 'magnitude') else float(pitch)
        
        return JsonResponse({
            'longitud_bloqueo': longitud_bloqueo_value,
            'pitch': pitch_value
        })
    
    except Exception as e:
        return JsonResponse({
            'error': _('Error al calcular longitud de bloqueo: %(error)s') % {'error': str(e)}
        }, status=500)
