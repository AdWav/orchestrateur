# syntax=docker/dockerfile:1

FROM debian:bookworm-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    cmake \
    curl \
    git \
    libcurl4-openssl-dev \
    pkg-config \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /build

RUN git clone --depth 1 https://github.com/ggml-org/llama.cpp.git /build/llama.cpp

COPY token-viz-service/ /build/token-viz-service/

RUN mkdir -p /build/token-viz-service/third_party/nlohmann \
  && curl -fsSL -o /build/token-viz-service/third_party/httplib.h \
    https://raw.githubusercontent.com/yhirose/cpp-httplib/v0.18.3/httplib.h \
  && curl -fsSL -o /build/token-viz-service/third_party/nlohmann/json.hpp \
    https://raw.githubusercontent.com/nlohmann/json/v3.11.3/single_include/nlohmann/json.hpp

RUN cmake -S /build/token-viz-service -B /build/token-viz-service/build \
    -DLLAMA_CPP_DIR=/build/llama.cpp \
    -DCMAKE_BUILD_TYPE=Release \
  && cmake --build /build/token-viz-service/build -j"$(nproc)"

FROM debian:bookworm-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    libcurl4 \
    libgomp1 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /build/token-viz-service/build/token-viz-service /app/token-viz-service
COPY token-viz-service/static /app/static

ENV TOKEN_VIZ_BIND_HOST=0.0.0.0
ENV TOKEN_VIZ_PORT=8091
ENV TOKEN_VIZ_STATIC_DIR=/app/static
ENV OLLAMA_BASE_URL=http://ollama:11434
ENV OLLAMA_MODELS_DIR=/ollama-models
ENV TOKEN_VIZ_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:8091

EXPOSE 8091

HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=20s \
  CMD curl -fsS "http://127.0.0.1:${TOKEN_VIZ_PORT}/health" || exit 1

CMD ["/app/token-viz-service"]
