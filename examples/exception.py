import getopt
import sys

import udon.log

foreground = True
opts, args = getopt.getopt(sys.argv[1:], "f")
for opt, arg in opts:
    if opt == '-f':
        foreground = False

udon.log.init(foreground = foreground)

try:
    1 / 0
except:
    udon.log.exception("here...")

try:
    3 / 0
except:
    udon.log.exception("fail %s", 6, 7)
