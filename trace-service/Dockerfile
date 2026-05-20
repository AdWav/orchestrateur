FROM python:3.11-slim

WORKDIR /app

COPY trace-service/pyproject.toml trace-service/README.md ./
COPY trace-service/orchestrateur_trace ./orchestrateur_trace

RUN pip install --no-cache-dir -e .

# Ecouter sur toutes les interfaces dans un conteneur ; sur l'hote, garder TRACE_BIND_HOST=127.0.0.1
ENV TRACE_BIND_HOST=0.0.0.0
ENV TRACE_PORT=8090

EXPOSE 8090

CMD ["python", "-m", "orchestrateur_trace"]
