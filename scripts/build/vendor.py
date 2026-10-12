"""Fetch the third-party board assets into book/assets.

Run by hand (`make vendor`), never by the build: the book renders from what is
already on disk, and these files are committed. Every pin below is exact, so a
later run either writes the same bytes or says what changed.
"""

import os
import sys
import urllib.request

ASSETS = os.path.join(os.path.dirname(__file__), "..", "..", "book", "assets")

# name in book/assets -> where it came from
FILES = {
    # The board. Legality, SAN and the end of a game come from chess.js; the
    # squares and the dragging from chessground. Both are ES modules.
    "chessground.min.js":
        "https://unpkg.com/chessground@9.2.1/dist/chessground.min.js",
    "chess.js":
        "https://unpkg.com/chess.js@1.4.0/dist/esm/chess.js",
    # Stockfish 19, lite and single-threaded: the only build that needs no
    # SharedArrayBuffer, and so the only one GitHub Pages can serve, since it
    # cannot send the COOP and COEP headers the threaded builds require.
    "stockfish-19-lite-single.js":
        "https://github.com/nmrugg/stockfish.js/releases/download/v19.0.1/"
        "stockfish-19-lite-single.js",
    "stockfish-19-lite-single.wasm":
        "https://github.com/nmrugg/stockfish.js/releases/download/v19.0.1/"
        "stockfish-19-lite-single.wasm",
}


def get(url):
    print("  %s" % url)
    with urllib.request.urlopen(url) as fh:
        return fh.read()


def write(name, data):
    path = os.path.join(ASSETS, name)
    old = open(path, "rb").read() if os.path.exists(path) else None
    with open(path, "wb") as fh:
        fh.write(data)
    print("%-32s %7.1f KB %s"
          % (name, len(data) / 1024,
             "unchanged" if old == data else "new" if old is None else "CHANGED"))


def main():
    if not os.path.isdir(ASSETS):
        sys.exit("no %s" % ASSETS)
    for name, url in FILES.items():
        data = get(url)
        # The map is not shipped, so the comment pointing at it only makes the
        # browser ask for a file that is not there.
        if name.endswith(".js"):
            data = b"\n".join(l for l in data.split(b"\n")
                              if not l.startswith(b"//# sourceMappingURL="))
        write(name, data)


if __name__ == "__main__":
    main()
