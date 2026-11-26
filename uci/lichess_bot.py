#!/usr/bin/env python3
"""Minimal Lichess bot bridge for the Step A UCI engine (uci.py).

Token: set the LICHESS_TOKEN environment variable to a Lichess personal
OAuth token with the bot:play scope. When LICHESS_TOKEN is not set, the
bridge falls back to Muse's Secure Vault surrogate (connector
custom.lichess), which is how the original AZALLY deployment runs; in
that mode no secret ever touches this file or its log.

Policy: standard variant only; blitz, rapid, classical and correspondence
speeds; rated and casual both accepted. Everything else is declined.
The engine never resigns and never offers or accepts draws.
"""
import json
import os
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request

TOKEN = os.environ.get("LICHESS_TOKEN")
if not TOKEN:
    sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")
    from dynamic_credentials import add_surrogate_to_request

PROVIDER = "custom.lichess"
HOSTS = ["lichess.org"]
BASE = "https://lichess.org"
HERE = __file__.rsplit("/", 1)[0]
ENGINE_CMD = ["python3", HERE + "/uci.py"]
ACCEPT_SPEEDS = {"blitz", "rapid", "classical", "correspondence"}
MY_ID = "azally"
LOG = open(HERE + "/lichess_bot.log", "a", buffering=1)


def log(*parts):
    print(time.strftime("%Y-%m-%d %H:%M:%S"), *parts, file=LOG)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        raise RuntimeError("redirect refused")


def request(method, path, data=None, stream=False):
    body = None
    headers = {}
    if data is not None:
        body = urllib.parse.urlencode(data).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(BASE + path, data=body, method=method, headers=headers)
    if TOKEN:
        req.add_header("Authorization", "Bearer " + TOKEN)
    else:
        add_surrogate_to_request(req, PROVIDER, allowed_hosts=HOSTS)
    opener = urllib.request.build_opener(NoRedirect())
    return opener.open(req, timeout=None if stream else 30)


def post(path, data=None):
    try:
        with request("POST", path, data=data) as r:
            r.read()
        return True
    except Exception as e:
        log("POST failed", path, repr(e))
        return False


class Engine:
    def __init__(self):
        self.p = subprocess.Popen(
            ENGINE_CMD, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True
        )
        self.send("uci")
        self.wait_for("uciok")
        self.send("isready")
        self.wait_for("readyok")

    def send(self, line):
        self.p.stdin.write(line + "\n")
        self.p.stdin.flush()

    def wait_for(self, token):
        while True:
            line = self.p.stdout.readline()
            if not line:
                raise RuntimeError("engine died")
            if token in line:
                return

    def bestmove(self, initial_fen, moves, wtime, btime, winc, binc):
        if initial_fen == "startpos":
            pos = "position startpos"
        else:
            pos = "position fen " + initial_fen
        if moves:
            pos += " moves " + moves
        self.send(pos)
        self.send(
            "go wtime %d btime %d winc %d binc %d"
            % (max(wtime, 1), max(btime, 1), winc, binc)
        )
        while True:
            line = self.p.stdout.readline()
            if not line:
                raise RuntimeError("engine died")
            parts = line.split()
            if parts and parts[0] == "bestmove":
                return parts[1] if len(parts) > 1 else None

    def close(self):
        try:
            self.send("quit")
            self.p.wait(timeout=5)
        except Exception:
            self.p.kill()


def play_game(game_id):
    log("game start", game_id)
    engine = Engine()
    my_white = None
    initial_fen = "startpos"
    try:
        with request("GET", "/api/bot/game/stream/" + game_id, stream=True) as resp:
            for raw in resp:
                line = raw.decode("utf-8", "replace").strip()
                if not line:
                    continue
                event = json.loads(line)
                if event.get("type") == "gameFull":
                    white = event["white"].get("id", "")
                    my_white = white.lower() == MY_ID
                    initial_fen = event.get("initialFen", "startpos")
                    state = event["state"]
                elif event.get("type") == "gameState":
                    state = event
                else:
                    continue
                if state.get("status") != "started" or my_white is None:
                    if state.get("status") not in ("started", "created"):
                        log("game over", game_id, state.get("status"),
                            "winner:", state.get("winner"))
                        break
                    continue
                moves = state.get("moves", "")
                played = len(moves.split()) if moves else 0
                my_turn = (played % 2 == 0) == my_white
                if not my_turn:
                    continue
                move = engine.bestmove(
                    initial_fen, moves,
                    int(state.get("wtime", 60000)), int(state.get("btime", 60000)),
                    int(state.get("winc", 0)), int(state.get("binc", 0)),
                )
                if move:
                    log("move", game_id, move, "after", played, "moves")
                    post("/api/bot/game/%s/move/%s" % (game_id, move))
    except Exception as e:
        log("game stream error", game_id, repr(e))
    finally:
        engine.close()
    log("game thread end", game_id)


def handle_challenge(ch):
    ch_id = ch["id"]
    variant = ch.get("variant", {}).get("key")
    speed = ch.get("speed")
    if variant == "standard" and speed in ACCEPT_SPEEDS:
        log("accept challenge", ch_id, speed, "rated:", ch.get("rated"))
        post("/api/challenge/%s/accept" % ch_id)
    else:
        log("decline challenge", ch_id, variant, speed)
        post("/api/challenge/%s/decline" % ch_id, data={"reason": "generic"})


def main():
    log("bridge starting")
    while True:
        try:
            with request("GET", "/api/stream/event", stream=True) as resp:
                log("event stream connected")
                for raw in resp:
                    line = raw.decode("utf-8", "replace").strip()
                    if not line:
                        continue
                    event = json.loads(line)
                    kind = event.get("type")
                    if kind == "challenge":
                        handle_challenge(event["challenge"])
                    elif kind == "gameStart":
                        threading.Thread(
                            target=play_game, args=(event["game"]["id"],), daemon=True
                        ).start()
                    elif kind == "gameFinish":
                        log("game finish event", event["game"]["id"])
        except Exception as e:
            log("event stream error", repr(e))
        time.sleep(5)


if __name__ == "__main__":
    main()
