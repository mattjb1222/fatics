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

# At present the parser below is only used for tests; make_pgn() is used
# by the 'showpgn' command to export a stored game as portable PGN.

import re
import copy

# XXX we ignore additional tags on the same line
tag_re = re.compile(r'''\[(\w+)\s+"([^"\n]*?)"\]\s*''')
space_re = re.compile(r'''\s+''')
move_num_re = re.compile(r'''(\d+)([AaBb])\.*''')
move_re = re.compile(r'''([NBRQK]?[a-h1-8x]{2,5}(?:=[NBRQK])?|[PNBRQpnbrq]@[a-h][1-8]|O-O-O|O-O)([+#])?''')
dots_re = re.compile(r'''\.\.\.''')
comment_re = re.compile(r'''\{(.*?)\}''', re.S)
nag_re = re.compile(r'''\$(\d+)''')
result_re = re.compile(r'''(1-0|0-1|1/2-1/2|\*)''')
checkmate_re = re.compile(r'''(\w+)\s+checkmated\s*$''')
#resign_re = re.compile(r'''(\w+)\s+resigns\s*$''')
#partner_won_re = re.compile(r'''(\w+)'s\s+partner\s+won\*$''')
stalemate_re = re.compile(r'''\s+drawn\s+by\s+stalemate\s*$''')
repetition_re = re.compile(r'''\s+drawn\s+by\s+repetition\s*$''')
fifty_re = re.compile(r'''\s+drawn\s+by\s+the\s+50\s+move\s+rule\s*$''')

class PgnError(Exception):
    def __init__(self, reason):
        self.reason = reason
        print(reason)

class BpgnMove(object):
    def __init__(self, text, decorator, char):
        self.text = text
        self.decorator = decorator if decorator is not None else ''
        self.char = char
        self.comments = []

    def add_comment(self, com):
        self.comments.append(com)

class Bpgn(object):
    def __init__(self, f):
        self.f = f

    def __iter__(self):
        skip_blank = True
        line_num = 0
        tags = {}
        in_tag_section = True

        for line in self.f:
            line = line.rstrip('\r\n')
            if skip_blank:
                if line == '' or line[0:6] == '{ FEN ':
                    line_num += 1
                    continue
                else:
                    skip_blank = False

            if in_tag_section:
                if line == '':
                    movetext = []
                    in_tag_section = False
                else:
                    if len(line) > 0 and line[0] == ';':
                        # skip comment
                        line_num += 1
                        continue
                    m = tag_re.match(line)
                    if not m:
                        in_tag_section = False
                        movetext = []
                    else:
                        tags[m.group(1)] = m.group(2).replace(r'\"', '"')

            if not in_tag_section:
                if line == '':
                    # Search for the result to try to handle blank lines
                    # within the movetext.  This doesn't account for
                    # results within user comments, but works for now.
                    movetext_str = '\n'.join(movetext)
                    if not result_re.search(movetext_str):
                        movetext.append(line)
                        line_num += 1
                        continue
                    yield PgnGame(tags, movetext_str)
                    tags.clear()
                    skip_blank = True
                    in_tag_section = True
                else:
                    movetext.append(line)

            line_num += 1

        if len(tags) > 0:
            movetext_str = '\n'.join(movetext)
            yield PgnGame(tags, movetext_str)

        self.f.close()

