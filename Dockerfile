# Wolfi (Chainguard) multi-stage build for catalog-autopilot-backend.
#
# NOTE ON THE BASE IMAGE NAME: the ECR tag below is `.../utility/docker/library/
# python:wolfi-base-latest` — that name is MISLEADING. It is NOT CPython/Debian;
# it is the mirror of `cgr.dev/chainguard/wolfi-base:latest` (Chainguard's glibc
# base with apk, no Python). We install Python ourselves via `apk add python-3.12`,
# so the Python version is pinned here, not by the tag.
#
# WHY Wolfi over Alpine: glibc → every native dep (uvloop, httptools, asyncpg,
# psycopg2-binary, Pillow, rapidfuzz, xxhash, psutil, pydantic-core, cryptography)
# installs from a prebuilt manylinux wheel — no rustup, no -dev headers, no source
# builds, and none of the musl band-aids the Alpine image needed.
# Wolfi's continuously-rebuilt packages also clear OS CVEs unfixable on Alpine/musl.

ARG cloud

# ---------- builder: install python + toolchain, clone git+ssh deps, resolve venv ----------
FROM --platform=linux/amd64 ${cloud:+"831059512818.dkr.ecr.ap-south-1.amazonaws.com/utility/docker/library/"}python:wolfi-base-latest AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ARG SSH_PRIVATE_KEY
ARG SSH_PUBLIC_KEY
ARG SERVICE_NAME

# Wolfi apk (the base has no Python). python-3.12 pins the interpreter; git +
# openssh-client clone the git+ssh:// internal deps (vortex, cache-wrapper, animus).
# build-base/openssl-dev/libffi-dev are insurance — on glibc every native dep
# installs from a prebuilt manylinux wheel, so nothing actually compiles.
RUN apk add --no-cache \
    python-3.12 python-3.12-dev \
    build-base openssl-dev libffi-dev \
    git openssh-client curl

ENV UV_INSTALL_DIR=/usr/local/bin
RUN curl -LsSf https://astral.sh/uv/0.11.7/install.sh | sh

# Install dbmate in the builder and copy the binary into runtime.
RUN curl -fsSL https://github.com/amacneil/dbmate/releases/latest/download/dbmate-linux-amd64 \
    -o /usr/local/bin/dbmate && chmod +x /usr/local/bin/dbmate

WORKDIR /home/ubuntu/1mg/$SERVICE_NAME
COPY pyproject.toml uv.lock README.md ./
ENV VIRTUAL_ENV=/home/ubuntu/1mg/$SERVICE_NAME/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Inject SSH keys (builder stage only — never copied to runtime).
RUN mkdir -p /root/.ssh && chmod 0700 /root/.ssh && \
    echo "$SSH_PRIVATE_KEY" > /root/.ssh/id_ed25519 && \
    echo "$SSH_PUBLIC_KEY"  > /root/.ssh/id_ed25519.pub && \
    chmod 600 /root/.ssh/id_ed25519 /root/.ssh/id_ed25519.pub

# Wolfi's openssh-client has no ssh-keyscan; accept bitbucket + github host keys
# on first connect instead of pre-seeding known_hosts.
ENV GIT_SSH_COMMAND="ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=accept-new -o IdentitiesOnly=yes"

# Resolve the venv against the Wolfi python-3.12 interpreter.
RUN uv sync --frozen --no-dev --python /usr/bin/python3.12 && rm -rf /root/.cache/uv

# ---------- runtime: minimal Wolfi base + python-3.12 + the resolved venv ----------
FROM --platform=linux/amd64 ${cloud:+"831059512818.dkr.ecr.ap-south-1.amazonaws.com/utility/docker/library/"}python:wolfi-base-latest AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ARG SERVICE_NAME

# Runtime libs only:
#   python-3.12  — the interpreter
#   libstdc++    — required by Rust/Cython/C++ wheels at runtime: pydantic-core,
#                  cryptography, uvloop, httptools, asyncpg, rapidfuzz, xxhash
#   ca-certificates — TLS (httpx, redis, qdrant-client, etc.)
#   tzdata       — timezone support
#   git          — kept for any runtime git operations / health-check scripts
RUN apk add --no-cache python-3.12 libstdc++ ca-certificates tzdata git curl

RUN mkdir -p /home/ubuntu/1mg/$SERVICE_NAME/logs

WORKDIR /home/ubuntu/1mg/$SERVICE_NAME
ENV VIRTUAL_ENV=/home/ubuntu/1mg/$SERVICE_NAME/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY --from=builder $VIRTUAL_ENV $VIRTUAL_ENV
COPY --from=builder /usr/local/bin/dbmate /usr/local/bin/dbmate
COPY . .

# Make deployment scripts executable
RUN chmod +x deployment/*.sh
