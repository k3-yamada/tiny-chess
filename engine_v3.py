"""Tiny Chess Engine V3 (pure Python stdlib, packs under 4,096 bytes).

V3 additions over V2:
- Aspiration Windows in iterative deepening.
- Endgame mop-up evaluation (pushing losing king to edge & bringing winning king closer).
- Excluding checking moves (giving check) from LMR reductions.
"""

import json, os, urllib.request as urlreq

URL = os.getenv("MAKEFUN_ENV_URL", "")
PIECE_VAL = [0, 100, 320, 330, 500, 900, 0]
PHASE_WT = [0, 0, 1, 1, 2, 4, 0]
KNIGHT_DIRS = (-33, -31, -18, -14, 14, 18, 31, 33)
BISHOP_DIRS = (-17, -15, 15, 17)
ROOK_DIRS = (-16, -1, 1, 16)
KING_DIRS = BISHOP_DIRS + ROOK_DIRS

PST = [
    ord(c) - 80
    for c in (
        "PPPPPPPPUZZ<<ZZUUKFPPFKUPPPddPPPUUZiiZUUZZdnndZZ}}}}}}}}PPPPPPPP"
        "#(2222(#(<PUUP<(2UZ__ZU22P_dd_P22U_dd_U22PZ__ZP2(<PPPP<(#(2222(#"
        "<FFFFFF<F_PPPP_FFZZZZZZFFPZZZZPFFUUZZUUFFPUZZUPFFPPPPPPF<FFFFFF<"
        "PPPUUPPPKPPPPPPKKPPPPPPKKPPPPPPKKPPPPPPKKPPPPPPKUZZZZZZUPPPPPPPP"
        "<FFKKFF<FPUPPPPFFUUUUUPFKPUUUUPKKPUUUUPKFPUUUUPFFPPPPPPF<FFKKFF<"
        "dnZPPZndddPPPPddF<<<<<<F<22((22<2((##((22((##((22((##((22((##((2"
        "#222222#22PPPP222FdnndF22FnxxnF22FnxxnF22FdnndF22<FPPF<2#(2<<2(#"
    )
]
SQUARES = [i for i in range(120) if not (i & 136)]
BUDGET = 95000

nodes = 0
aborted = 0
node_limit = BUDGET
history_pos = set()
tt = {}
hist_tbl = {}
killers = {}


def load(fen):
    parts = fen.split()
    board = [0] * 128
    for rank_idx, row in enumerate(parts[0].split("/")):
        file_idx = 0
        for ch in row:
            if ch.isdigit():
                file_idx += int(ch)
            else:
                piece = " PNBRQK".index(ch.upper())
                board[(7 - rank_idx) * 16 + file_idx] = piece if ch.isupper() else -piece
                file_idx += 1
    side = 0 if parts[1] == "w" else 1
    castling = parts[2].strip("-")
    ep = -1 if parts[3] == "-" else ord(parts[3][0]) - 97 + (int(parts[3][1]) - 1) * 16
    return board, side, castling, ep


