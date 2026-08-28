# -*- coding: utf-8 -*-
"""操作ページを「コントローラ図の周りに説明を置く」形に組み直す。

書き出しのままだと〈左＝コントローラの絵／右＝操作の一覧〉の2カラムで、
絵と説明が離れている。どのボタンが何なのかを目で追う必要があり、
試遊台で一瞬見るには向かない。

ボタンの位置に合わせて説明を配置し直す:

    ┌ 左スティック ┐   [PUNCH]─  (Y)      ─[PICK UP / PLACE]
    │   MOVE      │           (X) (B)
    └─────────────┘             (A)
                               [JUMP]

X は十字の左、B は右、A は下、Y は上 —— という実際の配置のまま、
説明をその隣に置くので、線を追わなくても対応が分かる。
説明ブロックにはボタンと同じ色の短い接続線を付けている。

英文は100字以内（キオスクは100字超を画面から落とす）。

ボタンを横一列に並べるため、狭い画面では図が画面幅に収まらない。
カードに overflow-x: auto を入れ、**ページごと横スクロールするのではなく
カードの中でスクロール**させている（キオスクは幅1280で組むので溢れない）。
"""

# 置換範囲: 〈コントローラ図＋操作一覧〉の2カラムブロックまるごと。
# 先頭はこの div、末尾はキーボード帯の直前まで。
START = '<div data-keep="1" style="display: grid; grid-template-columns: 1fr 1fr; gap: 56px; align-items: start;">'
END_ANCHOR = '<div data-keep="1" style="margin-top: 40px; background: #EDEAE0;'

INK = '#0E1116'
BODY = '#3B434D'
MUTED = '#8A9099'
JA = '#A2A8AF'

_A = ('#C7F000', INK)          # A ボタン
_X = ('#1F6DFF', '#F4F1EA')    # X ボタン
_B = ('#FF2E6E', '#F4F1EA')    # B ボタン
_Y = ('#F2C94C', INK)          # Y ボタン


def _btn(letter, bg, fg, col, row, size=78):
    return ('<div style="grid-column: %d; grid-row: %d; width: %dpx; height: %dpx; border-radius: 50%%; '
            'background: %s; border: 4px solid #0E1116; display: flex; align-items: center; '
            'justify-content: center; font-family: \'Archivo Black\', sans-serif; font-size: 28px; '
            'color: %s;">%s</div>' % (col, row, size, size, bg, fg, letter))


def _label(title, en, de, ja, align):
    return ("""<div style="text-align: %s;">
              <div style="font-family: 'Archivo Black', sans-serif; font-size: 24px; letter-spacing: -0.01em; color: %s;">%s</div>
              <div style="font-size: 15px; line-height: 1.45; color: %s; max-width: 232px;">%s</div>
              <div style="font-family: 'Barlow Condensed', sans-serif; font-size: 15px; color: %s;">%s</div>
              <div style="font-family: 'Noto Sans JP', sans-serif; font-size: 11px; color: %s;">%s</div>
            </div>""" % (align, INK, title, BODY, en, MUTED, de, JA, ja))


def _line(color, horizontal=True, length=34):
    if horizontal:
        return '<div style="width: %dpx; height: 3px; background: %s; flex: 0 0 auto;"></div>' % (length, color)
    return '<div style="width: 3px; height: %dpx; background: %s; margin: 0 auto;"></div>' % (length, color)


