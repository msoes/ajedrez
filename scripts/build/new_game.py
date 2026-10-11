"""Write a blank game record, ready to fill in.

    uv run python scripts/build/new_game.py 1960-spassky-bronstein

The file name is the game's slug and the chapter's URL, so it is worth
choosing: year first keeps games/ in the order the book publishes them.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import gamespath  # noqa: F401,E402  -- project root on sys.path and as cwd

import os

TEMPLATE = '''\
title: A short name for the game, as it is known
white: Full name
black: Full name
result: "1-0"            # 1-0, 0-1 or 1/2-1/2
date: 1900-01-01         # 1900, 1900-01 or 1900-01-01, to the precision known
# circa: true            # for a date that is only a tradition
event: The tournament, match or occasion
site: City, Country
opening: Opening name, as the source gives it
eco: A00

why: >
  One sentence on why the game is in the book. It is the chapter's subtitle and
  its description in search results.

summary: >
  A paragraph for the head of the chapter: what happens in the game, and what
  to watch for. Say who the players were if the names need placing.

# The moves, in algebraic notation, exactly as played. Move numbers are
# ignored, 0-0 is read as castling, and ! ? !! ?? after a move are kept as the
# editor's marks. Every move is replayed on a board at build time, so an
# illegal one stops the build rather than reaching the book.
moves: |
  1. e4 e5

# Where the moves were read from. At least one is required, and the first is
# taken to be the one the moves were transcribed from.
sources:
  - title: Title of the page
    url: https://example.org/
    note: what was taken from it

# Notes keyed to a move: 18w for White's 18th, 18b for Black's reply. They
# become the hoverable references in the move list, the notes under it, and the
# comments in the published PGN. `by` is whose judgement it is, where the note
# is reporting someone else's.
annotations:
  - at: 1w
    by: ""
    text: >
      What there is to say about this move.
'''


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    slug = sys.argv[1].removesuffix(".yml")
    path = os.path.join(gamespath.GAMES_DIR, slug + ".yml")
    if os.path.exists(path):
        raise SystemExit("%s already exists" % os.path.relpath(path))
    with open(path, "w") as fh:
        fh.write(TEMPLATE)
    print("wrote %s\nfill it in, then: make all" % os.path.relpath(path))


if __name__ == "__main__":
    main()
