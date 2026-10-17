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

from command import ics_command, Command

import game
import user

def follow_user(conn, u2):
    """Follow the given user (see all of their games).  Shared by the
    'follow <name>' and 'pfollow' commands."""
    if u2 == conn.user:
        conn.write(_("You can't follow your own games.\n"))
        return
    u = conn.user
    # FICS labels a follow of your bughouse partner "<self>'s partner"
    # rather than the partner's name; this label is also what private
    # handling uses to exempt the follow from private=1.
    label = ("%s's partner" % u.name
        if (u.session.partner and u2 == u.session.partner) else u2.name)
    if conn.user.session.following:
        if u2 == conn.user.session.following:
            conn.write(_("You are already following %s's games.\n")
                % u2.name)
            return
        conn.user.write(_("You will no longer be following %s's games.\n")
            % conn.user.session.following.name)
        conn.user.session.following.session.followed_by.remove(conn.user)
        conn.user.session.following = None
    conn.write(_("You will now be following %s.\n") % label)
    conn.user.session.following = u2
    u2.session.followed_by.add(conn.user)

    # If there is a game in progress and we are not already
    # observing it, start observing it.
    if (u2.session.game and
            u2.session.game not in conn.user.session.observed):
        u2.session.game.observe(conn.user)
        assert(u2.session.game in conn.user.session.observed)

@ics_command('observe', 'i')
class Observe(Command):
    def run(self, args, conn):
        if args[0] in ['/l', '/b', '/s', '/S', '/w', '/z', '/B', '/L', '/x']:
            conn.write('TODO: observe flag\n')
            return
        g = game.from_name_or_number(args[0], conn)
        if g:
            if g in conn.user.session.observed:
                conn.write(_('You are already observing game %d.\n' % g.number))
            elif conn.user in g.players:
                conn.write(_('You cannot observe yourself.\n'))
            else:
                assert(conn.user not in g.observers)
                g.observe(conn.user)

@ics_command('pobserve', 'o', aliases=['pobs'])
class Pobserve(Command):
    def run(self, args, conn):
        # optional argument: a player name.  Standalone targets self.
        if args[0] is None:
            g = conn.user.session.game
            if not g:
                conn.write(_('You are not playing a game.\n'))
                return
            if not g.bug_link:
                conn.write(_('Your game is not linked to a partner game.\n'))
                return
        else:
            target = user.find_by_name_exact_for_user(args[0], conn,
                online_only=True)
            if target is None:
                return
            g = target.session.game
            if not g:
                conn.write(_('%s is not playing a game.\n') % args[0])
                return
            if not g.bug_link:
                conn.write(_('That game is not linked to a partner game.\n'))
                return
        pgame = g.bug_link
        if conn.user in pgame.observers:
            conn.write(_('You are already observing game %d.\n') % pgame.number)
        elif conn.user in pgame.players:
            conn.write(_('You are a player in that game, so you cannot observe it.\n'))
        else:
            pgame.observe(conn.user)

    def usage(self, conn):
        conn.write(_('Usage: pobserve [name]\n')
            + _('  Observe the partner board (bug_link) of a bughouse game.\n')
            + _('  With no argument, uses the game you are playing;\n')
            + _('  with a name, uses that player\'s game.\n'))

@ics_command('follow', 'o')
class Follow(Command):
    def run(self, args, conn):
        if args[0] is None:
            uf = conn.user.session.following
            if not uf:
                conn.write(_("You are not following any player's games.\n"))
            else:
                assert(uf.is_online)
                uf.session.followed_by.remove(conn.user)
                conn.user.session.following = None
                conn.write(_("You will not follow any player's games.\n"))
        else:
            u2 = user.find_by_prefix_for_user(args[0], conn,
                online_only=True)
            if u2:
                follow_user(conn, u2)

@ics_command('pfollow', 'o')
class Pfollow(Command):
    def run(self, args, conn):
        # optional argument: a player name.  Standalone targets self;
        # with a name, follows that player's partner.
        if args[0] is None:
            u = conn.user
        else:
            u = user.find_by_prefix_for_user(args[0], conn,
                online_only=True)
            if u is None:
                return
        u2 = u.session.partner
        if not u2:
            if args[0] is None:
                conn.write(_('You have no partner.\n'))
            else:
                conn.write(_('%s has no partner.\n') % u.name)
            return
        if not u2.is_online:
            conn.write(_('%s is not online.\n') % u2.name)
            return
        follow_user(conn, u2)

    def usage(self, conn):
        conn.write(_('Usage: pfollow [name]\n')
            + _('  With no argument, follow your own bughouse partner\'s games;\n')
            + _('  with a name, follow that player\'s partner.\n'))

@ics_command('allobservers', 'o')
class Allobservers(Command):
    def run(self, args, conn):
        count = 0
        if args[0] is not None:
            g = game.from_name_or_number(args[0], conn)
            if g:
                if g.allobservers(conn):
                    count = 1
                else:
                    conn.write(_('No one is observing game %d.\n')
                        % g.number)
        else:
            for g in game.games.itervalues():
                if g.allobservers(conn):
                    count += 1

        if count > 0:
            conn.write(ngettext(
                '  %(count)d game displayed (of %(total)d in progress).\n',
                '  %(count)d games displayed (of %(total)d in progress).\n',
                    count) % {'count': count, 'total': len(game.games)})

@ics_command('unobserve', 'n')
class Unobserve(Command):
    def run(self, args, conn):
        if args[0] is not None:
            g = game.from_name_or_number(args[0], conn)
            if g:
                if g in conn.user.session.observed:
                    g.unobserve(conn.user)
                else:
                    conn.write(_('You are not observing game %d.\n')
                        % g.number)
        else:
            if not conn.user.session.observed:
                conn.write(_('You are not observing any games.\n'))
            else:
                for g in conn.user.session.observed.copy():
                    g.unobserve(conn.user)
                assert(not conn.user.session.observed)

@ics_command('primary', 'n')
class Primary(Command):
    def run(self, args, conn):
        if args[0] is None:
            if not conn.user.session.observed:
                conn.write(_('You are not observing any games.\n'))
            else:
                conn.write('TODO: primary no param\n')
        else:
            g = game.from_name_or_number(args[0], conn)
            if g:
                if g in conn.user.session.observed:
                    if g == conn.user.session.observed.primary():
                        conn.write(_('Game %d is already your primary game.\n') %
                            g.number)
                    else:
                        conn.user.session.observed.make_primary(g)
                        conn.write(_('Game %d is now your primary game.\n') %
                            g.number)

                else:
                    conn.write('You are not observing game %d.\n' % g.number)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
