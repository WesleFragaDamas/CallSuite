from django import template
register = template.Library()

@register.filter(name='list_item')
def list_item_filter(list_obj, index):
    try:
        return list_obj[int(index)]
    except: # Pega IndexError, TypeError, ValueError, AttributeError
        return None