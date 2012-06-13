django_ratchet - Django notifier for Ratchet.io
-----------------------------------------------

Configuration:
Add this to MIDDLEWARE_CLASSES in settings.py:
    'django_ratchet.middleware.RatchetNotifierMiddleware',

Add the bare minimum ratchet configuration to settings.py:
    
    RATCHET = {
        'access_token': '32charactertokengoeshere'
    }

Additional config variables:
    endpoint
    timeout
    branch
    environment
    github.account
    github.repo

