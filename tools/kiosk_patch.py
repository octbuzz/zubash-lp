# -*- coding: utf-8 -*-
"""キオスク（gamescom 試遊台の自動ローテーション）まわりの改造。

素の書き出しのキオスクは「セクションを1440px幅で組んで画面に収まるよう一様縮小し、
18秒ずつ送る」だけで、試遊台の 1920x1080 には合っていなかった。実測したところ：

  * 縮小率がセクションごとに 0.57〜1.28 とバラバラで、Rules は 0.571 倍。
    本文19pxが **9.1px** まで縮み、1920幅のうち877pxしか使えていなかった
  * 縦長の原因は文字量ではなく構造（ヘッダ＋大ブロックの縦積み）。
    幅を変えても高さはほとんど変わらない＝文章を削るだけでは直らない
  * 全ブロックが英・独・日の3言語で、画面上の文字量を押し上げていた

そこで以下を当てている。

  1. PV（動画）をローテーションの1枚目として差し込む
  2. 動画フレームは動画の尺で送る（終了イベントでも送る）
  3. 音を出す（自動再生ポリシー上ミュート開始→最初のユーザー操作で解除）
  4. 全画面表示
  5. **1920x1080 向けのスライド組み直し**（下記）
  6. フッターだけのフレームをローテーションから外す
  7. キオスク離脱時のイベント購読解除（解除漏れの不具合修正）

## 5. スライドの組み直し

  * キャンバス幅 1440 → **1280**。拡大率の上限が 1920/1280*0.96 = **1.44 倍**になる
  * 縦の余白（スクロール前提で広い）を **0.45倍**に詰める
  * **日本語ブロックと100字超の解説文を落とす**。試遊台では口頭で説明するので、
    画面に残すのは見出し・数値・短いラベルと独語の要約でよい
  * 小さすぎる字に下限（13px）を入れる
  * それでも 1スライドに収まらないセクションは、**ヘッダを繰り返しつつ自動でページ分割**する

  実測（余白0.45・日本語と長文を除いた高さ / 幅1280）:
    Hero 803 / Goal 1215 / Rules 1236 / Controls 1177 / Gimmicks 926 /
    Characters 650 / Stage 815 … 予算 750 を超えるものが分割対象。

原本の DOM には触らず**複製**でスライドを作るため、離脱時に元へ戻す処理が要らない。
"""

# ── 1枚あたりの表示秒数 ──────────────────────────────────────────────────
# 書き出し時点の既定値は18秒。展示では長すぎたので半分にする。
# props の既定値と JS 側のフォールバックの両方を書き換える（実行時に効くのは props）。
SECONDS_PER_PAGE = 9

PROPS_OLD = "&quot;kioskSeconds&quot;:{&quot;editor&quot;:&quot;range&quot;,&quot;default&quot;:18,"
PROPS_NEW = "&quot;kioskSeconds&quot;:{&quot;editor&quot;:&quot;range&quot;,&quot;default&quot;:%d," % SECONDS_PER_PAGE

# ── スライド組版のパラメータ ────────────────────────────────────────────
KIOSK_W = 1280        # スライドを組むキャンバス幅
KIOSK_FIT = 0.96      # 画面に対する余白率（元の実装と同じ）
SPACE_K = 0.45        # 縦の余白の圧縮率
FONT_MIN = 13         # 拡大前の最小フォントサイズ
MAX_CHARS = 100       # これより長い文章は画面に出さない（口頭で説明する）
# 幅で頭打ちになる最大倍率にちょうど収まる高さ = 1080 / (1920/W) / FIT
BUDGET = int(1080 / (1920 / KIOSK_W) / KIOSK_FIT)

# ── 通常表示の <video> に操作UIを付ける ──────────────────────────────────
# dc のテンプレートコンパイラは値なしの controls 属性を落とす
# （playsinline は残るのに controls だけ消える）。マウント時に JS で付け直す。
MOUNT_OLD = "  componentDidMount() { setTimeout(() => this.initKiosk(), 60); }"
MOUNT_NEW = """  componentDidMount() {
    document.querySelectorAll('video').forEach((v) => { v.controls = true; });
    setTimeout(() => this.initKiosk(), 60);
  }"""

# ── PV セクション（ローテーションの1枚目）────────────────────────────────
HERO_ANCHOR = '<section data-screen-label="Hero"'

