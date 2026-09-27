"""Round 26: the probe log's line formats -- one pattern per kind (native/include/Trace.h writes them).

Both readers use this one table: native/tests/trace_test.cpp (through build/fix26-trace-format.json, ECMAScript regex)
checks that every line the real formatters write matches its kind's pattern, and build/probe-judge.py parses the game's
log with the same patterns. So a format change that the judge would misread fails the native test first.

Run as a script (or FIXTURE()) to write build/fix26-trace-format.json.
"""
from pathlib import Path
import json, sys

ROOT = Path(__file__).resolve().parents[1]
JSON = ROOT / 'build/fix26-trace-format.json'

PREFIX = r'^\[ESSB\]\[T\]\[{kind}\] #(\d+) g=(\d+) r=(\d+)'
STEP = r'^\[ESSB\]\[STEP\] (\d+) #(\d+) g=(\d+) r=(\d+) via=([a-z-]+)$'
NUM = r'[-+]?(?:\d+(?:\.\d+)?(?:e[-+]?\d+)?|inf|nan(?:\(ind\))?)'
B = r'[01]'
FID8 = r'0x[0-9A-F]{8}'
FID6 = r'0x[0-9A-F]{6}'
# name(0xFORMID)[h=cur/max m=cur/max s=cur/max( dead)?], or "-" (no actor). Names cannot hold ( ) [ ] = (Trace.h Line::Actor).
ACTOR = (r'(?:-|[^()\[\]=]*\(' + FID8 + r'\)\[h=' + NUM + '/' + NUM + ' m=' + NUM + '/' + NUM + ' s=' + NUM + '/' + NUM +
         r'(?: dead)?\])')

