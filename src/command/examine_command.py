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

import examine
import bpgn

from .command import *

@ics_command('examine', 'on')
class Examine(Command):
    def run(self, args, conn):
        if conn.user.session.game:
            if conn.user.session.game.gtype == game.EXAMINED:
                conn.write(_("You are already examining a game.\n"))
            else:
                conn.write(_("You are playing a game.\n"))
            return

        if args[0] is None:
            conn.write(_("Starting a game in examine (scratch) mode.\n"))
            examine.ExaminedGame(conn.user)
            return

        if args[0] == 'b':
            conn.write('TODO: EXAMINE SCRATCH BOARD\n')
            return

        u = user.find_by_prefix_for_user(args[0], conn, min_len=2)
        if not u:
            return

        if args[1] is None:
            conn.write('TODO: EXAMINE ADJOURNED GAME\n')
            return

        try:
            num = int(args[1])
            # history game
            h = u.get_history_game(num, conn)
            if h:
                examine.ExaminedGame(conn.user, h)
            return
        except ValueError:
            m = re.match(r'%(\d\d?)', args[1])
            if m:
                num = int(m.group(1))
                conn.write('TODO: EXAMINE JOURNAL GAME\n')
                return

            u2 = user.find_by_prefix_for_user(args[1], conn, min_len=2)
            if not u2:
                return
            conn.write('TODO: EXAMINE ADJOURNED GAME\n')

@ics_command('showpgn', 'on')
class Showpgn(Command):
    """ Send a stored history game to the client as portable PGN text.

    This is the 'text/raw' examination path (as opposed to 'examine', which
    sends a server-rendered single-board board list for XBoard/WinBoard).
    The client decides which it wants by choosing which command to send: a
    single-board GUI uses 'examine <name> <num>', while a text-based or
    bughouse-capable client uses 'showpgn <name> <num>' to get the PGN
    (movetext + move-time comments + drop notation) it can load directly.
    """
    def run(self, args, conn):
        if args[0] is None or args[1] is None:
            conn.write(_("Usage: showpgn <name> <num>\n"))
            return
        u = user.find_by_prefix_for_user(args[0], conn, min_len=2)
        if not u:
            return
        try:
            num = int(args[1])
        except ValueError:
            conn.write(_("Usage: showpgn <name> <num>\n"))
            return
        h = u.get_history_game(num, conn)
        if not h:
            return
        conn.write(_("PGN for game %d:\n\n") % num)
        # If this is a bughouse board with a saved partner board, emit a
        # two-board PGN (four players, interleaved 1a/1A/1b/1B); otherwise
        # a standard single-board two-player PGN.
        partner_id = h.get('partner_game_id')
        if partner_id:
            partner = db.game_get(partner_id)
            if partner:
                conn.write(bpgn.make_bughouse_pgn(h, partner))
                return
        conn.write(bpgn.make_pgn(h))


@ics_command('mexamine', 'w')
class Mexamine(Command):
    def run(self, args, conn):
        g = conn.user.session.game
        if not g or g.gtype != game.EXAMINED:
            conn.write(_("You are not examining a game.\n"))
            return

        u = user.find_by_prefix_for_user(args[0], conn, online_only=True)
        if not u:
            return

        g.mexamine(u, conn)

@ics_command('backward', 'p')
class Backward(Command):
    def run(self, args, conn):
        n = args[0] if args[0] is not None else 1
        g = conn.user.session.game
        if not g or g.gtype != game.EXAMINED:
            conn.write(_("You are not examining a game.\n"))
            return
        g.backward(n, conn)

@ics_command('forward', 'p', admin.Level.user)
class Forward(Command):
    def run(self, args, conn):
        n = args[0] if args[0] is not None else 1
        g = conn.user.session.game
        if not g or g.gtype != game.EXAMINED:
            conn.write(_("You are not examining a game.\n"))
            return
        g.forward(n, conn)

@ics_command('unexamine', '')
class Unexamine(Command):
    def run(self, args, conn):
        g = conn.user.session.game
        if not g or g.gtype != game.EXAMINED:
            conn.write(_("You are not examining a game.\n"))
            return
        g.leave(conn.user)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
