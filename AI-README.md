# FatICS — Codebase Guide for AI Agents

FatICS is a Python 3 / Twisted Internet Chess Server (ICS) compatible with the
FICS protocol (telnet + Winboard style 12). This file is a map of the codebase
plus the rules of each supported variant. Read this first; then jump to the
file:line anchors.

## Quick operations

- Run/restart server (dev): `./chessd-local restart` (wraps
  `venv3/bin/twistd -r epoll -oy src/chessd.tac`; PID in `chessd.pid`, log in
  `chessd.log`). Ports: 5000 (main), 5001 (zipseal), 5003 (compatibility) —
  `src/config.py`.
- Test suite (e2e over telnet against the *running* server):
  `PYTHONPATH=".:$PWD/test" venv3/bin/trial fat_tests.<module>[.<Class>.<test>]`
  Core modules: `fat_tests.test_bug fat_tests.variant.test_bughouse
  fat_tests.test_ginfo fat_tests.test_match fat_tests.test_style
  fat_tests.test_game`. `fat_tests/` is a symlink to `test/` (git tracks
  `test/...`).
- **Important:** the suite talks to the live server on port 5000 and state
  (logged-in guests) persists between runs. Restart the server with fresh code
  before a suite run; a failed test leaves leaked connections that tearDown
  cleans up, but a stale server is a common source of confusing failures.
- Variant unit tests live in `fat_tests/variant/` (test_bughouse.py is the
  main end-to-end one: guest login → `part` → bughouse match → style-12 wire
  assertions).

## Object model

```
Connection (src/connection.py:47, twisted LineReceiver; login, timeseal sync)
  └─ Session (src/session.py:30; command dispatch, vars, partner, seeks)
       ├─ Session.user → User (src/user.py; db-backed, ratings, settings)
       ├─ Offer / Challenge (src/offer.py, src/match.py:293)
       │    └─ Challenge.accept() → game.PlayedGame  (match.py:586)
       └─ Examine (src/examine.py) → game.ExaminedGame
Game (src/game.py:85) — base: board line rendering, clocks, observers
  └─ PlayedGame (src/game.py:494) — move application, bughouse links,
     next_move(), gameinfo, notifications
```

- `User` settings are ivars (`src/var.py`; `BoolVar`/`IntVar`/`StringVar`
  `.add_as_var()`), read with `user.vars.get('name')`.
- Commands: one module per command in `src/command/` (e.g. `match_command.py`,
  `observe_command.py`, `var_command.py`), dispatched by `src/command/command.py`
  with `src/command_parser.py`. `match` string parsing: `MatchStringParser`
  (`src/match.py:55`) — speed name, variant name/abbrev, side, clock.
- Variant/speed pairing: `src/speed_variant.py` — `SpeedAndVariant`; the
  **name → class registry is `speed_variant.variant_class`** (populated by
  `_init()` at import, `speed_variant.py:98-109`), used by
  `PlayedGame.__init__` (`game.py:546`) and `Examine`.
- Persistence: `src/db.py` (MySQL, see `config.py`); ratings: `src/glicko2.py`,
  `src/rating.py`.
- Time control: `src/timer.py` (game clock driver), `src/clock.py` (clock
  types), `src/timeseal.py` (client clock sync protocol; zipseal =
  encrypted/compressed timeseal, port 5001). Clock types: standard, Fischer
  (+inc), Bronstein (−inc), hourglass, overtime, untimed (`clock.py:122-197`).

## Wire protocol (style 12)

Board lines are the core client contract (Winboard/Thief/icsdrone).
`Game.send_board()` (`game.py:214`) splits the variant's `to_style12()` output
(`variant/base_variant.py:119`) on newlines and writes each line as its own
wire message (batched for all users by `send_boards()`, `game.py:208`):

