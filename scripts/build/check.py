"""Every check the published book rests on.

records.py already refuses to build a game whose moves are not playable, so
this is what is left: that the PGN written out plays back to the same game,
that nothing is published twice, and that the book's own table of contents
points at files that exist.

Run by `make check`. A failure is a non-zero exit and a line naming the game.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import gamespath  # noqa: F401,E402  -- project root on sys.path and as cwd

import io
import json
import os
import re

import chess
import chess.pgn
import yaml


def fail(problems, game, message):
    problems.append("%s: %s" % (game, message))


def check_pgn_roundtrip(rec, problems):
    """The published PGN must replay to exactly the game it came from.

    This is the check that matters most to a reader, because the PGN is what
    they take away. It is read back with a parser that was not involved in
    writing it.
    """
    path = os.path.join("pgn", rec["slug"] + ".pgn")
    if not os.path.exists(path):
        return fail(problems, rec["slug"], "no PGN was written")
    game = chess.pgn.read_game(open(path))
    if game is None:
        return fail(problems, rec["slug"], "the PGN does not parse")
    if game.errors:
        return fail(problems, rec["slug"],
                    "the PGN parses with errors: %s" % game.errors[0])
    board = game.board()
    san = []
    for move in game.mainline_moves():
        san.append(board.san(move))
        board.push(move)
    if san != rec["san"]:
        for i, (a, b) in enumerate(zip(san, rec["san"])):
            if a != b:
                return fail(problems, rec["slug"],
                            "the PGN differs from the record at ply %d: "
                            "%s against %s" % (i, a, b))
        return fail(problems, rec["slug"],
                    "the PGN holds %d plies, the record %d"
                    % (len(san), len(rec["san"])))
    if game.headers["Result"] != rec["result"]:
        fail(problems, rec["slug"], "the PGN result disagrees with the record")


def check_game(rec, problems):
    if rec["checkmate"] and not rec["san"][-1].endswith("#"):
        fail(problems, rec["slug"], "the last move mates but is not marked #")
    if not rec["checkmate"] and rec["san"][-1].endswith("#"):
        fail(problems, rec["slug"], "the last move is marked # but does not mate")
    for src in rec["sources"]:
        if not src["url"].startswith(("http://", "https://")):
            fail(problems, rec["slug"], "source %r is not a URL" % src["url"])
    # A sentence borrowed from somewhere else is footnoted, not credited in
    # passing: `make why` writes the reference, and a bare "(Wikipedia)" left
    # at the end of a why means it was pasted in by hand and never was.
    if re.search(r"\((?:from\s+)?Wikipedia\)\s*\.?\s*$", rec["why"], re.I):
        fail(problems, rec["slug"],
             "the why credits Wikipedia in passing; run `make why` to replace "
             "it with a reference to the source it came from")
    if rec["why"] and not rec["why"].rstrip().endswith((".", "!", "?", '"')):
        fail(problems, rec["slug"], "the why does not end in a full stop")
    for note in rec["notes"]:
        if len(note["text"]) < 20:
            fail(problems, rec["slug"],
                 "note (%s) is too short to be worth a reference"
                 % note["letter"])
    # A draw agreed in a dead-drawn position is normal; a draw claimed in a
    # position one side is mating in is worth a second look.
    if rec["result"] == "*":
        fail(problems, rec["slug"], "the result is unknown")


def check_book(recs, problems):
    cfg = yaml.safe_load(open(os.path.join("book", "_quarto.yml")))
    listed = []
    for item in cfg["book"]["chapters"]:
        listed += item["chapters"] if isinstance(item, dict) else [item]
    listed += cfg["book"].get("appendices", [])
    for name in listed:
        if not os.path.exists(os.path.join("book", name)):
            fail(problems, "book", "_quarto.yml lists %s, which is missing"
                 % name)
    for rec in recs:
        name = "games/%s.qmd" % rec["slug"]
        if name not in listed:
            fail(problems, rec["slug"], "the book does not list its chapter")


def check_corpus(recs, problems):
    seen_moves, seen_titles = {}, {}
    for rec in recs:
        key = " ".join(rec["san"])
        if key in seen_moves:
            fail(problems, rec["slug"], "the same moves as %s" % seen_moves[key])
        seen_moves[key] = rec["slug"]
        if rec["title"].lower() in seen_titles:
            fail(problems, rec["slug"],
                 "the same title as %s" % seen_titles[rec["title"].lower()])
        seen_titles[rec["title"].lower()] = rec["slug"]
    order = [r["sort"] for r in recs]
    if order != sorted(order):
        fail(problems, "book", "the games are not in chronological order")


def main():
    recs = json.load(open("games.json"))
    problems = []
    for rec in recs:
        check_game(rec, problems)
        check_pgn_roundtrip(rec, problems)
    check_corpus(recs, problems)
    check_book(recs, problems)
    if problems:
        print("\n".join(["%d problem(s):" % len(problems)]
                        + ["  " + p for p in problems]))
        raise SystemExit(1)
    print("checked %d games: every move legal, every PGN replays to its "
          "record, every chapter listed" % len(recs))


if __name__ == "__main__":
    main()
