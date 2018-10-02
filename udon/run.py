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
import atexit
import errno
import fcntl
import grp
import os
import pwd
import signal
import socket
import sys
import time

try:
    from setproctitle import setproctitle
except ImportError:
    def setproctitle(name):
        pass

def _mkdir_p(*path):
    try:
        os.makedirs(os.path.join(*path))
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

def gethostname():
    name = socket.gethostname()
    if '.' not in name:
        name = socket.getaddrinfo(name, 0, 0, 0, 0, socket.AI_CANONNAME)[0][3]
    return name


def _drop_priv(username):
    pw = pwd.getpwnam(username)
    groups = list(set([ g.gr_gid for g in grp.getgrall()
                        if pw.pw_name in g.gr_mem ] + [ pw.pw_gid]))
    os.setgroups(groups)
    os.setresgid(pw.pw_gid, pw.pw_gid, pw.pw_gid)
    os.setresuid(pw.pw_uid, pw.pw_uid, pw.pw_uid)


def kill(pidfile, signum = signal.SIGKILL):
    """
    Send a signal to the given app process.
    """
    try:
        pid = int(open(pidfile).read().strip())
    except FileNotFoundError:
        return False
    os.kill(pid, signum)
    return True


_HAS_EXLOCK = hasattr(os, "O_EXLOCK")
def _wopenpidfile(pidfile):
    if _HAS_EXLOCK:
        return os.open(pidfile, os.O_CREAT | os.O_TRUNC | os.O_EXLOCK | os.O_WRONLY | os.O_NONBLOCK | os.O_CLOEXEC)

    fd = os.open(pidfile, os.O_CREAT | os.O_WRONLY | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except:
        os.close(fd)
        raise
    os.ftruncate(fd, 0)
    os.lseek(fd, 0, os.SEEK_SET)
    return fd

def _ropenpidfile(pidfile):
    if _HAS_EXLOCK:
        return os.open(pidfile, os.O_EXLOCK | os.O_WRONLY | os.O_NONBLOCK)

    fd = os.open(pidfile, os.O_WRONLY | os.O_NONBLOCK)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except:
        os.close(fd)
        raise
    fcntl.flock(fd, fcntl.LOCK_UN)
    return fd

def wait(pidfile, delay = 30):
    """
    Wait for the given app process to terminate.
    """
    t0 = time.time()
    while time.time() - t0 < delay:
        try:
            fd = _ropenpidfile(pidfile)
            os.close(fd)
            return
        except BlockingIOError:
            pass
        except FileNotFoundError:
            return
        except:
            raise
        time.sleep(.2)
    raise TimeoutError("Process is still running")


def daemon(pidfile = None):
    """
    Run as daemon.
    """

    # If necessary, get an exclusive lock on the pid file,
    # to make sure it is not running already.
    if pidfile:
        pidfd = _wopenpidfile(pidfile)
        os.write(pidfd, ("%d\n" % os.getpid()).encode())

    # Now fork twice, and create a new session.
    if os.fork() > 0:
        os._exit(0)
    os.setsid()
    if os.fork() > 0:
        os._exit(0)

    # Rewrite the content of the pidfile with the new pid.
    if pidfile:
        os.truncate(pidfd, 0)
        os.lseek(pidfd, 0, os.SEEK_SET)
        os.write(pidfd, ("%d\n" % os.getpid()).encode())
        # Keep pidfd open to hold the lock

    # Set umask
    os.umask(000)

    # Redirect standard io to dev/null
    fd = os.open('/dev/null', os.O_RDWR)
    os.dup2(fd, 0)
    os.dup2(fd, 1)
    os.dup2(fd, 2)
    os.close(fd)

    # Properly exit on SIGTERM
    def _terminate(signum, frame):
        sys.exit(0)
    signal.signal(signal.SIGTERM, _terminate)


def stop(pidfile):
    """
    Send the SIGTERM signal to the given app process if running,
    and wait for the process to stop.
    """
    kill(pidfile, signum = signal.SIGTERM)
