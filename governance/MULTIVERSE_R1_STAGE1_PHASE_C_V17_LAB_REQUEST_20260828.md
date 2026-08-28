# FINAL LAB IMPLEMENTATION REVIEW REQUEST — R1 STAGE 1 PHASE C v17 SINGLE-PASTE RECOVERY

Role: Independent Lab. Do not use Core conclusions as your judgment. Fresh-read the exact current branch head first.

Review branch: agent/r1-stage1-phase-c-v17-full-step1-single-paste-recovery
Expected predecessor head entering request creation: 1cbef677d7e7d7bf369207fbf2d9737da4316a8b
Canonical main remains 74ea95e59ac0654e1a0c1f811a178b3eef7b073c. Runtime OFF.

Review the recovery note, implementation-freeze note, and tools/multiverse_r1_stage1_phase_c_step1_single_paste_v17.py as one unit. Fresh-read authoritative manifest comment 5420731105 and the exact reviewed v2/v3 repository artifacts. Independently rederive the 4687-byte Step1 source, its SHA-256, 6252-character RFC4648 base64, and all thirteen chunk boundaries/hashes.

Required review questions:
1. Does the generator reject any payload not exactly matching the frozen authoritative Step1 bytes?
2. Is the emitted action deterministic and fully hash-freezable?
3. Does the emitted action preserve the authoritative successful Step1 INIT + journal-dominant chunk + ASSEMBLE + SOURCE + RETRIEVAL evidence/durability/file-trust semantics, rather than merely reproducing decoded payload bytes?
4. Are quoting, environment inheritance, nofollow/exclusive creation, tmpfs assumptions, file mode/owner/type checks, fsync boundaries and final success/failure observability correct?
5. Can Core mechanically Fresh-fetch and verify the complete reviewed action hash immediately before future delivery, eliminating template-selection ambiguity?
6. Does anything in the candidate authorize OAuth, authenticated probe, production preflight retry, Step4, --apply, production mutation, secret/writer-key operation, main/ruleset mutation, merge or Runtime activation? It must not.

Run harmless local positive/negative tests as needed. If any authoritative Step1 semantic is missing, verdict must be FIX_REQUIRED and identify the smallest exact remediation. Do not repair the implementation yourself.

Write the independent result back to PR #74. No live Codespace, OAuth, authenticated GET /user, production mutation, merge, or Runtime activation.