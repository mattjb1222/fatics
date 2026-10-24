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

from .command import ics_command, Command

import game

@ics_command('holding', 'n')
class Holding(Command):
    def run(self, args, conn):
        # With no argument, use the game you are playing (the board
        # you are sitting at, i.e. the holding you can drop from);
        # if not playing, the first game you are observing.
        # With a name or number, use that game (e.g. the partner
        # board).
        if args[0] is None:
            g = conn.user.session.game
            if g is None:
                for g2 in conn.user.session.observed:
                    if g2.gtype == game.PLAYED:
                        g = g2
                        break
            if g is None:
                conn.write(_('You are not playing or observing a game.\n'))
                return
        else:
            g = game.from_name_or_number(args[0], conn)
            if g is None:
                return
        if g.speed_variant.variant.name != 'bughouse':
            conn.write(_('That game is not a bughouse game.\n'))
            return
        (holding_white, holding_black) = g.variant.pos.get_holding_str()
        conn.write('holding [%s] [%s]\n' % (holding_white, holding_black))

    def usage(self, conn):
        conn.write(_('Usage: holding [name|number]\n')
            + _('  Prints the current holding (pieces available to drop)\n')
            + _('  of a bughouse game.\n')
            + _('  With no argument, uses the game you are playing\n')
            + _('  (or observing); with a name or number, uses that\n')
            + _('  game (e.g. your partner\'s board).\n'))

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
