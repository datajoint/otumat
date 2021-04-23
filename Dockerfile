ARG  PY_VER=3.7
ARG  ALPINE_VER=3.10
FROM python:${PY_VER}-alpine${ALPINE_VER}

RUN \
    # for packaging to PyPi
    apk add gcc musl-dev libffi-dev openssl-dev git && \
    # version pinned cryptography due to Rust dependency (for now)
    pip install --user cryptography==3.3.2 twine