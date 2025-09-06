from django import template
register = template.Library()


@register.filter
def percent(value, total):
    return value / total * 100
