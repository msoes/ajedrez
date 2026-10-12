// The board a reader can play on: guess the move the game went on to make,
// or take the position over and try something else.
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

const DEPTH = 10;       // deep enough to tell a blunder from a choice, and quick
const MATE = 10000;     // a mate outscores any amount of material

// What the engine plays like as an opponent. Skill Level is Stockfish's own
// handicap and a shallow search blunts it further: the point is a game a child
// can win, not a good one. Level 0 is no opponent at all.
const LEVELS = [null, { skill: 0, depth: 4 },
                      { skill: 3, depth: 8 },
                      { skill: 8, depth: 12 }];


// --- The engine ------------------------------------------------------------
// A megabyte and a half of WebAssembly, so it is started by the first guess
// that needs judging and never on a page that is only read. Single-threaded
// on purpose: the threaded builds want SharedArrayBuffer, which wants COOP and
// COEP headers, which GitHub Pages cannot send.

let engine = null;

function stockfish() {
  if (engine) return engine;

  const worker = new Worker(
    new URL('./stockfish-19-lite-single.js', import.meta.url));
  let pending = null;

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
  let turn = ask('uci', /^uciok/).then(() => ask('isready', /^readyok/));
  const queued = fn => {
    const result = turn.then(fn, fn);
    turn = result.catch(() => {});
    return result;
  };

  // Skill Level sticks until it is set again, so every search says what it
  // wants: judging a guess is always done at full strength.
  const search = (fen, skill, depth) => {
    worker.postMessage('setoption name Skill Level value ' + skill);
    worker.postMessage('position fen ' + fen);
    return ask('go depth ' + depth, /^bestmove/);
  };

  engine = {
    // What the engine makes of a position, in centipawns, from the point of
    // view of whoever is to move in it.
    score(fen) {
      return queued(async () => {
        const lines = await search(fen, 20, DEPTH);
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

    // The move the engine would play, as the two squares it moves between.
    // Nothing comes back from a position that is already over.
    reply(fen, level) {
      const { skill, depth } = LEVELS[level];
      return queued(async () => {
        const lines = await search(fen, skill, depth);
        for (let i = lines.length - 1; i >= 0; i--) {
          const m = /^bestmove (\S+)/.exec(lines[i]);
          if (m) return m[1] === '(none)' ? null : m[1];
        }
        return null;
      });
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

// --- The two modes ---------------------------------------------------------

const LEVEL_KEY = 'chess-engine-level';

function storedLevel() {
  try {
    return Math.max(0, Math.min(LEVELS.length - 1, +localStorage.getItem(LEVEL_KEY)));
  } catch { return 0; }
}

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

export function attach({ boardEl, lpv, game }) {
  const column = boardEl.parentElement;
  // The viewer patches itself over the element it was handed, so it is found
  // rather than kept: what was passed to it is no longer in the page.
  const viewer = () => boardEl.querySelector('.lpv:not(.sandbox)');
  const bar = document.createElement('div');
  bar.className = 'board-bar';
  boardEl.after(bar);

  const guessBtn = button('Guess', 'Guess the next move');
  const exploreBtn = button('Explore', 'Play on from this position');
  const undoBtn = button('↶', 'Take the move back');
  const vsBtn = button('vs', 'Let the engine answer');
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
  let level = storedLevel();   // how strong the opponent is, 0 for none
  let side = null;    // the colour the engine answers as
  let turn = 0;       // bumped to drop an answer that is no longer wanted
  let answered = false;   // a guess has been made and judged

  function paint() {
    bar.textContent = '';
    if (!mode) {
      bar.append(guessBtn, exploreBtn);
      guessBtn.disabled = !game.san[lpv.path.size()];
    } else if (mode === 'explore') {
      vsBtn.textContent = 'vs' + (level ? ' ' + '•'.repeat(level) : '');
      vsBtn.setAttribute('aria-pressed', level ? 'true' : 'false');
      vsBtn.title = level ? 'The engine answers; again for a stronger one'
                          : 'Let the engine answer';
      bar.append(undoBtn, vsBtn, backBtn);
      undoBtn.disabled = !chess.history().length;
      verdict.textContent = chess.history().join(' ');
      verdict.className = 'verdict verdict--line';
      bar.appendChild(verdict);
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

  // The engine's answer, if one was asked for. It is fetched while the board
  // is frozen, and dropped if the reader takes the move back or leaves in the
  // meantime -- the first answer of all has a megabyte and a half to load.
  async function engineReply() {
    if (!level || chess.isGameOver() || colourOf(chess) !== side) return;
    const mine = ++turn;
    ground.set({ movable: { color: undefined } });
    verdict.textContent = chess.history().join(' ') + ' …';
    const uci = await stockfish().reply(chess.fen(), level);
    if (mine !== turn || mode !== 'explore') return;
    if (uci) {
      const from = uci.slice(0, 2), to = uci.slice(2, 4);
      chess.move({ from, to, promotion: uci.slice(4, 5) || undefined });
      sync([from, to]);
    }
    paint();
  }

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
    }
    paint();
    if (mode === 'explore') engineReply();
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
      drawable: { enabled: false }
    });
    column.classList.add('is-' + which);
    // The engine takes the side the reader is not about to move.
    side = which === 'explore' ? other(colourOf(chess)) : null;
    verdict.textContent = '';
    verdict.className = 'verdict';
    answered = false;
    if (which === 'guess') {
      answer = game.san[lpv.path.size()];
      verdict.className = 'verdict verdict--ask';
      verdict.textContent = colourOf(chess) === 'white' ? 'White?' : 'Black?';
    }
    paint();
  }

  // Back to the game, at the move it was left on -- or one further, which is
  // how a right guess becomes the move the reader goes on to read about.
  function leave(forward) {
    if (!mode) return;
    turn++;
    ground.destroy();
    host.remove();
    viewer().style.display = '';
    column.classList.remove('is-guess', 'is-explore');
    mode = null;
    chess = null;
    lpv.toPath(resume);
    if (forward) lpv.goTo('next');
    paint();
  }

  guessBtn.addEventListener('click', () => enter('guess'));
  onBtn.addEventListener('click', () => leave(1));
  againBtn.addEventListener('click', () => { leave(1); enter('guess'); });
  exploreBtn.addEventListener('click', () => enter('explore'));
  backBtn.addEventListener('click', () => leave(0));
  vsBtn.addEventListener('click', () => {
    level = (level + 1) % LEVELS.length;
    try { localStorage.setItem(LEVEL_KEY, level); } catch { /* private window */ }
    if (level === 1) side = other(colourOf(chess));
    paint();
  });

  undoBtn.addEventListener('click', () => {
    turn++;
    if (!chess.undo()) return;
    // Against an opponent a take-back undoes its answer too, so what comes
    // back is the reader's own move rather than the engine's.
    if (level && colourOf(chess) === side) chess.undo();
    const last = chess.history({ verbose: true }).slice(-1)[0];
    sync(last ? [last.from, last.to] : null);
    paint();
  });

  paint();
  // The viewer's own navigation decides whether there is a move left to guess.
  return { refresh: () => { if (!mode) paint(); } };
}
