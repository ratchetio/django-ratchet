django_ratchet - Django notifier for [Ratchet.io](http://ratchet.io)
====================================================================

django_ratchet is a simple middleware for reporting errors from Django apps to [Ratchet.io](http://ratchet.io).


Requirements
------------
django_ratchet requires:

- Python 2.6 or 2.7
- Django 1.4+
- requests 0.13.1+
- a [Ratchet.io](http://ratchet.io) account


Installation
------------
abcdefg


Configuration
-------------
Basic configuration requires two changes in your `settings.py`.

1. Add `'django_ratchet.middleware.RatchetNotifierMiddleware'` as the last item in `MIDDLEWARE_CLASSES`:
    
        MIDDLEWARE_CLASSES = (
            # ... other middleware classes ...
            'django_ratchet.middleware.RatchetNotifierMiddleware',
        )

2. Add the `RATCHET` settings dictionary somewhere in `settings.py`. The bare minimum is:
    
        RATCHET = {
            'access_token': '32charactertokengoeshere',
        }

    Most users will want a few extra settings to take advantage of more features:
    
        RATCHET = {
            'access_token': '32charactertokengoeshere',
            'github.user': 'brianr',
            'github.repo': 'django_ratchet',
            'branch': 'master',
            'root': '/absolute/path/to/code/root',
        }

Here's the full list of configuration variables:

<dl class="dl-horizontal">
  <dt>access_token</dt>
    <dd>Access token from your Ratchet.io project</dd>
  <dt>endpoint</dt>
    <dd>URL items are posted to.<br>
        <b>default:</b> <code>http://submit.ratchet.io/api/item/</code>
    </dd>
  <dt>handler</dt>
    <dd>Currently only one choice, <code>blocking</code>.<br>
        <b>default:</b> <code>blocking</code>
    </dd>
  <dt>timeout</dt>
    <dd>Request timeout (in seconds) when posting to Ratchet.<br>
        <b>default:</b> <code>1</code>
    </dd>
  <dt>environment</dt>
    <dd>Environment name; should be <code>production</code>, <code>staging</code>, or <code>development</code><br>
        <b>default:</b> <code>development</code> if settings.DEBUG is True, <code>production</code> otherwise
    </dd>
  <dt>root</dt>
    <dd>Absolute path to the root of your application, not including the final <code>/</code>. If your manage.py is in <code>/home/brian/www/coolapp/manage.py</code>, then this should be set to <code>/home/brian/www/coolapp</code> . Required for Github integration.</dd>
  <dt>github.user</dt>
    <dd>Github username for your github repo. Required for Github integration.</dd>
  <dt>github.repo</dt>
    <dd>Github repo name. Required for Github integration.</dd>
  <dt>branch</dt>
    <dd>Name of the checked-out branch. Required for Github integration.</dd>
</dl>


Caveats
-------
There is currently only one handler, 'blocking', which makes and blocks on an HTTP POST to report each error. More handlers are coming soon (or fork and write your own).
