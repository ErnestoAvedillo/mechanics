from django.shortcuts import render
from urllib.parse import urlparse, parse_qs
from django.utils.translation import gettext as _
import re


def _extract_youtube_id(video_value: str) -> str | None:
    """Extracts a YouTube video ID from a URL or from a direct ID."""
    if not video_value:
        return None

    video_value = video_value.strip()

    if re.fullmatch(r'[A-Za-z0-9_-]{11}', video_value):
        return video_value

    parsed = urlparse(video_value)
    hostname = parsed.hostname or ''

    if 'youtu.be' in hostname:
        return parsed.path.lstrip('/') or None

    if 'youtube.com' in hostname:
        if parsed.path.startswith('/embed/'):
            return parsed.path.split('/embed/')[-1]
        if parsed.path.startswith('/v/'):
            return parsed.path.split('/v/')[-1]
        query = parse_qs(parsed.query)
        if 'v' in query:
            return query['v'][0]

    query = parse_qs(video_value)
    if 'v' in query:
        return query['v'][0]

    return None


def video_tolerancias_absolutas(request):
    titulo = request.GET.get('title', _('Tolerancias Absolutas'))
    descripcion = request.GET.get('descripcion', '')
    video_value = request.GET.get('video', request.GET.get('v', ''))
    video_id = _extract_youtube_id(video_value)

    if video_id is None:
        video_id = 'p3TKKJof8W4'
        video_error = None
        if video_value:
            video_error = _('URL de vídeo no reconocida. Se muestra el vídeo por defecto.')
    else:
        video_error = None

    youtube_embed_url = f'https://www.youtube.com/embed/{video_id}?rel=0&modestbranding=1'
    youtube_watch_url = f'https://www.youtube.com/watch?v={video_id}'

    context = {
        'titulo': titulo,
        'descripcion': descripcion,
        'youtube_embed_url': youtube_embed_url,
        'youtube_watch_url': youtube_watch_url,
        'video_error': video_error,
    }

    return render(request, 'tolerances/video_tolerancias absolutas.html', context)
