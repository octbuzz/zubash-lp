# -*- coding: utf-8 -*-
"""遊び方（ソロ／協力／得点戦）のセクションを追加する。

Unity 側の実装（octbuzz-client）から拾った仕様:

  * `MultiRule`（Enums.cs）… Score = 従来の得点戦 / Coop = 協力
  * メニューでマルチを選ぶと "HOW DO YOU PLAY?" の二択が出る
    （右 = CO-OP / 左 = VERSUS、B で閉じるとメニューに留まる）
  * 協力: 全員がゴールに入った時点でステージクリア。以降のラウンドは走らせない
    （`coopCleared`）。未ゴール人数ぶんのボーナスは配らない
    ——「味方の失敗が自分の得点になるのは協力の趣旨に合わない」
  * ソロ: ゴールした時点でステージクリア（`soloCleared`）。
    届かなければマルチと同じく次ラウンドへ
  * ステージ開始時に目的を1行で出す（`StageObjectiveBanner`）:
      ソロ REACH THE GOAL! / 協力 EVERYONE REACH THE GOAL! / 得点戦 GRAB THE MOST POINTS!
  * 復活待ち `ReviveWaitSec = 10.0` 秒。残り秒数を各自の枠に出す

英文は**100字以内**に収めてある。キオスクは100字超のブロックを画面から落とす
ため、超えると試遊台の画面に出なくなる（tools/kiosk_patch.py の MAX_CHARS）。
"""

ANCHOR = '<section data-screen-label="Controls"'

# 見出し番号の繰り下げ（Modes を 03 に入れるため）
RENUMBER = [
    ('>03 — Controls<', '>04 — Controls<'),
    ('>04 — Gimmicks<', '>05 — Gimmicks<'),
    ('>05 — Characters<', '>06 — Characters<'),
    ('>06 — Stage<', '>07 — Stage<'),
]

_EYEBROW = ("font-family: 'Barlow Condensed', sans-serif; font-weight: 700; font-size: 13px; "
            "letter-spacing: 0.24em; text-transform: uppercase;")


def _card(accent, ink, name, players, objective, en, de, ja, note_en, note_de, note_ja):
    note = ''
    if note_en:
        note = (
            '\n          <div style="margin-top: 12px; border-top: 1px solid rgba(244,241,234,0.18); padding-top: 10px;">'
            '\n            <div style="font-size: 14.5px; line-height: 1.5; color: rgba(244,241,234,0.75);">%s</div>'
            '\n            <div style="font-family: \'Barlow Condensed\', sans-serif; font-size: 14px; color: rgba(244,241,234,0.5); margin-top: 4px;">%s</div>'
            '\n            <div style="font-family: \'Noto Sans JP\', sans-serif; font-size: 10.5px; color: rgba(244,241,234,0.35); margin-top: 2px;">%s</div>'
            '\n          </div>' % (note_en, note_de, note_ja)
        )
    return """<div style="border: 3px solid %(accent)s; background: #141922; display: flex; flex-direction: column;">
          <div style="background: %(accent)s; color: %(ink)s; padding: 10px 16px; %(eyebrow)s">%(objective)s</div>
          <div style="padding: 18px 18px 20px; flex: 1;">
            <div style="display: flex; align-items: baseline; gap: 10px; margin-bottom: 10px;">
              <div style="font-family: 'Archivo Black', sans-serif; font-size: 26px; letter-spacing: -0.01em; color: #F4F1EA;">%(name)s</div>
              <div style="font-family: 'Barlow Condensed', sans-serif; font-size: 14px; letter-spacing: 0.16em; text-transform: uppercase; color: %(accent)s;">%(players)s</div>
            </div>
            <div style="font-size: 14.5px; line-height: 1.5; color: rgba(244,241,234,0.85);">%(en)s</div>
            <div style="font-family: 'Barlow Condensed', sans-serif; font-size: 14px; color: rgba(244,241,234,0.5); margin-top: 4px;">%(de)s</div>
            <div style="font-family: 'Noto Sans JP', sans-serif; font-size: 10.5px; color: rgba(244,241,234,0.35); margin-top: 2px;">%(ja)s</div>%(note)s
          </div>
        </div>""" % dict(accent=accent, ink=ink, name=name, players=players, objective=objective,
                         en=en, de=de, ja=ja, note=note, eyebrow=_EYEBROW)


