FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock /app/

RUN uv sync --locked # pip install -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["uv", "run", "src/app.py", "--host", "0.0.0.0", "--port", "5000"]