class PgnGame(object):
    def __init__(self, tags, movetext):
        self.tags = copy.copy(tags)
        self.movetext = movetext
        self.is_checkmate = False
        self.is_stalemate = False
        self.is_repetition = False
        self.is_fifty = False
        #self.is_resign = False
        #self.partner_won = False
        self.initial_comments = []
        assert(movetext)
        self.parse(movetext)
        assert('WhiteA' in self.tags)
        assert('BlackA' in self.tags)
        assert('WhiteB' in self.tags)
        assert('BlackB' in self.tags)

    def parse(self, s):
        """parses moves and their comments"""
        i = 0
        self.moves = []
        move_char = None
        while i < len(s):
            m = space_re.match(s, i)
            if m:
                i = m.end()
                continue

            m = result_re.match(s, i)
            if m:
                self.result = m.group(1)
                i = m.end()
                continue

            # The move_num re should come before the move re because
            # a move cannot start with a number.
            m = move_num_re.match(s, i)
            if m:
                move_char = m.group(2)
                i = m.end()
                continue

            m = dots_re.match(s, i)
            if m:
                i = m.end()
                continue

            m = move_re.match(s, i)
            if m:
                self.moves.append(BpgnMove(m.group(1), m.group(2), move_char))
                i = m.end()
                continue

            m = comment_re.match(s, i)
            if m:
                i = m.end()
                if checkmate_re.search(m.group(1)):
                    self.is_checkmate = True
                    m2 = checkmate_re.search(m.group(1))
                    who = m2.group(1)
                    if who == self.tags['WhiteA']:
                        self.mated = 'A'
                    elif who == self.tags['BlackA']:
                        self.mated = 'a'
                    elif who == self.tags['WhiteB']:
                        self.mated = 'B'
                    elif who == self.tags['BlackB']:
                        self.mated = 'b'
                    else:
                        raise PgnError('unknown player checkmated: %s' % who)
                elif stalemate_re.search(m.group(1)):
                    self.is_stalemate = True
                elif repetition_re.search(m.group(1)):
                    self.is_repetition = True
                elif fifty_re.search(m.group(1)):
                    self.is_fifty = True
                '''elif resign_re.search(m.group(1)):
                    self.is_resign = True
                    m2 = resign_re.search(m.group(1))
                    who = m2.group(1)
                    if who == self.tags['WhiteA']:
                        self.resigned = 'A'
                    elif who == self.tags['BlackA']:
                        self.resigned = 'a'
                    elif who == self.tags['WhiteB']:
                        self.resigned = 'B'
                    elif who == self.tags['BlackB']:
                        self.resigned = 'b'
                    else:
                        raise PgnError('unknown player resigned: %s' % who)
                elif partner_won_re.search(m.group(1)):
                    self.partner_won = True
                    m2 = partner_won_re.search(m.group(1))
                    who = m2.group(1)
                    if who == self.tags['WhiteA']:
                        self.won = 'b'
                    elif who == self.tags['BlackA']:
                        self.won = 'B'
                    elif who == self.tags['WhiteB']:
                        self.won = 'a'
                    elif who == self.tags['BlackB']:
                        self.won = 'A'
                    else:
                        raise PgnError("unknown player's partner won: %s" % who)'''
                if len(self.moves) > 0:
                    self.moves[-1].add_comment(m.group(1))
                else:
                    self.initial_comments.append(m.group(1))
                continue

            m = nag_re.match(s, i)
            if m:
                i = m.end()
                continue

            print(('match %r' % move_num_re.match(s, i)))
            raise PgnError('unrecognized sytax in pgn: "%s", i %d' % (s[i:i+15], i))

    def __str__(self):
        return '%s vs. %s and %s vs. %s' % (self.tags['WhiteA'],
            self.tags['BlackA'], self.tags['WhiteB'], self.tags['BlackB'])


def _split_move_times(mt_raw):
    if isinstance(mt_raw, str):
        return mt_raw.split(' ')
    if mt_raw:
        return list(mt_raw)
    return []


