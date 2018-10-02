#
# Copyright (c) 2018 Eric Faurot <eric@faurot.net>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#
import logging
import logging.handlers
import os
import sys
import traceback

_logger = None
_procname = None

def init(procname = None,
         foreground = False,
         level = "INFO",
         logfile = None,
         logfile_maxcount = 10,
         logfile_maxsize = 10 * 1024 * 1024,
         facility = "user"):

    global _logger
    global _procname
    assert _logger is None

    if procname is None:
        procname = sys.argv[0]
    _procname = procname

    if foreground:
        # Log to stderr.
        logging.basicConfig(level = level)
        logger = logging.getLogger(procname)

    else:

        if logfile:
            # Log to file.
            formatter = logging.Formatter(fmt = " ".join(["%(asctime)s",
                                                          "%s[%%(process)s]:" % procname,
                                                          "%(levelname)s:",
                                                          "%(message)s" ]),
                                          datefmt = "%Y-%m-%d %H:%M:%S")
            handler = logging.handlers.RotatingFileHandler(logfile,
                                                           maxBytes = logfile_maxsize,
                                                           backupCount = logfile_maxcount)
        else:
            # Log to syslog.
            formatter = logging.Formatter(fmt = " ".join(["%s[%%(process)s]:" % procname,
                                                          "%(levelname)s:",
                                                          "%(message)s" ]),
                                          datefmt = "%Y-%m-%d %H:%M:%S")
            handler = logging.handlers.SysLogHandler("/dev/log" if os.path.exists("/dev/log") else "/var/run/syslog",
                                                     facility = facility)

        handler.setLevel(level)
        handler.setFormatter(formatter)
        logger = logging.getLogger(procname)
        logger.addHandler(handler)
        logger.setLevel(level)

    _logger = logger

    return logger

def procname():
    return _procname

def debug(*args):
    _logger.debug(*args)

def info(*args):
    _logger.info(*args)

def warn(*args):
    _logger.warn(*args)

def error(*args):
    _logger.error(*args)

def exception(*args):
    try:
        if len(args) > 1:
            msg = args[0] % args[1:]
        elif len(args) == 1:
            msg = args[0]
        else:
            msg = 'EXCEPTION'
    except Exception as exc:
        msg = 'FAILURE IN EXCEPTION LOGGING: %s' % exc
    _logger.critical(msg + "\n" + traceback.format_exc())


def future(future):
    if future.cancelled():
        warn("FUTURE CANCELLED")
    elif future.exception():
        try:
            raise future.exception()
        except:
            exception("FUTURE EXCEPTION")
    else:
        result = future.result()
        if result is not None:
            warn("FUTURE RESULT: %r", result)