def play(board, move, side, castling, ep):
    frm, to, promo = move
    nxt = board[:]
    piece = nxt[frm]
    if abs(piece) == 1 and to == ep and frm % 16 != to % 16:
        nxt[to - 16 if side == 0 else to + 16] = 0
    nxt[to] = promo * (1 - 2 * side) or piece
    nxt[frm] = 0
    if abs(piece) == 6 and abs(to - frm) == 2:
        rook_sq = to + 1 if to > frm else to - 2
        nxt[(frm + to) // 2] = nxt[rook_sq]
        nxt[rook_sq] = 0
    cr = castling
    for sq, ch in ((0, "Q"), (7, "K"), (112, "q"), (119, "k")):
        if frm == sq or to == sq:
            cr = cr.replace(ch, "")
    if abs(piece) == 6:
        cr = cr.replace("K", "").replace("Q", "") if side == 0 else cr.replace("k", "").replace("q", "")
    new_ep = (frm + to) // 2 if abs(piece) == 1 and abs(to - frm) == 32 else -1
    return nxt, cr, new_ep


def pseudo(board, side, ep, caps_only):
    moves = []
    sign = 1 - 2 * side
    step = 16 * sign
    for frm in SQUARES:
        piece = board[frm]
        if piece * sign <= 0:
            continue
        ptype = abs(piece)
        if ptype == 1:
            to = frm + step
            promos = (5, 4, 3, 2) if to // 16 in (0, 7) else (0,)
            if (not caps_only or promos[0]) and not board[to]:
                moves.extend((frm, to, pr) for pr in promos)
                dbl = to + step
                if frm // 16 == (1 if side == 0 else 6) and not board[dbl]:
                    moves.append((frm, dbl, 0))
            for delta in (step - 1, step + 1):
                to = frm + delta
                if not (to & 136) and (board[to] * sign < 0 or to == ep):
                    moves.extend((frm, to, pr) for pr in promos)
        else:
            dirs = KNIGHT_DIRS if ptype == 2 else BISHOP_DIRS if ptype == 3 else ROOK_DIRS if ptype == 4 else KING_DIRS
            for delta in dirs:
                to = frm + delta
                while not (to & 136):
                    if board[to] * sign > 0 or abs(board[to]) == 6:
                        break
                    if not caps_only or board[to]:
                        moves.append((frm, to, 0))
                    if board[to] or ptype in (2, 6):
                        break
                    to += delta
    return moves


def attacked(board, sq, by_side):
    sign = 1 - 2 * by_side
    for delta in KING_DIRS:
        cur = sq + delta
        first = 1
        while not (cur & 136):
            p = board[cur] * sign
            if p:
                if (
                    p == 5
                    or p == (3 if delta in BISHOP_DIRS else 4)
                    or (first and (p == 6 or (p == 1 and delta in (-15 * sign, -17 * sign))))
                ):
                    return 1
                break
            cur += delta
            first = 0
    for delta in KNIGHT_DIRS:
        cur = sq + delta
        if not (cur & 136) and board[cur] == 2 * sign:
            return 1


def gen(board, side, castling, ep, caps_only=0, pseudo_only=0):
    sign = 1 - 2 * side
    moves = pseudo(board, side, ep, caps_only)
    if not pseudo_only:
        moves = [
            m
            for m in moves
            if not attacked((b := play(board, m, side, castling, ep)[0]), b.index(sign * 6), 1 - side)
        ]
    if caps_only:
        return moves
    home_rank = 112 * side
    king_sq = home_rank + 4
    if board[king_sq] == sign * 6 and not attacked(board, king_sq, 1 - side):
        for flag, rook_sq, empty_sqs, dest in (
            ("K", home_rank + 7, (home_rank + 5, home_rank + 6), home_rank + 6),
            ("Q", home_rank, (home_rank + 1, home_rank + 2, home_rank + 3), home_rank + 2),
        ):
            ch = flag if side == 0 else flag.lower()
            if (
                ch in castling
                and board[rook_sq] == sign * 4
                and all(not board[sq] for sq in empty_sqs)
                and not attacked(board, (king_sq + dest) // 2, 1 - side)
                and not attacked(board, dest, 1 - side)
            ):
                moves.append((king_sq, dest, 0))
    return moves


def evaluate(board, side):
    score = phase = king_mg = king_eg = 0
    pawns = [0] * 22
    rooks = []
    wk = bk = 0
    for sq in SQUARES:
        piece = board[sq]
        if not piece:
            continue
        ptype = abs(piece)
        sign = (piece > 0) * 2 - 1
        fl = sq & 7
        rk = sq >> 4
        idx = (rk if piece > 0 else 7 - rk) * 8 + fl
        if ptype > 5:
            king_mg += sign * PST[320 + idx]
            king_eg += sign * PST[384 + idx]
            if piece > 0:
                wk = sq
            else:
                bk = sq
        else:
            score += sign * (PIECE_VAL[ptype] + PST[ptype * 64 - 64 + idx])
            phase += PHASE_WT[ptype]
            if ptype == 1:
                pawns[fl + 6 - 5 * sign] += 1
                step = sign * 16
                if idx > 23 and -sign not in (
                    board[sq + step - 1 :: step] + board[sq + step :: step] + board[sq + step + 1 :: step]
                ):
                    adv = idx >> 3
                    score += sign * (adv * adv * 5 // 2)
            elif ptype == 3:
                pawns[20 + (piece > 0)] += 1
            elif ptype == 4:
                rooks.append((sign, fl))

    for sign, fl in rooks:
        if not pawns[fl + 6 - 5 * sign]:
            score += sign * (20 if not pawns[fl + 6 + 5 * sign] else 10)

    for j in range(1, 19):
        cnt = pawns[j]
        if cnt:
            score += (2 * (j > 9) - 1) * (cnt * 15 - 15 + (pawns[j - 1] + pawns[j + 1] < 1) * cnt * 12)

    phase = min(phase, 24)
    score += (king_mg * phase + king_eg * (24 - phase)) // 24 + (pawns[21] > 1) * 30 - (pawns[20] > 1) * 30

    if phase < 8 and abs(score) > 250:
        win = 1 if score > 0 else -1
        lose_k = bk if win > 0 else wk
        cmd = abs((lose_k & 7) * 2 - 7) + abs((lose_k >> 4) * 2 - 7)
        dist = abs((wk & 7) - (bk & 7)) + abs((wk >> 4) - (bk >> 4))
        score += win * (cmd * 5 + (14 - dist) * 4)

    return score if side == 0 else -score


def move_key(board, tt_move, ep, k1, k2):
    return lambda m: (
        9e9 if m == tt_move else
        1e6 + (PIECE_VAL[abs(board[m[1]])] or 100) * 10 - PIECE_VAL[abs(board[m[0]])] + m[2] * 1e5
        if board[m[1]] or (m[1] == ep and abs(board[m[0]]) == 1) else
        9e5 + m[2] * 1e5 if m[2] else
        8e5 if m == k1 else
        7e5 if m == k2 else
        hist_tbl.get(m, 0)
    )


def search(board, side, castling, ep, depth, alpha, beta, ply):
    global nodes, aborted
    nodes += 1
    if nodes > node_limit:
        aborted = 1
        return 0, None

    sign = 1 - 2 * side
    in_check = attacked(board, board.index(6 * sign), 1 - side)

    if depth <= 0 and (not in_check or depth < -1):
        stand = evaluate(board, side)
        if stand >= beta:
            return beta, None
        alpha = max(alpha, stand)
        for m in sorted(gen(board, side, castling, ep, 1, 1), key=move_key(board, 0, ep, 0, 0), reverse=True):
            nxt, ncr, nep = play(board, m, side, castling, ep)
            if attacked(nxt, nxt.index(6 * sign), 1 - side):
                continue
            val = -search(nxt, 1 - side, ncr, nep, -1, -beta, -alpha, ply + 1)[0]
            if aborted:
                return 0, None
            if val >= beta:
                return beta, None
            alpha = max(alpha, val)
        return alpha, None

    pos_key = (tuple(board), side, castling, ep)
    orig_alpha = alpha
    tt_move = None
    if ply and pos_key in history_pos:
        return 0, None

    entry = tt.get(pos_key)
    if entry:
        e_depth, e_val, e_flag, tt_move = entry
        if (
            ply
            and e_depth >= depth
            and abs(e_val) < 9999
            and (e_flag == 0 or (e_flag == 1 and e_val >= beta) or (e_flag == 2 and e_val <= alpha))
        ):
            return e_val, tt_move

    if ply and depth > 0 and not in_check and abs(beta) < 9999:
        static_ev = evaluate(board, side)
        if depth <= 3 and static_ev - 120 * depth >= beta:
            return beta, None
        if depth > 2 and static_ev >= beta and any(1 < p * sign < 6 for p in board):
            val = -search(board, 1 - side, castling, -1, depth - 3, -beta, 1 - beta, ply + 1)[0]
            if aborted:
                return 0, None
            if val >= beta:
                return beta, None

    opp_king = board.index(-6 * sign)
    k1, k2 = killers.get(ply, (None, None))
    moves = gen(board, side, castling, ep, 0, 1)
    moves.sort(key=move_key(board, tt_move, ep, k1, k2), reverse=True)

    best_move = None
    best_val = -31000
    history_pos.add(pos_key)
    legal_idx = 0

    for m in moves:
        nxt, ncr, nep = play(board, m, side, castling, ep)
        if attacked(nxt, nxt.index(6 * sign), 1 - side):
            continue
        legal_idx += 1
        is_cap = board[m[1]] or (m[1] == ep and abs(board[m[0]]) == 1)

        if legal_idx == 1:
            val = -search(nxt, 1 - side, ncr, nep, depth - 1, -beta, -alpha, ply + 1)[0]
        else:
            red = int(
                depth > 2
                and legal_idx > 3
                and not (is_cap or m[2] or in_check)
                and not attacked(nxt, opp_king, side)
            )
            val = -search(nxt, 1 - side, ncr, nep, depth - 1 - red, -alpha - 1, -alpha, ply + 1)[0]
            if val > alpha and not aborted and (red or val < beta):
                val = -search(nxt, 1 - side, ncr, nep, depth - 1, -beta, -alpha, ply + 1)[0]

        if aborted:
            history_pos.discard(pos_key)
            return 0, best_move

        if val > best_val:
            best_val = val
            best_move = m
        alpha = max(alpha, val)
        if alpha >= beta:
            if not is_cap and not m[2]:
                hist_tbl[m] = hist_tbl.get(m, 0) + depth * depth
                if m != k1:
                    killers[ply] = (m, k1)
            break

    history_pos.discard(pos_key)
    if not best_move:
        return (ply - 30000 if in_check else 0), None

    if depth > 0 and (not entry or depth >= entry[0]):
        tt[pos_key] = (depth, best_val, (best_val >= beta) + 2 * (best_val <= orig_alpha), best_move)
    return best_val, best_move


def choose(fen, legal_moves, start_fen=0, moves=()):
    global nodes, aborted, node_limit
    ok = list(legal_moves)
    if len(ok) < 2:
        return ok[0]

    board, side, cr, ep = load(start_fen or fen)
    nodes = 0
    aborted = 0
    best = None
    history_pos.clear()
    tt.clear()
    hist_tbl.clear()
    killers.clear()
    node_limit = BUDGET if len(moves) < 60 else BUDGET // 4

    for uci in (start_fen and moves) or ():
        history_pos.add((tuple(board), side, cr, ep))
        mv = (
            ord(uci[0]) - 97 + int(uci[1]) * 16 - 16,
            ord(uci[2]) - 97 + int(uci[3]) * 16 - 16,
            " pnbrq".find(uci[4:].lower()),
        )
        board, cr, ep = play(board, mv, side, cr, ep)
        side = 1 - side

    cur = load(fen)
    if board != cur[0]:
        history_pos.clear()
    board, side, cr, ep = cur

    prev_val = 0
    for depth in range(1, 30):
        delta = 40
        al, be = (prev_val - delta, prev_val + delta) if depth > 3 and abs(prev_val) < 9000 else (-31000, 31000)
        while 1:
            val, cand = search(board, side, cr, ep, depth, al, be, 0)
            if aborted or al < val < be:
                best = cand or best
                if not aborted:
                    prev_val = val
                break
            if val <= al:
                al = max(-31000, al - delta)
            else:
                be = min(31000, be + delta)
            delta *= 2
        if aborted:
            break

    uci_move = (
        chr(97 + best[0] % 16)
        + str(best[0] // 16 + 1)
        + chr(97 + best[1] % 16)
        + str(best[1] // 16 + 1)
        + " pnbrq"[best[2]].strip()
        if best
        else ""
    )
    return uci_move if uci_move in ok else ok[0]


def post(path, data):
    req = urlreq.Request(URL + path, data=json.dumps(data).encode(), headers={"content-type": "application/json"})
    return json.load(urlreq.urlopen(req, timeout=30))


if __name__ == "__main__":
    while 1:
        game = post("/game", {})
        if game["status"] == "done":
            break
        while game["status"] == "your_move":
            mv = choose(game["fen"], game["legal_moves"], game.get("start_fen"), game.get("moves") or ())
            game = post("/move", {"game": game["game"], "move": mv})
