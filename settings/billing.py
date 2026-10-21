from .dev import *  # noqa: F401

INSTALLED_APPS.insert(INSTALLED_APPS.index('juntagrico'), 'juntagrico_billing')

ROOT_URLCONF = 'urls.billing'