PV_SECTION = """<section data-screen-label="PV" style="position: relative; background: #0E1116; overflow: hidden; display: flex; align-items: center; justify-content: center;">
    <video id="zb-pv" playsinline preload="metadata" poster="pv-poster.jpg" controls style="display: block; width: 100%; height: auto; aspect-ratio: 3 / 2; max-height: 78vh; background: #0E1116; object-fit: contain;">
      <source src="pv.mp4" type="video/mp4">
    </video>
    <div style="position: absolute; left: 24px; top: 20px; display: flex; gap: 10px; align-items: center; pointer-events: none;">
      <span style="font-family: 'Barlow Condensed', sans-serif; font-weight: 700; font-size: 13px; letter-spacing: 0.22em; text-transform: uppercase; color: #0E1116; background: #C7F000; padding: 5px 12px;">PV</span>
      <span style="font-family: 'Barlow Condensed', sans-serif; font-weight: 600; font-size: 13px; letter-spacing: 0.22em; text-transform: uppercase; color: #F4F1EA; border: 1.5px solid rgba(244,241,234,0.45); padding: 4px 12px;">ZUBASH</span>
    </div>
  </section>

  """

# ── キオスク実装の全面差し替え ──────────────────────────────────────────
# kioskExit / componentWillUnmount / initKiosk の3メソッドを丸ごと置き換える。
# 範囲は「  kioskExit() {」から「  renderVals()」の直前まで。
import re

_REGION = re.compile(r"  kioskExit\(\) \{.*?(?=\n  renderVals\(\))", re.S)

