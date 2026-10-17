"""Read games/*.yml, replay every move on a board, write games.json.

The YAML files are the only thing written by hand. Everything downstream -- the
PGN files, the book's chapters, the timeline, the list of sources -- is built
from the records this produces, so adding a game means adding one file here and
running make.

Nothing is published that the board has not played. A move the rules do not
allow stops the build and names the game, the move number and the position it
was tried in, because a wrong move copied off a web page is the one error this
project cannot see by eye.
"""

import glob
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import gamespath  # noqa: F401,E402  -- project root on sys.path and as cwd

import json
import os
import re
import unicodedata

import chess
import chess.pgn
import yaml

OUT = "games.json"

# A record carries no era of its own: the era follows from the year, so a game
# added later lands in the right part of the book without being told to.
ERAS = [
    (0, 1799, "The early game",
     "Chess before the tournament: games recorded because someone thought "
     "them worth writing down."),
    (1800, 1879, "The romantic era",
     "Gambits accepted on principle, kings hunted down the board, and the "
     "first games to be famous."),
    (1880, 1934, "The classical era",
     "Position before combination. The world championship begins, and with "
     "it the idea that a game can be won by accumulation."),
    (1935, 1974, "The Soviet school",
     "Preparation as a discipline, and a generation that studied the game "
     "the way one studies a science."),
    (1975, 1995, "The modern era",
     "Opening theory to move twenty, matches decided by seconds and "
     "databases, and two champions who played each other 144 times."),
    (1996, 9999, "The computer age",
     "The machines arrive as opponents, then as analysts, and finally as "
     "teachers."),
]

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]

RESULTS = {"1-0", "0-1", "1/2-1/2", "*"}

# Fields a record may carry. Anything else in a YAML file is a typo, and is
# easier to catch here than to find later in a rendered page.
FIELDS = {
    "title", "white", "black", "result", "result_note", "date", "circa",
    "event", "site", "opening", "eco", "why", "summary", "moves", "sources",
    "annotations", "start_fen", "orientation",
}
REQUIRED = {"title", "white", "black", "result", "date", "moves", "sources"}


class Bad(Exception):
    """A game that cannot be published, with the file and the reason."""


def slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")


def era(year):
    for lo, hi, name, blurb in ERAS:
        if lo <= year <= hi:
            return name
    raise Bad("no era covers the year %d" % year)


def read_date(value, circa):
    """Accept 1620, 1851-06 or 1851-06-21, however YAML chose to read it.

    Returns the three parts for sorting and a form fit to print. The precision
    is the author's: a game known only to the year must not be published as
    though it happened on the first of January.
    """
    text = str(value).strip()
    m = re.match(r"^(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?$", text)
    if not m:
        raise Bad("date %r is not 1851, 1851-06 or 1851-06-21" % text)
    year = int(m.group(1))
    month = int(m.group(2)) if m.group(2) else 0
    day = int(m.group(3)) if m.group(3) else 0
    if month > 12:
        raise Bad("date %r has no such month" % text)
    if day:
        shown = "%d %s %d" % (day, MONTHS[month - 1], year)
    elif month:
        shown = "%s %d" % (MONTHS[month - 1], year)
    else:
        shown = str(year)
    if circa:
        shown = "c. " + shown
    return year, month, day, shown


# The marks an editor puts on a move. Kept apart from the move itself so the
# board is given notation and the reader is given the judgement.
MARK = re.compile(r"([!?]+)$")

TOKEN_NOISE = re.compile(
    r"\{[^}]*\}"          # comments
    r"|;[^\n]*"           # end-of-line comments
    r"|\$\d+"             # NAGs
    r"|\d+\.(\.\.)?"      # move numbers, and 12... for a black move
    r"|[()]"              # variations are not published, so they are an error
)


def read_moves(text):
    """Turn a movetext block into plain SAN tokens and their editorial marks."""
    if "(" in text or ")" in text:
        raise Bad("movetext contains a variation; publish the game as played "
                  "and put the alternative in an annotation")
    text = TOKEN_NOISE.sub(" ", text)
    out = []
    for token in text.split():
        if token in RESULTS or token in ("1–0", "0–1"):
            continue
        token = (token.replace("0-0-0", "O-O-O").replace("0-0", "O-O")
                      .replace("–", "-").replace("—", "-"))
        m = MARK.search(token)
        mark = m.group(1) if m else ""
        out.append((token[:m.start()] if m else token, mark))
    return out


