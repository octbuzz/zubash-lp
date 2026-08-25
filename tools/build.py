#!/usr/bin/env python3
"""Claude Design の素の書き出しを、公開用 index.html に変換する。

素の書き出しには公開サイトとして足りないものが2つある:

  1. <title> / description / OGP が無い。バンドルは実行時に documentElement を
     テンプレートごと差し替えるため、外側の <head> に入れるだけでは実行後に
     捨てられる。両方に入れる必要がある。
  2. キオスク（自動再生）に全画面表示が無い。展示用途でブラウザの枠と
     URL バーを消せない。

このスクリプトはその2つを素の書き出しに当てる。Claude Design から
書き出し直したときは、上書きせずにこれを通すこと:

    python3 tools/build.py <素の書き出し.html> index.html

置換元の文字列が1つも見つからない／複数見つかった場合は assert で止まる。
書き出し側が変わったら、ここを直すこと（黙って壊れたまま公開しない）。
"""
import json
import re
import sys

BASE = "https://octbuzz.github.io/zubash-lp/"
TITLE = "ZUBASH — Local Multiplayer Physics Action"
DESC = (
    "Four gas-masked animals race across the rooftops of a sunlit flooded city — "
    "help each other over the gaps, then betray. 1–4 player local multiplayer physics action. "
    "水没都市の屋上を舞台にした 1〜4 人ローカルマルチ物理アクションの仕様紹介。"
)


def head_block(indent=""):
    tags = [
        '<title>%s</title>' % TITLE,
        '<meta name="description" content="%s">' % DESC,
        '<meta name="theme-color" content="#0E1116">',
        '<meta property="og:type" content="website">',
        '<meta property="og:site_name" content="OCTBUZZ">',
        '<meta property="og:title" content="%s">' % TITLE,
        '<meta property="og:description" content="%s">' % DESC,
        '<meta property="og:url" content="%s">' % BASE,
        '<meta property="og:image" content="%sog-image.jpg">' % BASE,
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        '<meta property="og:locale" content="en_US">',
        '<meta property="og:locale:alternate" content="ja_JP">',
        '<meta property="og:locale:alternate" content="de_DE">',
        '<meta name="twitter:card" content="summary_large_image">',
        '<meta name="twitter:title" content="%s">' % TITLE,
        '<meta name="twitter:description" content="%s">' % DESC,
        '<meta name="twitter:image" content="%sog-image.jpg">' % BASE,
        '<link rel="icon" href="favicon.svg" type="image/svg+xml">',
        '<link rel="canonical" href="%s">' % BASE,
    ]
    return "".join("\n" + indent + t for t in tags) + "\n" + indent


def sub1(text, old, new, what):
    n = text.count(old)
    assert n == 1, "%s: 置換元が %d 件（1件であるべき）" % (what, n)
    return text.replace(old, new, 1)


# ── 全画面表示（Fullscreen API）────────────────────────────────────────────
# requestFullscreen はユーザー操作（transient activation）が無いと必ず拒否される。
# ?kiosk で開いただけでは活性化が無いので、自動要求は「通れば儲けもの」の扱いにし、
# F キーと画面上のボタンを本線にする。

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

EXIT_OLD = """  kioskExit() {
    if (!this._kioskOn) return;
    clearInterval(this._tick);
"""
EXIT_NEW = """  kioskExit() {
    if (!this._kioskOn) return;
    clearInterval(this._tick);
    this._fsLeave();
    // キオスクを抜けたらキーとリサイズの購読も外す。外さないと通常表示に
    // 戻ったあとも Space が preventDefault されてページがスクロールできない。
    if (this._onKey) window.removeEventListener('keydown', this._onKey);
    if (this._onResize) window.removeEventListener('resize', this._onResize);
    if (this._onFsChange) {
      document.removeEventListener('fullscreenchange', this._onFsChange);
      document.removeEventListener('webkitfullscreenchange', this._onFsChange);
    }
    this._onKey = this._onResize = this._onFsChange = null;
"""

HINT_OLD = "    hint.textContent = '← → skip · space pause · esc exit';"
HINT_NEW = "    hint.textContent = '← → skip · space pause · f full screen · esc exit';"

SHOW_OLD = """    show(0);
    window.addEventListener('resize', () => fit(i));
"""
SHOW_NEW = """    show(0);
"""