_IMPL = r"""  _fsEl() {
    return document.fullscreenElement || document.webkitFullscreenElement || null;
  }
  _fsSupported() {
    return !!(document.fullscreenEnabled || document.webkitFullscreenEnabled);
  }
  _fsEnter() {
    const el = document.documentElement;
    const req = el.requestFullscreen || el.webkitRequestFullscreen;
    if (!req) return Promise.reject(new Error('unsupported'));
    try { return Promise.resolve(req.call(el)); } catch (e) { return Promise.reject(e); }
  }
  _fsLeave() {
    const ex = document.exitFullscreen || document.webkitExitFullscreen;
    if (!ex || !this._fsEl()) return;
    try { ex.call(document); } catch (e) {}
  }
  _fsToggle() {
    if (this._fsEl()) this._fsLeave();
    else this._fsEnter().catch(() => {});
  }

  kioskExit() {
    if (!this._kioskOn) return;
    clearInterval(this._tick);
    this._fsLeave();
    (this._vids || []).forEach((v) => { v.pause(); try { v.currentTime = 0; } catch (e) {} });
    this._vids = null;
    this._soundArmed = false;
    // 購読を外す。外さないと通常表示に戻ったあとも Space が preventDefault され、
    // スペースキーでページをスクロールできなくなる。
    if (this._onKey) window.removeEventListener('keydown', this._onKey);
    if (this._onResize) window.removeEventListener('resize', this._onResize);
    if (this._onGesture) window.removeEventListener('pointerdown', this._onGesture);
    if (this._onFsChange) {
      document.removeEventListener('fullscreenchange', this._onFsChange);
      document.removeEventListener('webkitfullscreenchange', this._onFsChange);
    }
    this._onKey = this._onResize = this._onGesture = this._onFsChange = null;
    // スライドは複製なので、キオスクUIごと捨てれば原本はそのまま残る。
    document.querySelectorAll('[data-kiosk-ui]').forEach((n) => n.remove());
    document.body.style.overflow = '';
    this._kioskOn = false;
    this._dismissed = true;
  }
  componentWillUnmount() { clearInterval(this._tick); }

  /* 要素の位置を root からの子インデックス列で表す（複製間で対応を取るため）。 */
  _pathOf(el, root) {
    const p = [];
    while (el && el !== root) {
      p.unshift(Array.prototype.indexOf.call(el.parentNode.children, el));
      el = el.parentNode;
    }
    return p;
  }
  _atPath(root, path) {
    let el = root;
    for (const i of path) { if (!el) return null; el = el.children[i]; }
    return el;
  }

  /* 1920x1080 向けにスライドを組む。原本には触らず複製で作る。 */
  _kioskSlides(host) {
    const W = __KIOSK_W__, BUDGET = __BUDGET__, SPACE_K = __SPACE_K__;
    const FONT_MIN = __FONT_MIN__, MAX_CHARS = __MAX_CHARS__;
    // 日本語を含む「最も内側の」要素だけを消す。`3 Rounds / 3ラウンド制` のような
    // 英日混在では、外側を消すと英語まで失われ、比率で判定すると取りこぼす
    // （実際 0.357 で英語ごと消え、0.33 の `/ 各120秒` は残った）。
    // 内側だけを狙えば、英語を残したまま日本語だけを落とせる。
    const hasJP = (s) => /[぀-ヿ㐀-鿿]/.test(s);
    // ブロック要素を含まない＝それ自体がひと塊の文章、と見なす。<strong>/<em> を
    // 含む段落を取りこぼさないため、葉ノード判定ではなくこちらを使う。
    const BLOCKY = 'div,p,section,article,ul,ol,li,table,img,video,svg,h1,h2,h3,h4,header,footer,figure';
    const VSPACE = ['paddingTop', 'paddingBottom', 'marginTop', 'marginBottom', 'rowGap'];
    const prep = (el) => {
      // 展示では口頭で説明するので、日本語と長い解説文は画面に出さない。
      // まず日本語（内側から）。
      el.querySelectorAll('*').forEach((e) => {
        const t = (e.textContent || '').trim();
        if (!t || !hasJP(t)) return;
        if (Array.from(e.children).some((c) => hasJP(c.textContent || ''))) return;
        e.style.display = 'none';
      });
      // 次に長い解説文。日本語を消した後の「実際に見えている文字数」で測る。
      el.querySelectorAll('*').forEach((e) => {
        if (getComputedStyle(e).display === 'none' || e.querySelector(BLOCKY)) return;
        const t = (e.innerText || '').trim().replace(/\s+/g, ' ');
        if (t.length > MAX_CHARS) e.style.display = 'none';
      });
      // 縦の余白はスクロール前提で広いので詰める。小さすぎる字には下限を入れる。
      [el].concat(Array.from(el.querySelectorAll('*'))).forEach((e) => {
        const cs = getComputedStyle(e);
        VSPACE.forEach((p) => {
          const v = parseFloat(cs[p]);
          if (v > 0) e.style[p] = (v * SPACE_K).toFixed(1) + 'px';
        });
        const fs = parseFloat(cs.fontSize);
        if (fs && fs < FONT_MIN) e.style.fontSize = FONT_MIN + 'px';
      });
    };
    const H = (el) => el.getBoundingClientRect().height;
    const slides = [];
    Array.from(document.querySelectorAll('section[data-screen-label]')).forEach((sec) => {
      const label = sec.getAttribute('data-screen-label');
      const base = sec.cloneNode(true);
      base.style.width = W + 'px';
      host.appendChild(base);
      if (label !== 'PV') prep(base);
      if (label === 'PV' || H(base) <= BUDGET) { slides.push(base); return; }

      // 収まらないので分割する。コンテナ（単一子を辿った先）の子をページに詰める。
      let c = base;
      while (c.children.length === 1 && c.children[0].children.length) c = c.children[0];
      const kids = Array.from(c.children).filter((k) => getComputedStyle(k).display !== 'none');
      // ヒーローのように絶対配置で重ねてある構成は切り出せないので1枚のまま出す。
      if (kids.some((k) => getComputedStyle(k).position === 'absolute')) { slides.push(base); return; }
      // 先頭の小さい要素（見出し帯・H2・独語リード）はヘッダ扱いで全ページに残す。
      let hi = 0;
      while (hi < kids.length && H(kids[hi]) <= 150) hi++;
      const headerH = kids.slice(0, hi).reduce((a, k) => a + H(k), 0);
      const room = Math.max(120, BUDGET - headerH);
      // 本文パーツ。単体で溢れるものは1段だけ子へ降りる（Way A/B や ギミック8枚）。
      const parts = [];
      kids.slice(hi).forEach((el) => {
        if (H(el) > room && el.children.length > 1) Array.from(el.children).forEach((x) => parts.push(x));
        else parts.push(el);
      });
      // グリッドや横並びの子は縦に積み上がらないので「行」にまとめてから詰める。
      // これをやらないとギミックのカード8枚が1枚ずつ別ページになる。
      const rows = [];
      parts.forEach((p) => {
        const r = p.getBoundingClientRect();
        if (r.height < 4) return;
        const last = rows[rows.length - 1];
        if (last && Math.abs(last.top - r.top) < 24) {
          last.items.push(p);
          last.h = Math.max(last.h, r.height);
        } else rows.push({ top: r.top, h: r.height, items: [p] });
      });
      // 貪欲に詰める
      const groups = [];
      let cur = [], curH = 0;
      rows.forEach((row) => {
        if (cur.length && curH + row.h > room) { groups.push(cur); cur = []; curH = 0; }
        cur = cur.concat(row.items); curH += row.h;
      });
      if (cur.length) groups.push(cur);
      const paths = groups.map((g) => g.map((p) => this._pathOf(p, base)));
      const allPaths = [].concat.apply([], paths);
      host.removeChild(base);
      paths.forEach((keep) => {
        const cl = base.cloneNode(true);
        cl.style.width = W + 'px';
        host.appendChild(cl);
        const keepKeys = keep.map((p) => p.join('.'));
        allPaths.forEach((p) => {
          if (keepKeys.indexOf(p.join('.')) >= 0) return;
          const el = this._atPath(cl, p);
          if (el) el.style.display = 'none';
        });
        slides.push(cl);
      });
    });
    return slides;
  }

  initKiosk() {
    if (this._kioskOn) return;
    let want = this.props.kioskMode ?? false;
    try { if (/[?&]kiosk(=1|=true)?(&|$)/i.test(window.location.search)) want = true; } catch (e) {}
    if (!want || this._dismissed) return;
    if (!document.querySelector('section[data-screen-label]')) return;
    this._kioskOn = true;

    const KIOSK_W = __KIOSK_W__, FIT = __KIOSK_FIT__;
    const stage = document.createElement('div');
    stage.setAttribute('data-kiosk-ui', '1');
    stage.style.cssText = 'position:fixed;inset:0;z-index:9999;background:#0E1116;overflow:hidden;';
    document.body.appendChild(stage);
    document.body.style.overflow = 'hidden';

    // 採寸用の隠し領域でスライドを組んでから stage へ移す。
    const host = document.createElement('div');
    host.setAttribute('data-kiosk-ui', '1');
    host.style.cssText = 'position:fixed;left:-99999px;top:0;width:' + KIOSK_W + 'px;';
    document.body.appendChild(host);
    const pages = this._kioskSlides(host);
    host.remove();
    if (!pages.length) { this._kioskOn = false; stage.remove(); document.body.style.overflow = ''; return; }

    const frames = pages.map((el) => {
      const f = document.createElement('div');
      f.style.cssText = 'position:absolute;inset:0;display:flex;align-items:center;justify-content:center;opacity:0;transition:opacity .6s ease;pointer-events:none;';
      const inner = document.createElement('div');
      inner.style.cssText = 'width:' + KIOSK_W + 'px;transform-origin:center center;';
      el.style.width = KIOSK_W + 'px';
      inner.appendChild(el);
      f.appendChild(inner);
      stage.appendChild(f);
      return { f, inner, el };
    });

    const barTrack = document.createElement('div');
    barTrack.setAttribute('data-kiosk-ui', '1');
    barTrack.style.cssText = 'position:fixed;left:0;right:0;top:0;height:5px;background:rgba(14,17,22,0.55);z-index:10000;';
    const bar = document.createElement('div');
    bar.setAttribute('data-kiosk-ui', '1');
    bar.style.cssText = 'position:fixed;left:0;top:0;height:5px;background:#C7F000;width:0%;z-index:10001;transition:width .2s linear;';
    document.body.appendChild(barTrack);
    document.body.appendChild(bar);

    const dots = document.createElement('div');
    dots.setAttribute('data-kiosk-ui', '1');
    dots.style.cssText = 'position:fixed;left:50%;transform:translateX(-50%);bottom:16px;display:flex;gap:8px;justify-content:center;align-items:center;padding:8px 12px;background:rgba(14,17,22,0.72);z-index:10000;pointer-events:none;';
    const dotEls = frames.map(() => {
      const d = document.createElement('div');
      d.style.cssText = 'width:26px;height:4px;background:rgba(244,241,234,0.3);transition:background .3s;';
      dots.appendChild(d);
      return d;
    });
    document.body.appendChild(dots);

    const hint = document.createElement('div');
    hint.setAttribute('data-kiosk-ui', '1');
    hint.style.cssText = "position:fixed;right:16px;bottom:16px;z-index:10000;padding:8px 12px;background:rgba(14,17,22,0.72);font-family:'Barlow Condensed',sans-serif;font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:rgba(244,241,234,0.65);";
    hint.textContent = '← → skip · space pause · m sound · f full screen · esc exit';
    document.body.appendChild(hint);

    let i = 0, t = 0, paused = false;
    const fit = (k) => {
      const { inner, el } = frames[k];
      inner.style.transform = 'scale(1)';
      const h = el.getBoundingClientRect().height || 1;
      const sc = Math.min(window.innerWidth / KIOSK_W, window.innerHeight / h) * FIT;
      inner.style.transform = 'scale(' + sc + ')';
    };
    const show = (k) => {
      i = (k + frames.length) % frames.length;
      t = 0;
      frames.forEach((fr, n) => { fr.f.style.opacity = n === i ? '1' : '0'; });
      dotEls.forEach((d, n) => { d.style.background = n === i ? '#C7F000' : 'rgba(244,241,234,0.3)'; });
      fit(i);
      // 表示中のフレームの動画だけを頭から再生し、他は止めて巻き戻す。
      frames.forEach((fr, n) => {
        const v = fr.el.querySelector('video');
        if (!v) return;
        if (n === i) {
          try { v.currentTime = 0; } catch (e) {}
          const p = v.play();
          if (p && p.catch) p.catch(() => {});
        } else {
          v.pause();
          try { v.currentTime = 0; } catch (e) {}
        }
      });
    };

    // キオスク中の <video> はブラウザ標準の操作UIを消し、ローテーション側から制御する。
    // 音声は自動再生ポリシーによりユーザー操作があるまで出せないので、まずミュートで
    // 開始し、最初のクリック／キー入力で解除する（下の _onGesture）。
    this._vids = frames.map((fr) => fr.el.querySelector('video')).filter(Boolean);
    this._vids.forEach((v) => {
      v.controls = false;
      v.muted = true;
      v.loop = false;
      v.preload = 'auto';
      v.style.maxHeight = 'none';
      // 尺どおりに終わったら次へ（タイマーは読み込み失敗時の保険）。
      v.addEventListener('ended', () => {
        const cur = frames[i] && frames[i].el.querySelector('video');
        if (cur === v) show(i + 1);
      });
      // 動画上のクリックが stage の «次へ» と二重に走らないようにする。
      v.addEventListener('click', (e) => e.stopPropagation());
    });
    show(0);

    // 動画フレームは動画の尺で送る。尺が取れないとき（読み込み失敗・stall）は
    // 通常の秒数に落とし、無人運用でローテーションが止まらないようにする。
    const dur = () => {
      const v = frames[i] && frames[i].el.querySelector('video');
      if (v && isFinite(v.duration) && v.duration > 0) return (v.duration + 0.5) * 1000;
      return Math.max(4, this.props.kioskSeconds ?? __SECONDS__) * 1000;
    };
    this._tick = setInterval(() => {
      if (paused) return;
      t += 100;
      const d = dur();
      bar.style.width = Math.min(100, (t / d) * 100) + '%';
      if (t >= d) { bar.style.width = '0%'; show(i + 1); }
    }, 100);

    const mkBtn = (bottom) => {
      const b = document.createElement('button');
      b.setAttribute('data-kiosk-ui', '1');
      b.type = 'button';
      b.style.cssText = "position:fixed;right:16px;bottom:" + bottom + "px;z-index:10002;padding:8px 12px;border:1px solid rgba(244,241,234,0.35);background:rgba(14,17,22,0.72);color:#F4F1EA;font-family:'Barlow Condensed',sans-serif;font-size:12px;letter-spacing:.16em;text-transform:uppercase;cursor:pointer;";
      return b;
    };

    const fsBtn = mkBtn(52);
    const syncFs = () => {
      fsBtn.textContent = this._fsEl() ? 'exit full screen (f)' : 'full screen (f)';
    };
    syncFs();
    fsBtn.addEventListener('click', (e) => { e.stopPropagation(); this._fsToggle(); });
    if (this._fsSupported()) document.body.appendChild(fsBtn);

    const isMuted = () => !!(this._vids && this._vids.length && this._vids[0].muted);
    const sndBtn = mkBtn(88);
    const syncSnd = () => {
      const m = isMuted();
      sndBtn.textContent = m ? 'sound off — press m' : 'sound on (m)';
      sndBtn.style.borderColor = m ? '#C7F000' : 'rgba(244,241,234,0.35)';
      sndBtn.style.color = m ? '#C7F000' : '#F4F1EA';
    };
    const setSound = (on) => {
      (this._vids || []).forEach((v) => { v.muted = !on; });
      syncSnd();
    };
    syncSnd();
    sndBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      this._soundArmed = true;
      setSound(isMuted());
      const v = frames[i] && frames[i].el.querySelector('video');
      if (v && v.paused && !paused) { const p = v.play(); if (p && p.catch) p.catch(() => {}); }
    });
    if (this._vids && this._vids.length) document.body.appendChild(sndBtn);

    // 自動再生ポリシー上、最初のユーザー操作までは音を出せない。何か触られた
    // 時点で一度だけ音を入れる（展示では全画面ボタン／F キーがその操作になる）。
    this._onGesture = () => {
      if (this._soundArmed) return;
      this._soundArmed = true;
      setSound(true);
    };
    window.addEventListener('pointerdown', this._onGesture);

    this._onFsChange = () => { syncFs(); fit(i); };
    document.addEventListener('fullscreenchange', this._onFsChange);
    document.addEventListener('webkitfullscreenchange', this._onFsChange);

    stage.addEventListener('click', () => show(i + 1));
    this._onKey = (e) => {
      this._onGesture();
      if (e.key === 'ArrowRight') show(i + 1);
      else if (e.key === 'ArrowLeft') show(i - 1);
      else if (e.key === ' ') {
        paused = !paused;
        bar.style.background = paused ? '#FF2E6E' : '#C7F000';
        const v = frames[i] && frames[i].el.querySelector('video');
        if (v) {
          if (paused) v.pause();
          else { const p = v.play(); if (p && p.catch) p.catch(() => {}); }
        }
        e.preventDefault();
      }
      else if (e.key === 'm' || e.key === 'M') { this._soundArmed = true; setSound(isMuted()); }
      else if (e.key === 'f' || e.key === 'F') this._fsToggle();
      // 全画面中の Esc は全画面だけ解除する（ローテーションは続行）。
      // もう一度押すとキオスクを抜ける。
      else if (e.key === 'Escape') { if (this._fsEl()) this._fsLeave(); else this.kioskExit(); }
    };
    this._onResize = () => fit(i);
    window.addEventListener('keydown', this._onKey);
    window.addEventListener('resize', this._onResize);
    // 起動時に自動で全画面へは入らない。?kiosk で直に開いた時点では
    // ユーザー操作（transient activation）が無く必ず拒否され、
    // コンソールに警告が出るだけで一度も成功しないため。F キーかボタンで入る。
  }
"""


def _impl():
    return (_IMPL
            .replace('__KIOSK_W__', str(KIOSK_W))
            .replace('__KIOSK_FIT__', str(KIOSK_FIT))
            .replace('__BUDGET__', str(BUDGET))
            .replace('__SPACE_K__', str(SPACE_K))
            .replace('__FONT_MIN__', str(FONT_MIN))
            .replace('__MAX_CHARS__', str(MAX_CHARS))
            .replace('__SECONDS__', str(SECONDS_PER_PAGE)))


def apply(tpl, sub1):
    tpl = sub1(tpl, PROPS_OLD, PROPS_NEW, "1枚あたりの表示秒数")
    tpl = sub1(tpl, MOUNT_OLD, MOUNT_NEW, "通常表示の video に操作UIを付ける")
    hits = _REGION.findall(tpl)
    assert len(hits) == 1, "キオスク実装の置換範囲が %d 件（1件であるべき）" % len(hits)
    tpl = _REGION.sub(lambda m: _impl(), tpl, count=1)
    tpl = sub1(tpl, HERO_ANCHOR, PV_SECTION + HERO_ANCHOR, "PV セクションの挿入")
    return tpl
