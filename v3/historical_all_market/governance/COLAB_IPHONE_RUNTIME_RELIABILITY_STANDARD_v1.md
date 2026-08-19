# Multiverse — Colab / iPhone Runtime Reliability Standard v1

Status: ENGINEERING STANDARD — ROUTINE / REVERSIBLE
Effective: 2026-08-19 JST
Scope: Multiverse historical-development Colab notebooks and long-running data-engineering stages

## Purpose

Repeated red-cell failures caused by notebook UI, Google Drive I/O, large artifact packaging, or non-resumable execution must not be confused with scientific failure.

This standard changes execution engineering only. It does not change any frozen model, probability, economic rule, HOLDOUT rule, trial definition, or scientific semantics.

## Mandatory rules for future long-running Colab stages

1. **Scientific completion is separated from packaging.**
   - A completed scientific artifact must not be invalidated merely because ZIP creation, browser download, display, or optional packaging fails afterward.

2. **No automatic browser download for large artifacts.**
   - `google.colab.files.download()` is prohibited for normal pipeline artifacts.
   - Artifacts remain in Drive and are inspected through receipts / hashes.

3. **No mandatory giant ZIP after computation.**
   - ZIP creation is optional and must not be a success gate.

4. **Long-running work must be resumable.**
   - Work expected to process hundreds or thousands of records must persist completed chunks or checkpoints.
   - A rerun skips already valid completed chunks rather than restarting from record zero.

5. **Chunk outputs must be atomic.**
   - Write to a temporary local file first.
   - Validate the chunk.
   - Copy/replace the final chunk artifact only after validation.
   - A partially written chunk is never treated as complete.

6. **Heavy Drive writes are minimized.**
   - Do not write one Drive row for every small diagnostic when a compact per-record or per-chunk structure is sufficient.
   - Prefer local `/content` working files and periodic compact Drive checkpoints.

7. **Fatal errors must leave evidence.**
   - On a genuine execution failure, persist a small fatal receipt containing stage, exception type, message, traceback, last completed chunk, scientific trial count, Settlement state, and HOLDOUT state.

8. **Existing PASS fast-path is mandatory.**
   - If exact required artifacts already exist and their receipts/hashes pass, the notebook exits green without recomputation.

9. **Resume fast-path is mandatory where practical.**
   - Valid completed chunks are reused.
   - Only incomplete/missing chunks are recomputed.

10. **Console output stays bounded.**
    - Do not print massive JSON reports into the notebook UI.
    - Print compact stage/chunk progress and final receipt summary only.

11. **Scientific firewall remains strict.**
    - Runtime resilience must never silently substitute data, relax FAIL-CLOSED invariants, open Settlement/RESULT/PAYOUT, alter frozen semantics, or access ECON_HOLDOUT1000.

12. **A UI/I/O failure is classified separately from a scientific failure.**
    - `SCIENTIFIC_FAIL_CLOSED`: a bound scientific/data invariant failed.
    - `RUNTIME_RETRYABLE`: environment/I/O/interruption occurred without violating scientific state.
    - `POSTPROCESS_ONLY`: scientific outputs are complete; optional packaging/display failed.

## Stage 3 v1 incident motivating this standard

Stage 3 v1 wrote an expanded diagnostics CSV directly to mounted Google Drive while simultaneously scanning the ~557 MB Stage 2 catalog. The partial CSV ended during profile rows inside one market, which is incompatible with a normal Stage 3 semantic Fail-Closed point and is consistent with runtime / Drive I/O interruption.

Stage 3 v2 therefore uses compact race/model records, resumable chunks, bounded output, and atomic chunk completion while preserving the exact Stage 3 preregistered filter family.

END OF STANDARD v1
