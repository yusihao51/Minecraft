# Imports, sorted alphabetically.

# Python packages
import time
import threading
# Third-party packages
# Nothing for now...

# Modules from this project
import globals as G


__all__ = (
    'performance_info',
)


def performance_info(func):
    def inner(*args, **kwargs):
        if not G.DEBUG:
            return func(*args, **kwargs)
        start = time.time()
        out = func(*args, **kwargs)
        print('%s took %f seconds.' % (func.__name__, time.time() - start))
        return out

    return inner

log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'FATAL']

def log(log_level, msg):
    if log_level >= G.LOG_LEVEL:
        now = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
        thread = '[' + threading.currentThread().getName() + ']'
        level = '[' + log_levels[log_level] + ']'
        print now + ' ' + thread + ' ' + level + ' ' + msg

def log_debug(msg):
    log(G.LOG_DEBUG, msg)

def log_info(msg):
    log(G.LOG_INFO, msg)

def log_warning(msg):
    log(G.LOG_WARNING, msg)

def log_error(msg):
    log(G.LOG_ERROR, msg)

def log_fatal(msg):
    log(G.LOG_FATAL, msg)