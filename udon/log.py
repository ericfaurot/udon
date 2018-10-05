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


def init(procname = None,
         foreground = False,
         level = "INFO",
         logfile = None,
         logfile_maxcount = 10,
         logfile_maxsize = 10 * 1024 * 1024,
         facility = "user"):

    if procname is None:
        procname = sys.argv[0]

    if foreground:
        # Log to stdout
        formatter = logging.Formatter(fmt = " ".join(["%(asctime)s",
                                                      "%s[%%(process)s]:" % procname,
                                                      "%(levelname)s:",
                                                      "%(name)s:",
                                                      "%(message)s"]),
                                      datefmt = "%Y-%m-%d %H:%M:%S")
        handler = logging.StreamHandler(stream = sys.stdout)

    elif logfile:
        # Log to file.
        formatter = logging.Formatter(fmt = " ".join(["%(asctime)s",
                                                      "%s[%%(process)s]:" % procname,
                                                      "%(levelname)s:",
                                                      "%(name)s:",
                                                      "%(message)s"]),
                                      datefmt = "%Y-%m-%d %H:%M:%S")
        handler = logging.handlers.RotatingFileHandler(logfile,
                                                       maxBytes = logfile_maxsize,
                                                       backupCount = logfile_maxcount)

    else:
        # Log to syslog.
        formatter = logging.Formatter(fmt = " ".join(["%s[%%(process)s]:" % procname,
                                                      "%(levelname)s:",
                                                      "%(name)s:",
                                                      "%(message)s"]),
                                      datefmt = "%Y-%m-%d %H:%M:%S")
        handler = logging.handlers.SysLogHandler("/dev/log" if os.path.exists("/dev/log") else "/var/run/syslog",
                                                 facility = facility)

    handler.setLevel(level)
    handler.setFormatter(formatter)
    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(level)


def fmt_traceback(exc_info):
    exc_type, exc_value, exc_traceback = exc_info
    return "".join(traceback.format_exception(exc_type,
                                              exc_value,
                                              exc_traceback))
