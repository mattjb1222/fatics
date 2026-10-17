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

            print('match %r' % move_num_re.match(s, i))
            raise PgnError('unrecognized sytax in pgn: "%s", i %d' % (s[i:i+15], i))

    def __str__(self):
        return '%s vs. %s and %s vs. %s' % (self.tags['WhiteA'],
            self.tags['BlackA'], self.tags['WhiteB'], self.tags['BlackB'])


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
    movetext = (h.get('movetext') or '').split(' ')
    movetext = [m for m in movetext if m]

    mt_raw = h.get('move_times')
    if isinstance(mt_raw, str):
        move_times = mt_raw.split(' ')
    elif mt_raw:
        move_times = list(mt_raw)
    else:
        move_times = []

    color = h.get('color_char')
    ur = h.get('user_rating') or 0
    orr = h.get('opp_rating') or 0
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
    time_min = h.get('time') or 0
    inc = h.get('inc') or 0
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

    mt = []
    for i, mv in enumerate(movetext):
        if i % 2 == 0:
            mt.append('%d. ' % (i // 2 + 1))
        mt.append(mv)
        if i < len(move_times) and move_times[i]:
            mt.append(' {%s}' % move_times[i])
        mt.append(' ')
    out.append(''.join(mt))
    out.append(result)

    return '\n'.join(out) + '\n'


# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
