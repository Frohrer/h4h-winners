FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim
WORKDIR /app
# The venv lives outside /app so mounting the source in dev doesn't hide it.
ENV UV_PROJECT_ENVIRONMENT=/venv UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-install-project
COPY . .
EXPOSE 8000
CMD ["uv", "run", "--frozen", "fastapi", "dev", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]
