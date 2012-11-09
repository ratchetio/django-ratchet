"""
django-ratchet middleware

To install, add the following in your settings.py:
1. add 'django_ratchet.middleware.RatchetNotifierMiddleware' to MIDDLEWARE_CLASSES 
2. add a section like this:
RATCHET = {
    'access_token': 'tokengoeshere',
}

See README.rst for full installation and configuration instructions.
"""

import json
import logging
import socket
import sys
import threading
import time
import traceback
import uuid

import requests

from django.core.exceptions import MiddlewareNotUsed
from django.conf import settings

log = logging.getLogger(__name__)

VERSION = '0.3.2'


DEFAULTS = {
    'endpoint': 'https://submit.ratchet.io/api/1/item/',
    'web_base': 'https://ratchet.io',
    'enabled': True,
    'handler': 'thread',
    'timeout': 1,
    'environment': lambda: 'development' if settings.DEBUG else 'production',
    'agent.log_file': 'log.ratchet',
    'patch_debugview': True
}


def _extract_user_ip(request):
    # some common things passed by load balancers... will need more of these.
    forwarded_for = request.environ.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for
    real_ip = request.environ.get('HTTP_X_REAL_IP')
    if real_ip:
        return real_ip
    return request.environ['REMOTE_ADDR']


def _patch_debugview(ratchet_web_base):
    try:
        from django.views import debug
    except ImportError:
        return
    
    if ratchet_web_base.endswith('/'):
        ratchet_web_base = ratchet_web_base[:-1]
    
    # modify the TECHNICAL_500_TEMPLATE
    new_data = """
{% if view_in_ratchet_url %}
  <h3 style="margin-bottom:15px;"><a href="{{ view_in_ratchet_url }}" target="_blank">View in Ratchet.io</a></h3>
{% endif %}
    """
    insert_before = '<table class="meta">'
    replacement = new_data + insert_before
    debug.TECHNICAL_500_TEMPLATE = debug.TECHNICAL_500_TEMPLATE.replace(insert_before, 
        replacement, 1)

    # patch ExceptionReporter.get_traceback_data
    old_get_traceback_data = debug.ExceptionReporter.get_traceback_data
    def new_get_traceback_data(exception_reporter):
        data = old_get_traceback_data(exception_reporter)
        try:
            item_uuid = exception_reporter.request.META.get('ratchet.uuid')
            if item_uuid:
                url = '%s/item/uuid/?uuid=%s' % (ratchet_web_base, item_uuid)
                data['view_in_ratchet_url'] = url
        except:
            log.exception("Exception while adding view-in-ratchet link to technical_500_template.")
        return data
    debug.ExceptionReporter.get_traceback_data = new_get_traceback_data


