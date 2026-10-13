// The board a reader can play on: guess the move the game went on to make,
// or take the position over and analyse it.
//
// Both modes need move input, which the viewer the book embeds cannot give.
// It is read-only by construction: it hard-codes draggable, selectable and
// movable off after its own options, and binds no drag listeners at all when
// it starts out view-only, so there is nothing to switch on afterwards. The
// two modes therefore share a board of their own, mounted over the viewer and
// handed the position the viewer is showing. Leaving a mode throws that board
// away and puts the viewer back where it was.

import { Chessground } from './chessground.min.js';
import { Chess } from './chess.js';
import { SETS } from './pieces/sets.js';

const JUDGE_DEPTH = 10;   // deep enough to tell a blunder from a choice, and quick
const ANALYSE_DEPTH = 12; // the suggested moves, where a little more is worth it
const ENRICH_DEPTH = 10;  // the background replies: shallow, so they land fast
const CANDIDATES = 4;     // the moves Explore offers for the side to move
const REPLIES = 3;        // the answers it gathers for each of them
const MATE = 10000;       // a mate outscores any amount of material


// --- The engine ------------------------------------------------------------
// A megabyte and a half of WebAssembly, so it is started by the first guess
// that needs judging and never on a page that is only read. Single-threaded
// on purpose: the threaded builds want SharedArrayBuffer, which wants COOP and
// COEP headers, which GitHub Pages cannot send.
//
// Explore leans on MultiPV: one search returns the best few moves at once,
// each with the line that follows it. The same search answers both questions
// it asks -- what to play and what comes next -- and its `pv` supplies the
// reply that is shown before any background search has run.

let engine = null;

// The moves in a batch of `info ... multipv N ... pv ...` lines, one per
// index, the deepest reading the search reached for each. Nothing comes back
// from a position that is already over.
function pvs(lines) {
  const found = new Map();
  for (const line of lines) {
    const index = /\bmultipv (\d+)/.exec(line);
    const sc = /\bscore (cp|mate) (-?\d+)/.exec(line);
    const pv = /\bpv (.+)$/.exec(line);
    if (!index || !sc || !pv) continue;
    const moves = pv[1].trim().split(/\s+/);
    found.set(parseInt(index[1], 10), {
      uci: moves[0],
      pv: moves,
      score: { type: sc[1], n: parseInt(sc[2], 10) }
    });
  }
  return [...found.keys()].sort((a, b) => a - b).map(k => found.get(k));
}

function stockfish() {
  if (engine) return engine;

  const worker = new Worker(
    new URL('./stockfish-19-lite-single.js', import.meta.url));
  let pending = null;
  let searching = false;
  let gen = 0;

  worker.onmessage = e => {
    const line = typeof e.data === 'string' ? e.data : (e.data && e.data.data);
    if (!line || !pending) return;
    pending.lines.push(line);
    if (pending.until.test(line)) {
      const done = pending;
      pending = null;
      done.resolve(done.lines);
    }
  };

  const ask = (cmd, until) => new Promise(resolve => {
    pending = { lines: [], until, resolve };
    worker.postMessage(cmd);
  });

  // One worker answers one question at a time, so questions wait their turn.
  // A failed one must not jam the queue behind it.
  let turn = ask('uci', /^uciok/).then(() => ask('isready', /^readyok/)).then(() => {
    worker.postMessage('setoption name Skill Level value 20');
  });
  // A queued question is dropped whole if the reader has moved on by the time
  // its turn comes: it was asked about a position no longer on the board.
  const queued = fn => {
    const mine = gen;
    const run = () => (mine === gen ? fn() : null);
    const result = turn.then(run, run);
    turn = result.then(() => {}, () => {});
    return result;
  };

  // Every search says what it wants: Skill Level and MultiPV both stick.
  const search = (fen, multipv, depth) => {
    worker.postMessage('setoption name MultiPV value ' + multipv);
    worker.postMessage('position fen ' + fen);
    searching = true;
    return ask('go depth ' + depth, /^bestmove/)
      .finally(() => { searching = false; });
  };

  engine = {
    // What the engine makes of a position, in centipawns, from the point of
    // view of whoever is to move in it.
    score(fen) {
      return queued(async () => {
        const lines = await search(fen, 1, JUDGE_DEPTH);
        // The last line carrying a score is the deepest the search reached;
        // the bestmove line that ends it carries none.
        for (let i = lines.length - 1; i >= 0; i--) {
          const m = /\bscore (cp|mate) (-?\d+)/.exec(lines[i]);
          if (!m) continue;
          const n = parseInt(m[2], 10);
          return m[1] === 'cp' ? n : n > 0 ? MATE - n : -MATE - n;
        }
        return 0;
      });
    },

    // The best few moves for the side to move, each with its own line. The
    // score is from that side's point of view, like score().
    candidates(fen) {
      return queued(async () =>
        pvs(await search(fen, CANDIDATES, ANALYSE_DEPTH)).slice(0, CANDIDATES));
    },

    // The best few answers to a move already made, from the position it
    // leaves; the score is from the answering side's point of view.
    replies(fen) {
      return queued(async () =>
        pvs(await search(fen, REPLIES, ENRICH_DEPTH)).slice(0, REPLIES));
    },

    // Drop everything not yet run and cut the search in flight, so a reader
    // who moves on does not wait behind answers to a position they left.
    abort() {
      gen++;
      if (searching) worker.postMessage('stop');
    }
  };
  return engine;
}


