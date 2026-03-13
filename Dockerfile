FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1

COPY --from=ghcr.io/astral-sh/uv:0.7.12 /uv /uvx /bin/

COPY pyproject.toml uv.lock /app/
COPY src/ /app/src/

RUN cd /app && uv pip --no-cache-dir install --system .

WORKDIR /home/entropy-data

ENTRYPOINT ["entropy-data"]