- `<12>` line: `<12>` + 72-char board (8 ranks × " " + 8 chars, from a8) +
  ` <side> <ep> <w_oo> <w_ooo> <b_oo> <b_ooo> <fifty> <game#> <white name>
  <black name> <w time> <b time> ... <clock/inc fields> <last move>` (see
  `base_variant.py:119-190` for exact field order).
- `<b1>` line (crazyhouse/bughouse only, active non-examined games):
  `<b1> game <N> white [P] black [p] ...` — the **complete** captured-pieces
  holding for that board (`get_b1()` in `variant/bughouse.py:1424` and
  `variant/crazyhouse.py:1365`).
- Plain text lines: `White holding: [...]` / `Black holding: [...]` (same data,
  human-readable; gated by `show_holding`, `base_variant.py:43`).

Clients dispatch lines by prefix. **Thief** (and icsdrone/Sunsetter) treat
`<12>`, `<b1>`, and the holding text lines as separate handlers:
- Thief's `<12>` handler (`FICS_ParseBoard`) also parses the embedded last-move
  string and plays sounds from it (check → check sound). It has **no
  board-line dedup** — a re-sent `<12>` line re-plays sounds.
- Thief's `<b1>` handler (`FICS_ParsePiece` → `BOARD_LoadBuffer`) is
  self-contained: it updates the drop hand with no position/sound side
  effects. Thief builds its bughouse drop hand **exclusively** from the `<b1>`
  field — it has no `holding` text-line handler.
- icsdrone/Sunsetter use the `holding [...]` text line (their only holding
  source) and ignore `<b1>`; icsdrone dedups `<12>` lines itself via board
  hash + move number.

## Variants

Four variants, each a self-contained module in `src/variant/` sharing the
`BaseVariant` interface (`base_variant.py:27`). Each module re-implements the
full position stack (`Position`, `Move`, `Undo`, `PositionHistory`, `Zobrist`,
SAN/lalg/castle/drop move parsers) on the bitboard layout in
`src/game_constants.py`; new code in one variant usually must be mirrored in
the others if it touches shared logic.

### Chess (`variant/chess.py:1183`, name `chess`, abbrev `chess`/normal)
Standard chess. Default when no variant is given (`match.py:245`). Castling
rules per the variant's `move_from_castle`.

### Chess960 (`variant/chess960.py:1309`, name `chess960`, abbrevs `960`, `chess960`)
Fischer Random. King-castling is a **king move to the castling square**
(`move_from_castle` handles `0-0`/`O-O` only when it unambiguously maps;
else the king must move to c/g). FEN: `game.py`/match reject explicit FEN for
960 (`match.py:251`). Otherwise standard rules.

### Crazyhouse (`variant/crazyhouse.py:1321`, name `crazyhouse`, abbrev `czh`)
Standard chess + captures add the piece to the **capturer's** holding (same
board) and the holder may drop it (`P[x]` syntax via `move_from_drop`,
parser at `crazyhouse.py:1137`), tried **before** long algebraic
(`parse_move`, `crazyhouse.py:1323-1345`). Castling requires
the castling king and *rook* to be on the board. Holding is per-player on the
same game; `<b1>` line and holding text lines carry it. Drops and castling
undo/redo are handled by the variant's own `Undo`/`Move`.

### Bughouse (`variant/bughouse.py:1361`, name `bughouse`, abbrev `bug`/`bh`)
The distinctive one: **two linked games, two pairs of players.**

- Setup: players `part` a partner first (commands in `src/command/bug_command.py`,
  state in `session.partner`); `match <opponent> bughouse` requires both sides
  to have partners (`match.py:497-510`). `Challenge.accept()` (`match.py:586`)
  creates the partner's game: `chal2.a = a.partner, chal2.b = b.partner,
  chal2.side = b's side` — note **`side` applies to `chal2.b`**, so the
  partner of the black player is white on the partner board. The two games are
  linked: `g.bug_link = g2; g2.bug_link = g`, and positions linked
  (`g2.variant.pos.bug_link = g.variant.pos`, `match.py:598-601`).
