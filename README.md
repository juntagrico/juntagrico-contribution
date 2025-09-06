# juntagrico-contribution

[![image](https://github.com/juntagrico/juntagrico-contribution/actions/workflows/juntagrico-ci.yml/badge.svg?branch=main&event=push)](https://github.com/juntagrico/juntagrico-contribution/actions/workflows/juntagrico-ci.yml)
[![Maintainability](https://api.codeclimate.com/v1/badges/4e1874454ccc91505707/maintainability)](https://codeclimate.com/github/juntagrico/juntagrico-contribution/maintainability)
[![Test Coverage](https://api.codeclimate.com/v1/badges/4e1874454ccc91505707/test_coverage)](https://codeclimate.com/github/juntagrico/juntagrico-contribution/test_coverage)
[![image](https://img.shields.io/github/last-commit/juntagrico/juntagrico-contribution.svg)](https://github.com/juntagrico/juntagrico-contribution)
[![image](https://img.shields.io/github/commit-activity/y/juntagrico/juntagrico-contribution)](https://github.com/juntagrico/juntagrico-contribution)

Run contribution rounds (Beitragsrunden) with juntagrico

This is an extension for juntagrico. You can find more information about juntagrico here
(https://github.com/juntagrico/juntagrico)

## Features

* ...

## Installation


Install juntagrico-contribution via `pip`

    $ pip install juntagrico-contribution

or add it in your projects `requirements.txt`

In `settings.py` add `'juntagrico_contribution',`, **above** `'juntagrico''`.

```python
INSTALLED_APPS = [
    ...
    'juntagrico_contribution',
    'juntagrico',
]
```

In your `urls.py` you also need to extend the pattern:

```python
urlpatterns = [
    ...
    path('jcr/', include('juntagrico_contribution.urls')),
]
```
