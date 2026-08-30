# v19.7.16 Revision-C frozen review fixtures

NONLIVE / NONCANONICAL. These files are review inputs only.

`bin/git`, `bin/sha256sum`, and `SCENARIO_MATRIX.json` are frozen fixture objects for `BYTE_IDENTICAL_COMPLETE_LOADER` cases 103..112 only. A Lab-created scenario directory MUST copy only frozen objects plus a one-line `SCENARIO` selector and a `MANIFEST.sha256` covering every file. The case-run maps `git` to `/usr/local/bin/git` and `sha256sum` to `/usr/bin/sha256sum`, matching loader-visible paths.

Revision-C evidence classes are strict and non-substitutable:
- 103..112: `BYTE_IDENTICAL_COMPLETE_LOADER` using these fixtures.
- production-positive 113: immutable recovery-head static/mechanical proof only; these fixture objects do not satisfy it.
- 114/success: `GENERATED_POST_TRUST_BOUNDARY_EQUIVALENT` only, generated from exact loader boundary plus mechanically extracted proof-relevant loader dependencies. These fixture objects do not satisfy it.
- fallback115: `SYNTHETIC_FALLBACK_EQUIVALENT` only.

No network/live/OAuth/Runtime authority. Runtime OFF.
