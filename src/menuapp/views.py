from django.shortcuts import render, redirect
from django.urls import reverse
from django.conf import settings
from django.contrib import messages
import subprocess
import json
import csv
import os
import re
import base64
import hashlib


URL_RE = re.compile(r'^(https?://)', re.IGNORECASE)
DATA_DIR = os.path.join(settings.BASE_DIR, "muelles", "static", "muelles", "data")


def open_show_folder(ruta):
    subprocess.Popen(f'explorer "{ruta}"')


def open_json(file_to_open, asJSON=True):
    json_file = os.path.join(DATA_DIR, file_to_open)
    with open(json_file, 'r', encoding='utf-8') as file:
        my_json = file.read()
    if asJSON:
        my_json = re.sub(r'%2F', '/', my_json)
        my_json = json.loads(my_json)
    return my_json


def open_csv(file_to_open, asJSON=True):
    output_dict = {}
    csv_file = os.path.join(DATA_DIR, file_to_open)
    with open(csv_file, 'r', encoding='utf-8') as file:
        if asJSON:
            for i, fila in enumerate(csv.DictReader(file)):
                output_dict[i] = fila
        else:
            output_dict = file.read()
    return output_dict


def save(filename, data):
    full_filename = os.path.join(DATA_DIR, filename)
    parsed_data = re.sub(r"/", "%2F", data)
    with open(full_filename, 'w', encoding='utf-8', newline='') as file:
        file.write(parsed_data)


def get_bloques():
    """Carga la configuración de bloques desde bloques.json"""
    try:
        bloques_config = open_json("bloques.json")
        return bloques_config.get("bloques", [])
    except:
        return []


def get_links():
    """Carga los enlaces dinámicamente basado en la configuración de bloques"""
    General = open_json("General.json")
    bloques = get_bloques()
    grupos = {'General': General}
    
    # Cargar grupos dinámicamente desde bloques.json
    for bloque in bloques:
        name = bloque["name"]
        if name == "General":
            continue
            
        try:
            # Crear estructura del grupo desde la configuración del bloque
            grupo_json = {
                "name": name,
                "links": {}  # Los links se cargarán desde CSV si existe
            }
            
            # Cargar el CSV correspondiente si existe
            csv_filename = bloque.get("csv_file", f"muelles/static/muelles/data/{name}.csv")
            csv_basename = os.path.basename(csv_filename)
            if os.path.exists(os.path.join(DATA_DIR, csv_basename)):
                lista_items = open_csv(csv_basename)
                grupo_json["links"] = lista_items
            
            # Agregar las carpetas de configuración desde bloques.json
            for key, value in bloque.items():
                if key != "name" and key != "csv_file":
                    grupo_json[key] = value
                    
            grupos[name] = grupo_json
        except Exception as e:
            print(f"Error cargando grupo {name}: {e}")
            continue
    
    return grupos


def is_url(s: str) -> bool:
    return isinstance(s, str) and bool(URL_RE.match(s))


def home(request):
    group_name_param = request.GET.get('group_name', 'General')
    grupos = get_links()
    bloques = get_bloques()

    group_name = grupos.get(group_name_param, grupos.get('General', {}))
    
    return render(request, 'menuapp/index.html', {
        'group_name': group_name, 
        'grupos': grupos,
        'bloques': bloques
    })


def editor(request, datos, filename):
    parsed_data = re.sub(r'%2F', '/', datos)
    name, extension = os.path.splitext(filename)
    
    # Usar editor de tabla para archivos CSV
    if extension == ".csv":
        return render(request, 'menuapp/table_editor.html', {'datos': parsed_data, 'filename': filename})
    # Usar editor de JSON para archivos JSON
    elif extension == ".json":
        return render(request, 'menuapp/json_editor.html', {'datos': parsed_data, 'filename': filename})
    else:
        return render(request, 'menuapp/editor.html', {'datos': parsed_data, 'filename': filename})


