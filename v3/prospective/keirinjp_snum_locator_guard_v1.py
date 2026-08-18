#!/usr/bin/env python3
import hashlib,unicodedata
TERM_INTERVALS={57: [(11332, 11453)], 58: [(11454, 11558)], 59: [(11559, 11667)], 60: [(11668, 11763)], 61: [(11764, 11861)], 62: [(11862, 11962)], 63: [(11963, 12062)], 64: [(12063, 12158)], 65: [(12159, 12255)], 66: [(12256, 12332)], 67: [(12333, 12407)], 68: [(12408, 12481)], 69: [(12482, 12556)], 70: [(12557, 12632)], 71: [(12633, 12707)], 72: [(12708, 12782)], 73: [(12783, 12857)], 74: [(12858, 12929)], 75: [(12930, 13003)], 76: [(13004, 13078)], 77: [(13079, 13155)], 78: [(13156, 13229)], 79: [(13230, 13302)], 80: [(13303, 13377)], 81: [(13378, 13451)], 82: [(13452, 13520)], 83: [(13521, 13598)], 84: [(13599, 13668)], 85: [(13669, 13745)], 86: [(13746, 13824)], 87: [(13825, 13899)], 88: [(13900, 13975)], 89: [(13976, 14049)], 90: [(14050, 14122)], 91: [(14123, 14200)], 92: [(14201, 14275)], 93: [(14276, 14346)], 94: [(14347, 14422)], 95: [(14423, 14495), (14568, 14568)], 96: [(14496, 14567)], 97: [(14569, 14639), (14693, 14693)], 98: [(14640, 14692), (14694, 14709)], 99: [(14710, 14790)], 100: [(14791, 14856)], 101: [(14857, 14893)], 102: [(14894, 14926)], 103: [(14927, 14958), (14977, 14979)], 104: [(14959, 14976)], 105: [(14980, 15015)], 106: [(15016, 15033)], 107: [(15034, 15067)], 108: [(15068, 15082)], 109: [(15083, 15132)], 110: [(15133, 15154)], 111: [(15155, 15215)], 112: [(15216, 15232)], 113: [(15233, 15300)], 114: [(15301, 15321)], 115: [(15322, 15390)], 116: [(15391, 15411)], 117: [(15412, 15483)], 118: [(15484, 15504)], 119: [(15505, 15572), (15594, 15595)], 120: [(15573, 15593)], 121: [(15596, 15665)], 122: [(15666, 15684)], 123: [(15685, 15754)], 124: [(15755, 15777)], 125: [(15778, 15848)], 126: [(15849, 15867)], 127: [(15868, 15937)], 128: [(15938, 15957)], 129: [(15958, 16025)], 130: [(16026, 16045)]}
PREF_FULL={"北海道":"北海道","青森":"青森県","岩手":"岩手県","宮城":"宮城県","秋田":"秋田県","山形":"山形県","福島":"福島県","茨城":"茨城県","栃木":"栃木県","群馬":"群馬県","埼玉":"埼玉県","千葉":"千葉県","東京":"東京都","神奈川":"神奈川県","新潟":"新潟県","富山":"富山県","石川":"石川県","福井":"福井県","山梨":"山梨県","長野":"長野県","岐阜":"岐阜県","静岡":"静岡県","愛知":"愛知県","三重":"三重県","滋賀":"滋賀県","京都":"京都府","大阪":"大阪府","兵庫":"兵庫県","奈良":"奈良県","和歌山":"和歌山県","鳥取":"鳥取県","島根":"島根県","岡山":"岡山県","広島":"広島県","山口":"山口県","徳島":"徳島県","香川":"香川県","愛媛":"愛媛県","高知":"高知県","福岡":"福岡県","佐賀":"佐賀県","長崎":"長崎県","熊本":"熊本県","大分":"大分県","宮崎":"宮崎県","鹿児島":"鹿児島県","沖縄":"沖縄県"}
def norm(s):
    s=unicodedata.normalize("NFKC",str(s)); s=unicodedata.normalize("NFC",s)
    return "".join(ch for ch in s if not ch.isspace())
def snum_in_term(snum,term):
    n=int(str(snum)); t=int(term)
    if t not in TERM_INTERVALS: raise RuntimeError("QUARANTINE unknown term interval")
    return any(lo<=n<=hi for lo,hi in TERM_INTERVALS[t])
def validate_hint(snum,expected_name,expected_pref,expected_term):
    if not str(snum).isdigit() or len(str(snum)) not in (5,6): raise RuntimeError("QUARANTINE invalid snum hint")
    if not snum_in_term(snum,expected_term): raise RuntimeError("QUARANTINE snum outside official term interval")
    return {"status":"HINT_RANGE_PASS","snum":str(snum).zfill(6)}
def verify_official_profile(profile,expected_name,expected_pref,expected_term,snum):
    if str(profile.get("registration_number","")).zfill(6)!=str(snum).zfill(6): raise RuntimeError("QUARANTINE registration mismatch")
    if norm(profile.get("name",""))!=norm(expected_name): raise RuntimeError("QUARANTINE name mismatch")
    if norm(profile.get("prefecture",""))!=norm(PREF_FULL[expected_pref]): raise RuntimeError("QUARANTINE prefecture mismatch")
    pterm=norm(profile.get("term","")).removesuffix("期")
    if pterm!=str(int(expected_term)): raise RuntimeError("QUARANTINE term mismatch")
    return {"status":"OFFICIAL_IDENTITY_VERIFIED","snum":str(snum).zfill(6)}