def replay(tokens, start_fen=None):
    """Play the game out, and return the canonical SAN of each move.

    What goes into the book is what the board produced, not what was typed:
    a source that writes Qxd4 where the position needs Qxd4+ is published
    with the check mark it earned.
    """
    board = chess.Board(start_fen) if start_fen else chess.Board()
    san, marks = [], {}
    for i, (token, mark) in enumerate(tokens):
        try:
            move = board.parse_san(token)
        except (ValueError, chess.IllegalMoveError) as exc:
            # python-chess puts the position in its own message, so the reason
            # is taken apart from it and printed once.
            why = str(exc).split(" in ")[0] or "not a legal move"
            raise Bad("move %d%s %r: %s\n    position: %s"
                      % (i // 2 + 1, "." if i % 2 == 0 else "...", token,
                         why, board.fen()))
        san.append(board.san(move))
        if mark:
            marks[str(i)] = mark
        board.push(move)
    return san, marks, board


AT = re.compile(r"^(\d+)\s*(w|b|\.\.\.)?$", re.I)


def read_at(at, plies):
    """Resolve an annotation's `at: 18w` to a ply index."""
    m = AT.match(str(at).strip())
    if not m:
        raise Bad("annotation at %r is not 18w, 18b or 18" % at)
    number = int(m.group(1))
    side = (m.group(2) or "w").lower()
    ply = (number - 1) * 2 + (1 if side in ("b", "...") else 0)
    if not 0 <= ply < plies:
        raise Bad("annotation at %r falls outside the game's %d plies"
                  % (at, plies))
    return ply


