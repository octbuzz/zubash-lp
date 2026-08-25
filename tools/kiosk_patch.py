# -*- coding: utf-8 -*-
"""キオスク（自動再生ローテーション）まわりの改造。build.py から呼ばれる。

素の書き出しのキオスクは「セクションを18秒ずつ送るだけ」で、gamescom の
試遊台で無人ローテーションさせるには足りない。ここで足しているのは4つ:

  1. PV（動画）をローテーションの1枚目として差し込む
  2. 動画フレームは18秒ではなく「動画の尺」で送る（終了イベントでも送る）
  3. 音を出す（自動再生ポリシー上ミュート開始→最初のユーザー操作で解除）
  4. 全画面表示（ブラウザの枠と URL バーを消す）

あわせて、フッターだけのフレームをローテーションから外し、
キオスク離脱時にイベント購読を解除する（解除漏れの不具合修正）。
"""

# ── 通常表示の <video> に操作UIを付ける ──────────────────────────────────
# dc のテンプレートコンパイラは値なしの controls 属性を落としてしまう
# （playsinline は残るのに controls だけ消える）。素の HTML では直せないので、
# マウント時に JS で付け直す。キオスク中は initKiosk 側で外す。
MOUNT_OLD = "  componentDidMount() { setTimeout(() => this.initKiosk(), 60); }"
MOUNT_NEW = """  componentDidMount() {
    document.querySelectorAll('video').forEach((v) => { v.controls = true; });
    setTimeout(() => this.initKiosk(), 60);
  }"""


# ── ローテーション対象 ────────────────────────────────────────────────────
# フッターだけの1枚は無人ローテでは中身が無く、18秒の空白になるので外す。
# （スクロール表示のページ下部にはそのまま残る）
PAGES_OLD = "    const pages = Array.from(document.querySelectorAll('section[data-screen-label], footer'));"
PAGES_NEW = "    const pages = Array.from(document.querySelectorAll('section[data-screen-label]'));"

# ── 全画面表示のヘルパ ────────────────────────────────────────────────────
FS_HELPERS = """  _fsEl() {
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

"""

# ── 離脱時の後始末 ────────────────────────────────────────────────────────
EXIT_OLD = """  kioskExit() {
    if (!this._kioskOn) return;
    clearInterval(this._tick);
"""
EXIT_NEW = """  kioskExit() {
    if (!this._kioskOn) return;
    clearInterval(this._tick);
    this._fsLeave();
    // 動画を止め、通常表示用の状態（操作UIあり・ミュート解除）に戻す。
    (this._vids || []).forEach((v) => {
      v.pause();
      try { v.currentTime = 0; } catch (e) {}
      v.muted = false;
      v.controls = v.dataset.zbControls === '1';
      v.style.maxHeight = v.dataset.zbMaxH || '';
      v.preload = 'metadata';
    });
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
"""

HINT_OLD = "    hint.textContent = '← → skip · space pause · esc exit';"
HINT_NEW = "    hint.textContent = '← → skip · space pause · m sound · f full screen · esc exit';"

# ── フレームの表示時間 ────────────────────────────────────────────────────
DUR_OLD = "    const dur = () => Math.max(4, this.props.kioskSeconds ?? 18) * 1000;"
DUR_NEW = """    // 動画フレームは動画の尺で送る。尺が取れないとき（読み込み失敗・stall）は
    // 通常の秒数に落とし、無人運用でローテーションが止まらないようにする。
    const dur = () => {
      const v = frames[i] && frames[i].el.querySelector('video');
      if (v && isFinite(v.duration) && v.duration > 0) return (v.duration + 0.5) * 1000;
      return Math.max(4, this.props.kioskSeconds ?? 18) * 1000;
    };"""

# ── フレーム切り替え時に動画を頭出し／停止する ────────────────────────────
SHOWFN_OLD = """    const show = (k) => {
      i = (k + frames.length) % frames.length;
      t = 0;
      frames.forEach((fr, n) => { fr.f.style.opacity = n === i ? '1' : '0'; });
      dotEls.forEach((d, n) => { d.style.background = n === i ? '#C7F000' : 'rgba(244,241,234,0.3)'; });
      fit(i);
    };"""