TAIL_OLD = """    stage.addEventListener('click', () => show(i + 1));
    window.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowRight') show(i + 1);
      else if (e.key === 'ArrowLeft') show(i - 1);
      else if (e.key === ' ') { paused = !paused; bar.style.background = paused ? '#FF2E6E' : '#C7F000'; e.preventDefault(); }
      else if (e.key === 'Escape') this.kioskExit();
    });
  }
"""
TAIL_NEW = """    const fsBtn = document.createElement('button');
    fsBtn.setAttribute('data-kiosk-ui', '1');
    fsBtn.type = 'button';
    fsBtn.style.cssText = "position:fixed;right:16px;bottom:52px;z-index:10002;padding:8px 12px;border:1px solid rgba(244,241,234,0.35);background:rgba(14,17,22,0.72);color:#F4F1EA;font-family:'Barlow Condensed',sans-serif;font-size:12px;letter-spacing:.16em;text-transform:uppercase;cursor:pointer;";
    const syncFs = () => {
      fsBtn.textContent = this._fsEl() ? 'exit full screen (f)' : 'full screen (f)';
    };
    syncFs();
    // stage の click は「次へ」なので、ボタンの click は止めておく。
    fsBtn.addEventListener('click', (e) => { e.stopPropagation(); this._fsToggle(); });
    if (this._fsSupported()) document.body.appendChild(fsBtn);

    this._onFsChange = () => { syncFs(); fit(i); };
    document.addEventListener('fullscreenchange', this._onFsChange);
    document.addEventListener('webkitfullscreenchange', this._onFsChange);

    stage.addEventListener('click', () => show(i + 1));
    this._onKey = (e) => {
      if (e.key === 'ArrowRight') show(i + 1);
      else if (e.key === 'ArrowLeft') show(i - 1);
      else if (e.key === ' ') { paused = !paused; bar.style.background = paused ? '#FF2E6E' : '#C7F000'; e.preventDefault(); }
      else if (e.key === 'f' || e.key === 'F') this._fsToggle();
      // 全画面中の Esc は全画面を抜けるだけにする（キオスクは続行）。
      // もう一度押すとキオスクを抜ける。
      else if (e.key === 'Escape') { if (this._fsEl()) this._fsLeave(); else this.kioskExit(); }
    };
    this._onResize = () => fit(i);
    window.addEventListener('keydown', this._onKey);
    window.addEventListener('resize', this._onResize);
    // 起動時に自動で全画面へ入ろうとはしない。?kiosk で直に開いた時点では
    // ユーザー操作（transient activation）が無く必ず拒否され、
    // コンソールに警告が出るだけで一度も成功しないため。F キーかボタンで入る。
  }
"""


def patch_kiosk(tpl):
    tpl = sub1(tpl, EXIT_OLD, EXIT_NEW, "kioskExit の後始末")
    tpl = sub1(tpl, "  kioskExit() {", FS_HELPERS + "  kioskExit() {", "全画面ヘルパの挿入")
    tpl = sub1(tpl, HINT_OLD, HINT_NEW, "操作ヒント")
    tpl = sub1(tpl, SHOW_OLD, SHOW_NEW, "resize 購読の移設")
    tpl = sub1(tpl, TAIL_OLD, TAIL_NEW, "キー操作と全画面ボタン")
    return tpl


def main():
    src, dst = sys.argv[1], sys.argv[2]
    s = open(src, encoding="utf-8").read()

    # 1) 外側の <head>（JS を実行しないクローラが見るのはこちらだけ）
    s = sub1(s, "<title>Bundled Page</title>", head_block("  ").strip("\n"), "外側の head")

    # 2) バンドル内テンプレート（実行時に documentElement ごと置き換わる本体）
    m = re.search(r'(<script type="__bundler/template">)(.*?)(</script>)', s, re.S)
    assert m, "__bundler/template が見つからない"
    tpl = json.loads(m.group(2))

    assert "<title>" not in tpl[:4000].lower(), "テンプレートに既に title がある"
    hm = re.search(r"<head[^>]*>", tpl, re.I)
    assert hm, "テンプレートに head が無い"
    tpl = tpl[: hm.end()] + head_block("") + tpl[hm.end() :]

    tpl = re.sub(r"<html(?![^>]*\blang=)", '<html lang="en"', tpl, count=1)
    assert '<html lang="en"' in tpl, "html lang が入らなかった"

    tpl = patch_kiosk(tpl)

    # <script> の中に生の </ を置けないので、JSON 側の / をエスケープする。
    enc = json.dumps(tpl, ensure_ascii=False).replace("</", "<\\u002F")
    s = s[: m.start(2)] + enc + s[m.end(2) :]

    open(dst, "w", encoding="utf-8").write(s)
    print("wrote %s (%d chars)" % (dst, len(s)))


if __name__ == "__main__":
    main()
