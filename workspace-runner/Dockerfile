FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV WORKSPACE_ROOT=/workspaces

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir "pytest>=8.0"

WORKDIR /workspaces

CMD ["sleep", "infinity"]