- Rules: captures/drops follow crazyhouse-style holding, **but captures on
  board Y are added to board X's holding** (and vice versa) — via
  `pos.bug_link.add_to_holding()` in the move application
  (`bughouse.py:559-578`; `add_to_holding`/`remove_from_holding` at `:509`/`:522`); players drop from their board's holding (case of the
  piece = its color; white drops uppercase).
- Wire: each board is a normal style-12 board with its own game number; clients
  auto-observe the partner board from the `Your partner is playing game N`
  line (Thief auto-issues `observe N`).
- **Holding refresh on partner-board captures** (`game.py` `next_move`): when a
  move changes the partner board's holding, the partner board's holding is
  refreshed by sending a **bare `<b1>` line** (`Game.send_b1()`), *not* a
  re-send of its board block. Re-sending the board block would re-deliver its
  `<12>` line and make clients like Thief re-play their
  check sound on every partner-board move while the user is checked and not
  moving (see `git log` `02d0a46` and the e2e test
  `test_bughouse_b1_only_on_partner_capture`).
- The human-readable `holding [...]` text lines are **opt-in**: gated on the
  non-persistent ivar `bugholding` (default off, `var.py`) so plain telnet
  clients see the board only; icsdrone/Sunsetter send `set bugholding 1` after
  login. `Game.send_holding_if_changed()` sends a holding text line only when
  the line changed since the last send (dedup in `self._last_holding_line`).
- Examined bughouse games: no partner; the position is linked to itself
  (`self.pos.bug_link = self.pos`, `check_integrity = False`,
  `bughouse.py:1369-1382`) so captures/drops work in review without a second
  board.

## Critical invariants (learned from real bugs — do not break)

1. **Thief's drop hand depends on `<b1>` re-delivery** whenever a partner-board
   capture changes holdings — but the *board block* must not be re-sent (sound
   replay). Keep `send_b1()` (bare line) for holding refreshes; the initial
   `send_boards()` calls at game setup/observation (e.g. `game.py` setup paths)
   are untouched and required.
2. **Holding text lines** (`White holding: [...]`) must keep working for
   clients that opted in via `set bugholding 1` (icsdrone/Sunsetter) — they
   have no `<b1>` handler.
3. **Timeseal clock** (`timeseal.py`, `game.py` clock handling) is clamped and
   defensive against ping/pong desync (commit `a6a2c8b`): never subtract more
   than the clock holds; do not rename the local `move_time` back to `time`
   (it shadows the `time` module and crashed `time.time()`).
4. Bughouse examined games need the self-linked position; played bughouse games
   assert both sessions have partners (`bughouse.py:1369-1373`).
5. `side` in a `Match`/`Challenge` applies to player **a** for the main game
   (and `chal2.b` for the bughouse partner game — `match.py:593-595`).

## Adding a new variant (checklist)

1. Copy `src/variant/chess.py` → `src/variant/<name>.py`; change
   `self.name`, adjust `parse_move` (add parsers in the right order — drops
   before long algebraic), holding/`get_b1` if applicable.
2. Register in `src/speed_variant.py` `_init()` (`variant_class`) + `from_names`
   combos as needed.
3. If it has a holding: extend `show_holding` in `base_variant.py` (both the
   style-12 and style-1 paths) and the `<b1>` gating in `get_b1()` callers.
4. FEN acceptance/`idn` handling in `match.py:251` if the variant forbids FEN.
5. Add wire-format tests in `fat_tests/variant/test_<name>.py` (model on
   `test_bughouse.py`: connect guests via `self.connect_as_guest()`, set style
   12, play real moves, assert on wire lines; use `self.expect` /
   `self.expect_not` — note `expect_not` has a 0.3 s window).
6. Reload module list: `src/reload.py` includes the variant modules if hot
   reload is to pick it up.
