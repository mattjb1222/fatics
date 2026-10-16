# Copyright (C) 2010  Wil Mahan <wmahan+fatics@gmail.com>
#
# This file is part of FatICS.
#
# FatICS is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# FatICS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with FatICS.  If not, see <http://www.gnu.org/licenses/>.
#

import re
import subprocess

TIMESEAL_1_PING = '[G]\n'
ZIPSEAL_PING = '[G]\x00'
REPLY = '\x02\x39' # also known as "\x29" or "9"

class Timeseal(object):
    _timeseal_pat = re.compile(r'''^(\d+): (.*)\n$''')
    _zipseal_pat = re.compile(r'''^([0-9a-f]+): (.*)\n$''')
    zipseal_in = 0
    zipseal_out = 0
    _cmds = {
        'timeseal': ['timeseal/openseal_decoder'],
        'zipseal_decoder': ['timeseal/zipseal_decoder'],
        'zipseal_encoder': ['timeseal/zipseal_encoder'],
    }
    def __init__(self):
        self.timeseal = self._spawn('timeseal')
        self.zipseal_decoder = self._spawn('zipseal_decoder')
        self.zipseal_encoder = self._spawn('zipseal_encoder')

    def _spawn(self, name):
        try:
            return subprocess.Popen(self._cmds[name], stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        except Exception as e:
            print('timeseal: failed to spawn %s: %s' % (name, e))
            return None

    def _ensure(self, name):
        """Return the live Popen for name, respawning it if it died."""
        p = getattr(self, name)
        if p is not None and p.poll() is None:
            return p
        print('timeseal: respawning %s' % name)
        p = self._spawn(name)
        setattr(self, name, p)
        return p

    def decode_timeseal(self, line):
        p = self._ensure('timeseal')
        if p is None:
            return (0, line)
        try:
            p.stdin.write(line + '\n')
            dec = p.stdout.readline()
        except (IOError, OSError):
            # process died mid-use; it will be respawned next time.
            # Treat this line as not timeseal-encoded.
            return (0, line)
        m = self._timeseal_pat.match(dec)
        if not m:
            print('timeseal failed to match: {{%r}}' % dec)
            return (-1, None)
        return (int(m.group(1), 10), m.group(2))

    def decode_zipseal(self, line):
        p = self._ensure('zipseal_decoder')
        if p is None:
            return (0, line)
        try:
            p.stdin.write(line + '\n')
            dec = p.stdout.readline()
        except (IOError, OSError):
            return (0, line)
        m = self._zipseal_pat.match(dec)
        if not m or int(m.group(1), 16) == 0:
            print('zipseal failed to match: {{%r}}' % dec)
            return (-1, None)
        return (int(m.group(1), 16), m.group(2))

    def compress_zipseal(self, line):
        p = self._ensure('zipseal_encoder')
        if p is None:
            return None
        try:
            line = line[0:1023] # XXX
            p.stdin.write('%04x%s' % (len(line),line))
            count_str = p.stdout.read(4)
            count = int(count_str, 16)
            ret = p.stdout.read(count)
        except IOError:
            ret = None
        else:
            self.zipseal_in += len(line)
            self.zipseal_out += len(ret)
        return ret

    def print_stats(self):
        return
        if self.zipseal_in > 0:
            print("compression statistics: %d in, %d out, ratio = %.3f" %
                (self.zipseal_in, self.zipseal_out,
                    float(self.zipseal_out) / self.zipseal_in))

timeseal = Timeseal()

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