BLOCK = """<div data-keep="1" style="background: #FFFFFF; border: 3px solid #0E1116; padding: 34px 30px; overflow-x: auto;">
        <div style="display: grid; grid-template-columns: repeat(4, max-content); grid-template-rows: auto auto auto; column-gap: 30px; row-gap: 8px; align-items: center; justify-items: center; justify-content: center;">

          <div style="grid-column: 3; grid-row: 1; text-align: center;">
            <div style="font-family: 'Barlow Condensed', sans-serif; font-weight: 700; font-size: 14px; letter-spacing: 0.18em; text-transform: uppercase; color: %(muted)s;">Y works too</div>
            <div style="font-family: 'Barlow Condensed', sans-serif; font-size: 13px; color: %(ja)s;">Y geht auch</div>
            %(yline)s
          </div>

          <div style="grid-column: 1; grid-row: 2; text-align: center;">
            <div style="width: 128px; height: 128px; border-radius: 50%%; background: #E7E3D8; border: 4px solid #0E1116; display: flex; align-items: center; justify-content: center; box-shadow: inset 0 -6px 0 rgba(0,0,0,0.35); margin: 0 auto;">
              <div style="width: 74px; height: 74px; border-radius: 50%%; background: #0E1116;"></div>
            </div>
            %(sline)s
            %(move)s
          </div>

          <div style="grid-column: 2; grid-row: 2; display: flex; align-items: center;">
            %(punch)s
            %(pline)s
          </div>

          <div style="grid-column: 3; grid-row: 2; display: grid; grid-template-columns: repeat(3, 84px); grid-template-rows: repeat(3, 84px); place-items: center;">
            %(by)s
            %(bx)s
            %(bb)s
            %(ba)s
          </div>

          <div style="grid-column: 4; grid-row: 2; display: flex; align-items: center;">
            %(bline)s
            %(pick)s
          </div>

          <div style="grid-column: 3; grid-row: 3; text-align: center;">
            %(aline)s
            %(jump)s
          </div>

        </div>
      </div>

      """ % dict(
    muted=MUTED, ja=JA,
    yline=_line(_Y[0], horizontal=False, length=16),
    sline='<div style="width: 3px; height: 16px; background: #1F6DFF; margin: 8px auto;"></div>',
    move=_label('MOVE', 'Left stick, snapped to eight directions.',
                'Bewegen — linker Stick, 8 Richtungen', '移動（左スティック・8方向）', 'center'),
    punch=_label('PUNCH', 'Knock players and props forward and up. Short cooldown.',
                 'Schlagen', '殴る（前方＋上方向にふっとばす）', 'right'),
    pline=_line(_X[0]),
    bline=_line(_B[0]),
    pick=_label('PICK UP / PLACE', 'Grab anything nearby and drop it where it hurts.',
                'Aufheben / Ablegen', 'ギミックを拾う／置く', 'left'),
    aline='<div style="width: 3px; height: 16px; background: #C7F000; margin: 0 auto 6px;"></div>',
    jump=_label('JUMP', 'Hop gaps, land on heads, bail out of trouble.',
                'Springen', 'ジャンプ', 'center'),
    by=_btn('Y', _Y[0], _Y[1], 2, 1),
    bx=_btn('X', _X[0], _X[1], 1, 2),
    bb=_btn('B', _B[0], _B[1], 3, 2),
    ba=_btn('A', _A[0], _A[1], 2, 3),
)

# START/SELECT はコントローラ図の下に横帯で残す（元は図の枠の中にあった）
START_SELECT = """<div data-keep="1" style="margin-top: 20px; display: flex; gap: 40px; justify-content: center; flex-wrap: wrap;">
        <div style="text-align: center;">
          <div style="font-family: 'Barlow Condensed', sans-serif; font-weight: 700; font-size: 13px; letter-spacing: 0.18em; text-transform: uppercase; color: %(muted)s;">Start</div>
          <div style="font-size: 15px; color: %(body)s;">Pause / End round</div>
          <div style="font-family: 'Barlow Condensed', sans-serif; font-size: 14px; color: %(muted)s;">Pause / Runde beenden</div>
        </div>
        <div style="text-align: center;">
          <div style="font-family: 'Barlow Condensed', sans-serif; font-weight: 700; font-size: 13px; letter-spacing: 0.18em; text-transform: uppercase; color: %(muted)s;">Select</div>
          <div style="font-size: 15px; color: %(body)s;">Back to title</div>
          <div style="font-family: 'Barlow Condensed', sans-serif; font-size: 14px; color: %(muted)s;">Zurück zum Titel</div>
        </div>
      </div>

      """ % dict(muted=MUTED, body=BODY)


def apply(tpl, sub1):
    i = tpl.find(START)
    assert i >= 0, "操作ページの2カラムブロックが見つからない"
    assert tpl.find(START, i + 1) < 0, "操作ページの2カラムブロックが複数ある"
    j = tpl.find(END_ANCHOR, i)
    assert j > i, "キーボード帯（置換範囲の終端）が見つからない"
    return tpl[:i] + BLOCK + START_SELECT + tpl[j:]
