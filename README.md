# ZUBASH — LP

ZUBASH（OCTBUZZ）の仕様紹介ランディングページ。

- 公開URL: https://octbuzz.github.io/zubash-lp/
- `index.html` は Claude Design から書き出した自己展開バンドル1枚。
  画像168点とWebフォントを base64 で内蔵しており、外部リソースへの依存は無い
  （静的ファイルとして置くだけで動く）。
- `.nojekyll` … Jekyll の処理を止めるための空ファイル。消さないこと。
- `og-image.jpg` / `favicon.svg` … OGP・ファビコン用。`index.html` から絶対URLで参照。

`index.html` を差し替えるときは、`<head>`（外側の素のHTML側と、
`__bundler/template` 島の中の両方）に入れてある title / description / OGP が
消えていないか確認すること。バンドルは実行時に documentElement ごと
テンプレートで置き換えるため、外側の `<head>` だけではタブのタイトルが空になる。
