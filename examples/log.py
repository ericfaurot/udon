import getopt
import logging
import sys
import time

import udon.log

procname = None
foreground = False
logfile = None

opts, args = getopt.getopt(sys.argv[1:], "-df:p:")
for opt, arg in opts:
    if opt == '-d':
        foreground = True
    elif opt == '-f':
        logfile = arg
    elif opt == '-p':
        procname = arg


udon.log.init(procname = procname,
              foreground = foreground,
              logfile = logfile,
              level = "DEBUG")

logging.info("starting")

for i in range(10):
    logging.info("%d...", i)
    time.sleep(1)

logging.info("done")
