# Games not yet in the book

Every game in Wikipedia's [list of chess games](https://en.wikipedia.org/wiki/List_of_chess_games) that this book does not have: **6** of them. Nothing here was left out for want of a source. The book stops at forty because that is where the selection stopped.

## How to add one

1. Open the game's page in your browser and copy its PGN.
2. Save it in this folder as `<game id>.pgn` -- the id is the number at the
   end of the URL, so the Steinitz-Mongredien game below becomes
   `drafts/1001497.pgn`. The name matters: it is how the record learns which
   page to cite.
3. Run `make import`. Each PGN becomes `games/<year>-<white>-<black>.yml`
   with the players, date, event, opening code, result and moves already
   filled in, and the source pointing back at the page.
4. Run `make why`. Where Wikipedia's list describes the game, its sentence
   becomes the record's `why` and the two pages behind it become sources the
   why cites. A game the list does not have is left for you to write.
5. Open the new record and give the game a `title`. Rename the file if you
   would rather it had a different slug.
6. `make all`, then `make check`.

Every move is replayed on a board at import and again at build, so a PGN
that did not copy cleanly will be refused rather than published.

A game with its own Wikipedia article is marked **W** below: for those the
move list can be taken from the article instead, and cited to it.

## The games

| Year | Game | PGN from |
| ---: | --- | --- |
| c. 1933 | Albert Einstein vs  Oppenheimer | _no id in the list_ |
