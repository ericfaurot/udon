import getopt
import logging
import sys
import time

import udon.log
import udon.run

pidfile = None

opts, args = getopt.getopt(sys.argv[1:], "p:")
for opt, arg in opts:
    if opt == '-p':
        pidfile = arg

if args:
    if args[0] == 'stop':
        udon.run.stop(pidfile)
    elif args[0] == 'kill':
        udon.run.kill(pidfile)
else:
    udon.log.init(foreground = False, level = "DEBUG")
    udon.run.daemon(pidfile)

    logging.info("starting")
    for i in range(20):
        logging.info("%d...", i)
        time.sleep(1)
    logging.info("done")