def _strip(title, en, de, ja):
    return """<div style="border-top: 3px solid #2B3340; padding-top: 14px;">
          <div style="font-family: 'Archivo Black', sans-serif; font-size: 18px; margin-bottom: 6px;">%s</div>
          <div style="font-size: 14.5px; line-height: 1.5; color: rgba(244,241,234,0.75);">%s</div>
          <div style="font-family: 'Barlow Condensed', sans-serif; font-size: 14px; color: rgba(244,241,234,0.5); margin-top: 4px;">%s</div>
          <div style="font-family: 'Noto Sans JP', sans-serif; font-size: 10.5px; color: rgba(244,241,234,0.35); margin-top: 2px;">%s</div>
        </div>""" % (title, en, de, ja)


SECTION = """<section data-screen-label="Modes" style="padding: 104px 48px; background: #0E1116; color: #F4F1EA;">
    <div style="max-width: 1180px; margin: 0 auto;">
      <div style="%(eyebrow)s color: #C7F000; margin-bottom: 14px;">03 — Modes</div>
      <h2 style="font-family: 'Archivo Black', sans-serif; font-size: clamp(38px, 4.6vw, 62px); line-height: 0.94; letter-spacing: -0.02em; margin: 0 0 10px;">SAME ROOFTOP.<br>THREE OBJECTIVES.</h2>
      <div style="font-family: 'Barlow Condensed', sans-serif; font-size: 20px; color: rgba(244,241,234,0.6); margin-bottom: 4px;">Dasselbe Dach — drei Spielarten mit unterschiedlichem Ziel.</div>
      <div style="font-family: 'Noto Sans JP', sans-serif; font-size: 11px; color: rgba(244,241,234,0.4); margin-bottom: 44px;">同じ屋上を、3つの遊び方で。開始時に目的が1行で表示される。</div>

      <div data-keep="1" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 28px;">
        %(solo)s
        %(coop)s
        %(versus)s
      </div>

      <div data-keep="1" style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px;">
        %(how)s
        %(revive)s
      </div>
    </div>
  </section>

  """ % dict(
    eyebrow=_EYEBROW,
    solo=_card(
        '#F4F1EA', '#0E1116', 'SOLO', '1 Player', 'REACH THE GOAL!',
        'Touch the flag and the stage is cleared. Miss it and the next round starts.',
        'Flagge berühren — Stage geschafft.',
        'ゴールに触れた時点でステージクリア。届かなければ次のラウンドへ。',
        '', '', ''),
    coop=_card(
        '#C7F000', '#0E1116', 'CO-OP', '2–4 Players', 'EVERYONE REACH THE GOAL!',
        'The stage clears when the last player touches the flag. Nobody is left behind.',
        'Erst wenn der Letzte die Flagge berührt, ist die Stage geschafft.',
        '全員がゴールに入った時点でステージクリア。誰も置いていかない。',
        'No bonus for a teammate who did not make it.',
        'Kein Bonus für zurückgelassene Mitspieler.',
        '未ゴール者ぶんのボーナスは配られない。'),
    versus=_card(
        '#FF2E6E', '#0E1116', 'VERSUS', '2–4 Players', 'GRAB THE MOST POINTS!',
        'Three rounds, two ways to score. Highest total wins.',
        'Drei Runden — die höchste Gesamtpunktzahl gewinnt.',
        '3ラウンドの合計点で勝敗。得点方法は前ページの2つ。',
        '', '', ''),
    how=_strip(
        'HOW DO YOU PLAY?',
        'Pick multiplayer in the menu and the game asks: CO-OP or VERSUS.',
        'Nach der Mehrspieler-Auswahl fragt das Spiel: CO-OP oder VERSUS.',
        'マルチを選ぶと「CO-OP か VERSUS か」を聞かれる。'),
    revive=_strip(
        'BACK IN 10 SECONDS',
        'Knocked into the sea? A countdown on your marker shows when you return.',
        'Ins Wasser gefallen? Ein Countdown zeigt, wann ihr zurückkommt.',
        '海に落ちても10秒で復活。残り秒数が自分の×印に出る。'),
)


def apply(tpl, sub1):
    for old, new in RENUMBER:
        tpl = sub1(tpl, old, new, "見出し番号の繰り下げ（%s）" % old.strip('><'))
    tpl = sub1(tpl, ANCHOR, SECTION + ANCHOR, "Modes セクションの挿入")
    return tpl
