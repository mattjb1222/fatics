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

legal_chars_re = re.compile(rb'''^[\x20-\xfd]*$''')
def check_user_utf8(s):
    # input is already-decoded text; re-encode to bytes to preserve the
    # original byte-level checks (no control chars, no 0x7f, valid UTF-8)
    if isinstance(s, str) and '\ufffd' in s:
        # a replacement character means the original line contained
        # invalid (e.g. raw 0xff) bytes, like python 2 would have seen
        return False
    try:
        if isinstance(s, bytes):
            b = s
        else:
            b = s.encode('utf-8')
    except UnicodeEncodeError:
        return False
    ret = legal_chars_re.match(b)
    if ret:
        try:
            b.decode('utf-8')
        except UnicodeDecodeError:
            ret = False
    return ret

illegal_char_re = re.compile(rb'''[^\x20-\xfd]''')
def utf8_to_ascii(s):
    """ Try to gracefully convert UTF-8 to ASCII.  Non-ASCII chars are
    replaced by '?'. Input/output are bytes. """
    if isinstance(s, str):
        s = s.encode('utf-8')
    try:
        return s.decode('utf-8').encode('ascii', 'replace')
    except UnicodeDecodeError:
        return re.sub(illegal_char_re, b'?', s)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
