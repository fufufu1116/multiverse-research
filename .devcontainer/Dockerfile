FROM mcr.microsoft.com/devcontainers/universal@sha256:4100b24aa64681c143715b6b9ba9db79cbd237b00edfe64782b20e8427648fc9
USER root
SHELL ["/bin/bash","-o","pipefail","-c"]
RUN install -d -o root -g root -m 0555 /opt/multiverse/v36 /opt/multiverse/v36/empty-config /opt/multiverse/v36/pydeps /usr/local/libexec
COPY .devcontainer/v19_7_36_requirements.txt /opt/multiverse/v36/requirements.txt
COPY governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7_RUNTIME_20260901.py /opt/multiverse/v36/runtime-v7.py
COPY governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V6_STEP3_BINDING_20260901.json /opt/multiverse/v36/step3-binding.json
COPY governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V6_STEP3_NONMUTATING_PAYLOAD_20260901.py /opt/multiverse/v36/step3.py
COPY governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7R2_ROOT_ANCHOR_PRODUCER_20260901.go /tmp/producer.go
COPY governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7R2_CONTROL_PLANE_RUNNER_20260901.go /tmp/control.go
COPY governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7R2_RECURSIVE_CLOSURE_MANIFEST_20260901.py /tmp/manifest.py
COPY governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7R2_PYTHON_ACTUAL_USE_SELFTEST_20260901.py /tmp/python-actual-use-selftest.py
COPY governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7R6_EXTERNAL_SESSION_GATE_20260901.go /tmp/session-gate-v7r6.go
COPY governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R7_EVIDENCE_SCHEMA_ADAPTER_20260901.py /tmp/evidence-schema-adapter.py
COPY governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R7_ATTACH_READY_STATUS_ADDON_20260901.go /tmp/session-status-addon-v7r7.go
COPY governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R7_MANUAL_ARM_LAUNCHER_20260901.go /tmp/manual-arm-v7r7.go
COPY governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R7_UI_READY_WRITER_20260901.go /tmp/ui-ready-v7r7.go
COPY governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R7_UI_READY_STATIC_ENV_GUARD_20260902.go /tmp/ui-ready-env-guard-v7r7.go
COPY governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7R3_IMAGE_IDENTITY_BUILDER_20260901.py /tmp/image-identity-builder.py
COPY governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R6_RATE_BUDGET_HISTORY_SELFTEST_20260901.py /tmp/rate-budget-history-selftest.py
RUN set -eu; \
 /usr/bin/python3 -m pip install --no-cache-dir --no-compile --only-binary=:all: --require-hashes --target /opt/multiverse/v36/pydeps -r /opt/multiverse/v36/requirements.txt; \
 find /opt/multiverse/v36/pydeps -type f -name '*.pyc' -delete; \
 find /opt/multiverse/v36/pydeps -type d -name '__pycache__' -prune -exec rm -rf {} +; \
 test -z "$(find /opt/multiverse/v36/pydeps \( -type f -name '*.pyc' -o -type d -name '__pycache__' \) -print -quit)"; \
 /usr/bin/python3 -m py_compile /opt/multiverse/v36/runtime-v7.py /opt/multiverse/v36/step3.py /tmp/manifest.py /tmp/python-actual-use-selftest.py /tmp/image-identity-builder.py /tmp/rate-budget-history-selftest.py /tmp/evidence-schema-adapter.py; \
 /usr/bin/python3 /tmp/evidence-schema-adapter.py --selftest /tmp/session-gate-v7r6.go; \
 /usr/bin/python3 /tmp/evidence-schema-adapter.py /tmp/session-gate-v7r6.go /tmp/session-gate.go; \
 CGO_ENABLED=0 go build -trimpath -buildvcs=false -ldflags='-s -w -buildid=' -o /usr/local/sbin/multiverse-v36-anchor-v7r2 /tmp/producer.go; \
 CGO_ENABLED=0 go build -trimpath -buildvcs=false -ldflags='-s -w -buildid=' -o /usr/local/sbin/multiverse-v36-control-v7r2 /tmp/control.go; \
 CGO_ENABLED=0 go build -trimpath -buildvcs=false -ldflags='-s -w -buildid=' -o /usr/local/sbin/multiverse-v36-session-gate-v7r7 /tmp/session-gate.go /tmp/session-status-addon-v7r7.go; \
 CGO_ENABLED=0 go build -trimpath -buildvcs=false -ldflags='-s -w -buildid=' -o /usr/local/bin/multiverse-v36-arm-v7r7 /tmp/manual-arm-v7r7.go; \
 CGO_ENABLED=0 go build -trimpath -buildvcs=false -ldflags='-s -w -buildid=' -o /usr/local/bin/multiverse-v36-ui-ready-v7r7 /tmp/ui-ready-v7r7.go; \
 CGO_ENABLED=0 go build -trimpath -buildvcs=false -ldflags='-s -w -buildid=' -o /usr/local/bin/multiverse-v36-ui-ready-env-guard-v7r7 /tmp/ui-ready-env-guard-v7r7.go; \
 /usr/local/sbin/multiverse-v36-session-gate-v7r7 build-selftest; \
 /usr/bin/python3 /tmp/rate-budget-history-selftest.py; \
 rm -f /tmp/producer.go /tmp/control.go /tmp/session-gate-v7r6.go /tmp/session-gate.go /tmp/evidence-schema-adapter.py /tmp/session-status-addon-v7r7.go /tmp/manual-arm-v7r7.go /tmp/ui-ready-v7r7.go /tmp/ui-ready-env-guard-v7r7.go; \
 chown -R root:root /opt/multiverse/v36 /usr/local/sbin/multiverse-v36-anchor-v7r2 /usr/local/sbin/multiverse-v36-control-v7r2 /usr/local/sbin/multiverse-v36-session-gate-v7r7 /usr/local/bin/multiverse-v36-arm-v7r7 /usr/local/bin/multiverse-v36-ui-ready-v7r7 /usr/local/bin/multiverse-v36-ui-ready-env-guard-v7r7; \
 chmod 0555 /usr/local/sbin/multiverse-v36-anchor-v7r2 /usr/local/sbin/multiverse-v36-control-v7r2 /usr/local/sbin/multiverse-v36-session-gate-v7r7 /usr/local/bin/multiverse-v36-ui-ready-v7r7 /usr/local/bin/multiverse-v36-ui-ready-env-guard-v7r7; \
 chmod 0444 /opt/multiverse/v36/runtime-v7.py /opt/multiverse/v36/step3-binding.json /opt/multiverse/v36/step3.py /opt/multiverse/v36/requirements.txt; \
 chmod -R go-w /opt/multiverse/v36/pydeps; chmod 0555 /opt/multiverse/v36/pydeps /opt/multiverse/v36/empty-config /opt/multiverse/v36; \
 test "$(sha256sum /usr/local/bin/multiverse-v36-ui-ready-v7r7 | cut -d' ' -f1)" = '2fd9e085e866924fb52995e5bb5fcb58763bdbd1fa1ee2c96e1d57df28a42301'; \
 command -v readelf >/dev/null; \
 if readelf -l /usr/local/bin/multiverse-v36-ui-ready-env-guard-v7r7 | grep -F 'Requesting program interpreter'; then exit 92; fi; \
 rm -f /etc/sudoers.d/*; find /bin /sbin /usr/bin /usr/sbin /usr/local/bin /usr/local/sbin /usr/local/libexec -xdev -type f -perm /6000 -exec chmod a-s {} + 2>/dev/null || true; \
 if command -v getcap >/dev/null 2>&1 && command -v setcap >/dev/null 2>&1; then getcap -r /bin /sbin /usr/bin /usr/sbin /usr/local/bin /usr/local/sbin /usr/local/libexec 2>/dev/null | cut -d= -f1 | while read -r p; do [ -n "$p" ] && setcap -r "$p" || true; done; fi; \
 chown root:root /usr/local/bin/multiverse-v36-arm-v7r7; chmod 4555 /usr/local/bin/multiverse-v36-arm-v7r7; \
 test "$(stat -c '%u %g %a' /usr/local/bin/multiverse-v36-arm-v7r7)" = '0 0 4555'; \
 test "$(stat -c '%u %g %a' /usr/local/bin/multiverse-v36-ui-ready-env-guard-v7r7)" = '0 0 555'; \
 test -z "$(find /bin /sbin /usr/bin /usr/sbin /usr/local/bin /usr/local/sbin /usr/local/libexec -xdev -type f -perm /6000 ! -path /usr/local/bin/multiverse-v36-arm-v7r7 -print -quit 2>/dev/null)"; \
 /usr/bin/python3 /tmp/manifest.py; \
 exec 3</usr/bin/python3; /proc/self/fd/3 -I -S -B /tmp/python-actual-use-selftest.py; exec 3<&-; \
 /usr/local/sbin/multiverse-v36-control-v7r2 build-selftest; \
 test "$(stat -c '%u %a' /opt/multiverse/v36/closure-manifest-v7.json)" = '0 444'; \
 /usr/bin/python3 /tmp/image-identity-builder.py; \
 test "$(stat -c '%u %a' /opt/multiverse/v36/image-identity-v7r3.json)" = '0 444'; \
 rm -f /tmp/manifest.py /tmp/python-actual-use-selftest.py /tmp/image-identity-builder.py /tmp/rate-budget-history-selftest.py
