from django import template
import re

register = template.Library()

URL_RE = re.compile(r'^(https?://)', re.IGNORECASE)


@register.filter(name='is_url')
def is_url(s):
    """Check if a string is a URL"""
    return isinstance(s, str) and bool(URL_RE.match(s))


@register.simple_tag
def concat_path(base, project):
    """Concatenate base path and project name"""
    return base + project
