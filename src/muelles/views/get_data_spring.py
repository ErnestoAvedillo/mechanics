def get_data_spring(request):
    def to_float(field_name, default=None):
        value = request.POST.get(field_name)
        if value in (None, ''):
            return default
        return float(value)

    datos_muelle = {
        'material': request.POST.get('material'),
        'diametro_hilo': to_float('diametro_hilo'),
        'shot_peening': request.POST.get('shot_peening') == 'si',
        'diametro_exterior': to_float('diametro_exterior'),
        'diametro_medio': to_float('diametro_medio'),
        'diametro_interior': to_float('diametro_interior'),
        'diametro_medio_superior': to_float('diametro_medio_superior'),
        'diametro_medio_inferior': to_float('diametro_medio_inferior'),
        'longitud_libre': to_float('longitud_libre', 0.0),
        'numero_espiras': to_float('numero_espiras', 0.0),
        'numero_ciclos': to_float('numero_ciclos', 1e6),
        'longitud_inicial': to_float('longitud_inicial'),
        'longitud_final': to_float('longitud_final'),
        'pitch': to_float('pitch'),
        'angulo_libre': to_float('angulo_libre'),
        'longitud_sujecion': to_float('longitud_sujecion'),
        'Radio_sujecion': to_float('Radio_sujecion'),
        'angulo_inicial': to_float('angulo_inicial'),
        'angulo_final': to_float('angulo_final'),
        'pitch_superior': to_float('pitch_superior'),
        'pitch_inferior': to_float('pitch_inferior'),
        'length_1': to_float('length_1'),
        'pitch_1': to_float('pitch_1'),
        'length_2': to_float('length_2'),
        'pitch_2': to_float('pitch_2'),
        'length_3': to_float('length_3'),
        'pitch_3': to_float('pitch_3'),
    }
    return datos_muelle
