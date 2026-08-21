# Named stage rather than an inline `COPY --from=ghcr.io/astral-sh/uv:...`:
# Dependabot's Docker parser only reads FROM lines, so an inline image
# reference is never updated.
FROM ghcr.io/astral-sh/uv:0.12.5 AS uv

FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1

COPY --from=uv /uv /uvx /bin/

COPY pyproject.toml uv.lock README.md /app/
COPY src/ /app/src/

RUN cd /app && uv pip --no-cache-dir install --system .

WORKDIR /home/entropy-data

ENTRYPOINT ["entropy-data"]