// --- Rules and pieces ------------------------------------------------------

// Chessground asks, for every square a piece can leave, which squares it can
// reach. chess.js knows, which keeps the rules in one place.
function destinations(chess) {
  const dests = new Map();
  for (const move of chess.moves({ verbose: true })) {
    const to = dests.get(move.from) || [];
    if (!to.includes(move.to)) to.push(move.to);
    dests.set(move.from, to);
  }
  return dests;
}

function promotionsFor(chess, from, to) {
  return chess.moves({ verbose: true })
    .filter(m => m.from === from && m.to === to && m.promotion)
    .map(m => m.promotion);
}

const ROLES = { q: 'queen', r: 'rook', b: 'bishop', n: 'knight' };

// A pawn reaching the last rank asks what it becomes. The pieces are drawn by
// the viewer's own stylesheet, which wants each of them under a .cg-wrap.
function askPromotion(host, options, colour) {
  return new Promise(resolve => {
    const pane = document.createElement('div');
    pane.className = 'promo';
    for (const option of options) {
      const btn = document.createElement('button');
      btn.className = 'promo__pick';
      btn.title = ROLES[option];
      btn.innerHTML = '<span class="cg-wrap"><piece class="'
        + ROLES[option] + ' ' + colour + '"></piece></span>';
      btn.addEventListener('click', () => { pane.remove(); resolve(option); });
      pane.appendChild(btn);
    }
    host.appendChild(pane);
  });
}

// A move as UCI gives it, and back. UCI carries the promotion letter as a
// fifth character, which chess.js wants as its own field.
const decode = uci => ({
  from: uci.slice(0, 2),
  to: uci.slice(2, 4),
  promotion: uci.slice(4, 5) || undefined
});

function positionAfter(fen, uci) {
  const chess = new Chess(fen);
  chess.move(decode(uci));
  return chess.fen();
}

function sanIn(fen, uci) {
  const chess = new Chess(fen);
  const move = chess.move(decode(uci));
  return move ? move.san : uci;
}

// --- The pieces ------------------------------------------------------------
// The set is a class on the document and a line in localStorage, so a reader
// who prefers another keeps it across the whole book. Each set but the default
// is one stylesheet, fetched the first time it is chosen; a reader who never
// chooses fetches none, because the viewer's own stylesheet carries that one.

const PIECE_KEY = 'chess-pieces';
const DEFAULT_SET = SETS[0].id;
const fetched = new Set();

function storedSet() {
  try {
    const saved = localStorage.getItem(PIECE_KEY);
    return SETS.some(s => s.id === saved) ? saved : DEFAULT_SET;
  } catch { return DEFAULT_SET; }
}

