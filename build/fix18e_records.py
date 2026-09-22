"""Console-free setup records; the original sixteen probe records stay unchanged."""
import struct

QUEST = 0x840
POWERS = [(1, 0x841, 0x844, 'ESSB_ProbePreparePower', '探針：準備＋第一題'),
          (2, 0x842, 0x845, 'ESSB_ProbeSecondPower', '探針：第二題'),
          (3, 0x843, 0x846, 'ESSB_ProbeCleanupPower', '探針：清理'),
          (5, 0x880, 0x881, 'ESSB_ProbeFourthPower', '探針：第四題'),
          (4, 0x847, 0x848, 'ESSB_ProbeThirdPower', '探針：第三題')]


def setup_props(b):
    props = {name: (1, b.own(fid)) for name, fid in [
        ('PreparePower', 0x841), ('SecondPower', 0x842), ('CleanupPower', 0x843), ('ThirdPower', 0x847),
        ('Meter', 0x831), ('ProbeAB', 0x820), ('ProbeHit', 0x821),
        ('ProbeMultiply', 0x822), ('Gate', 0x832), ('Session', 0x833),
        ('CrossA', 0x850), ('CrossB', 0x851), ('CrossA2', 0x852), ('CrossB2', 0x853), ('FourthPower', 0x880), ('TieA', 2144), ('TieB', 2145), ('TieA2', 2147), ('TieB2', 2146), ('TieVariant', 2160), ('TieResult1', 2161), ('TieResult2', 2162), ('TieResult3', 2163), ('TieResult4', 2164)]}
    props.update(Dagger=(1, 0x1397e), BanditBase=(1, 0xc3ca0))
    return props


def quest_vmad(b):
    return (struct.pack('<3H', 5, 2, 0) + b'\x02' + struct.pack('<3H', 0, 0, 1)
            + b.obj(b.own(QUEST), 0) + struct.pack('<3H', 5, 2, 1)
            + b.script('ESSBProbeSetup', setup_props(b)))


def add_records(b, add, folder):
    for mode, spell, effect, edid, label in POWERS:
        add('MGEF', effect, edid+'Effect', [
            ('VMAD', b.vmad('ESSBProbePower', {'Setup': (1, (b.own(QUEST), 0)), 'Mode': (3, mode)})),
            ('FULL', b.Z(label)),
            ('DATA', b.mgef_data(b.MGEF_UTILITY_FLAGS, 1, casting=1, delivery=0))])
        add('SPEL', spell, edid, [
            ('OBND', bytes(12)), ('FULL', b.Z(label)), ('ETYP', b.I(0x25bee)),
            ('DESC', b.Z('一次性測試存檔專用。施放後依畫面提示與 READY 日誌操作。')),
            ('SPIT', b.spit(3, 1, 0)), ('EFID', b.I(b.own(effect))),
            ('EFIT', struct.pack('<fII', 0.0, 0, 1))])
    add('QUST', QUEST, 'ESSB_ProbeSetupQuest', [
        ('VMAD', quest_vmad(b)), ('FULL', b.Z('探針自動準備')),
        ('DNAM', struct.pack('<HBBII', 0x11, 0, 255, 0, 0)),
        ('NEXT', b''), ('ANAM', b.I(1)), ('ALST', b.I(0)),
        ('ALID', b.Z('Player')), ('FNAM', b.I(0)), ('ALFR', b.I(0x14)),
        ('VTCK', b.I(0)), ('ALED', b'')])
    (folder/'SEQ').mkdir(exist_ok=True)
    (folder/'SEQ/Elements Spellblade Round18 Probes.seq').write_bytes(b.I(b.own(QUEST)))
