import getopt
import logging
import sys

import udon.log

foreground = True
opts, args = getopt.getopt(sys.argv[1:], "f")
for opt, arg in opts:
    if opt == '-f':
        foreground = False

udon.log.init(foreground = foreground, level = "DEBUG")

try:
    1 / 0
except:
    logging.exception("here...")

try:
    3 / 0
except:
    logging.exception("fail %r", (6, 7))