function usePieces(id) {
  if (id !== DEFAULT_SET && !fetched.has(id)) {
    fetched.add(id);
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = new URL('./pieces/' + id + '.css', import.meta.url);
    document.head.appendChild(link);
  }
  for (const s of SETS)
    document.documentElement.classList.toggle('pieces-' + s.id, s.id === id);
}

export function initPieces() {
  usePieces(storedSet());
}

// The picker, and beside it whoever drew what is on the board: three of these
// sets are CC BY, which asks for the name, and the rest ask that their notice
// travel with them.
function picker() {
  const row = document.createElement('div');
  row.className = 'board-pieces';

  const label = document.createElement('label');
  label.className = 'board-pieces__label';
  label.htmlFor = 'board-pieces-select';
  label.textContent = 'Pieces';

  const select = document.createElement('select');
  select.id = 'board-pieces-select';
  select.title = 'The pieces';
  for (const set of SETS) {
    const option = document.createElement('option');
    option.value = set.id;
    option.textContent = set.id;
    select.appendChild(option);
  }

  const credit = document.createElement('span');
  credit.className = 'board-pieces__by';

  function show() {
    const set = SETS.find(s => s.id === select.value) || SETS[0];
    credit.textContent = set.by + ' \u00B7 ' + set.licence;
  }
  select.value = storedSet();
  show();

  select.addEventListener('change', () => {
    usePieces(select.value);
    try { localStorage.setItem(PIECE_KEY, select.value); } catch { /* private */ }
    show();
  });

  row.append(label, select, credit);
  return row;
}


// --- The two modes ---------------------------------------------------------

// How a guess is answered. The face is thrown over the board big enough to
// read from across a room, and says the same thing as the colour.
const GRADES = {
  right: { face: '🎉', why: 'the move the game made' },
  same:  { face: '👍', why: 'as good as the move the game made' },
  fair:  { face: '🤔', why: 'playable, but not what was played' },
  weak:  { face: '❌', why: 'it costs material' }
};

const colourOf = chess => (chess.turn() === 'w' ? 'white' : 'black');
const other = colour => (colour === 'white' ? 'black' : 'white');
const bare = san => san.replace(/[!?]+$/, '');

function button(label, title) {
  const btn = document.createElement('button');
  btn.className = 'board-bar__btn';
  btn.textContent = label;
  btn.title = title;
  return btn;
}

// An evaluation as a reader reads one: from White's side throughout, so the
// sign means the same thing at every depth of the tree. Mate folded.
function evaluation(score, white) {
  const n = white ? score.n : -score.n;
  if (score.type === 'mate') return n > 0 ? '#' + n : '#-' + Math.abs(n);
  const pawns = n / 100;
  return (pawns > 0 ? '+' : '') + pawns.toFixed(2);
}

