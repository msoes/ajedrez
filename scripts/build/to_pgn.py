"""Emit one PGN per game, with the annotations as move comments.

Generated from games.json, never hand-edited. The PGN is what a reader takes
away to their own board, so it carries the provenance too: the tags name the
source the moves were read from.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import gamespath  # noqa: F401,E402  -- project root on sys.path and as cwd

import json
import os
import re
import textwrap

OUT = "pgn"


def clean_comment(text):
    """PGN comments are brace-delimited, so braces cannot appear inside."""
    return re.sub(r"\s+", " ", text.replace("{", "(").replace("}", ")")).strip()


def pgn_date(rec):
    parts = rec["sort"][:3]
    return "%04d.%s.%s" % (parts[0],
                           "%02d" % parts[1] if parts[1] else "??",
                           "%02d" % parts[2] if parts[2] else "??")


def game_pgn(rec):
    tags = [
        ("Event", rec["event"] or "?"),
        ("Site", rec["site"] or "?"),
        ("Date", pgn_date(rec)),
        ("Round", "-"),
        ("White", rec["white"]),
        ("Black", rec["black"]),
        ("Result", rec["result"]),
    ]
    if rec["eco"]:
        tags.append(("ECO", rec["eco"]))
    if rec["opening"]:
        tags.append(("Opening", rec["opening"]))
    if rec["start_fen"]:
        tags.append(("SetUp", "1"))
        tags.append(("FEN", rec["start_fen"]))
    if rec["notes"]:
        tags.append(("Annotator", "chess_games"))
    for i, src in enumerate(rec["sources"]):
        suffix = "" if i == 0 else str(i + 1)
        tags.append(("Source" + suffix, src["title"]))
        tags.append(("SourceURL" + suffix, src["url"]))
    if rec["result_note"]:
        tags.append(("ResultNote", rec["result_note"]))

    # A tag is one line, and its value is delimited by quotes, so neither a
    # line break nor a quote can survive inside one.
    head = "".join('[%s "%s"]\n'
                   % (k, " ".join(str(v).split()).replace('"', "'"))
                   for k, v in tags)

    by_ply = {}
    for note in rec["notes"]:
        label = (note["by"] + ": ") if note["by"] else ""
        by_ply.setdefault(note["ply"], []).append(label + note["text"])

    body = []
    for i, san in enumerate(rec["san"]):
        if i % 2 == 0:
            body.append("%d." % (i // 2 + 1))
        body.append(san + rec["marks"].get(str(i), ""))
        if i in by_ply:
            body.append("{%s}" % clean_comment("  ".join(by_ply[i])))
    body.append(rec["result"])

    return head + "\n" + textwrap.fill(" ".join(body), 96) + "\n"


def main():
    recs = json.load(open("games.json"))
    os.makedirs(OUT, exist_ok=True)
    for old in os.listdir(OUT):
        os.remove(os.path.join(OUT, old))
    for rec in recs:
        with open(os.path.join(OUT, rec["slug"] + ".pgn"), "w") as fh:
            fh.write(game_pgn(rec))
    print("wrote %d PGN files to %s/" % (len(recs), OUT))


if __name__ == "__main__":
    main()
