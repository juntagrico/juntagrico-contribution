from django import template
register = template.Library()


@register.filter
def percent(value, total):
    if total == 0:
        return 100
    return value / total * 100
