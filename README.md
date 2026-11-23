# Tiny Chess entry (Step A)

A chess engine in one file, `main.py` (4,090 bytes, under the 4,096
limit): an lzma (raw LZMA1) + base85 payload that unpacks to pure
standard-library Python (6,892 bytes).

## Search
- 10x12 mailbox board, legal move generation with castling, en passant
  and promotions.
- Iterative deepening negamax alpha-beta with a transposition table.
- Null-move pruning, reverse futility pruning at shallow depths,
  late-move reductions for late quiet moves, killer moves (2 per ply),
  history heuristic and MVV-LVA ordering.
- Quiescence search over captures, promotions and moves attacking the
  king; a check at the horizon gets one more full ply (up to ply 20).
- Mate scores as 30000 minus ply; repetition (game history and search
  path) scores as a draw.

## Evaluation
- Piece-square tables with separate middlegame and endgame values,
  blended by game phase (0-24).
- Bishop-pair bonus, material values and phase tracking from the same
  tables; a small constant tempo term.

## Budget and determinism
- Each move searches a fixed 130,000 nodes (`LIM=130000`). A node
  counter stops the search; the best move found so far is kept. No
  clock and no randomness: the same position and history always give
  the same move.

## Protocol
Reads `MAKEFUN_ENV_URL`, POSTs `/game` for the game in play and `/move`
with a UCI move until the env answers `done`. It replays `moves` from
`start_fen` for repetition history and searches from `fen`.

## Verification (2026-11-23)
The engine was rebuilt in a recorded Claude Code session on
2026-11-23 and independently rechecked the same day:
- The rebuilt source and the packed `main.py` are byte-identical to
  the verified reference implementation.
- Unpacking the lzma payload reproduces the source exactly.
- `gen()` on the initial position: 20 moves. `think()` on the initial
  position: e2e4. After f2f3 e7e5 g2g4: d8h4.
- Determinism: `PYTHONHASHSEED` 0 and 1 both give e2e4.
- Practice trial 0 on the rebuilt file: 6 wins, 0 draws, 0 losses
  (all by checkmate), Elo 2112, no time losses — the same scoreline
  and spare plies (697) as the reference file. Across three practice
  trials the reference scored Elo 2112 / 1809 / 1451 (mean 1791).

MIT licensed; see LICENSE.
