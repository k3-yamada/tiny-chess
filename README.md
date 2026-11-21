# Tiny Chess entry

A chess engine in one file, `main.py` (under 4,096 bytes): a zlib+base85
payload that unpacks to pure standard-library Python.

## Search
- 0x88 board, legal move generation with castling, en passant and promotions.
- Iterative-deepening negamax alpha-beta with a transposition table,
  null-move pruning (skipped in check and when the mover has only king and
  pawns), reverse futility pruning at depth 1-2, late-move reductions and
  MVV-LVA plus history move ordering.
- Quiescence search over captures and promotions, quiet push-promotions
  included; a check at the horizon gets one more full ply first.
- Repetition: positions from the game history and the current search path
  score as a draw, with contempt: if the side to move is ahead by static
  evaluation it gets a quarter of that instead of 0.

## Evaluation
Material, piece-square tables (separate king tables for middlegame and
endgame), doubled and isolated pawn penalties, a rank-scaled passed-pawn
bonus, the bishop pair and rooks on open or half-open files.

## Budget and determinism
Each move searches a fixed 87,000 nodes, a quarter of that from ply 60 on;
a depth cut short keeps its best move so far. A single legal move is played
at once. No clock and no randomness: the same position and history always
give the same move.

## Protocol
Reads `MAKEFUN_ENV_URL`, POSTs `/game` for the game in play and `/move`
with a UCI move until the env answers `done`. It replays `moves` from
`start_fen` for repetition history and searches from `fen`.

MIT licensed; see LICENSE.
