FROM python:3.12-slim

WORKDIR /app

RUN pip install uv --quiet

# Copia apenas o necessário para cachear o layer de dependências
COPY pyproject.toml README.md ./

# Instala só as deps (sem editable — não precisa de src code ainda)
RUN uv pip install --system --no-build-isolation \
    agno fastapi "uvicorn[standard]" pydantic pydantic-settings \
    python-dotenv sqlalchemy "groq" "anthropic" "openai" \
    "tavily-python" ddgs httpx beautifulsoup4 lxml feedparser

# Copia o resto do código
COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