SHOWFN_NEW = """    const show = (k) => {
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
    };"""

# ── 動画の下ごしらえ（show(0) より前に済ませる必要がある）────────────────
SHOW0_OLD = """    show(0);
    window.addEventListener('resize', () => fit(i));
"""
SHOW0_NEW = """    // キオスク中の <video> はブラウザ標準の操作UIを消し、ローテーション側から制御する。
    // 音声は自動再生ポリシーによりユーザー操作があるまで出せないので、まずミュートで
    // 開始し、最初のクリック／キー入力で解除する（下の _onGesture）。
    this._vids = frames.map((fr) => fr.el.querySelector('video')).filter(Boolean);
    this._vids.forEach((v) => {
      v.dataset.zbControls = v.controls ? '1' : '';
      // 通常表示ではコントロールが画面外に出ないよう max-height で抑えているが、
      // キオスクでは 1440x960 のフレームとして扱うので外す。
      v.dataset.zbMaxH = v.style.maxHeight || '';
      v.style.maxHeight = 'none';
      v.controls = false;
      v.muted = true;
      v.loop = false;
      v.preload = 'auto';
      // 尺どおりに終わったら次へ（タイマーは読み込み失敗時の保険）。
      v.addEventListener('ended', () => {
        const cur = frames[i] && frames[i].el.querySelector('video');
        if (cur === v) show(i + 1);
      });
      // 動画上のクリックが stage の «次へ» と二重に走らないようにする。
      v.addEventListener('click', (e) => e.stopPropagation());
    });
    show(0);
"""

# ── 操作系（キー・全画面ボタン・音声ボタン）──────────────────────────────
TAIL_OLD = """    stage.addEventListener('click', () => show(i + 1));
    window.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowRight') show(i + 1);
      else if (e.key === 'ArrowLeft') show(i - 1);
      else if (e.key === ' ') { paused = !paused; bar.style.background = paused ? '#FF2E6E' : '#C7F000'; e.preventDefault(); }
      else if (e.key === 'Escape') this.kioskExit();
    });
  }
"""
TAIL_NEW = """    const mkBtn = (bottom) => {
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
    // stage の click は «次へ» なので、ボタンの click は伝播を止める。
    fsBtn.addEventListener('click', (e) => { e.stopPropagation(); this._fsToggle(); });
    if (this._fsSupported()) document.body.appendChild(fsBtn);

    const isMuted = () => !!(this._vids && this._vids.length && this._vids[0].muted);
    const sndBtn = mkBtn(88);
    const syncSnd = () => {
      const m = isMuted();
      sndBtn.textContent = m ? 'sound off — press m' : 'sound on (m)';
      // ミュート中は展示で気づけるよう強調する。
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

# ── PV セクション（ローテーションの1枚目）────────────────────────────────
# アンカーは書き出し側のヒーローセクション開始タグ。
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


def apply(tpl, sub1):
    tpl = sub1(tpl, MOUNT_OLD, MOUNT_NEW, "通常表示の video に操作UIを付ける")
    tpl = sub1(tpl, PAGES_OLD, PAGES_NEW, "ローテーション対象からフッターを外す")
    tpl = sub1(tpl, EXIT_OLD, EXIT_NEW, "kioskExit の後始末")
    tpl = sub1(tpl, "  kioskExit() {", FS_HELPERS + "  kioskExit() {", "全画面ヘルパの挿入")
    tpl = sub1(tpl, HINT_OLD, HINT_NEW, "操作ヒント")
    tpl = sub1(tpl, DUR_OLD, DUR_NEW, "フレーム表示時間を動画の尺に対応させる")
    tpl = sub1(tpl, SHOWFN_OLD, SHOWFN_NEW, "フレーム切り替え時の動画制御")
    tpl = sub1(tpl, SHOW0_OLD, SHOW0_NEW, "動画の下ごしらえ")
    tpl = sub1(tpl, TAIL_OLD, TAIL_NEW, "キー操作・全画面／音声ボタン")
    tpl = sub1(tpl, HERO_ANCHOR, PV_SECTION + HERO_ANCHOR, "PV セクションの挿入")
    return tpl