class RatchetNotifierMiddleware(object):
    def __init__(self):
        self.settings = getattr(settings, 'RATCHET', {})
        if not self.settings.get('access_token'):
            raise MiddlewareNotUsed

        if not self._get_setting('enabled'):
            raise MiddlewareNotUsed
        
        self.encoder = ErrorIgnoringJSONEncoder()
        self._ensure_log_handler()
        
        # basic settings
        self.endpoint = self._get_setting('endpoint')
        self.timeout = self._get_setting('timeout')
        self.handler_name = self._get_setting('handler')
        try:
            self.handler = getattr(self, '_handler_%s' % self.handler_name)
        except AttributeError:
            self.handler_name = DEFAULTS['handler']
            log.warning("Unknown handler name, defaulting to %s", self.handler_name)
            self.handler = getattr(self, '_handler_%s' % self.handler_name)

        # cache settings/environment variables that won't change across requests
        self.environment = self._get_setting('environment')
        self.server_host = socket.gethostname()
        self.server_branch = self._get_setting('branch')
        self.server_root = self._get_setting('root')

        # special case for 'agent' handler
        if self.handler_name == 'agent':
            self.agent_log = self._create_agent_log()

        # monkeypatch debug module
        if self._get_setting('patch_debugview'):
            _patch_debugview(self._get_setting('web_base'))

    def _ensure_log_handler(self):
        """
        If there's no log configuration, set up a default handler.
        """
        if log.handlers:
            return
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s %(levelname)-5.5s [%(name)s][%(threadName)s] %(message)s')
        handler.setFormatter(formatter)
        log.addHandler(handler)
    
    def _create_agent_log(self):
        log_file = self._get_setting('agent.log_file')
        if not log_file.endswith('.ratchet'):
            log.error("Provided agent log file does not end with .ratchet, which it must. "
                "Using default instead.")
            log_file = DEFAULTS['agent.log_file']
        
        retval = logging.getLogger('ratchet_agent')
        handler = logging.FileHandler(log_file, 'a', 'utf-8')
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        retval.addHandler(handler)
        retval.setLevel(logging.WARNING)
        return retval

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
        except Exception, e:
            log.exception("Error while reporting exception to ratchet.")
        return None

    def _process_exception(self, request, exc):
        payload = self._build_payload(request)
        self.handler(payload)

    def _build_payload(self, request):
        # basic params
        data = {
            'timestamp': int(time.time()),
            'environment': self.environment,
            'level': 'error',
            'language': 'python',
            'framework': 'django',
            'notifier': {
                'name': 'django_ratchet',
                'version': VERSION,
            }
        }

        # uuid
        data['uuid'] = str(uuid.uuid4())
        # save in request.META for later
        request.META['ratchet.uuid'] = data['uuid']

        # exception info
        cls, exc, trace = sys.exc_info()
        # most recent call last
        raw_frames = traceback.extract_tb(trace)
        frames = [{'filename': f[0], 'lineno': f[1], 'method': f[2], 'code': f[3]} 
            for f in raw_frames]
        data['body'] = {
            'trace': {
                'frames': frames,
                'exception': {
                    'class': cls.__name__,
                    'message': str(exc),
                }
            }
        }

        # request data
        data['request'] = {
            'url': request.build_absolute_uri(),
            'method': request.method,
            'GET': dict(request.GET),
            'POST': dict(request.POST),
            'user_ip': _extract_user_ip(request),
        }
        # headers
        headers = {}
        for k, v in request.environ.iteritems():
            if k.startswith('HTTP_'):
                header_name = '-'.join(k[len('HTTP_'):].replace('_', ' ').title().split(' '))
                headers[header_name] = v
        data['request']['headers'] = headers

        # current user
        self._extract_person_data(request, data)

        # server environment
        data['server'] = {
            'host': self.server_host,
        }
        if self.server_root:
            data['server']['root'] = self.server_root
        if self.server_branch:
            data['server']['branch'] = self.server_branch

        # build into final payload
        payload = {
            'access_token': self.settings['access_token'],
            'data': data
        }
        return self.encoder.encode(payload)
    
    def _extract_person_data(self, request, data):
        """
        Try to build the Person data, using request.user
        Assumes a standard-ish use of django.contrib.auth
        """
        def wrapped():
            if not request.user.is_authenticated():
                return
            person = {}
            for prop in ['id', 'username', 'email']:
                try:
                    person[prop] = getattr(request.user, prop, None)
                except:
                    pass
            # save to data, if we have anything at all
            if person:
                data['person'] = person

        try:
            wrapped()
        except:
            log.exception("Exception in _extract_person_data()")

    def _handler_blocking(self, payload):
        """
        Send the payload immediately, and block until the request completes.
        If self.timeout is nonzero, use it as the timeout (in seconds).
        """
        kw = {}
        if self.timeout:
            kw['timeout'] = self.timeout

        resp = requests.post(self.endpoint, data=payload, **kw)
        if resp.status_code != 200:
            log.warning("Got unexpected status code from Ratchet.io api: %s\nResponse:\n%s",
                resp.status_code, resp.text)

    def _handler_thread(self, payload):
        """
        Spawn a new single-use thread to send the payload immediately.
        """
        thread = threading.Thread(target=self._handler_blocking, args=(payload,))
        thread.start()

    def _handler_agent(self, payload):
        """
        Write a the payload to the ratchet-agent log file; ratchet-agent will post it to the server.
        """
        self.agent_log.error(json.dumps(payload))


class ErrorIgnoringJSONEncoder(json.JSONEncoder):
    def __init__(self, **kw):
        kw.setdefault('skipkeys', True)
        super(ErrorIgnoringJSONEncoder, self).__init__(**kw)

    def default(self, o):
        try:
            return repr(o)
        except:
            try:
                return str(o)
            except:
                return "<Unencodable object>"
    
