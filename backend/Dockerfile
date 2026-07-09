FROM python:3.12-slim

# git is needed to install the pinned ca-roads-mcp git dependency.
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src/ src/
RUN pip install --no-cache-dir .

RUN useradd --uid 1001 --create-home appuser
USER 1001

ENV PORT=8080
CMD ["chaincheck-api"]
