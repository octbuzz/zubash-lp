# -*- coding: utf-8 -*-
"""キャラクターカードの切り出し位置を直す。

素材（`05 — Characters` の4枚）は 1448×1086 の三面図
（正面 / 側面 / 背面）で、カードは CSS で正面図だけを拡大表示している。
書き出し時点では4体とも同じ切り出し位置

    width: 333%; left: -13.3%; top: -34%

が当たっているが、キャラごとに頭の高さも身幅も違うため、**4体とも頭頂が
切れていた**（元画像px換算でウサギ143 / オオカミ111 / カエル84 / ネズミ69）。
丸い頭のカエルでいちばん目立つ。

そこで PIL で各画像の正面図の外接矩形を実測し、切り出しを計算し直した。

  実測（元画像px、正面図のみ。側面図とは30px以上の余白で分離されている）
    wolf   x  61..489 (幅429)  y  86..935   中心x 275
    rabbit x  85..483 (幅399)  y  54..956   中心x 284
    mouse  x  50..468 (幅419)  y 128..897   中心x 259
    frog   x  56..505 (幅450)  y 113..926   中心x 280

方針:
  * 拡大率は4体共通にする（カード間で見た目の大きさを揃えるため）。
    いちばん横幅のあるカエル(450px)が左右10pxの余白付きで収まるよう
    可視幅を470pxに取り、333% → **308%** にした。
    この幅なら4体とも側面図が写り込まない。
  * 縦は「頭頂の30px上」から切る（頭上の余白を4体で揃える）。
  * 横はキャラごとに正面図の中心へ合わせる。

figure の高さは770〜903pxあり可視高626pxに収まらないので、全身は入らない
（元の設計どおり頭〜腿までの構図）。ここで直しているのは上の見切れだけ。

数式（カード幅W、カード高H=4W/3、可視は元画像px換算）:
    scale   = 3.08W / 1448                     … 表示px / 元画像px
    可視幅  = W / scale = 470.1
    可視高  = H / scale = 626.8
    left%   = -可視左端(px) * scale / W   * 100 = -可視左端 * 0.21271
    top%    = -可視上端(px) * scale / H   * 100 = -可視上端 * 0.159533
"""

WIDTH_PCT = 308

# alt 属性 → (可視左端, 可視上端)  ※元画像px
_WINDOW = {
    "BLUE WOLF":   (39.95, 56.0),
    "WHITE RABBIT": (48.95, 24.0),
    "YELLOW MOUSE": (23.95, 98.0),
    "GREEN FROG":  (44.95, 83.0),
}

OLD_STYLE = 'style="position: absolute; width: 333%; height: auto; left: -13.3%; top: -34%;"'


def apply(tpl, sub1):
    for alt, (vis_left, vis_top) in _WINDOW.items():
        left = -vis_left * 0.21271
        top = -vis_top * 0.159533
        new_style = (
            'style="position: absolute; width: %d%%; height: auto; '
            'left: %.2f%%; top: %.2f%%;"' % (WIDTH_PCT, left, top)
        )
        tpl = sub1(
            tpl,
            'alt="%s" %s' % (alt, OLD_STYLE),
            'alt="%s" %s' % (alt, new_style),
            "キャラ切り出し（%s）" % alt,
        )
    return tpl
