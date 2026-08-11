from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import gettext as _
from springcalc import Material, CompressionSpring



@csrf_exempt
@require_http_methods(["POST"])
def calculate_pitch(request):
    """
    Calculates the pitch of a compression spring.

    Receives via POST:
    - material: material code
    - diametro_hilo: wire diameter in mm
    - numero_espiras: total number of coils

    Returns JSON with:
    - pitch: spring pitch in mm
    - error: error message if one occurs
    """
    try:
        material_code = request.POST.get('material', '').strip()
        diametro_hilo = request.POST.get('diametro_hilo', '').strip()
        numero_espiras = request.POST.get('numero_espiras', '').strip()
        longitud_libre = request.POST.get('longitud_libre', '').strip()

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

        if not longitud_libre:
            return JsonResponse({
                'error': _('Longitud libre no proporcionada')
            }, status=400)

        # Convert to numbers
        try:
            diametro_hilo = float(diametro_hilo)
            numero_espiras = float(numero_espiras)
            longitud_libre = float(longitud_libre)
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

        # Calculate the pitch to return it
        muelle.nr_coils = numero_espiras
        muelle.free_length = longitud_libre
        pitch = muelle.calculate_pitch()

        # Convert to float if it's a Quantity
        pitch_value = float(pitch.magnitude) if hasattr(pitch, 'magnitude') else float(pitch)
        
        return JsonResponse({
            'pitch': pitch_value
        })
    
    except Exception as e:
        return JsonResponse({
            'error': _('Error al calcular pitch: %(error)s') % {'error': str(e)}
        }, status=500)
