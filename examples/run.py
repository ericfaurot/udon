import time
import getopt
import sys

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
    udon.log.init()
    udon.run.daemon(pidfile)

    udon.log.info("starting %s", udon.log.procname())
    for i in range(20):
        udon.log.info("%d...", i)
        time.sleep(1)
    udon.log.info("done")
