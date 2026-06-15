# ---------------------------------------------------------------------------
# robo_assess — runs the assessment generator fully offline by default.
# ---------------------------------------------------------------------------
FROM python:3.11-slim

LABEL org.opencontainers.image.title="robo_assess" \
      org.opencontainers.image.description="Multi-agent ROS2 coding-assessment generator" \
      org.opencontainers.image.version="1.0.0"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ROBO_PROVIDER=offline

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project.
COPY . .

# Install the package (provides the `robo-assess` console script).
RUN pip install --no-cache-dir .

# Generate datasets at build time so the image ships populated.
RUN python tools/generate_datasets.py

# Default: print CLI help. Override the command to generate, e.g.:
#   docker run --rm -v $(pwd)/outputs:/app/outputs robo-assess \
#       generate --request configs/ros2_fundamentals.yaml
ENTRYPOINT ["python", "-m", "robo_assess.cli"]
CMD ["--help"]
