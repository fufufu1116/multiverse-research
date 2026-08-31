FROM mcr.microsoft.com/devcontainers/universal@sha256:4100b24aa64681c143715b6b9ba9db79cbd237b00edfe64782b20e8427648fc9

USER root
SHELL ["/bin/bash","-o","pipefail","-c"]

RUN install -d -o root -g root -m 0555 /opt/multiverse/v36 /opt/multiverse/v36/empty-config /opt/multiverse/v36/pydeps
COPY .devcontainer/v19_7_36_requirements.txt /opt/multiverse/v36/requirements.txt
COPY governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V4_RUNTIME_20260831.py /opt/multiverse/v36/runtime.py
COPY governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V4_ROOT_ANCHOR_PRODUCER_20260831.go /tmp/mv-v36-anchor.go

RUN set -eu; \
    test -x /usr/bin/python3; \
    /usr/bin/python3 -m pip install --no-cache-dir --only-binary=:all: --require-hashes --target /opt/multiverse/v36/pydeps -r /opt/multiverse/v36/requirements.txt; \
    CGO_ENABLED=0 go build -trimpath -buildvcs=false -ldflags='-s -w -buildid=' -o /usr/local/sbin/multiverse-v36-anchor-producer /tmp/mv-v36-anchor.go; \
    rm -f /tmp/mv-v36-anchor.go; \
    chown -R root:root /opt/multiverse/v36 /usr/local/sbin/multiverse-v36-anchor-producer; \
    chmod 0555 /usr/local/sbin/multiverse-v36-anchor-producer; \
    chmod 0444 /opt/multiverse/v36/runtime.py /opt/multiverse/v36/requirements.txt; \
    chmod -R go-w /opt/multiverse/v36/pydeps; \
    chmod 0555 /opt/multiverse/v36/pydeps /opt/multiverse/v36/empty-config /opt/multiverse/v36; \
    rm -f /etc/sudoers.d/*; \
    find /bin /sbin /usr/bin /usr/sbin /usr/local/bin /usr/local/sbin -xdev -type f -perm /6000 -exec chmod a-s {} + 2>/dev/null || true; \
    if command -v getcap >/dev/null 2>&1 && command -v setcap >/dev/null 2>&1; then getcap -r /bin /sbin /usr/bin /usr/sbin /usr/local/bin /usr/local/sbin 2>/dev/null | cut -d= -f1 | while read -r p; do [ -n "$p" ] && setcap -r "$p" || true; done; fi; \
    test "$(stat -c '%u %a' /usr/local/sbin/multiverse-v36-anchor-producer)" = '0 555'; \
    test "$(stat -c '%u %a' /opt/multiverse/v36/runtime.py)" = '0 444'

ENTRYPOINT ["/usr/local/sbin/multiverse-v36-anchor-producer"]
