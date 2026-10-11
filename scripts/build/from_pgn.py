"""Turn a downloaded PGN into a game record, ready to finish by hand.

    make import

Reads every .pgn in drafts/ and writes games/<slug>.yml, filling in everything
the PGN already knows: the players, the date, the event, the opening code, the
result and the moves. What it cannot know -- the name the game goes by, and
why it is in the book -- is left for you.

The file name is taken to be the chessgames.com game id, so saving the game as
drafts/1001497.pgn is enough for the record to cite the page it came from. Any
other name is kept as the slug and no source is filled in.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import gamespath  # noqa: F401,E402  -- project root on sys.path and as cwd

import glob
import io
import os
import re
import unicodedata

import chess.pgn

DRAFTS = "drafts"
OUT = "games"

CG = "https://www.chessgames.com/perl/chessgame?gid=%s"


def ascii_name(name):
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def surname(name):
    """The last word of a name, which is the part a slug wants."""
    name = re.sub(r"\(.*?\)|,.*", "", name).strip()
    parts = [p for p in name.split() if len(p) > 1]
    return ascii_name(parts[-1]) if parts else "nn"


def pgn_date(headers):
    raw = headers.get("Date", "")
    m = re.match(r"^(\d{4})\.(\d{2}|\?\?)\.(\d{2}|\?\?)", raw)
    if not m:
        return "", ""
    year, month, day = m.groups()
    date = year
    if month != "??":
        date += "-" + month
        if day != "??":
            date += "-" + day
    return date, year


def wrap(moves, width=72):
    out, line = [], ""
    for token in moves.split():
        if len(line) + len(token) + 1 > width:
            out.append(line)
            line = token
        else:
            line = (line + " " + token).strip()
    if line:
        out.append(line)
    return "\n".join("  " + l for l in out)


def convert(path):
    game = chess.pgn.read_game(open(path, errors="replace"))
    if game is None:
        return None, "does not parse as a PGN"
    h = game.headers

    board = game.board()
    moves, n = [], 0
    for move in game.mainline_moves():
        if n % 2 == 0:
            moves.append("%d." % (n // 2 + 1))
        moves.append(board.san(move))
        board.push(move)
        n += 1
    if n < 2:
        return None, "holds no moves"

    date, year = pgn_date(h)
    if not year:
        return None, "has no usable Date tag"

    # However the browser named the download: game_1259987.pgn, 1259987.pgn,
    # "1259987 (1).pgn". The id is the long run of digits in it.
    stem = os.path.splitext(os.path.basename(path))[0]
    found = re.findall(r"\d{5,}", stem)
    gid = found[0] if found else None
    slug = "%s-%s-%s" % (year, surname(h.get("White", "")), surname(h.get("Black", "")))

    src = ""
    if gid:
        src = ('sources:\n'
               '  - title: %s vs %s (%s) (chessgames.com)\n'
               '    url: %s\n'
               '    note: move list, date and event\n'
               % (h.get("White", "?"), h.get("Black", "?"), year, CG % gid))
    else:
        src = ('# At least one source is required, and the build will refuse the\n'
               '# record without it. Give the page the moves were taken from.\n'
               'sources:\n'
               '  - title: \n'
               '    url: \n'
               '    note: move list\n')

    body = [
        "# Written by `make import` from %s. Fill in the title and the prose,\n"
        "# then run `make all`." % os.path.basename(path),
        "title: %s vs %s, %s" % (h.get("White", "?"), h.get("Black", "?"), year),
        "white: %s" % h.get("White", "?"),
        "black: %s" % h.get("Black", "?"),
        'result: "%s"' % h.get("Result", "*"),
        "date: %s" % date,
    ]
    for field, tag in (("event", "Event"), ("site", "Site"), ("eco", "ECO")):
        if h.get(tag) and h.get(tag) not in ("?", "-"):
            body.append("%s: %s" % (field, h.get(tag)))
    body += [
        "",
        "# why: >",
        "#   One sentence on why the game is in the book.",
        "",
        "moves: |",
        wrap(" ".join(moves)),
        "",
        src.rstrip(),
        "",
    ]
    return slug, "\n".join(body) + "\n"


def main():
    paths = sorted(glob.glob(os.path.join(DRAFTS, "*.pgn")))
    if not paths:
        raise SystemExit("no .pgn files in %s/ -- see %s/README.md"
                         % (DRAFTS, DRAFTS))
    written, skipped = 0, []
    for path in paths:
        slug, body = convert(path)
        if slug is None:
            skipped.append("%s: %s" % (os.path.basename(path), body))
            continue
        out = os.path.join(OUT, slug + ".yml")
        if os.path.exists(out):
            skipped.append("%s: %s already exists, left alone"
                           % (os.path.basename(path), out))
            continue
        with open(out, "w") as fh:
            fh.write(body)
        print("  %-22s -> %s" % (os.path.basename(path), out))
        written += 1
    print("imported %d game(s)" % written)
    if skipped:
        print("\n".join(["skipped %d:" % len(skipped)] + ["  " + s for s in skipped]))


if __name__ == "__main__":
    main()
