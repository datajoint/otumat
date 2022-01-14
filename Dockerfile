ARG  PY_VER=3.8
ARG  ALPINE_VER=3.10
FROM python:${PY_VER}-alpine${ALPINE_VER}

RUN \
    # for packaging to PyPi and conda recipe generation
    apk add gcc musl-dev libffi-dev openssl-dev git build-base 
    # && \
    # version pinned cryptography due to Rust dependency (for now)
    # pip install --user cryptography==3.3.2 twine grayskull flask appdirs watchdog

ENV PATH "/root/.local/bin:$PATH"