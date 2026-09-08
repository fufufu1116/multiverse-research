# Lane B Integrated Resilience Convergence v1

Research Lane B closure Candidate under Issue #254 / parents #239 and #201.

This Candidate composes the fresh-base publisher resilience integration from PR #250 and the T2 resilience integration from PR #252 on one canonical-main tree. It also includes the pre-adoption combined fault replay harness from PR #242 and a joint wrapper-aware validator.

Integrated behavior:

1. Publisher side
   - reject stale/noncanonical request before result use or publication;
   - canonicalize concurrent trusted result comments by smallest GitHub comment ID;
   - recover an exact existing canonical PASS receipt after publication-success / receipt-loss crash;
   - after a new publication, Fresh-read and require the new result itself to be canonical.

2. T2 side
   - require the referenced Lab PASS to be the canonical trusted result for the exact marker;
   - later duplicate Lab PASS comments remain durable but non-consumable;
   - recover an exact canonical T2 receipt after publication-success / receipt-loss crash;
   - converge concurrent T2 publication to the smallest trusted T2 comment ID;
   - after new T2 publication, Fresh-read and require the new T2 itself to be canonical.

3. Compatibility
   - adopted publisher implementation is preserved byte-for-byte as `publisher_legacy_v1.py`;
   - adopted T2 implementation is preserved byte-for-byte as `t2_legacy_v1.py`;
   - new logic is applied through thin wrappers and isolated helper modules;
   - fixed shared Lab/Auditor Steps remain unchanged.

4. Validation
   - the common legacy validator continues to validate the rest of the fixed dispatcher surface;
   - known publisher-wrapper and T2-wrapper source-layout findings are replaced by explicit checks against legacy + wrapper files;
   - the combined replay harness remains pre-adoption preparation and does not count as the final Lane B exit replay until the relevant integration is independently reviewed/adopted and replayed on adopted lineage.

Proof ceiling: `LANE_B_INTEGRATED_RESILIENCE_CONVERGENCE_REPOSITORY_PREPARATION_ONLY`.

RUNTIME: OFF.
