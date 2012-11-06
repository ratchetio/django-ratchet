django-ratchet - Django notifier for Ratchet.io_
================================================

django-ratchet is a simple middleware for reporting errors from Django apps to Ratchet.io_.


Requirements
------------
django-ratchet requires:

- Python 2.6 or 2.7
- Django 1.4+
- requests 0.13.1+
- a Ratchet.io_ account


Installation
------------
Install using pip::
    
    pip install django-ratchet


Configuration
-------------
Basic configuration requires two changes in your ``settings.py``.

1. Add ``'django_ratchet.middleware.RatchetNotifierMiddleware'`` as the last item in ``MIDDLEWARE_CLASSES``::

        MIDDLEWARE_CLASSES = (
            # ... other middleware classes ...
            'django_ratchet.middleware.RatchetNotifierMiddleware',
        )

2. Add the ``RATCHET`` settings dictionary somewhere in ``settings.py``. The bare minimum is::

    RATCHET = {
        'access_token': '32charactertokengoeshere',
    }
    

  Most users will want a few extra settings to take advantage of more features::

    RATCHET = {
        'access_token': '32charactertokengoeshere',
        'environment': 'production',
        'branch': 'master',
        'root': '/absolute/path/to/code/root',
    }

Here's the full list of configuration variables:

access_token
    Access token from your Ratchet.io project
environment
    Environment name. Any string up to 255 chars is OK. For best results, use "production" for your production environment.
    
    **default:** ``development`` if ``settings.DEBUG`` is ``True``, ``production`` otherwise
handler
    One of:

    - blocking -- runs in main thread
    - thread -- spawns a new thread
    - agent -- writes messages to a log file for consumption by ratchet-agent_

    **default:** ``thread``
timeout
    Request timeout (in seconds) when posting to Ratchet.
    
    **default:** ``1``
root
    Absolute path to the root of your application, not including the final ``/``. If your ``manage.py`` is in ``/home/brian/www/coolapp/manage.py``, then this should be set to ``/home/brian/www/coolapp`` . Required for Github integration.
branch
    Name of the checked-out branch. Required for Github integration.
agent.log_file
    If ``handler`` is ``agent``, the path to the log file. Filename must end in ``.ratchet``
endpoint
    URL items are posted to.
    
    **default:** ``https://submit.ratchet.io/api/1/item/``
web_base
    Base URL of the Ratchet.io web interface. Used for "view in ratchet.io" links.

    **default:** ``https://ratchet.io``
patch_debugview
    If True, django.views.debug will be patched to show a "View in Ratchet.io" link on technical 500 debug error pages.

    **default:** ``True``


Contributing
------------

Contributions are welcome. The project is hosted on github at http://github.com/ratchetio/django-ratchet


Additional Help
---------------
If you have any questions, feedback, etc., drop us a line at support@ratchet.io


.. _Ratchet.io: http://ratchet.io/
.. _ratchet-agent: http://github.com/ratchetio/ratchet-agent