def abrir(request, filename):
    # Para bloques.json, usar el editor especializado
    if filename == "bloques.json":
        return redirect(reverse('bloques_editor'))
    
    name, extension = os.path.splitext(filename)
    if extension == ".csv":
        datos = open_csv(filename, asJSON=False)
    elif extension == ".json":
        datos = open_json(filename, asJSON=False)
    else:
        # Para extensiones no soportadas, redirigir al home
        return redirect(reverse('home') + '?group_name=General')
    
    # Para archivos grandes, usar sessions
    if len(datos) > 1000:
        # Crear un identificador único para los datos
        data_id = hashlib.md5(f"{filename}_{datos[:100]}".encode()).hexdigest()
        request.session[f"editor_data_{data_id}"] = datos
        return redirect(reverse('editor_with_session', kwargs={'data_id': data_id, 'filename': filename}))
    else:
        return redirect(reverse('editor', kwargs={'datos': datos, 'filename': filename}))


def abrir_carpeta(request, folder, group_name):
    if os.path.exists(folder):
        open_show_folder(folder)
    else:
        print("La carpeta no existe")
    return redirect(reverse('home') + f'?group_name={group_name}')


def editor_with_session(request, data_id, filename):
    """Editor que usa session para archivos grandes"""
    # Para bloques.json, redirigir al editor especializado
    if filename == "bloques.json":
        return redirect(reverse('bloques_editor'))
        
    datos = request.session.get(f"editor_data_{data_id}")
    if not datos:
        messages.error(request, "Los datos del archivo han expirado. Por favor, intenta de nuevo.")
        return redirect(reverse('home') + '?group_name=General')
    
    parsed_data = re.sub(r'%2F', '/', datos)
    name, extension = os.path.splitext(filename)
    
    # Usar editor de tabla para archivos CSV
    if extension == ".csv":
        return render(request, 'menuapp/table_editor.html', {
            'datos': parsed_data, 
            'filename': filename,
            'use_session': True,
            'data_id': data_id
        })
    # Usar editor de JSON para archivos JSON
    elif extension == ".json":
        return render(request, 'menuapp/json_editor.html', {
            'datos': parsed_data, 
            'filename': filename,
            'use_session': True,
            'data_id': data_id
        })
    else:
        return render(request, 'menuapp/editor.html', {
            'datos': parsed_data, 
            'filename': filename,
            'use_session': True,
            'data_id': data_id
        })


def guarda(request):
    if request.method == 'POST':
        datos = request.POST['datos_modificados']
        filename = request.POST['filename']
        use_session = request.POST.get('use_session', False)
        data_id = request.POST.get('data_id', '')
        
        # Limpiar la session si se usó
        if use_session and data_id:
            session_key = f"editor_data_{data_id}"
            if session_key in request.session:
                del request.session[session_key]
        
        _, extension = os.path.splitext(filename)
        if extension == ".csv" or extension == ".json":
            save(filename=filename, data=datos)
            messages.success(request, f"Archivo {filename} guardado correctamente.")
        else:
            messages.error(request, "Tipo de archivo no soportado.")
            return redirect(reverse('home') + '?group_name=General')
        return redirect(reverse('home') + '?group_name=General')
    return redirect(reverse('home') + '?group_name=General')


def bloques_editor(request):
    """Vista para el editor de bloques dinámicos"""
    if request.method == 'POST':
        bloques_json = request.POST.get('bloques_json', '{}')
        try:
            # Guardar los bloques actualizados
            save(filename="bloques.json", data=bloques_json)
            return redirect(reverse('home') + '?group_name=General')
        except Exception as e:
            print(f"Error guardando bloques: {e}")
    
    # Cargar bloques existentes
    try:
        bloques_config = open_json("bloques.json")
        bloques = bloques_config.get("bloques", [])
    except:
        bloques = []
    
    return render(request, 'menuapp/bloques_editor.html', {
        'bloques_json': json.dumps(bloques),
        'bloques': bloques
    })


def json_visualizer(request):
    """Vista para visualizar los bloques JSON de forma amigable"""
    try:
        bloques_config = open_json("bloques.json")
        bloques = bloques_config.get("bloques", [])
        bloques_dinamicos = [b for b in bloques if b.get("name") != "General"]
    except:
        bloques = []
        bloques_dinamicos = []
    
    return render(request, 'menuapp/json_visualizer.html', {
        'bloques': bloques,
        'bloques_dinamicos': bloques_dinamicos
    })
