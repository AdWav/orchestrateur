FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Couche mise en cache : ne rerun que si les deps changent (pas lors d'un edit Python).
COPY mcp-server/requirements-container.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /tmp/requirements.txt

# Application : seule cette couche invalide lors des modifications du code MCP.
COPY mcp-server/orchestrateur_mcp /app/orchestrateur_mcp

ENV ORCHESTRATOR_API_BASE=http://backend:8000

EXPOSE 8010

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8010/healthz', timeout=3)"

CMD ["uvicorn", "orchestrateur_mcp.app:app", "--host", "0.0.0.0", "--port", "8010"]
