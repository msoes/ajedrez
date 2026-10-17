"""Fill in a game's why from Wikipedia's list of chess games, with references.

    make why                      # write the sentence and its sources
    make why ARGS="--dry-run"     # what would change, and nothing written

Wikipedia's list of chess games gives each game a sentence saying why it is
remembered, and cites a page for it -- almost always the game's page at
chessgames.com. This reads that list and writes both into the record: the
sentence as the game's `why`, and the two pages as sources the why is
`cited_by`, so the sentence is footnoted where it is read and not merely
credited at the foot of the page.

A game is matched to its entry by the chessgames.com game id that both sides
already carry, which `make import` fills in from the PGN's file name. A game
whose record cites no id is matched on its year and the surname of each
player instead, and one that cannot be matched either way is reported.

Only a why that is empty, still the placeholder `make import` left, or ends in
a bare `(Wikipedia)` is written to. Prose written for this book is left alone
unless --force says otherwise, and no source is ever removed.

This fetches, and nothing else in the build does: it is run by hand, like
`make vendor`, and what it writes into games/ is what the book is built from.
The text it copies is Wikipedia's, under CC BY-SA, which is why the reference
it writes is not optional.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import gamespath  # noqa: F401,E402  -- project root on sys.path and as cwd

import argparse
import glob
import html
import json
import os
import re
import unicodedata
import urllib.request

import yaml

GAMES = "games"

PAGE = "List_of_chess_games"
LIST_URL = "https://en.wikipedia.org/wiki/" + PAGE
API = ("https://en.wikipedia.org/w/api.php?action=parse&page=%s"
       "&prop=text&formatversion=2&format=json" % PAGE)

# Wikimedia asks that a script say what it is and how to be reached.
UA = ("ajedrez/1.0 (+https://github.com/twaclaw/ajedrez) "
      "one-off annotation fetch")

WIKI_SOURCE = {
    "title": "List of chess games (Wikipedia)",
    "url": LIST_URL,
    "note": "the entry this game's description comes from",
}
CITATION_NOTE = "the page Wikipedia cites for the description"


# --- Wikipedia -------------------------------------------------------------

def fetch():
    req = urllib.request.Request(API, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as fh:
        return json.load(fh)["parse"]["text"]


# A full stop that ends the identification rather than an abbreviation in it:
# the entries run `1874: Knorre vs Chigorin, St. Petersburg. The sentence.`
ABBR = {"St", "Ste", "Mt", "Ft", "Dr", "Mr", "Mrs", "Jr", "Sr", "vs", "No", "c"}
SENTENCE = re.compile(r"\.\s+(?=[A-Z\"'“])")

TAG = re.compile(r"<[^>]+>")
REFMARK = re.compile(r"<sup[^>]*class=\"reference\".*?</sup>", re.S)
ENTRY = re.compile(r"<li>(<b>.*?)</li>", re.S)
FOOTNOTE = re.compile(r"<li id=\"cite(?:&#95;|_)note-([^\"]+)\">(.*?)</li>", re.S)
EXTERNAL = re.compile(r"class=\"external text\" href=\"([^\"]+)\">(.*?)</a>", re.S)
CITE_REF = re.compile(r"<a href=\"#cite_note-([^\"]+)\"")
GID = re.compile(r"chessgames\.com/perl/chessgame\?gid=(\d+)")
HEAD_YEAR = re.compile(r"^(?:c\.\s*)?(\d{4})")


def plain(markup):
    return " ".join(html.unescape(TAG.sub("", markup)).split())


def footnotes(doc):
    """Every reference on the page, by its number: the page it sends you to."""
    out = {}
    for key, body in FOOTNOTE.findall(doc):
        m = EXTERNAL.search(body)
        if m:
            # Wikipedia still cites a good many pages over http.
            out[key] = (m.group(1).replace("http://", "https://", 1),
                        plain(m.group(2)).strip('"'))
    return out


def split_entry(text):
    """`1923: A vs B, Copenhagen. Why.` -> the identification and the why."""
    for m in SENTENCE.finditer(text):
        head = text[:m.start()]
        last = re.split(r"[\s(]", head)[-1].rstrip(".")
        if last in ABBR or (len(last) == 1 and last.isupper()):
            continue
        return head, text[m.end():].strip()
    return text, ""


def entries(doc):
    """Each game the list names, with its sentence and what backs it."""
    notes = footnotes(doc)
    out = []
    for markup in ENTRY.findall(doc):
        refs = CITE_REF.findall(markup)
        head, why = split_entry(plain(REFMARK.sub("", markup)))
        year = HEAD_YEAR.match(head)
        cited = [notes[r] for r in refs if r in notes]
        if not why or not year:
            continue
        out.append({
            "head": head,
            "why": why,
            "year": int(year.group(1)),
            "cited": cited,
            "gids": [m.group(1) for url, _ in cited
                     for m in [GID.search(url)] if m],
        })
    return out


# --- the records -----------------------------------------------------------

WHY_BLOCK = re.compile(r"^why: >[ \t]*\n(?:[ \t]+[^\n]*\n)+", re.M)
WHY_PLACEHOLDER = re.compile(r"^# why: >[ \t]*\n(?:^#[ \t]+[^\n]*\n)+", re.M)
WHY_TEXT = re.compile(r"^why: >[ \t]*\n((?:[ \t]+[^\n]*\n)+)", re.M)
MOVES = re.compile(r"^moves:", re.M)
LOOSE_CREDIT = re.compile(r"\s*\((?:from\s+)?Wikipedia\)\s*\.?\s*$", re.I)


def wrap(text, width=76):
    """One sentence, folded the way the records are written by hand."""
    out, line = [], ""
    for word in text.split():
        if line and len(line) + len(word) + 1 > width:
            out.append(line)
            line = word
        else:
            line = (line + " " + word).strip()
    if line:
        out.append(line)
    return "".join("  %s\n" % l for l in out)


def current_why(text):
    m = WHY_TEXT.search(text)
    return " ".join(m.group(1).split()) if m else ""


def norm(url):
    url = re.sub(r"^https?://(www\.)?", "", url.strip().lower())
    return url.rstrip("/")


def surname(name):
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    name = re.sub(r"\(.*?\)|,.*", "", name).strip()
    parts = [p for p in name.split() if len(p) > 1]
    return parts[-1].lower() if parts else ""


def set_why(text, why):
    block = "why: >\n" + wrap(why)
    if WHY_BLOCK.search(text):
        return WHY_BLOCK.sub(lambda _: block, text, count=1)
    if WHY_PLACEHOLDER.search(text):
        return WHY_PLACEHOLDER.sub(lambda _: block, text, count=1)
    m = MOVES.search(text)
    if not m:
        return text.rstrip("\n") + "\n\n" + block
    return text[:m.start()] + block + "\n" + text[m.start():]


def sources_lines(text):
    """Where the sources list starts and ends, as line numbers."""
    lines = text.splitlines(True)
    start = next((n for n, l in enumerate(lines)
                  if re.match(r"^sources:[ \t]*$", l.rstrip("\n"))), None)
    if start is None:
        return None
    end = start + 1
    while end < len(lines) and (lines[end][:1] in (" ", "\t")
                                or not lines[end].strip()):
        end += 1
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1
    return lines, start, end


def items_of(block):
    items, cur = [], []
    for line in block:
        if re.match(r"^\s*-\s", line):
            if cur:
                items.append(cur)
            cur = [line]
        elif cur:
            cur.append(line)
    if cur:
        items.append(cur)
    return items


def url_of(item):
    m = re.search(r"^\s*url:\s*(\S+)", "".join(item), re.M)
    return m.group(1) if m else ""


def scalar(value):
    """A value written back as YAML, quoted when it has to be.

    Wikipedia's citation titles are headlines, and a headline often carries a
    colon -- `Mtel R1: Kramnik beats Ponomariov` -- which YAML reads as a
    mapping and the record then refuses to load. Rather than guess at which
    characters matter, the line is parsed back and quoted unless it reads as
    the string it was written from.
    """
    text = " ".join(str(value).split())
    try:
        if text and yaml.safe_load("v: " + text) == {"v": text}:
            return text
    except yaml.YAMLError:
        pass
    return "'%s'" % text.replace("'", "''")


def render_source(src, cited_by=""):
    out = ["  - title: %s\n" % scalar(src["title"]),
           "    url: %s\n" % scalar(src["url"])]
    if src.get("note"):
        out.append("    note: %s\n" % scalar(src["note"]))
    if cited_by:
        out.append("    cited_by: %s\n" % scalar(cited_by))
    return out


def cite_source(text, src, note=None):
    """Make sure the record carries this source, and that the why cites it."""
    split = sources_lines(text)
    if split is None:
        body = "".join(render_source(src, "why"))
        return text.rstrip("\n") + "\n\nsources:\n" + body
    lines, start, end = split
    items = items_of(lines[start + 1:end])

    for item in items:
        if norm(url_of(item)) != norm(src["url"]):
            continue
        if re.search(r"^\s*cited_by:", "".join(item), re.M):
            return text
        # The page is already cited for the moves; it is the same page the
        # sentence rests on, so it is marked rather than listed twice.
        while item and not item[-1].strip():
            item.pop()
        item.append("    cited_by: why\n")
        rebuilt = [l for it in items for l in it]
        return "".join(lines[:start + 1] + rebuilt + lines[end:])

    fresh = dict(src)
    if note is not None:
        fresh["note"] = note
    rebuilt = [l for it in items for l in it] + render_source(fresh, "why")
    return "".join(lines[:start + 1] + rebuilt + lines[end:])


# --- putting the two together ----------------------------------------------

def match(text, path, by_gid, by_name):
    for gid in GID.findall(text):
        if gid in by_gid:
            return by_gid[gid], "gid=%s" % gid
    m = re.match(r"^(\d{4})-(.+?)-(.+)$", os.path.splitext(os.path.basename(path))[0])
    if m:
        key = (int(m.group(1)), m.group(2), m.group(3))
        if key in by_name:
            return by_name[key], "%d %s/%s" % key
    return None, ""


def writable(text, force):
    """A why this script may write over, and why it may."""
    why = current_why(text)
    if not why:
        return True, "no why"
    if LOOSE_CREDIT.search(why):
        return True, "credits Wikipedia loosely"
    if force:
        return True, "--force"
    return False, "has its own why"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-n", "--dry-run", action="store_true",
                    help="say what would change and write nothing")
    ap.add_argument("-f", "--force", action="store_true",
                    help="write over a why that was written for this book")
    ap.add_argument("--html", metavar="FILE",
                    help="read the page from a file instead of fetching it")
    ap.add_argument("slugs", nargs="*",
                    help="only these games, by slug (default: all of them)")
    args = ap.parse_args()

    if args.html:
        doc = open(args.html, errors="replace").read()
    else:
        print("reading %s" % LIST_URL)
        doc = fetch()

    found = entries(doc)
    by_gid, by_name = {}, {}
    for e in found:
        for gid in e["gids"]:
            by_gid.setdefault(gid, e)
        head = unicodedata.normalize("NFKD", e["head"])
        head = head.encode("ascii", "ignore").decode()
        words = [w.lower() for w in re.findall(r"[A-Za-z]+", head)]
        for a in range(len(words)):
            for b in range(len(words)):
                by_name.setdefault((e["year"], words[a], words[b]), e)
    print("%d entries on the page, %d with a game id\n" % (len(found), len(by_gid)))

    paths = sorted(glob.glob(os.path.join(GAMES, "*.yml")))
    if args.slugs:
        want = {s.removesuffix(".yml") for s in args.slugs}
        paths = [p for p in paths
                 if os.path.splitext(os.path.basename(p))[0] in want]

    written, kept, unmatched = [], [], []
    for path in paths:
        text = open(path).read()
        entry, how = match(text, path, by_gid, by_name)
        slug = os.path.splitext(os.path.basename(path))[0]
        may, reason = writable(text, args.force)
        if not may:
            kept.append("%s (%s)" % (slug, reason))
            continue
        if entry is None:
            unmatched.append(slug)
            continue

        out = set_why(text, entry["why"])
        out = cite_source(out, WIKI_SOURCE)
        for url, title in entry["cited"]:
            out = cite_source(out, {"title": title or url, "url": url},
                              note=CITATION_NOTE)
        if out == text:
            kept.append("%s (already written)" % slug)
            continue

        print("  %-34s %s, %s" % (slug, how, reason))
        print("      %s" % entry["why"])
        if not args.dry_run:
            with open(path, "w") as fh:
                fh.write(out)
        written.append(slug)

    print("\n%s %d game(s)" % ("would write" if args.dry_run else "wrote",
                               len(written)))
    if kept:
        print("left alone %d: %s" % (len(kept), ", ".join(kept)))
    if unmatched:
        print("no entry on the page for %d: %s"
              % (len(unmatched), ", ".join(unmatched)))
    if written and not args.dry_run:
        print("\nnow: make all")


if __name__ == "__main__":
    main()
