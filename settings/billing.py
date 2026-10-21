from .dev import *  # noqa: F403

INSTALLED_APPS.insert(INSTALLED_APPS.index('juntagrico'), 'juntagrico_billing')  # noqa: F405

ROOT_URLCONF = 'urls.billing'
