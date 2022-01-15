ARG  CONDA_VER=4.10.3
ARG  PY_VER=3.9
FROM datajoint/miniconda3:${CONDA_VER}-py${PY_VER}-debian

COPY --chown=anaconda:anaconda ./apt_requirements.txt ./pip_requirements.txt /tmp/
RUN \
    /entrypoint.sh echo "System packages installed." && \
    rm /tmp/apt_requirements.txt /tmp/pip_requirements.txt
