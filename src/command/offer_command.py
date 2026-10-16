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

from command import *

def pick_offer(offers, arg, who):
    """Select an offer by 1-based index ("accept n") or by the
    other player's name ("accept <name>", as sent by clients such
    as icsdroneng). 'who' is 'a' for received offers, 'b' for sent."""
    if arg.isdigit():
        i = int(arg)
        if 1 <= i <= len(offers):
            return offers[i - 1]
        return None
    for of in offers:
        if getattr(of, who).name.lower() == arg.lower():
            return of
    return None

@ics_command('accept', 'n', admin.Level.user)
class Accept(Command):
    def run(self, args, conn):
        if not conn.user.session.offers_received:
            # original FICS uses "There are no offers to accept."
            conn.write(_('You have no pending offers from other players.\n'))
            return
        if args[0] is None:
            if len(conn.user.session.offers_received) > 1:
                conn.write(_('You have more than one pending offer. Use "pending" to see them and "accept n" to choose one.\n'))
                return
            conn.user.session.offers_received[0].accept()
        else:
            o = pick_offer(conn.user.session.offers_received, args[0], 'a')
            if o is None:
                conn.write(_('No offer from %s to accept.\n', (args[0],)))
                return
            o.accept()

@ics_command('decline', 'n', admin.Level.user)
class Decline(Command):
    def run(self, args, conn):
        if len(conn.user.session.offers_received) == 0:
            conn.write(_('You have no pending offers from other players.\n'))
            return
        if args[0] is None:
            if len(conn.user.session.offers_received) > 1 and args[0] is None:
                conn.write(_('You have more than one pending offer. Use "pending" to see them and "decline n" to choose one.\n'))
                return
            conn.user.session.offers_received[0].decline()
        else:
            o = pick_offer(conn.user.session.offers_received, args[0], 'a')
            if o is None:
                conn.write(_('No offer from %s to decline.\n', (args[0],)))
                return
            o.decline()

@ics_command('withdraw', 'n', admin.Level.user)
class Withdraw(Command):
    def run(self, args, conn):
        if len(conn.user.session.offers_sent) == 0:
            # original FICS uses "There are no offers to withdraw."
            conn.write(_('You have no pending offers to other players.\n'))
            return
        if args[0] is None:
            if len(conn.user.session.offers_sent) > 1:
                conn.write(_('You have more than one pending offer. Use "pending" to see them and "withdraw n" to choose one.\n'))
                return
            conn.user.session.offers_sent[0].withdraw()
        else:
            o = pick_offer(conn.user.session.offers_sent, args[0], 'b')
            if o is None:
                conn.write(_('No offer to %s to withdraw.\n', (args[0],)))
                return
            o.withdraw()

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
