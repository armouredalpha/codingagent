# ---------------------------------------------------------------------------
# robo_assess — generator app image.
# Runs the assessment pipeline; requires OPENROUTER_API_KEY or ANTHROPIC_API_KEY.
#
# Build:  docker build -t robo-assess:latest .
# Run:    docker run --rm \
#           -e OPENROUTER_API_KEY=sk-... \
#           -v $(pwd)/outputs:/app/outputs \
#           robo-assess:latest \
#           generate --md configs/Navigation_Assessment.docx.md
# ---------------------------------------------------------------------------
FROM python:3.11-slim

LABEL org.opencontainers.image.title="robo_assess" \
      org.opencontainers.image.description="Multi-agent ROS2 coding-assessment generator" \
      org.opencontainers.image.version="1.0.0"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install --no-cache-dir .

ENTRYPOINT ["robo-assess"]
CMD ["--help"]
