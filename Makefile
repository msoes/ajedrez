# Historical Chess Games -- a Quarto book built from games/*.yml

PY    := uv run python
BUILD := scripts/build

# The games, by the name each is published under. Adding a file to games/ is
# enough: the records, the PGN and the chapters all follow from it.
RECORDS := $(wildcard games/*.yml)

# The chapters and the downloads are committed, so the book renders and
# publishes on its own. Where the build scripts are present, rendering waits
# on them as usual.
ifneq ($(wildcard $(BUILD)/build_book.py),)
CHAPTERS := book/games/.stamp
endif

CYAN  := \033[36m
BOLD  := \033[1m
RESET := \033[0m

.PHONY: help all book site preview publish check new import why vendor clean clean-data
.DEFAULT_GOAL := help

## Show this help
help:
	@printf "$(BOLD)Historical Chess Games$(RESET) -- a Quarto book built from games/*.yml\n\n"
	@awk '/^# --- / { gsub(/^# --- | -*$$/, ""); printf "\n$(BOLD)%s$(RESET)\n", $$0; next } \
	    /^## / { d = substr($$0, 4); next } \
	    /^[a-zA-Z0-9_\/.-]+:/ && d { split($$0, t, ":"); \
	      printf "  $(CYAN)%-12s$(RESET) %s\n", t[1], d; d = "" }' \
	    $(MAKEFILE_LIST)
	@printf "\n  Add a game: $(CYAN)make new SLUG=1960-spassky-bronstein$(RESET)\n\n"

## Build the data and render the book
all: book

# --- The data --------------------------------------------------------------

## Replay every game and write games.json
games.json: $(RECORDS) $(BUILD)/records.py
	$(PY) $(BUILD)/records.py

pgn/.stamp: games.json $(BUILD)/to_pgn.py
	$(PY) $(BUILD)/to_pgn.py
	@mkdir -p pgn && touch $@

## Write one PGN per game, notes included
pgn: pgn/.stamp

# --- The book --------------------------------------------------------------

book/games/.stamp: games.json pgn/.stamp $(BUILD)/build_book.py \
                   book/theme.scss book/_includes/head.html book/_includes/foot.html
	$(PY) $(BUILD)/build_book.py
	@touch $@

## Regenerate the chapters from the data
chapters: book/games/.stamp

# Quarto renders each chapter beside its source and then moves it into the
# output directory. A cache left from an earlier run makes it try to move a
# file it did not write this time, which fails with a bare "NotFound"; both
# are cleared first so a build is always reproducible.
## Render the book into _site
site: $(CHAPTERS)
	rm -rf book/.quarto book/site_libs _site/site_libs
	find book/games -name '*.html' -delete
	cd book && quarto render

book: site

## Serve the book with live reload
preview: $(CHAPTERS)
	cd book && quarto preview

## Push the rendered book to GitHub Pages
publish: site
	cd book && quarto publish gh-pages --no-render

# --- Vendoring -------------------------------------------------------------

## Refetch the board, engine and piece assets into book/assets
vendor:
	$(PY) $(BUILD)/vendor.py

# --- Adding and checking games --------------------------------------------

## Turn PGNs saved in drafts/ into game records
import:
	$(PY) $(BUILD)/from_pgn.py

# Fetches, like `make vendor`, and for the same reason: what it writes is a
# record, kept in games/, and the build never goes back for it.
## Write each why from Wikipedia's list, with its references (ARGS=--dry-run)
why:
	$(PY) $(BUILD)/why_from_wikipedia.py $(ARGS)

## Write a blank game record (SLUG=1960-spassky-bronstein)
new:
	@test -n "$(SLUG)" || { echo "give a slug: make new SLUG=1960-spassky-bronstein"; exit 1; }
	$(PY) $(BUILD)/new_game.py $(SLUG)

## Run every check against the records
check: games.json pgn/.stamp book/games/.stamp
	$(PY) $(BUILD)/check.py

## Remove the rendered site
clean:
	rm -rf _site book/site_libs book/.quarto

## Remove the generated data and chapters as well
clean-data: clean
	rm -rf pgn book/games book/downloads
	rm -f games.json book/timeline.qmd book/sources.qmd
