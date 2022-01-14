ARG  CONDA_VER=4.10.3
ARG  PY_VER=3.9
FROM datajoint/miniconda3:${CONDA_VER}-py${PY_VER}-debian

# RUN \
#     # for packaging to PyPi and conda recipe generation
#     apk add gcc musl-dev libffi-dev openssl-dev git build-base 
#     # && \
#     # version pinned cryptography due to Rust dependency (for now)
#     # pip install --user cryptography==3.3.2 twine grayskull flask appdirs watchdog

COPY --chown=anaconda:anaconda ./apt_requirements.txt ./pip_requirements.txt /tmp/
RUN \
    /entrypoint.sh echo "System packages installed." && \
    rm /tmp/apt_requirements.txt /tmp/pip_requirements.txt

# ENV PATH "/root/.local/bin:$PATH"