def _make_movetext(moves, times):
    mt = []
    for i, mv in enumerate(moves):
        if i % 2 == 0:
            mt.append('%d. ' % (i // 2 + 1))
        mt.append(mv)
        if i < len(times) and times[i]:
            mt.append(' {%s}' % times[i])
        mt.append(' ')
    return ''.join(mt)


def _elo(v):
    """ A stored rating is char(4): '1234' for rated, '++++' (unrated),
    '0' or None otherwise.  PGN Elo tags are numeric, so only a real
    number is usable; anything else maps to 0 (tag omitted). """
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def make_pgn(h):
    """ Serialize a stored/history game into PGN text.

    ``h`` is a history-entry dict (as produced by ``user_get_history`` /
    ``get_history_game``): it must contain ``movetext``, ``move_times``,
    ``result``, ``time`` (initial minutes), ``inc`` (seconds),
    ``color_char`` ('W'/'B'), ``user_rating``, ``opp_rating``,
    ``opp_name``, and ``when_ended``; ``white_name``/``black_name`` may
    already be present (added by ``get_history_game``).

    FatICS games are single-board / two-player (white vs black), so this
    produces a standard two-player PGN.  Bughouse drops carry over verbatim
    as 'Piece@square' (already present in the movetext), and a '{time}'
    comment is appended after each move from the recorded ``move_times``.  A
    genuine four-board bughouse game (``1A/1B/1a/1b`` streams, as in
    data/bughouse.bpgn) is *not* produced here -- that format only applies
    to externally-imported games, which are passed through unchanged. """
    movetext = [m for m in (h.get('movetext') or '').split(' ') if m]
    move_times = _split_move_times(h.get('move_times'))

    color = h.get('color_char')
    ur = _elo(h.get('user_rating'))
    orr = _elo(h.get('opp_rating'))
    if 'white_name' in h:
        white_name = h['white_name']
        black_name = h['black_name']
    else:
        white_name = h.get('name') if color == 'W' else h.get('opp_name')
        black_name = h.get('opp_name') if color == 'W' else h.get('name')
    if color == 'W':
        white_elos, black_elos = ur, orr
    else:
        white_elos, black_elos = orr, ur

    result = h.get('result') or '*'
    time_min = _elo(h.get('time'))
    inc = _elo(h.get('inc'))
    we = h.get('when_ended')
    date = we.strftime('%Y.%m.%d') if hasattr(we, 'strftime') else '????.??.??'

    out = []
    out.append('[Event "FatICS game"]')
    out.append('[Site "FatICS"]')
    out.append('[Date "%s"]' % date)
    out.append('[White "%s"]' % white_name)
    out.append('[Black "%s"]' % black_name)
    if white_elos:
        out.append('[WhiteElo "%d"]' % white_elos)
    if black_elos:
        out.append('[BlackElo "%d"]' % black_elos)
    out.append('[Result "%s"]' % result)
    out.append('[TimeControl "%d+%d"]' % (time_min, inc))
    out.append('[Annotator "FatICS"]')
    out.append('')

    out.append(_make_movetext(movetext, move_times))
    out.append(result)

    return '\n'.join(out) + '\n'


def make_bughouse_pgn(h, partner):
    """ Serialize a bughouse match (two linked board-games) into a
    two-board PGN.

    ``h`` is this game's history entry; ``partner`` is the partner board's
    game row (as returned by ``db.game_get``: white_name, black_name,
    white_rating, black_rating, movetext, move_times, result, time, inc,
    when_ended).

    FatICS stores a bughouse match as two independent two-player games
    (one board each), linked via the game_partner table.  This emits one
    PGN with the four players (White A/B = the two board whites, Black
    A/B = the two board blacks) and interleaved move streams
    (1a/1A/1b/1B), matching the genuine bpgn layout in data/bughouse.bpgn.
    Drops carry over verbatim as 'Piece@square'; a '{time}' comment
    follows each move. """
    g_moves = [m for m in (h.get('movetext') or '').split(' ') if m]
    g_times = _split_move_times(h.get('move_times'))
    p_moves = [m for m in (partner.get('movetext') or '').split(' ') if m]
    p_times = _split_move_times(partner.get('move_times'))

    white_a, black_a = h['white_name'], h['black_name']
    white_b, black_b = partner['white_name'], partner['black_name']

    color = h.get('color_char')
    ur = _elo(h.get('user_rating'))
    orr = _elo(h.get('opp_rating'))
    if color == 'W':
        white_a_elo, black_a_elo = ur, orr
    else:
        white_a_elo, black_a_elo = orr, ur
    white_b_elo = _elo(partner.get('white_rating'))
    black_b_elo = _elo(partner.get('black_rating'))

    result = h.get('result') or '*'
    time_min = _elo(h.get('time'))
    inc = _elo(h.get('inc'))
    we = h.get('when_ended')
    date = we.strftime('%Y.%m.%d') if hasattr(we, 'strftime') else '????.??.??'

    out = []
    out.append('[Event "Bughouse (two-board)"]')
    out.append('[Site "FatICS"]')
    out.append('[Date "%s"]' % date)
    out.append('[WhiteA "%s"]' % white_a)
    out.append('[BlackA "%s"]' % black_a)
    out.append('[WhiteB "%s"]' % white_b)
    out.append('[BlackB "%s"]' % black_b)
    if white_a_elo:
        out.append('[WhiteAElo "%d"]' % white_a_elo)
    if black_a_elo:
        out.append('[BlackAElo "%d"]' % black_a_elo)
    if white_b_elo:
        out.append('[WhiteBElo "%d"]' % white_b_elo)
    if black_b_elo:
        out.append('[BlackBElo "%d"]' % black_b_elo)
    out.append('[Result "%s"]' % result)
    out.append('[TimeControl "%d+%d"]' % (time_min, inc))
    out.append('[Annotator "FatICS"]')
    out.append('')

    def emit(num, letter, idx, moves, times):
        if idx < len(moves):
            s = '%d%s. %s' % (num, letter, moves[idx])
            if idx < len(times) and times[idx]:
                s += ' {%s}' % times[idx]
            return s + ' '
        return ''

    max_moves = max(len(g_moves), len(p_moves))
    max_num = (max_moves + 1) // 2
    rows = []
    for n in range(1, max_num + 1):
        cells = [
            emit(n, 'a', 2 * (n - 1), g_moves, g_times),
            emit(n, 'A', 2 * (n - 1) + 1, g_moves, g_times),
            emit(n, 'b', 2 * (n - 1), p_moves, p_times),
            emit(n, 'B', 2 * (n - 1) + 1, p_moves, p_times),
        ]
        line = ' '.join(c for c in cells if c)
        if line:
            rows.append(line)
    out.append(' '.join(rows))
    out.append(result)

    return '\n'.join(out) + '\n'


# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
