# -*- coding: utf-8 -*-
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

def hms_words(secs):
    (days, secs) = divmod(secs, 86400)
    (hours, secs) = divmod(secs, 3600)
    (mins, secs) = divmod(secs, 60)
    ret = ''
    if days != 0:
        ret = ret + ngettext("%d day", "%d days", days) % days + " "
    if days != 0 or hours != 0:
        ret = ret + ngettext("%d hour", "%d hours", hours) % hours + " "
    if days != 0 or hours != 0 or mins != 0:
        ret = ret + ngettext("%d minute", "%d minutes", mins) % mins + " "
    ret = ret + ngettext("%d second", "%d seconds", secs) % secs
    return ret

def hms(secs, user=None):
    (hours, secs) = divmod(secs, 3600)
    (mins, secs) = divmod(secs, 60)

    if not user or user.session.ivars['ms']:
        # rounding for display can carry a second, e.g. 59.9999 -> 60.000
        # round to the centisecond for the carry decision, so that
        # 59.999 displays as 1:00.000 rather than 0:59.999
        if round(secs, 2) >= 60:
            r = 0.0
            mins += 1
            if mins >= 60:
                mins -= 60
                hours += 1
        else:
            r = round(secs, 3)
        if hours != 0:
            ret = '%d:%02d:%06.3f' % (hours, mins, r)
        else:
            ret = '%d:%06.3f' % (mins, r)
    else:
        r = int(round(secs))
        if r >= 60:
            r -= 60
            mins += 1
            if mins >= 60:
                mins -= 60
                hours += 1
        if hours != 0:
            ret = '%d:%02d:%02d' % (hours, mins, r)
        else:
            ret = '%d:%02d' % (mins, r)
    return ret

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
