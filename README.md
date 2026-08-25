# ZUBASH — LP

ZUBASH（OCTBUZZ）の仕様紹介ランディングページ。

- 公開URL: https://octbuzz.github.io/zubash-lp/
- 自動再生（キオスク）: https://octbuzz.github.io/zubash-lp/?kiosk

## ファイル

- `index.html` … Claude Design から書き出した自己展開バンドル1枚。
  画像168点とWebフォントを base64 で内蔵しており、外部リソースへの依存は無い
  （静的ファイルとして置くだけで動く）。**直接編集せず、`tools/build.py` で生成する**（下記）。
- `tools/build.py` … 素の書き出しを公開用 `index.html` に変換するスクリプト。
- `.nojekyll` … Jekyll の処理を止めるための空ファイル。消さないこと。
- `og-image.jpg` / `favicon.svg` … OGP・ファビコン用。`index.html` から絶対URLで参照。

## 更新のしかた

Claude Design から書き出し直したら、**上書きせずに** ビルドを通すこと:

```
python3 tools/build.py <素の書き出し.html> index.html
```

素の書き出しには公開サイトとして足りないものが2つあり、`build.py` がそれを当てている:

1. **`<title>` / description / OGP が無い。**
   バンドルは実行時に `document.documentElement` をテンプレートごと差し替えるため、
   外側の `<head>` に入れるだけでは実行後に捨てられる（タブのタイトルが空になる）。
   外側と `__bundler/template` 島の中、**両方**に入れる必要がある。
2. **キオスクに全画面表示が無い。** 下記。

`build.py` は置換元の文字列が1件見つからなければ assert で止まる。書き出し側の
コードが変わったら、黙って壊れたまま公開せずスクリプトを直すこと。

## キオスク（自動再生）

URL に `?kiosk`（`?kiosk=1` / `?kiosk=true` も可）を付けると、全画面のスライドショーに入る。
6セクション＋ヒーロー＋フッターの計8フレームを1枚 **18秒** で自動送りする。

| 操作 | 動作 |
|---|---|
| ← → | 前／次へ |
| クリック | 次へ |
| Space | 一時停止・再開（停止中は進捗バーがピンク） |
| **F / 画面右下のボタン** | **ブラウザの全画面表示に入る／出る** |
| Esc | 全画面中なら全画面だけ解除。全画面でなければキオスクを抜ける |

秒数は `kioskSeconds` プロパティ（既定18）に焼き込まれており、URL からは変えられない。

### 全画面まわりの注意

- **起動時に自動で全画面へは入らない。** Fullscreen API はユーザー操作
  （transient activation）を必須としており、`?kiosk` で直接開いた時点では操作が無く
  必ず拒否されるため。以前は起動時にも要求していたが、一度も成功せず
  コンソールに警告を出すだけだったので外した。**F キーかボタンを1回押すこと。**
- iOS Safari など要素の全画面表示に対応しない環境では、ボタン自体を出さない
  （`document.fullscreenEnabled` で判定）。
- キオスクを抜けるときに `keydown` / `resize` / `fullscreenchange` の購読を解除している。
  解除しないと通常表示に戻ったあとも Space が `preventDefault` され、
  スペースキーでページをスクロールできなくなる。
