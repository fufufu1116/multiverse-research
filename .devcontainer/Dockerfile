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
COPY governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7R3_EXTERNAL_SESSION_GATE_20260901.go /tmp/session-gate.go
COPY governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7R3_IMAGE_IDENTITY_BUILDER_20260901.py /tmp/image-identity-builder.py
RUN set -eu; \
 /usr/bin/python3 -m pip install --no-cache-dir --only-binary=:all: --require-hashes --target /opt/multiverse/v36/pydeps -r /opt/multiverse/v36/requirements.txt; \
 /usr/bin/python3 -m py_compile /opt/multiverse/v36/runtime-v7.py /opt/multiverse/v36/step3.py /tmp/manifest.py /tmp/python-actual-use-selftest.py /tmp/image-identity-builder.py; \
 CGO_ENABLED=0 go build -trimpath -buildvcs=false -ldflags='-s -w -buildid=' -o /usr/local/sbin/multiverse-v36-anchor-v7r2 /tmp/producer.go; \
 CGO_ENABLED=0 go build -trimpath -buildvcs=false -ldflags='-s -w -buildid=' -o /usr/local/sbin/multiverse-v36-control-v7r2 /tmp/control.go; \
 CGO_ENABLED=0 go build -trimpath -buildvcs=false -ldflags='-s -w -buildid=' -o /usr/local/sbin/multiverse-v36-session-gate-v7r3 /tmp/session-gate.go; \
 rm -f /tmp/producer.go /tmp/control.go /tmp/session-gate.go; \
 chown -R root:root /opt/multiverse/v36 /usr/local/sbin/multiverse-v36-anchor-v7r2 /usr/local/sbin/multiverse-v36-control-v7r2 /usr/local/sbin/multiverse-v36-session-gate-v7r3; \
 chmod 0555 /usr/local/sbin/multiverse-v36-anchor-v7r2 /usr/local/sbin/multiverse-v36-control-v7r2 /usr/local/sbin/multiverse-v36-session-gate-v7r3; \
 chmod 0444 /opt/multiverse/v36/runtime-v7.py /opt/multiverse/v36/step3-binding.json /opt/multiverse/v36/step3.py /opt/multiverse/v36/requirements.txt; \
 chmod -R go-w /opt/multiverse/v36/pydeps; chmod 0555 /opt/multiverse/v36/pydeps /opt/multiverse/v36/empty-config /opt/multiverse/v36; \
 rm -f /etc/sudoers.d/*; find /bin /sbin /usr/bin /usr/sbin /usr/local/bin /usr/local/sbin /usr/local/libexec -xdev -type f -perm /6000 -exec chmod a-s {} + 2>/dev/null || true; \
 if command -v getcap >/dev/null 2>&1 && command -v setcap >/dev/null 2>&1; then getcap -r /bin /sbin /usr/bin /usr/sbin /usr/local/bin /usr/local/sbin /usr/local/libexec 2>/dev/null | cut -d= -f1 | while read -r p; do [ -n "$p" ] && setcap -r "$p" || true; done; fi; \
 /usr/bin/python3 /tmp/manifest.py; \
 exec 3</usr/bin/python3; /proc/self/fd/3 -I -S -B /tmp/python-actual-use-selftest.py; exec 3<&-; \
 /usr/local/sbin/multiverse-v36-control-v7r2 build-selftest; \
 test "$(stat -c '%u %a' /opt/multiverse/v36/closure-manifest-v7.json)" = '0 444'; \
 /usr/bin/python3 /tmp/image-identity-builder.py; \
 test "$(stat -c '%u %a' /opt/multiverse/v36/image-identity-v7r3.json)" = '0 444'; \
 rm -f /tmp/manifest.py /tmp/python-actual-use-selftest.py /tmp/image-identity-builder.py
ENTRYPOINT ["/usr/local/sbin/multiverse-v36-session-gate-v7r3"]
