# Step A chess engine, UCI edition

The engine built for the make.fun Tiny Chess bounty (Step A, fixed
130,000-node alpha-beta search), made usable outside the contest.

The contest entry was rejected on a transcript-coverage technicality,
but the engine itself is complete and plays legal, reasonably strong
chess. This folder wraps it in UCI, the standard protocol spoken by
chess GUIs and by Lichess bot bridges, without changing the search or
the evaluation.

## Files

- `engine_core.py` — the submitted Step A source, unchanged
  (readable form of the 4,090-byte packed entry).
- `uci.py` — the UCI adapter. Translates FEN/UCI moves into the
  engine's internal state (board always shown from the side to move)
  by replaying moves through the engine's own move maker; a bare FEN
  is rebuilt from path-independent piece sums.
- `test_uci.py` — verification against python-chess (independent
  rules implementation). Needs `pip install python-chess`; run with
  `python3 test_uci.py`.
- `lichess_bot.py` — a minimal Lichess bot bridge. Accepts standard
  blitz, rapid, classical and correspondence challenges and plays
  them with this engine.
- `lichess-bot-watchdog.sh` — starts the bridge if it is not running.

## Run

```
python3 uci.py
```

Speaks UCI: `uci`, `isready`, `ucinewgame`, `position startpos|fen
... [moves ...]`, `go nodes N | go movetime MS | go wtime ...`,
`quit`. Default budget is the contest's 130,000 nodes (about 3.5 s
per move on the build VM, ~36k nodes/s). `go nodes` overrides it.

## Verified 2026-11-26

- Legal move sets identical to python-chess on 9 test positions
  (castling both colours, en passant, promotions, pins, black to move).
- Perft(2): startpos 400, Kiwipete 2039 — both match known values.
- Finds mate in 1 (Qxf7#) at the default budget.
- 60-ply self-play game: every move legal.

## Strength

In the bounty practice harness the engine's three trials measured
Elo 2112 / 1809 / 1451 (mean 1791) against the house opponents.
Those are 6-game samples, so treat the number as indicative, not
precise. A public rating needs real games — see below.

## Lichess bot (live)

This engine plays on Lichess as the bot
[AZALLY](https://lichess.org/@/AZALLY), through `lichess_bot.py`.
It accepts standard-variant blitz, rapid, classical and
correspondence challenges, rated or casual, and never resigns.

To run your own: create a Lichess account, upgrade it to a BOT
account (irreversible, and only possible before the account plays
any game), issue a personal OAuth token with the bot:play scope,
then run:

```
LICHESS_TOKEN=<your token> python3 lichess_bot.py
```