# A short name for each note within its game, so a check that rejects one can
# say which. Nothing on the page shows it.
def letter(n):
    return chr(ord("a") + n) if n < 26 else chr(ord("a") + n % 26) * (n // 26 + 1)


def text(value):
    """One line of prose, however the YAML was folded.

    A newline inside a value would end a tag in the PGN and leave the rest of
    the file unparseable, so no free-text field keeps its line breaks.
    """
    return " ".join(str(value or "").split())


# What a source may carry. `cited_by` names the piece of prose that rests on
# it, and the only one a reader is shown a reference for is the why: a sentence
# taken from somewhere else is footnoted where it is read, not only listed at
# the foot of the page.
SOURCE_FIELDS = {"title", "url", "note", "cited_by"}
CITED_BY = {"", "why"}


def read_sources(raw):
    if not raw:
        raise Bad("no source: every game must say where its moves came from")
    out = []
    for item in raw:
        if not isinstance(item, dict) or not (item.get("url") or "").strip():
            raise Bad("a source is missing its url; if the game was imported "
                      "from a PGN, name the file after the game id so the "
                      "page it came from can be cited")
        unknown = set(item) - SOURCE_FIELDS
        if unknown:
            raise Bad("source %r carries unknown field(s): %s"
                      % (item["url"].strip(), ", ".join(sorted(unknown))))
        cited_by = text(item.get("cited_by"))
        if cited_by not in CITED_BY:
            raise Bad("source %r is cited_by %r; only `why` is understood"
                      % (item["url"].strip(), cited_by))
        out.append({"title": text(item.get("title")) or item["url"],
                    "url": item["url"].strip(),
                    "note": text(item.get("note")),
                    "cited_by": cited_by})
    return out


def read_game(path):
    raw = yaml.safe_load(open(path))
    if not isinstance(raw, dict):
        raise Bad("file does not hold a mapping")
    unknown = set(raw) - FIELDS
    if unknown:
        raise Bad("unknown field(s): %s" % ", ".join(sorted(unknown)))
    missing = REQUIRED - set(raw)
    if missing:
        raise Bad("missing field(s): %s" % ", ".join(sorted(missing)))
    if raw["result"] not in RESULTS:
        raise Bad("result %r is not one of %s"
                  % (raw["result"], ", ".join(sorted(RESULTS))))

    year, month, day, shown = read_date(raw["date"], raw.get("circa"))
    start_fen = raw.get("start_fen")
    san, marks, board = replay(read_moves(raw["moves"]), start_fen)
    if len(san) < 2:
        raise Bad("a game needs more than one move")

    # The result and the final position have to agree. A game that ends in
    # mate cannot be a draw, and a mate cannot be scored for the side mated.
    if board.is_checkmate():
        won = "0-1" if board.turn == chess.WHITE else "1-0"
        if raw["result"] != won:
            raise Bad("the game ends in checkmate, so the result is %s, not %s"
                      % (won, raw["result"]))

    notes, note_for_ply = [], {}
    for i, item in enumerate(raw.get("annotations") or []):
        if not isinstance(item, dict) or "text" not in item:
            raise Bad("annotation %d needs at least `at` and `text`" % (i + 1))
        ply = read_at(item.get("at", 1), len(san))
        mark = letter(i)
        notes.append({"letter": mark, "ply": ply, "by": item.get("by", ""),
                      "text": " ".join(str(item["text"]).split())})
        note_for_ply.setdefault(str(ply), []).append(mark)

    slug = slugify(os.path.splitext(os.path.basename(path))[0])

    # The reference numbers the why is read with are the positions of its
    # sources in the list the page prints, so the two cannot disagree.
    sources = read_sources(raw.get("sources"))
    why_cites = [i + 1 for i, src in enumerate(sources) if src["cited_by"] == "why"]
    if why_cites and not text(raw.get("why")):
        raise Bad("a source is cited_by `why`, but the game has no why")

    return {
        "slug": slug,
        "source_file": os.path.relpath(path),
        "title": text(raw["title"]),
        "white": text(raw["white"]),
        "black": text(raw["black"]),
        "result": raw["result"],
        "result_note": text(raw.get("result_note")),
        "date": shown,
        "year": year,
        "sort": [year, month, day, slug],
        "era": era(year),
        "event": text(raw.get("event")),
        "site": text(raw.get("site")),
        "opening": text(raw.get("opening")),
        "eco": text(raw.get("eco")),
        "why": text(raw.get("why")),
        "summary": text(raw.get("summary")),
        "start_fen": start_fen,
        "orientation": raw.get("orientation", "white"),
        "san": san,
        "marks": marks,
        "notes": notes,
        "note_for_ply": note_for_ply,
        "sources": sources,
        "why_cites": why_cites,
        "final_fen": board.fen(),
        "checkmate": board.is_checkmate(),
    }


def load():
    """Every game, in the order the book publishes them."""
    recs, bad = [], []
    for path in sorted(glob.glob(os.path.join(gamespath.GAMES_DIR, "*.yml"))
                       + glob.glob(os.path.join(gamespath.GAMES_DIR, "*.yaml"))):
        try:
            recs.append(read_game(path))
        except Bad as exc:
            bad.append("%s: %s" % (os.path.relpath(path), exc))
        except yaml.YAMLError as exc:
            bad.append("%s: not valid YAML: %s" % (os.path.relpath(path), exc))
    if bad:
        raise SystemExit("\n".join(["%d game(s) will not build:" % len(bad)]
                                   + ["  " + b for b in bad]))
    seen = {}
    for rec in recs:
        if rec["slug"] in seen:
            raise SystemExit("two games share the slug %r: %s and %s"
                             % (rec["slug"], seen[rec["slug"]], rec["source_file"]))
        seen[rec["slug"]] = rec["source_file"]
    recs.sort(key=lambda r: r["sort"])
    return recs


def main():
    recs = load()
    with open(OUT, "w") as fh:
        json.dump(recs, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    plies = sum(len(r["san"]) for r in recs)
    notes = sum(len(r["notes"]) for r in recs)
    print("wrote %d games to %s (%d plies, %d annotations, %d-%d)"
          % (len(recs), OUT, plies, notes, recs[0]["year"], recs[-1]["year"]))


if __name__ == "__main__":
    main()
