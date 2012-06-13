"""
The django-ratchet middleware
"""

import json
import logging
import socket
import sys
import time
import traceback

import requests

from django.core.exceptions import MiddlewareNotUsed
from django.conf import settings

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


DEFAULTS = {
    #'endpoint': 'http://submit.ratchet.io/api/item/',
    'endpoint': 'http://localhost:6943/api/item/',
    'timeout': 1,
    'notify_while_debug': False,
    'environment': lambda: 'development' if settings.DEBUG else 'production',
}


def _extract_user_ip(request):
    # some common things passed by load balancers... will need more of these.
    real_ip = request.environ.get('HTTP_X_REAL_IP')
    if real_ip:
        return real_ip
    forwarded_for = request.environ.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for
    return request.environ['REMOTE_ADDR']
 

class RatchetNotifierMiddleware(object):
    def __init__(self):
        self.settings = getattr(settings, 'RATCHET', {})
        if not self.settings.get('access_token'):
            raise MiddlewareNotUsed
        
        if settings.DEBUG and not self._get_setting('notify_while_debug'):
            raise MiddlewareNotUsed
        
        self.endpoint = self._get_setting('endpoint')
        self.timeout = self._get_setting('timeout')

        self.server_host = socket.gethostname()
        self.server_environment = self._get_setting('environment')
        self.server_branch = self._get_setting('branch')
        self.server_root = self._get_setting('root')
        self.server_github_account = self._get_setting('github.account')
        self.server_github_repo = self._get_setting('github.repo')

    def _get_setting(self, name, default=None):
        try:
            return self.settings[name]
        except KeyError:
            if name in DEFAULTS:
                default_val = DEFAULTS[name]
                if callable(default_val):
                    return default_val()
                return default_val
            return default

    def process_response(self, request, response):
        return response

    def process_exception(self, request, exc):
        """
        Process an exception
        (Wrapper around _process_exception)

        Send it to Ratchet, and return None to fall back to django's normal exception handling.
        """
        try:
            self._process_exception(request, exc)
        except:
            log.exception("Error while reporting exception to ratchet.")
        return None

    def _process_exception(self, request, exc):
        payload = {}
        payload['access_token'] = self.settings['access_token']
        payload['timestamp'] = int(time.time())

        cls, exc, trace = sys.exc_info()
        payload['body'] = "".join(traceback.format_exception(cls, exc, trace))

        params = {}
        params['request.url'] = request.build_absolute_uri()
        params['request.method'] = request.method
        params['request.GET'] = dict(request.GET)
        params['request.POST'] = dict(request.POST)

        # expand headers
        for k, v in request.environ.iteritems():
            if k.startswith('HTTP_'):
                header_name = '-'.join(k[len('HTTP_'):].replace('_', ' ').title().split(' '))
                params['request.headers.%s' % header_name] = v
        params['request.user_ip'] = _extract_user_ip(request)
        params['server.host'] = self.server_host
        params['server.environment'] = self.server_environment
        params['server.branch'] = self.server_branch
        params['server.root'] = self.server_root
        params['server.github.account'] = self.server_github_account
        params['server.github.repo'] = self.server_github_repo
        params['server.language'] = 'python'
        params['notifier.name'] = 'django_ratchet'
        
        payload['params'] = json.dumps(params)

        requests.post(self.endpoint, data=payload, timeout=self.timeout)
