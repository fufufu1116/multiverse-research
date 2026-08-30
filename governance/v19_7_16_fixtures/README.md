# v19.7.16 frozen review fixtures

NONLIVE / NONCANONICAL. These files are review inputs only.

`bin/git`, `bin/sha256sum`, and `SCENARIO_MATRIX.json` are exact frozen fixture objects. A Lab-created scenario directory MUST copy only these frozen objects plus a one-line `SCENARIO` selector and a `MANIFEST.sha256` covering every file. The case-run maps the shims to loader-visible command paths: git to `/usr/local/bin/git`, sha256sum to the loader's absolute `/usr/bin/sha256sum`.

Important feasibility boundary: because the exact loader cryptographically binds the historical runner Git blob and SHA-256, scenarios 113, 114 and success cannot substitute arbitrary synthetic runner bytes while remaining byte-identical complete-loader tests. Independent Lab must determine whether those cases can be demonstrated without weakening those trust gates. If not, this candidate remains FIX_REQUIRED rather than fabricating evidence.

No network/live/OAuth/Runtime authority. Runtime OFF.
