# juntagrico-contribution

[![image](https://github.com/juntagrico/juntagrico-contribution/actions/workflows/juntagrico-ci.yml/badge.svg?branch=main&event=push)](https://github.com/juntagrico/juntagrico-contribution/actions/workflows/juntagrico-ci.yml)
[![Maintainability](https://qlty.sh/gh/juntagrico/projects/juntagrico-contribution/maintainability.svg)](https://qlty.sh/gh/juntagrico/projects/juntagrico-contribution)
[![Code Coverage](https://qlty.sh/gh/juntagrico/projects/juntagrico-contribution/coverage.svg)](https://qlty.sh/gh/juntagrico/projects/juntagrico-contribution)
[![image](https://img.shields.io/github/last-commit/juntagrico/juntagrico-contribution.svg)](https://github.com/juntagrico/juntagrico-contribution)
[![image](https://img.shields.io/github/commit-activity/y/juntagrico/juntagrico-contribution)](https://github.com/juntagrico/juntagrico-contribution)

Run contribution rounds (Beitragsrunden) with juntagrico

This is an extension for juntagrico. You can find more information about juntagrico here
(https://github.com/juntagrico/juntagrico)

## Features

* Run Contribution Rounds (Beitragsrunden) with or without predefined options.
* Transfer the contributions to bill in juntagrico-billing

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
