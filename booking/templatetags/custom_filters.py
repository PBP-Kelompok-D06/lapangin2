from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Memungkinkan akses dictionary key di template Django (untuk slots_by_date).
    """
    if dictionary is None:
        return None
    return dictionary.get(key)