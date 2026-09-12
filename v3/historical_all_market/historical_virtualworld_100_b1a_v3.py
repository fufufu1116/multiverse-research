from __future__ import annotations
import historical_virtualworld_100_b1a_v1 as v1
import historical_virtualworld_100_b1a_v2 as v2  # installs hardened winner parser

# Exact bank lengths for the two venues omitted from v1 mapping.
v1.CIRC.update({'maebashi':335.0,'kawasaki':400.0})
v1.OUT=v1.Path('v3/historical_all_market/research_candidates/virtualworld_100_b1a_v3')
v1.OUT.mkdir(parents=True,exist_ok=True)

if __name__=='__main__':
    v1.main()