export function attach({ boardEl, lpv, game }) {
  const column = boardEl.parentElement;
  // The viewer patches itself over the element it was handed, so it is found
  // rather than kept: what was passed to it is no longer in the page.
  const viewer = () => boardEl.querySelector('.lpv:not(.sandbox)');
  // The set is a preference, not a move, so it sits above the board and stays
  // put whichever mode the board is in.
  column.insertBefore(picker(), boardEl);

  const bar = document.createElement('div');
  bar.className = 'board-bar';
  boardEl.after(bar);

  // The tree, shown only while exploring. It goes below the box that names the
  // move on the board, so the proposals read as a continuation of it.
  const treeEl = document.createElement('div');
  treeEl.className = 'board-tree';
  treeEl.hidden = true;
  const head = document.createElement('div');
  head.className = 'board-tree__head';
  const crumb = document.createElement('div');
  crumb.className = 'board-tree__crumb';
  const list = document.createElement('ol');
  list.className = 'board-tree__list';
  treeEl.append(head, crumb, list);
  (column.querySelector('.move-text') || boardEl).after(treeEl);

  const guessBtn = button('Guess', 'Guess the next move');
  const exploreBtn = button('Explore', 'Analyse this position');
  const undoBtn = button('↶', 'Take the move back');
  const onBtn = button('▸', 'Play the move and read on');
  const againBtn = button('▸?', 'Play the move and guess the next one');
  const backBtn = button('↩︎', 'Back to the game');
  const verdict = document.createElement('span');
  verdict.className = 'verdict';

  let mode = null;    // null, 'guess' or 'explore'
  let chess = null;   // the rules, from the position the mode started at
  let ground = null;
  let host = null;    // the frame put over the viewer
  let square = null;  // the board inside it
  let answer = null;  // in guess mode, the move the game actually made
  let resume = null;  // where the viewer was when the mode was entered
  let answered = false;   // a guess has been made and judged

  // Explore, specifically: the line played from the position it started at,
  // and a cache so stepping back and forth does not re-ask the engine.
  let rootFen = null;
  let path = [];        // [{ uci, san }] from rootFen
  let entryPly = 0;     // where that position sits in the game, for the note
  let seq = 0;          // bumped on every analysis; drops a stale render
  const cache = new Map();   // fen -> { candidates, complete }

  function paint() {
    bar.textContent = '';
    if (!mode) {
      bar.append(guessBtn, exploreBtn);
      guessBtn.disabled = !game.san[lpv.path.size()];
    } else if (mode === 'explore') {
      undoBtn.disabled = path.length === 0;
      bar.append(undoBtn, backBtn, verdict);
    } else if (answered) {
      // The game is one move further on than the board: either way out of
      // here plays it, so a reader can read on or go straight to the next
      // question without first going back.
      againBtn.disabled = !game.san[resume.size() + 1];
      bar.append(onBtn, againBtn, backBtn, verdict);
    } else {
      bar.append(backBtn, verdict);
    }
  }

  function sync(lastMove) {
    ground.set({
      fen: chess.fen(),
      turnColor: colourOf(chess),
      check: chess.isCheck(),
      lastMove,
      movable: {
        color: chess.isGameOver() ? undefined : colourOf(chess),
        dests: destinations(chess)
      }
    });
  }

  // --- Guessing ------------------------------------------------------------

  // Judging a guess that is not the move the game made: the question is not
  // whether it differs but whether it costs anything, so the engine scores the
  // position each move leaves behind. Both scores are read from the guesser's
  // side, which is the side that is no longer to move once a move is made.
  async function judge(fen, after) {
    verdict.textContent = '…';
    verdict.className = 'verdict verdict--thinking';
    const played = new Chess(fen);
    played.move(answer);
    const sf = stockfish();
    const [mine, theirs] = await Promise.all([
      sf.score(after.fen()), sf.score(played.fen())
    ]);
    const cost = (-theirs) - (-mine);
    return cost <= 30 ? 'same' : cost <= 100 ? 'fair' : 'weak';
  }

  async function guessed(fen, move) {
    const right = bare(move.san) === bare(answer);
    let grade = right ? 'right'
      : chess.isCheckmate() ? 'same'
      : await judge(fen, chess);

    const { face, why } = GRADES[grade];
    verdict.className = 'verdict verdict--' + grade;
    verdict.textContent = right ? face + ' ' + answer
                                : face + ' ' + move.san + '  → ' + answer;
    verdict.title = why;

    const flash = document.createElement('div');
    flash.className = 'flash flash--' + grade;
    flash.textContent = face;
    square.appendChild(flash);
    setTimeout(() => flash.remove(), 1500);

    answered = true;
  }

  // --- Exploring -----------------------------------------------------------
  // Explore shows the engine's suggestions for the position on the board, with
  // its best answers to each, and the reader picks one -- or plays their own
  // move, which is treated the same. Picking a suggestion plays it and shows
  // the position it leads to, so the tree rolls forward one move at a time.

  function setStatus(text) {
    verdict.textContent = text;
    verdict.className = 'verdict' + (text ? ' verdict--line' : '');
  }

  // An arrow from a move, in chessground's own brushes: the candidate in blue,
  // the reply that hangs off it in yellow, so a hovered pair reads as two
  // moves rather than one.
  const arrow = (uci, brush) => ({
    orig: uci.slice(0, 2), dest: uci.slice(2, 4), brush
  });

  function row(san, score, white, mark) {
    const line = document.createElement('span');
    line.className = 'tree__row';
    if (mark) {
      const pip = document.createElement('span');
      pip.className = 'tree__game';
      pip.textContent = '◆';
      pip.title = 'the move the game played';
      line.appendChild(pip);
    }
    const text = document.createElement('span');
    text.className = 'tree__san';
    text.textContent = san;
    const value = document.createElement('span');
    value.className = 'tree__eval';
    value.textContent = score ? evaluation(score, white) : '';
    line.append(text, value);
    return line;
  }

  function renderCrumb() {
    crumb.textContent = '';
    // The root names the move that produced the position Explore began at,
    // rather than a home icon, so the breadcrumb reads as a game line. At the
    // very start of a game there is no such move, and the icon stands in.
    const start = document.createElement('button');
    start.className = 'crumb__node crumb__root';
    start.title = 'the position you started from';
    if (entryPly > 0) {
      const ply = entryPly - 1;
      start.textContent = (Math.floor(ply / 2) + 1) + (ply % 2 ? '…' : '.')
        + game.san[ply];
    } else {
      start.textContent = '\u2302';
    }
    start.disabled = path.length === 0;
    start.addEventListener('click', () => goTo(0));
    crumb.appendChild(start);
    // Numbered by the move's real ply in the game, not by its place here, so a
    // reader who entered mid-game sees the moves they actually are.
    path.forEach((move, i) => {
      const ply = entryPly + i;
      const node = document.createElement('button');
      node.className = 'crumb__node';
      node.textContent = (Math.floor(ply / 2) + 1) + (ply % 2 ? '…' : '.') + move.san;
      node.disabled = i === path.length - 1;
      node.addEventListener('click', () => goTo(i + 1));
      crumb.appendChild(node);
    });
  }

  // The move the game itself made from this position, if the reader is still
  // on the game's line: once they play something else, there is no such move.
  // It comes back as UCI too, so it can be played like any proposal.
  function gameMove() {
    for (let i = 0; i < path.length; i++)
      if (bare(path[i].san) !== bare(game.san[entryPly + i] || '')) return null;
    const ply = entryPly + path.length;
    if (ply >= game.san.length) return null;
    const wanted = bare(game.san[ply]);
    for (const move of chess.moves({ verbose: true }))
      if (bare(move.san) === wanted)
        return { uci: move.from + move.to + (move.promotion || ''), san: move.san };
    return null;
  }

  function renderTree(node) {
    // A re-render replaces the rows the hover was bound to, so any arrow the
    // reader was showing goes with them.
    ground.setAutoShapes([]);
    list.textContent = '';
    head.textContent = (node.white ? 'White' : 'Black')
      + ' to move \u2014 proposed by Stockfish';
    const played = gameMove();
    const playedSan = played ? bare(played.san) : null;
    let playedListed = false;
    node.candidates.forEach((candidate, i) => {
      const li = document.createElement('li');
      li.className = 'tree__cand' + (i === 0 ? ' tree__cand--best' : '');
      const game = playedSan !== null && bare(candidate.san) === playedSan;
      if (game) playedListed = true;
      li.appendChild(row(candidate.san, candidate.score, node.white, game));
      // Hovering a candidate draws it; hovering a reply draws it and the
      // candidate it hangs under, so the parent is never lost.
      const mine = [arrow(candidate.uci, 'blue')];
      li.addEventListener('click', () => advance([candidate.uci]));
      li.addEventListener('mouseenter', () => ground.setAutoShapes(mine));
      li.addEventListener('mouseleave', () => ground.setAutoShapes([]));
      if (candidate.replies.length) {
        const ul = document.createElement('ul');
        ul.className = 'tree__replies';
        candidate.replies.forEach(reply => {
          const rli = document.createElement('li');
          rli.className = 'tree__reply'
            + (reply.score ? '' : ' tree__reply--pending');
          rli.appendChild(row(reply.san, reply.score, !node.white));
          rli.addEventListener('click', ev => {
            ev.stopPropagation();
            advance([candidate.uci, reply.uci]);
          });
          rli.addEventListener('mouseenter', () =>
            ground.setAutoShapes([...mine, arrow(reply.uci, 'yellow')]));
          rli.addEventListener('mouseleave', () =>
            ground.setAutoShapes(mine));
          ul.appendChild(rli);
        });
        li.appendChild(ul);
      }
      list.appendChild(li);
    });
    // The engine did not propose the move the game played. It is still the
    // game's move, so it gets a row of its own, played the same way.
    if (played && !playedListed) {
      const li = document.createElement('li');
      li.className = 'tree__cand tree__game-move';
      li.appendChild(row(played.san, null, node.white, true));
      li.addEventListener('click', () => advance([played.uci]));
      li.addEventListener('mouseenter', () =>
        ground.setAutoShapes([arrow(played.uci, 'blue')]));
      li.addEventListener('mouseleave', () => ground.setAutoShapes([]));
      list.appendChild(li);
    }
    renderCrumb();
  }

  function renderNone() {
    list.textContent = '';
    head.textContent = 'No moves: the game is over.';
    const li = document.createElement('li');
    li.className = 'board-tree__none';
    li.textContent = 'No moves: the game is over.';
    list.appendChild(li);
    renderCrumb();
  }

  // Turn the engine's batch into what the tree draws: the moves for the side
  // to move, and -- from each line's second move -- one answer apiece, shown
  // before any background search has run.
  function build(fen, batch) {
    const white = colourOf(new Chess(fen)) === 'white';
    const candidates = batch.map(p => {
      const child = positionAfter(fen, p.uci);
      const reply = p.pv[1];
      return {
        uci: p.uci,
        san: sanIn(fen, p.uci),
        score: p.score,
        replies: reply
          ? [{ uci: reply, san: sanIn(child, reply), score: null }]
          : []
      };
    });
    return { candidates, white, complete: false };
  }

  // The background searches: one per candidate, from the position it leaves,
  // adding the answers the first search did not have. They update the tree as
  // they land and are dropped whole if the reader has moved in the meantime.
  async function enrich(fen, node, mine) {
    const sf = stockfish();
    await Promise.all(node.candidates.map(async candidate => {
      const child = positionAfter(fen, candidate.uci);
      const replies = await sf.replies(child);
      if (mine !== seq || !replies) return;
      candidate.replies = replies.map(r => ({
        uci: r.uci, san: sanIn(child, r.uci), score: r.score
      }));
      renderTree(node);
    }));
    if (mine === seq) node.complete = true;
  }

  async function analyse() {
    treeEl.hidden = false;
    const fen = chess.fen();
    const mine = ++seq;
    const first = !engine;
    const sf = stockfish();
    sf.abort();

    const cached = cache.get(fen);
    if (cached) {
      renderTree(cached);
      setStatus('');
      if (!cached.complete) enrich(fen, cached, mine);
      return;
    }

    setStatus(first ? 'loading…' : '…');
    const batch = await sf.candidates(fen);
    if (mine !== seq || !batch) return;
    if (!batch.length) { renderNone(); setStatus(''); return; }

    const node = build(fen, batch);
    cache.set(fen, node);
    renderTree(node);
    setStatus('');
    enrich(fen, node, mine);
  }

  // Play the moves and analyse what they lead to. A reply is two moves -- the
  // candidate it hangs under and the answer itself -- so picking one skips the
  // position between them.
  function advance(moves) {
    let last = null;
    for (const uci of moves) {
      const move = chess.move(decode(uci));
      if (!move) return;
      path.push({ uci, san: move.san });
      last = [uci.slice(0, 2), uci.slice(2, 4)];
    }
    sync(last);
    paint();
    analyse();
  }

  // Back to the n-th move of the line already played.
  function goTo(n) {
    chess = new Chess(rootFen);
    let last = null;
    for (let i = 0; i < n; i++) {
      const uci = path[i].uci;
      chess.move(decode(uci));
      last = [uci.slice(0, 2), uci.slice(2, 4)];
    }
    path = path.slice(0, n);
    sync(last);
    paint();
    analyse();
  }

  // --- Entering and leaving ------------------------------------------------

  async function moved(orig, dest) {
    const fen = chess.fen();
    const options = promotionsFor(chess, orig, dest);
    const promotion = options.length
      ? await askPromotion(square, options, colourOf(chess)) : undefined;
    const move = chess.move({ from: orig, to: dest, promotion });
    // Chessground has shown the piece arriving, but a castle moves a rook too,
    // a capture en passant clears a square the piece never touched, and a
    // promotion changes what landed, so the position is set from the rules.
    sync([orig, dest]);
    if (mode === 'guess') {
      ground.set({ movable: { color: undefined } });
      await guessed(fen, move);
      paint();
    } else if (mode === 'explore') {
      // A move the reader played rather than picked: it joins the line the
      // same way, and the engine is asked afresh from where it left off.
      path.push({ uci: orig + dest + (promotion || ''), san: move.san });
      paint();
      analyse();
    }
  }

  function enter(which) {
    if (which === 'guess' && !game.san[lpv.path.size()]) return;
    mode = which;
    resume = lpv.path;
    chess = new Chess(lpv.curData().fen);
    viewer().style.display = 'none';
    // The viewer's own frame, mounted the way it mounts its board: the grid
    // that sizes one sizes the other, so switching modes moves nothing.
    host = document.createElement('div');
    host.className = 'lpv lpv--moves-false sandbox';
    const area = document.createElement('div');
    area.className = 'lpv__board';
    square = document.createElement('div');
    area.appendChild(square);
    host.appendChild(area);
    boardEl.appendChild(host);
    ground = Chessground(square, {
      fen: chess.fen(),
      orientation: boardEl.dataset.orientation || 'white',
      turnColor: colourOf(chess),
      check: chess.isCheck(),
      addDimensionsCssVarsTo: host,
      animation: { enabled: true, duration: 180 },
      highlight: { lastMove: true, check: true },
      movable: {
        free: false,
        color: colourOf(chess),
        dests: destinations(chess),
        showDests: true,
        events: { after: moved }
      },
      draggable: { enabled: true, showGhost: true },
      selectable: { enabled: true },
      // Drawing is on only while exploring, where the hover arrows need it and
      // a reader's own right-click arrows are a help rather than a distraction.
      drawable: { enabled: which === 'explore' }
    });
    column.classList.add('is-' + which);
    verdict.textContent = '';
    verdict.className = 'verdict';
    answered = false;
    if (which === 'guess') {
      answer = game.san[lpv.path.size()];
      verdict.className = 'verdict verdict--ask';
      verdict.textContent = colourOf(chess) === 'white' ? 'White?' : 'Black?';
    } else {
      rootFen = chess.fen();
      entryPly = resume.size();
      path = [];
      analyse();
    }
    paint();
  }

  // Back to the game, at the move it was left on -- or one further, which is
  // how a right guess becomes the move the reader goes on to read about.
  function leave(forward) {
    if (!mode) return;
    engine && engine.abort();
    seq++;
    ground.destroy();
    host.remove();
    viewer().style.display = '';
    column.classList.remove('is-guess', 'is-explore');
    treeEl.hidden = true;
    list.textContent = '';
    crumb.textContent = '';
    mode = null;
    chess = null;
    path = [];
    lpv.toPath(resume);
    if (forward) lpv.goTo('next');
    paint();
  }

  guessBtn.addEventListener('click', () => enter('guess'));
  onBtn.addEventListener('click', () => leave(1));
  againBtn.addEventListener('click', () => { leave(1); enter('guess'); });
  exploreBtn.addEventListener('click', () => enter('explore'));
  backBtn.addEventListener('click', () => leave(0));
  undoBtn.addEventListener('click', () => {
    if (path.length) goTo(path.length - 1);
  });

  paint();
  // The viewer's own navigation decides whether there is a move left to guess.
  return { refresh: () => { if (!mode) paint(); } };
}
