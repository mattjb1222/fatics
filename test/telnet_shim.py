# Copyright (C) 2026  FatICS project
#
# This is a minimal Python 3 backport of the Python 2 telnetlib module,
# providing only the subset of the API used by the FatICS test suite
# (telnetlib was removed from the standard library in Python 3).

import re
import select
import socket

# telnet commands
IP = 244      # interrupt process
AYT = 246     # are you there
EL = 248      # erase line
WILL = 251
WONT = 252
DO = 253
DONT = 254
IAC = 255     # interpret as command

# telnet options
ECHO = 1
SGA = 3

__all__ = ['Telnet', 'IP', 'AYT', 'EL', 'WILL', 'WONT', 'DO', 'DONT', 'IAC',
           'ECHO', 'SGA']

class Telnet(object):
    def __init__(self, host=None, port=None, timeout=None):
        self.timeout = timeout if timeout is not None else 8
        self.sock = socket.create_connection((host, port), self.timeout)
        self._buffer = b''
        self._option_cb = None

    def set_option_negotiation_callback(self, callback):
        self._option_cb = callback

    def fileno(self):
        return self.sock.fileno()

    def close(self):
        self.sock.close()

    def write(self, data):
        if isinstance(data, str):
            data = data.encode('utf-8')
        self.sock.sendall(data)

    # ------------------------------------------------------------------
    # raw reading
    # ------------------------------------------------------------------
    def _recv(self, timeout):
        r, _, _ = select.select([self.sock], [], [], timeout)
        if not r:
            return b''
        data = self.sock.recv(4096)
        if data == b'':
            raise EOFError('socket closed')
        return data

    def _pull(self, data):
        """Pull out IAC sequences (notifying the option callback) and
        return the remaining bytes."""
        out = []
        i = 0
        while i < len(data):
            if (data[i] == IAC and i + 2 < len(data)
                    and data[i + 1] in (WILL, WONT, DO, DONT, IAC)):
                if self._option_cb is not None:
                    self._option_cb(self.sock, data[i + 1], data[i + 2])
                i += 3
            else:
                out.append(data[i:i + 1])
                i += 1
        return b''.join(out)

    def _decode(self, data):
        return self._pull(data).decode('utf-8', 'replace')

    # ------------------------------------------------------------------
    # public API (matches the py2 telnetlib subset used by the tests)
    # ------------------------------------------------------------------
    def read_lazy(self):
        """Return whatever data is currently available (or '')."""
        r, _, _ = select.select([self.sock], [], [], 0)
        if not r:
            return ''
        data = self.sock.recv(4096)
        if data == b'':
            raise EOFError('socket closed')
        return self._decode(data)

    def read_very_eager(self):
        """Read all currently available data, waiting briefly for the
        socket to go quiet so delayed chunks (e.g. a board following a
        game-creation message) are included too."""
        buf = []
        while True:
            r, _, _ = select.select([self.sock], [], [], 0.05)
            if not r:
                break
            data = self.sock.recv(4096)
            if data == b'':
                raise EOFError('socket closed')
            buf.append(self._decode(data))
        return ''.join(buf)

    def read_all(self):
        """Read all data until the connection closes."""
        buf = []
        while True:
            r, _, _ = select.select([self.sock], [], [], None)
            if not r:
                continue
            data = self.sock.recv(4096)
            if data == b'':
                break
            buf.append(self._decode(data))
        return ''.join(buf)

    def read_until(self, matches, timeout=None):
        """Read until 'matches' is seen; return everything read
        (including 'matches').  On timeout, return whatever was
        received so far (like the py2 telnetlib); raise EOFError when
        the connection closes before a match."""
        if timeout is None:
            timeout = self.timeout
        if isinstance(matches, str):
            matches = matches.encode('utf-8')
        buf = self._buffer
        self._buffer = b''
        while True:
            i = buf.find(matches)
            if i >= 0:
                ret = buf[:i + len(matches)]
                self._buffer = buf[i + len(matches):]
                return ret.decode('utf-8', 'replace')
            data = self._recv(timeout)
            if data == b'':
                # timeout: return what we have (py2 telnetlib behavior)
                return buf.decode('utf-8', 'replace')
            buf += self._pull(data)

    def expect(self, patterns, maxpattern=None, interped=None, timeout=None):
        """Read until one of 'patterns' (compiled regexes or strings)
        matches; return (index, match object or None)."""
        if timeout is None:
            timeout = self.timeout
        if isinstance(patterns, (str, type(re.compile('x')))):
            patterns = [patterns]
        if isinstance(patterns[0], str):
            patterns = [re.compile(p) for p in patterns]
        buf = self._buffer
        self._buffer = b''
        while True:
            text = buf.decode('utf-8', 'replace')
            for idx, pat in enumerate(patterns):
                m = pat.search(text)
                if m:
                    self._buffer = buf[m.end():]
                    return (idx, m)
            try:
                data = self._pull(self._recv(timeout))
                if data == b'':
                    # timeout: no match in time
                    if __import__('os').environ.get('SHIM_DEBUG'):
                        print('EXPECT TIMEOUT, buffer was: %r' % buf[:2000])
                    return (None, None)
                buf += data
            except EOFError:
                return (None, None)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent

if __import__('os').environ.get('SHIM_WATCHDOG'):
    import threading, traceback
    def _watchdog():
        import time
        time.sleep(45)
        import sys
        print('SHIM WATCHDOG: dumping stacks')
        for tid, frame in sys._current_frames().items():
            print('\n--- thread', tid)
            traceback.print_stack(frame)
    threading.Thread(target=_watchdog, daemon=True).start()
