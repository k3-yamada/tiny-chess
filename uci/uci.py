#!/usr/bin/env python3
"""UCI adapter for the Step A tiny-chess engine (engine_core.py).

The core engine always sees the board from the side to move (uppercase
pieces, board flipped after every move) and keeps its state in the tuple
(board, score, phase, own_castling, opp_castling, ep_square, castle_mark).
This adapter translates between UCI/FEN and that representation:

- positions given as startpos/FEN plus a move list are replayed through
  the engine's own move maker, so castling rights, en passant and the
  repetition table evolve exactly as they did in the make.fun harness;
- a bare FEN is rebuilt from scratch: the accumulated score and phase
  are path-independent sums over the pieces on the board, so they can be
  recomputed directly.

Search is the engine's fixed-node search. With no clock on the `go`
line it uses the submitted version's budget (130,000 nodes). `go nodes
N` overrides it; `go movetime` and clock times are converted at the
measured rate below. On a clock the budget scales with the time left:
about a thirtieth of the remaining time plus half the increment, never
more than a third of the clock or 60 seconds, so rapid and classical
games think several times deeper than the fixed budget while blitz
stays safely inside the flag.
"""
import importlib.util
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "engine_core", os.path.join(_HERE, "engine_core.py"))
E = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(E)

DEFAULT_NODES = 130000
NODES_PER_SECOND = 8000  # measured on this VM under the Lichess bridge (~7,700 nodes/s, 2026-11-27)

START = (E.I, 0j, 24, 3, 3, 0, 0)


def sq_name(idx):
    """Internal mailbox index (absolute orientation) -> 'e4'."""
    return chr(idx % 10 + 96) + str(10 - idx // 10)


def move_to_uci(m, flipped):
    i, j, r = m
    if flipped:
        i, j = 119 - i, 119 - j
    return sq_name(i) + sq_name(j) + (r.lower() if r else "")


def state_from_fen(fen):
    """Build the engine state tuple for a FEN. Returns (state, flipped)."""
    parts = fen.split()
    placement, active, castling, ep = parts[0], parts[1], parts[2], parts[3]
    rows = [" " * 9 + "\n", " " * 9 + "\n"]
    for rank in placement.split("/"):
        row = " "
        for ch in rank:
            row += "." * int(ch) if ch.isdigit() else ch
        rows.append(row + "\n")
    rows += [" " * 9 + "\n", " " * 9 + "\n"]
    board = "".join(rows)
    flipped = active == "b"
    if flipped:
        board = board[::-1].swapcase()
    score = 0j
    phase = 0
    for i, p in enumerate(board):
        if "A" <= p <= "Z":
            score += E.P[p][i]
            phase += E.PW[p] if p != "K" else 0
        elif "a" <= p <= "z":
            score -= E.P[p.upper()][119 - i]
            phase += E.PW[p.upper()] if p != "k" else 0

    def rights(white):
        letters = "KQ" if white else "kq"
        return (2 if letters[0] in castling else 0) | (1 if letters[1] in castling else 0)

    own = rights(active == "w")
    opp = rights(active != "w")
    ep_idx = 0
    if ep != "-":
        ep_idx = E.ps(ep)
        if flipped:
            ep_idx = 119 - ep_idx
    return (board, score, phase, own, opp, ep_idx, 0), flipped


class Position:
    def __init__(self):
        self.reset_game()
        self.set_startpos([])

    def reset_game(self):
        E.TT.clear()
        E.H.clear()
        E.KL.clear()
        E.RP.clear()

    def set_startpos(self, moves):
        self.state, self.flipped = START, False
        E.RP.clear()
        for uci in moves:
            self.apply(uci)

    def set_fen(self, fen, moves):
        self.state, self.flipped = state_from_fen(fen)
        E.RP.clear()
        for uci in moves:
            self.apply(uci)

    def apply(self, uci):
        i, j = E.ps(uci[0:2]), E.ps(uci[2:4])
        if self.flipped:
            i, j = 119 - i, 119 - j
        promo = uci[4].upper() if len(uci) > 4 else ""
        for m in E.gen(self.state):
            if m == (i, j, promo):
                E.RP[self.state[0]] = E.RP.get(self.state[0], 0) + 1
                self.state = E.mv(self.state, m)
                self.flipped = not self.flipped
                return
        raise ValueError(f"illegal move {uci}")

    def legal_moves_uci(self):
        return [move_to_uci(m, self.flipped) for m in E.leg_m(self.state, 0)]

    def bestmove(self, nodes):
        bm = E.think(self.state, 0, None, nodes)
        if not bm:
            return None, 0
        return move_to_uci(bm, self.flipped), E.N


def parse_go(tokens, flipped=False):
    args = dict(zip(tokens[::2], tokens[1::2])) if tokens else {}
    if "nodes" in args:
        return max(1000, int(args["nodes"]))
    if "movetime" in args:
        return int(min(300000, max(5000, int(args["movetime"]) * NODES_PER_SECOND // 1000)))
    # Use our own clock: `flipped` means Black is to move.
    tkey, ikey = ("btime", "binc") if flipped else ("wtime", "winc")
    if tkey in args:
        remain = max(0, int(args[tkey]) - 300)  # keep a small clock buffer
        inc = int(args.get(ikey, 0))
        budget_ms = remain // 30 + inc // 2
        budget_ms = max(200, min(budget_ms, remain // 3, 10000))
        return int(min(2200000, max(5000, budget_ms * NODES_PER_SECOND // 1000)))
    return DEFAULT_NODES


def main():
    pos = Position()
    out = sys.stdout
    for line in sys.stdin:
        tokens = line.split()
        if not tokens:
            continue
        cmd, rest = tokens[0], tokens[1:]
        if cmd == "uci":
            out.write("id name StepA-4K (UCI)\n")
            out.write("id author Keizo Yamada\n")
            out.write("uciok\n")
        elif cmd == "isready":
            out.write("readyok\n")
        elif cmd == "ucinewgame":
            pos.reset_game()
            pos.set_startpos([])
        elif cmd == "position":
            if rest[0] == "startpos":
                moves = rest[rest.index("moves") + 1:] if "moves" in rest else []
                pos.set_startpos(moves)
            elif rest[0] == "fen":
                end = rest.index("moves") if "moves" in rest else len(rest)
                moves = rest[end + 1:] if "moves" in rest else []
                pos.set_fen(" ".join(rest[1:end]), moves)
        elif cmd == "go":
            nodes = parse_go(rest, pos.flipped)
            t0 = time.time()
            bm, used = pos.bestmove(nodes)
            dt = max(time.time() - t0, 0.001)
            out.write(f"info nodes {used} nps {int(used / dt)}\n")
            out.write(f"bestmove {bm if bm else '(none)'}\n")
        elif cmd == "quit":
            break
        out.flush()


if __name__ == "__main__":
    main()
