#!/bin/bash
# Start the Lichess bot bridge if it is not running.
# Anchored pattern: the python process only, never a wrapping shell.
if ! pgrep -f "^/usr/bin/python3 lichess_bot.py" > /dev/null; then
  cd /home/hatch/workspace/makefun/chess-reuse
  setsid nohup /usr/bin/python3 lichess_bot.py >> lichess_bot.out 2>&1 < /dev/null &
fi
