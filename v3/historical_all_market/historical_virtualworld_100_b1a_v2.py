from __future__ import annotations
import re
from bs4 import BeautifulSoup
import historical_virtualworld_100_b1a_v1 as v1

v1.OUT=v1.Path('v3/historical_all_market/research_candidates/virtualworld_100_b1a_v2')
v1.OUT.mkdir(parents=True,exist_ok=True)

def parse_winner_v2(payload):
    soup=BeautifulSoup(payload,'lxml')
    # First attempt: semantic result rows. Accept both bare numeric and '1着'.
    for t in soup.find_all('table'):
        tt=v1.txt(t)
        if '着順' not in tt or '車番' not in tt:
            continue
        for tr in t.find_all('tr'):
            cs=[v1.txt(c) for c in tr.find_all(['td','th'])]
            for i,c in enumerate(cs):
                if re.fullmatch(r'1(?:着)?',c):
                    for d in cs[i+1:]:
                        if re.fullmatch(r'[1-9]',d):
                            return int(d)
    # Kdreams historical result pages sometimes render the same result area outside
    # a conventional table. Restrict fallback to the result section after 天候/着順.
    body=v1.txt(soup)
    anchors=[p for p in (body.find('天候'),body.find('着順')) if p>=0]
    if anchors:
        seg=body[min(anchors):min(anchors)+7000]
        # Typical normalized sequence: ... 着順 車番 選手名 ... 1 3 rider ...
        for pat in (r'着順\s*車番.*?(?:^|\s)1(?:着)?\s+([1-9])\s+',
                    r'(?:^|\s)1(?:着)?\s+([1-9])\s+[一-龯ぁ-んァ-ヶ]'):
            m=re.search(pat,seg,re.S)
            if m:
                return int(m.group(1))
    raise RuntimeError('winner_not_found_v2')

v1.parse_winner=parse_winner_v2
if __name__=='__main__':
    v1.main()
