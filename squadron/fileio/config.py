from ConfigParser import SafeConfigParser, NoSectionError
import sys
import socket
import os
from ..exceptions import UserException
import logging
import logging.handlers

def CONFIG_DEFAULTS():
    return {
        'polltime':'30',
        'keydir':'/etc/squadron/keydir',
        'nodename':socket.getfqdn(),
        'statedir':'/var/squadron',
        'send_status': 'false',
    }

#This is not a func so that we can change it in a test
CONFIG_PATHS = ['/etc/squadron/config',
        '/usr/local/etc/squadron/config',
        os.path.expanduser('~/.squadron/config'),
        ]

def CONFIG_SECTIONS():
    return ['squadron', 'status', 'daemon', 'log']

def VALID_LOG_HANDLERS():
    return ['file', 'stream', 'rotatingfile']

def VALID_STREAMS():
    return ['stdout', 'stderr']


def _get_parser(log, config_file, defaults):
    parser = SafeConfigParser()

    if config_file is None:
        # Try defaults
        parsed_files = parser.read(CONFIG_PATHS)
        log.debug("Using config files: %s", parsed_files)
    else:
        log.debug("Using config file: %s", config_file)
        with open(config_file) as cfile:
            parser.readfp(cfile, config_file)

    return parser

def parse_config(log, config_file = None, defaults = CONFIG_DEFAULTS()):
    """
    Parses a given config file using SafeConfigParser. If the specified
    config_file is None, it searches in the usual places. Returns a
    dictionary of config keys to their values.

    Keyword arguments:
        defaults -- the default global values for the config
        config_file -- the configuration file to read config from. If
            None, searches for system-wide configuration and from
            the local user's configuration.
    """
    parser = _get_parser(log, config_file, defaults)

    if parser.sections():
        log.debug("Original section squadron: %s", parser.items('squadron'))
        result = defaults.copy()
        for section in CONFIG_SECTIONS():
            try:
                result.update(parser.items(section))
            except NoSectionError:
                pass
        return result
    else:
        raise _log_throw(log, 'No config file could be loaded. Make sure at least one of these exists and can be parsed: %s', CONFIG_PATHS)

def parse_log_config(log, config_file):
    parser = _get_parser(log, config_file, {})
    if 'log' in parser.sections():
        PARSED_LOG_CONFIG = True
        for item in parser.items('log'):
            _, value = item

            logline = value.split()
            if len(logline) < 2:
                raise _log_throw(log, 'Invalid log config passed: %s', item)

            #parse level
            level_str = logline[0]
            level = getattr(logging, level_str.upper(), None)
            if not isinstance(level, int):
                raise _log_throw(log, 'Invalid log level passed for: %s', item)

            #parse handler
            handler = logline[1].lower()
            if handler not in VALID_LOG_HANDLERS():
                raise _log_throw(log, 'Invalid log handler passed for: %s', item)

            if handler == 'file':
                if len(logline) < 3:
                    raise _log_throw(log, 'File log handler needs output file as last parameter: %s', item)
                param = logline[2]
                fh = logging.FileHandler(param, 'a', None, False)
                fh.setLevel(level)
                log.addHandler(fh)

            if handler == 'stream':
                if len(logline) < 3:
                    raise _log_throw(log, 'File log handler needs stream such as sys.stderr as last parameter: %s', item)
                param = logline[2].lower()
                if param not in VALID_STREAMS():
                    raise _log_throw(log, 'Invalid stream param passed: %s', item)

                if param == 'stdout':
                    param = sys.stdout
                if param == 'stderr':
                    param = sys.stderr

                sh = logging.StreamHandler(param)
                sh.setLevel(level)
                log.addHandler(sh)
            if handler == 'rotatingfile':
                if len(logline) < 4:
                    raise _log_throw(log, 'Rotating log handler needs a file name, max size and maxCount')

                rh = logging.handlers.RotatingFileHandler(logline[2], 'a', logline[3], logline[4])
                rh.setLevel(level)
                log.addHandler(rh)

def _log_throw(log, error, *args):
    log.error(error, *args)
    raise UserException(error)
