# Historical Chess Games

## Building

```
uv sync          # chess and pyyaml, per pyproject.toml
make             # the list of targets
make all         # the data and the rendered book, into _site
make preview     # the book, served, with live reload
make check       # every audit
make clean
```

## Adding a game

From scratch:

```
make new SLUG=1963-byrne-fischer    # writes games/1963-byrne-fischer.yml
$EDITOR games/1963-byrne-fischer.yml
make all
```

From a downloaded PGN:

```
# save the game as drafts/<game id>.pgn, then
make import                         # -> games/<year>-<white>-<black>.yml
$EDITOR games/1862-steinitz-mongredien.yml
make all
```

The id is the number at the end of the game's URL, and the file name is how
the record learns which page to cite. Players, date, event, opening code,
result and moves are taken from the PGN; `title` and `why` must be manually edited.

Several PGNs can be dropped in and imported at once, an existing record is
never overwritten, and every move is replayed on a board at import and again
at build, so a PGN that did not copy cleanly is refused rather than published.


## The board

A game page shows a read-only viewer. Two modes take it over and give it back
where they found it, each recolouring the board while it has it: `Guess` asks
for the move the game made next, and judges any other legal move with
Stockfish, then plays it and either reads on (`▸`) or asks the next one
(`▸?`); `Explore` hands the position over to play on, with `vs` setting the
engine to answer at one of three strengths, and a take-back that undoes its
reply along with your move.

The viewer and the engine live in `book/assets` and are committed.
`make vendor` refetches them, from the pins in `scripts/build/vendor.py`; the
build itself fetches nothing.

## Publishing

```
git add -A && git commit -m "..." && git push
make publish
```

## Sources

The selection started from Wikipedia's
[list of chess games](https://en.wikipedia.org/wiki/List_of_chess_games). The
moves come from the game's page at
[chessgames.com](https://www.chessgames.com/) and, where the game has an
article of its own, from Wikipedia, with the two compared. Every source is
listed in the chapter that uses it and collected in the book's
[Sources](book/sources.qmd) appendix.

Nothing in this repository fetches anything. The game records were collected
once, by hand, and `games/` is the result; the build reads only what is already
on disk, so building the book does not go back to the sources it cites.
