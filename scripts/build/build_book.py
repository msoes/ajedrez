"""Generate the Quarto book from games.json.

Pages are content-only: a heading, a board carrying the PGN, and the data the
box under it reads. Everything about how those look belongs to book/theme.scss
and book/_includes, so restyling the book never means regenerating or
hand-editing a chapter.

The chronology is not written down anywhere. The chapters are ordered by date
and grouped into the eras records.py assigns, so a game added to games/ takes
its place in the book without any list being edited.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import gamespath  # noqa: F401,E402  -- project root on sys.path and as cwd

import collections
import html
import json
import os
import shutil

import yaml

from records import ERAS
from to_pgn import game_pgn

BOOK = "book"
GAMES = os.path.join(BOOK, "games")

# The chapters that are not games, in the order they appear. A chapter is
# listed only if its file is actually there, so deleting one removes it from
# the book instead of breaking the build: the hand-written chapters are the
# author's to keep or drop.
FRONT = ["index.qmd", "timeline.qmd", "method.qmd"]
BACK = ["sources.qmd", "adding-a-game.qmd"]

# Written on every build from the records, so they cannot fall behind the
# games they describe, and rewritten even when absent: they are not in the
# repository. To drop one from the book, take it out of this list.
GENERATED = {"timeline.qmd": "timeline_page", "sources.qmd": "sources_page"}

SCORE = {"1-0": "White won", "0-1": "Black won", "1/2-1/2": "Drawn",
         "*": "Unfinished"}


def game_data(rec):
    """What the board needs to say where it is, as JSON beside it.

    The page carries no move list of its own: the board is the move list, and
    this is what the box underneath it reads to name the move being shown and
    print any note on it.
    """
    notes = {}
    for note in rec["notes"]:
        notes.setdefault(str(note["ply"]), []).append(
            {"text": note["text"], "by": note["by"]})
    blob = json.dumps({"san": rec["san"], "marks": rec["marks"],
                       "notes": notes}, ensure_ascii=False)
    return ('<script type="application/json" class="game-data">%s</script>'
            % blob.replace("</", "<\\/"))


def board_html(rec):
    pgn = game_pgn(rec).replace("</script>", "<\\/script>")
    return ('<div class="pgn-board" data-orientation="%s">'
            '<script type="text/pgn">%s</script></div>'
            % (html.escape(rec["orientation"], quote=True), pgn))


def follow_html():
    """The box under the board, which names the move and carries its note.

    With no move list beside the board this is the only place the notes are
    read, so it is always shown rather than offered: hiding it would hide the
    annotation and the reader's place in the game at once.
    """
    return ('<div class="move-text">'
            '<p class="move-text__move"></p>'
            '<div class="move-text__notes"></div></div>')


def sources_html(rec):
    """The sources, numbered, because the why refers to them by number."""
    items = []
    for n, src in enumerate(rec["sources"], 1):
        note = (' <span class="source-note">%s</span>' % html.escape(src["note"])
                if src["note"] else "")
        items.append('<li id="src-%d"><a href="%s">%s</a>%s</li>'
                     % (n, html.escape(src["url"], quote=True),
                        html.escape(src["title"]), note))
    return ('<div class="game-sources"><h2>Sources</h2>'
            '<ol>%s</ol></div>' % "".join(items))


def why_html(rec):
    """The why, and a reference to each source the sentence rests on.

    The sentence is often not this book's own, and the mark after it says so
    where it is read. The number is the source's place in the list at the foot
    of the page, and the link goes to it rather than straight out, so the
    reader is shown what they are being sent to before they go.
    """
    marks = "".join('<a href="#src-%d">[%d]</a>' % (n, n) for n in rec["why_cites"])
    cite = '<sup class="game-cite">%s</sup>' % marks if marks else ""
    return '<p class="game-why">%s%s</p>' % (html.escape(rec["why"]), cite)


def downloads_html(rec):
    return ('<div class="downloads">'
            '<a class="download" href="../downloads/pgn/%s.pgn" download>'
            "PGN, with the notes as move comments</a>"
            '<a class="download" href="../downloads/games/%s">'
            "Source record</a></div>"
            % (rec["slug"], os.path.basename(rec["source_file"])))


def head_html(rec):
    meta = [rec["date"], rec["era"]]
    if rec["opening"]:
        meta.append(rec["opening"] + (" (%s)" % rec["eco"] if rec["eco"] else ""))
    elif rec["eco"]:
        meta.append(rec["eco"])

    where = [bit for bit in (rec["event"], rec["site"]) if bit]
    players = (
        '<div class="game-players">'
        '<span class="player">%s</span>'
        '<span class="versus">vs</span>'
        '<span class="player">%s</span>'
        '<span class="score" title="%s">%s</span></div>'
        % (html.escape(rec["white"]), html.escape(rec["black"]),
           html.escape(SCORE[rec["result"]], quote=True),
           html.escape(rec["result"])))

    out = ['<div class="game-head">',
           '<div class="game-meta">%s</div>'
           % html.escape(" &middot; ".join(meta)).replace("&amp;middot;", "&middot;"),
           players]
    if where:
        out.append('<div class="game-where">%s</div>'
                   % html.escape(", ".join(where)))
    out.append('<hr class="game-rule">')
    if rec["why"]:
        out.append(why_html(rec))
    if rec["summary"]:
        out.append('<p class="game-summary">%s</p>' % html.escape(rec["summary"]))
    if rec["result_note"]:
        out.append('<div class="game-note">%s</div>'
                   % html.escape(rec["result_note"]))
    out.append("</div>")
    return "".join(out)


def page(rec):
    body = [
        '<div class="game-page">',
        head_html(rec),
        '<div class="game-board">',
        board_html(rec), game_data(rec), follow_html(),
        "</div>",
        sources_html(rec),
        downloads_html(rec),
        "</div>",
    ]
    # A PGN carries a mandatory blank line between its tags and its moves,
    # which would end an ordinary raw-HTML block and orphan every div after
    # it. A fenced raw block passes the whole page through untouched.
    front = yaml.safe_dump(
        {"title": "%d \u00b7 %s" % (rec["year"], rec["title"]),
         "pagetitle": "%s, %s vs %s, %d"
                      % (rec["title"], rec["white"], rec["black"], rec["year"]),
         "description": rec["why"] or rec["summary"][:160]},
        allow_unicode=True, sort_keys=False).strip()
    return "---\n%s\n---\n\n```{=html}\n%s\n```\n" % (
        front, "\n".join(b for b in body if b))


def timeline_page(recs):
    """The whole book as one table, oldest first.

    Written on every build, so it cannot fall behind the games it lists.
    """
    blurbs = {name: blurb for _, _, name, blurb in ERAS}
    by_era = collections.OrderedDict()
    for rec in recs:
        by_era.setdefault(rec["era"], []).append(rec)

    out = ["# The games {.unnumbered}", "",
           "%d games, %d to %d, oldest first. Every one of them has been "
           "replayed move by move on a board before being published here, and "
           "every one names the source its moves were read from."
           % (len(recs), recs[0]["year"], recs[-1]["year"]), ""]

    # The notes column appears only when there is something in it, so an
    # unannotated book does not carry an empty column down every page.
    noted = any(r["notes"] for r in recs)
    head = "| Year | Game | Players | Result | Moves |"
    rule = "| ---: | --- | --- | :-: | -: |"
    if noted:
        head += " Notes |"
        rule += " -: |"

    for name, games in by_era.items():
        out += ["## %s" % name, "", blurbs[name], "", head, rule]
        for rec in games:
            row = ("| %s | [%s](games/%s.qmd) | %s &ndash; %s | %s | %d |"
                   % (rec["year"], rec["title"], rec["slug"],
                      rec["white"], rec["black"], rec["result"],
                      (len(rec["san"]) + 1) // 2))
            if noted:
                row += " %s |" % (len(rec["notes"]) or "")
            out.append(row)
        out.append("")
    return "\n".join(out)


def sources_page(recs):
    """Every source, game by game, and every site they came from."""
    out = ["# Sources {.unnumbered}", "",
           "Where each game's moves were read from. Nothing here is a "
           "reconstruction: the moves were taken from a published record, "
           "replayed on a board to check that every one of them is legal, and "
           "cross-checked against the result the source reports. Where two "
           "sources disagreed, both are listed and the chapter says so.", "",
           "The notes are written for this book unless the note says whose "
           "judgement it is reporting. Where a note carries a name, that name "
           "is the person the assessment belongs to, and the source it was "
           "read in is listed with the game.", ""]

    sites = collections.Counter()
    for rec in recs:
        out += ["## %d &middot; %s {.unnumbered}" % (rec["year"], rec["title"]),
                ""]
        for src in rec["sources"]:
            note = " &mdash; %s" % src["note"] if src["note"] else ""
            out.append("- [%s](%s)%s" % (src["title"], src["url"], note))
            host = src["url"].split("/")[2] if "//" in src["url"] else src["url"]
            sites[host.replace("www.", "")] += 1
        out.append("")

    out += ["## Where the moves came from, counted {.unnumbered}", "",
            "| Site | Games cited |", "| --- | -: |"]
    for host, n in sites.most_common():
        out.append("| %s | %d |" % (host, n))
    out.append("")
    return "\n".join(out)


def copy_downloads(recs):
    """The published files, where the book can serve them."""
    out = os.path.join(BOOK, "downloads")
    if os.path.isdir(out):
        shutil.rmtree(out)
    for kind in ("pgn", "games"):
        os.makedirs(os.path.join(out, kind), exist_ok=True)
    for rec in recs:
        pgn = os.path.join("pgn", rec["slug"] + ".pgn")
        if os.path.exists(pgn):
            shutil.copy2(pgn, os.path.join(out, "pgn"))
        shutil.copy2(rec["source_file"], os.path.join(out, "games"))


def present(names):
    """Only the chapters that exist, in the order given."""
    return [n for n in names if os.path.exists(os.path.join(BOOK, n))]


def chapter_list(recs):
    """The front matter, then one part per era that has games in it."""
    chapters = list(present(FRONT))
    for _, _, name, _ in ERAS:
        games = [r for r in recs if r["era"] == name]
        if games:
            chapters.append({"part": name,
                             "chapters": ["games/%s.qmd" % r["slug"]
                                          for r in games]})
    return chapters


def main():
    recs = json.load(open("games.json"))
    copy_downloads(recs)
    os.makedirs(GAMES, exist_ok=True)
    for old in os.listdir(GAMES):
        path = os.path.join(GAMES, old)
        shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)

    for rec in recs:
        with open(os.path.join(GAMES, rec["slug"] + ".qmd"), "w") as fh:
            fh.write(page(rec))

    for name, fn in GENERATED.items():
        with open(os.path.join(BOOK, name), "w") as fh:
            fh.write(globals()[fn](recs))

    cfg_path = os.path.join(BOOK, "_quarto.yml")
    cfg = yaml.safe_load(open(cfg_path))
    cfg["book"]["chapters"] = chapter_list(recs)
    cfg["book"]["appendices"] = present(BACK)
    with open(cfg_path, "w") as fh:
        yaml.safe_dump(cfg, fh, sort_keys=False, allow_unicode=True,
                       width=100)

    print("wrote %d game pages to %s/ (%d notes across them)"
          % (len(recs), GAMES, sum(len(r["notes"]) for r in recs)))


if __name__ == "__main__":
    main()
