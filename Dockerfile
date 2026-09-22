# ---------------------------------------------------------------------------
# coding_agent — generator app image.
# Runs the assessment pipeline; requires OPENROUTER_API_KEY or ANTHROPIC_API_KEY.
#
# Build:  docker build -t coding-agent:latest .
# Run:    docker run --rm \
#           -e OPENROUTER_API_KEY=sk-... \
#           -v $(pwd)/outputs:/app/outputs \
#           -v $(pwd)/memory:/app/memory \
#           -v $(pwd)/vectorstore:/app/vectorstore \
#           coding-agent:latest \
#           generate --md configs/Navigation_Assessment.docx.md
#
# Two stages: `builder` resolves + compiles wheels into a venv, `runtime`
# copies only that venv plus the source tree — no compiler toolchain, pip
# cache, or apt lists ship in the final image.
# ---------------------------------------------------------------------------

FROM python:3.11-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# build-essential only exists in this stage — some pinned deps (e.g.
# pydantic-core, numpy/scipy under the `dev` extra) need a compiler to
# build wheels on architectures without prebuilt ones.
RUN apt-get update -q \
    && apt-get install -y -q --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install --no-cache-dir .


FROM python:3.11-slim AS runtime

LABEL org.opencontainers.image.title="coding_agent" \
      org.opencontainers.image.description="Multi-agent ROS2 coding-assessment generator" \
      org.opencontainers.image.version="1.0.0"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

# ca-certificates: the pipeline calls out to api.openrouter.ai / api.anthropic.com
# over HTTPS — without it, every LLM call fails TLS verification.
RUN apt-get update -q \
    && apt-get install -y -q --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 --shell /usr/sbin/nologin coding

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app /app

# outputs/, memory/, vectorstore/, logs/ are written at runtime — typically
# bind-mounted (see the `docker run -v` examples above), but need to exist
# and be writable by the non-root user even when they aren't.
RUN mkdir -p outputs memory vectorstore logs \
    && chown -R coding:coding /app

USER coding

ENTRYPOINT ["coding-agent"]
CMD ["--help"]
