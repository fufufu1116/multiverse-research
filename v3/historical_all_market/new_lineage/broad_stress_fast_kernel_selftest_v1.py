from __future__ import annotations
import math
import numpy as np
from broad_stress_fast_kernel_v1 import TOP3_KEYS,pred_array,score_arrays,stress_truth_array
from c0_c1_n1_multiworld_stress_v1 import MODELS,_expected_log_loss,_joint_brier,_truth_entropy
from digital_twin_stress_grid_v1 import ASSUMPTION_GRID,stress_truth_joint
from digital_twin_v1 import pre_view
from c0_c1_n1_broad_assumption_range_stress_v1 import _materialize

def main():
    for idx,(world,line,bank,wind,rho) in enumerate([
        ('R0_CURRENT_SYNTHETIC','L322',333,0.0,0.55),
        ('R1_EMPIRICAL_MARGINAL','L43',400,3.0,0.75),
        ('R2_EMPIRICAL_JOINT','L511',500,5.0,0.90),
    ]):
        race=_materialize(world,line,bank,wind,rho,20260820,idx+2)
        preds={m:fn(pre_view(race)) for m,fn in MODELS.items()}
        for cfg in ASSUMPTION_GRID:
            slow=stress_truth_joint(race,cfg); fast=stress_truth_array(race,cfg)
            slow_arr=np.array([slow[k] for k in TOP3_KEYS],dtype=float)
            assert np.max(np.abs(slow_arr-fast)) < 2e-15,(cfg.scenario_id,np.max(np.abs(slow_arr-fast)))
            for m,p in preds.items():
                pa=pred_array(p); ll,kl,br=score_arrays(fast,pa)
                ll0=_expected_log_loss(slow,p); kl0=ll0-_truth_entropy(slow); br0=_joint_brier(slow,p)
                assert math.isclose(ll,ll0,rel_tol=2e-15,abs_tol=2e-15),(m,cfg.scenario_id,ll,ll0)
                assert math.isclose(kl,kl0,rel_tol=2e-14,abs_tol=2e-14)
                assert math.isclose(br,br0,rel_tol=2e-14,abs_tol=2e-14)
    print('BROAD_STRESS_FAST_KERNEL_SELFTEST_PASS')
if __name__=='__main__':main()
