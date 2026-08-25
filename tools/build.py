#!/usr/bin/env python3
"""Claude Design の素の書き出しを、公開用 index.html に変換する。

素の書き出しには公開サイトとして足りないものが2つある:

  1. <title> / description / OGP が無い。バンドルは実行時に documentElement を
     テンプレートごと差し替えるため、外側の <head> に入れるだけでは実行後に
     捨てられる。両方に入れる必要がある。
  2. キオスク（自動再生）が gamescom の試遊台での無人ローテーションに足りない。
     PV が入っていない、動画の尺で送れない、音が出せない、全画面にできない。
     詳細は tools/kiosk_patch.py を見ること。

このスクリプトはその2つを素の書き出しに当てる。Claude Design から
書き出し直したときは、上書きせずにこれを通すこと:

    python3 tools/build.py <素の書き出し.html> index.html

置換元の文字列が1つも見つからない／複数見つかった場合は assert で止まる。
書き出し側が変わったら、ここを直すこと（黙って壊れたまま公開しない）。
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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


import char_crop
import kiosk_patch


def patch_kiosk(tpl):
    return kiosk_patch.apply(tpl, sub1)


def patch_char_crop(tpl):
    return char_crop.apply(tpl, sub1)


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
    tpl = patch_char_crop(tpl)

    # <script> の中に生の </ を置けないので、JSON 側の / をエスケープする。
    enc = json.dumps(tpl, ensure_ascii=False).replace("</", "<\\u002F")
    s = s[: m.start(2)] + enc + s[m.end(2) :]

    open(dst, "w", encoding="utf-8").write(s)
    print("wrote %s (%d chars)" % (dst, len(s)))


if __name__ == "__main__":
    main()
