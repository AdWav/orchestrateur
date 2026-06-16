# token-viz-service (C++ / llama.cpp)

Service HTTP C++ qui tokenise du texte avec le **vocabulaire GGUF** du modèle Ollama (via llama.cpp), puis affiche les tokens Input / Output.

## Endpoints

| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/health` | Santé du service |
| `GET` | `/v1/tokenize/capabilities` | Source `llama_cpp` |
| `POST` | `/v1/tokenize` | Corps `{ "model", "text" }` |
| `POST` | `/v1/tokenize/split` | Corps `{ "model", "input", "output" }` |
| `POST` | `/v1/decode/tree` | Génération Ollama + arbre top-K logprobs (`prompt`, `top_logprobs`, `num_predict`) |
| `POST` | `/v1/embeddings` | Vecteurs `token_embd` réels depuis le GGUF (`text` ou `token_index`) |
| `GET` | `/` | UI tokenisation BPE (static) |
| `GET` | `/explainer.html` | **Transformer Explainer** — parcours pédagogique 4 étapes |
| `GET` | `/tree.html` | UI arbre de décodage (2D) |
| `GET` | `/v1/model/inspect?model=…` | Carte GGUF : tenseurs, couches, total paramètres |
| `GET` | `/cloud3d.html` | UI nuage 3D (Three.js, particules + probabilités) |
| `GET` | `/model3d.html` | Nuage volumique + inférence (prompt → impulsion couches → tokens émis) |

## Variables d'environnement

| Variable | Défaut | Description |
|----------|--------|-------------|
| `TOKEN_VIZ_BIND_HOST` | `127.0.0.1` | Interface d'écoute |
| `TOKEN_VIZ_PORT` | `8091` | Port HTTP |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | API Ollama (`/api/show`) |
| `OLLAMA_MODELS_DIR` | *(requis)* | Racine données Ollama (`models/blobs/`) |
| `TOKEN_VIZ_STATIC_DIR` | `static` | Dossier UI |
| `TOKEN_VIZ_CORS_ORIGINS` | localhost | Origines CORS |

## Docker (recommandé)

```bash
docker compose up --build token-viz-service
```

- UI : http://localhost:8091
- **Explainer** : http://localhost:8091/explainer.html
- API : http://localhost:8091/v1/tokenize/capabilities

## Build local (Linux / WSL)

Prérequis : `cmake`, `g++`, `libcurl4-openssl-dev`, clone [llama.cpp](https://github.com/ggml-org/llama.cpp).

```bash
git clone --depth 1 https://github.com/ggml-org/llama.cpp.git /tmp/llama.cpp
mkdir -p token-viz-service/third_party/nlohmann
curl -fsSL -o token-viz-service/third_party/httplib.h \
  https://raw.githubusercontent.com/yhirose/cpp-httplib/v0.18.3/httplib.h
curl -fsSL -o token-viz-service/third_party/nlohmann/json.hpp \
  https://raw.githubusercontent.com/nlohmann/json/v3.11.3/single_include/nlohmann/json.hpp

cmake -S token-viz-service -B token-viz-service/build \
  -DLLAMA_CPP_DIR=/tmp/llama.cpp \
  -DCMAKE_BUILD_TYPE=Release
cmake --build token-viz-service/build -j

export OLLAMA_MODELS_DIR="$HOME/.ollama"
export OLLAMA_BASE_URL="http://127.0.0.1:11434"
./token-viz-service/build/token-viz-service
```

## Exemple curl

```bash
curl -s http://localhost:8091/v1/tokenize/capabilities

curl -s -X POST http://localhost:8091/v1/tokenize/split \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5-coder:1.5b","input":"Bonjour","output":"Salut !"}'

curl -s -X POST http://localhost:8091/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5-coder:1.5b","text":"Bonjour"}'
```