BODIES = {
    'op': (r' ctx=\S+ op=\w+ who=(?:you|target) at=\d+ kind=\S+ el=\w+ mag=' + NUM + ' sec=' + NUM +
           r'(?: ev=\w+ args=\S+(?: reason=\w+)?)? on=' + ACTOR + r'(?: was=(?:-|' + NUM + ' left=' + NUM + r' n=\d+))?' +
           r'(?: cast=' + FID6 + ' cast_mag=' + NUM + ' eff=' + NUM + ')?$'),
    'op-done': r' ref=#\d+ on=' + ACTOR + '$',
    'proc': (r' src=\w+ tgt=' + ACTOR + ' you=' + ACTOR + r' el=\w+ spell=\S+ weapon=-?\d+ power=' + B + ' sneak=' + B + ' leftHand=' + B +
             ' mag=' + NUM + ' crit=' + B + r'(?: N=\d+ charges=\d+ critChance=' + NUM + r'| charges=\d+)' +
             ' siphon=' + NUM + ' burned=' + NUM + ' dispel=' + B + ' overloadAfter=' + NUM + ' overloaded=' + B +
             ' silenced=' + B + ' echo=' + B + ' riposte=' + B + r' steps=\S+ rolls=.+$'),
    'hit-end': r' tgt=' + ACTOR + ' you=' + ACTOR + r' ops=\d+$',
    'menu': r' name=.+ opening=' + B + ' paused=' + B + '$',
    'hit-late': r' tgt=' + ACTOR + r' reason=\w+$',
    'hit-reject': r' tgt=' + ACTOR + r' reason=[\w-]+ weapon=-?\d+$',
    'remove': (r' on=' + ACTOR + r' tag=\S+ mag=' + NUM + ' elapsed=' + NUM + ' duration=' + NUM + ' left=' + NUM +
               r' reason=(?:expired|dispel|death)$'),
    'apply': (r' on=' + ACTOR + ' effect=' + FID6 + r' tag=\S+ spell=' + FID6 + ' mag=' + NUM + ' duration=' + NUM +
              ' caster=' + ACTOR + '(?: d=' + NUM + ')?$'),
    'hurt': (r' att=' + ACTOR + ' you=' + ACTOR + ' before=' + NUM + ' after=' + NUM + ' lost=' + NUM + ' melee=' + B +
             ' spell=' + B + ' destructive=' + B + ' blocked=' + B + ' cloak=' + B + ' afterimage=' + B + ' linger=' + B +
             ' guardBefore=' + NUM + ' guardLeft=' + NUM + ' overloadBefore=' + NUM + ' magickaBefore=' + NUM +
             ' magickaNow=' + NUM + ' dot=' + NUM + r' form=\d+ ops=\d+ cd_you=\S+ cd_att=\S+$'),
    'cast': r' caster=' + ACTOR + ' spell=' + FID8 + ' marked=' + B + ' cost=' + NUM + ' near=' + B + r' form=\w+$',
    'death': (r' corpse=' + ACTOR + ' killer=' + ACTOR + ' killerYou=' + B + ' frenzied=' + B + ' servant=' + B +
              r' marks=\d+ curse=\d+ poison=' + B + ' bleed=' + B + ' frozen=' + B + ' hush=' + B + ' essential=' + B +
              r' level=\d+ curseCap=\d+ crowd=\d+ ops=\d+$'),
    'death-event': r' corpse=' + ACTOR + ' killer=' + ACTOR + ' dead=' + B + ' killerYou=' + B + ' servant=' + B + r' ours=\d+$',
    'burst-start': r' element=\w+ stage=\d+ sync=\d+ radius=' + NUM + ' you=' + ACTOR + '$',
    'burst': r' element=\w+ stage=\d+ targets=\d+ marks=\d+ crowd=\d+ ops=\d+$',
    'settle': r' on=' + ACTOR + r' tag=\S+ mag=' + NUM + ' elapsed=' + NUM + ' duration=' + NUM + r' crystals=\d+$',
    'native': r' fn=\w+ who=' + ACTOR + r' a=-?\d+ b=-?\d+ x=' + NUM + r' form=\w+$',
    'scan': r' ctx=\S+ centre=' + ACTOR + ' aroundCentre=' + NUM + ' aroundYou=' + NUM + r' high=\d+ picked=-?\d+$',
    'scan-c': (r'(?: who=' + ACTOR + ' d_you=' + NUM + ' d_centre=' + NUM + ' hostile=' + B + ' teammate=' + B + ' engaged=' + B +
               r' verdict=[\w-]+ member=\d+| beyond=\d+ verdict=far)$'),
    'second': (r' form=\w+ spent=' + NUM + ' bled=' + NUM + ' flow=' + NUM + ' close=' + B + ' storm=' + B +
               ' dH=(?:-|' + NUM + ') dM=(?:-|' + NUM + ') dS=(?:-|' + NUM + ') you=' + ACTOR + '$'),
    'env': (r' wet=' + B + ' stormy=' + B + ' thunder=' + B + ' night=' + B + ' changed=' + B +
            r' classification=-?\d+ lightning=\d+ wind=\d+ hour=' + NUM + ' interior=' + B + ' swimming=' + B +
            ' underwater=' + B + '(?: weather=' + FID8 + ')?$'),
    'domain': (r' el=\w+ ref=' + FID8 + ' age=' + NUM + ' lifetime=' + NUM + ' radius=' + NUM + ' magnitude=' + NUM +
               ' owner=you d=' + NUM + '$'),
    'domain-in': r' ref=' + FID8 + r' el=\w+ d=' + NUM + ' who=' + ACTOR + ' hostile=' + B + ' teammate=' + B + ' commanded=' + B + '$',
    'domain-new': r' ref=' + FID8 + r' el=\w+$',
    'domain-gone': r' ref=' + FID8 + '$',
    'domain-you': r' inside=[\w,]+ you=' + ACTOR + '$',
    'domain-enemy': r' who=' + ACTOR + r' inside=[\w,]+$',
    'switch': (r' via=\w+ wanted=\w+ kind=\w+ element=\w+ active=' + B + r' current=\w+ dead=' + B + ' enabled=' + B +
               ' freePass=' + B + ' freeOpen=' + B + ' gate=' + NUM + ' you=' + ACTOR + '$'),
    'key': (r' code=\d+ element=\w+ verdict=(?:accepted|blocked) paused=' + B + ' menu=' + B + ' console=' + B + ' text=' + B +
            ' loading=' + B + r' thread=\d+$'),
    'mcm': r' global=\S+ old=' + NUM + ' new=' + NUM + '$',
    'mcm-state': r'(?: [A-Za-z0-9_]+=' + NUM + ')+$',
    'node': r' change=[+-] id=[0-9A-F]{6} name=.*$',
    'node-state': r' count=\d+ ids=[0-9A-F,]*$',
    'pap': r' kind=\S+ who=' + ACTOR + '(?: .*)?$',
    'tick': r' state=(?:stopped|running) active=\d+(?: paused=' + B + ' loading=' + B + ')?$',
    'interrupt': r' who=' + ACTOR + '$',
    'casting': (r' who=' + ACTOR + r' caster=[01] state=-?\d+ castingTimer=' + NUM + ' spell=' + FID8 + ' casting=' + B + '$'),
    'wash': (r' on=' + ACTOR + r' effect=[0-9A-F]{8} type=-?\d+ castingSource=-?\d+ duration=' + NUM + ' elapsed=' + NUM +
             ' hostile=' + B + ' ours=' + B + ' company=' + B + ' verdict=(?:washed|kept)$'),
    'rng': r' ctx=\S+ draws=.+$',
    'trace': r' .+$',
    'fire-source': r' tier=\d+ radius=' + NUM + ' perEnemy=' + NUM + ' cost=' + NUM + r' hostiles=\d+ bath=' + B + '$',
    'spread': (r' kind=(?:miasma|plague) doses=' + NUM + '(?: chance=' + NUM + ')? d=' + NUM + ' from=' + ACTOR + ' to=' + ACTOR + '$'),
    'silence': r' on=' + ACTOR + '$',
    'slow-immune': r' dispelled=\d+$',
}


def pattern(kind):
    return PREFIX.format(kind=kind) + BODIES[kind]


def table():
    kinds = {k: pattern(k) for k in BODIES}
    kinds['step'] = STEP
    return {'note': 'GENERATED by build/fix26_format.py -- the probe log line formats (native/include/Trace.h); '
                    'trace_test.cpp and probe-judge.py read lines with these', 'kinds': kinds}


def FIXTURE():
    text = json.dumps(table(), indent=1, ensure_ascii=False) + '\n'
    if not JSON.exists() or JSON.read_text(encoding='utf-8') != text:
        JSON.write_text(text, encoding='utf-8', newline='\n')
    return JSON


if __name__ == '__main__':
    print(FIXTURE())
