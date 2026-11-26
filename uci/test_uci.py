#!/usr/bin/env python3
"""Correctness checks for uci.py against python-chess (independent rules)."""
import subprocess
import sys

import chess

sys.path.insert(0, "/home/hatch/workspace/makefun/chess-reuse")
import uci as U  # noqa: E402

FENS = [
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
    "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
    "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1",
    "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8",
    "r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1",
    "rnbqkbnr/ppp1p1pp/8/3pPp2/8/8/PPPP1PPP/RNBQKBNR w KQkq f6 0 3",
    "8/P6k/8/8/8/8/K6p/8 w - - 0 1",
    "4k3/8/8/8/8/8/6p1/K6R b - - 0 1",
]

fails = 0
for fen in FENS:
    pos = U.Position()
    pos.set_fen(fen, [])
    ours = set(pos.legal_moves_uci())
    theirs = {m.uci() for m in chess.Board(fen).legal_moves}
    ok = ours == theirs
    fails += not ok
    print(("OK  " if ok else "FAIL"), fen[:52], f"ours={len(ours)} theirs={len(theirs)}",
          "" if ok else f"diff={ours ^ theirs}")


def perft(state, depth):
    moves = U.E.leg_m(state, 0)
    if depth == 1:
        return len(moves)
    return sum(perft(U.E.mv(state, m), depth - 1) for m in moves)


for fen, depth, want in [
    ("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", 2, 400),
    ("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", 2, 2039),
]:
    state, _ = U.state_from_fen(fen)
    got = perft(state, depth)
    ok = got == want
    fails += not ok
    print(("OK  " if ok else "FAIL"), f"perft({depth}) = {got}, want {want}", fen[:40])

# --- UCI process level ---
proc = subprocess.Popen(
    ["python3", "/home/hatch/workspace/makefun/chess-reuse/uci.py"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)


def cmd(s):
    proc.stdin.write(s + "\n")
    proc.stdin.flush()


def bestmove_after(line, nodes=None):
    cmd(line)
    cmd(f"go nodes {nodes}" if nodes else "go")
    while True:
        out = proc.stdout.readline()
        if out.startswith("bestmove"):
            return out.split()[1]


cmd("uci")
while proc.stdout.readline().strip() != "uciok":
    pass
cmd("isready")
assert proc.stdout.readline().strip() == "readyok"

bm = bestmove_after("position startpos", 20000)
board = chess.Board()
ok = chess.Move.from_uci(bm) in board.legal_moves
fails += not ok
print(("OK  " if ok else "FAIL"), "startpos bestmove", bm)

mate_fen = "r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4"
bm = bestmove_after(f"position fen {mate_fen}")
ok = bm == "h5f7"
fails += not ok
print(("OK  " if ok else "FAIL"), "mate in 1 (Qxf7#) ->", bm)

board = chess.Board()
moves = []
for ply in range(60):
    if board.is_game_over():
        break
    bm = bestmove_after("position startpos moves " + " ".join(moves), 6000)
    mv = chess.Move.from_uci(bm)
    if mv not in board.legal_moves:
        fails += 1
        print("FAIL self-play illegal move", bm, "at ply", ply)
        break
    board.push(mv)
    moves.append(bm)
else:
    print("OK   self-play 60 plies, all legal; result so far:", board.result() if board.is_game_over() else "ongoing")
cmd("quit")
proc.wait(timeout=10)
print("DONE", "ALL PASS" if fails == 0 else f"{fails} FAILURES")
sys.exit(1 if fails else 0)
