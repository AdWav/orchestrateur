from __future__ import annotations

import os
import re
import threading
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import httpx

from app.config.settings import ollama_base_url
from app.services import ollama_ops

_TOKENIZE_BODY_KEYS = ("content", "prompt", "input", "text")
_VOCAB_CACHE_LOCK = threading.Lock()
_VOCAB_BY_MODEL: dict[str, Any] = {}


@dataclass(frozen=True, slots=True)
class ModelTokenPiece:
    id: int
    text: str


@dataclass(frozen=True, slots=True)
class ModelTokenizeResult:
    model: str
    source: Literal["ollama", "llama_cpp"]
    tokens: list[ModelTokenPiece]


class ModelTokenizeUnavailable(RuntimeError):
    """Aucune voie de tokenisation alignee sur le modele."""


def tokenize_capabilities() -> dict[str, bool | str]:
    ollama_api = _ollama_tokenize_api_available()
    llama_cpp = _llama_cpp_available() and _ollama_models_dir() is not None
    if ollama_api:
        source = "ollama"
    elif llama_cpp:
        source = "llama_cpp"
    else:
        source = "unavailable"
    return {
        "ollama_api": ollama_api,
        "llama_cpp": llama_cpp,
        "source": source,
    }


def tokenize_model_text(model: str, text: str) -> ModelTokenizeResult:
    content = text
    if not content:
        raise ValueError("Le texte a tokeniser ne peut pas etre vide.")

    ollama_ops.validate_models_installed({model})

    if _ollama_tokenize_api_available():
        return _tokenize_via_ollama_api(model, content)

    if _llama_cpp_available():
        models_dir = _ollama_models_dir()
        if models_dir is not None:
            return _tokenize_via_llama_cpp(model, content, models_dir)

    raise ModelTokenizeUnavailable(
        "Tokenisation BPE indisponible : mettre a jour Ollama (>= /api/tokenize) "
        "ou monter le volume Ollama sur le backend (OLLAMA_MODELS_DIR) avec llama-cpp-python."
    )


def _ollama_models_dir() -> Path | None:
    raw = os.getenv("OLLAMA_MODELS_DIR", "").strip()
    if not raw:
        return None
    path = Path(raw)
    blobs = path / "models" / "blobs"
    return path if blobs.is_dir() else None


def _llama_cpp_available() -> bool:
    try:
        import llama_cpp  # noqa: F401

        return True
    except ImportError:
        return False


@lru_cache(maxsize=1)
def _ollama_tokenize_api_available() -> bool:
    base = ollama_base_url().rstrip("/")
    try:
        response = httpx.post(
            f"{base}/api/tokenize",
            json={"model": "probe", "content": "."},
            timeout=3.0,
        )
    except httpx.HTTPError:
        return False
    return response.status_code != 404


def _tokenize_via_ollama_api(model: str, content: str) -> ModelTokenizeResult:
    base = ollama_base_url().rstrip("/")
    last_error: Exception | None = None
    for key in _TOKENIZE_BODY_KEYS:
        try:
            response = httpx.post(
                f"{base}/api/tokenize",
                json={"model": model, key: content},
                timeout=float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120")),
            )
            response.raise_for_status()
            payload = response.json()
            tokens = _pieces_from_ollama_payload(model, payload)
            if tokens:
                return ModelTokenizeResult(model=model, source="ollama", tokens=tokens)
        except Exception as exc:
            last_error = exc
            continue
    detail = str(last_error) if last_error else "reponse vide"
    raise RuntimeError(f"Ollama /api/tokenize a echoue : {detail}") from last_error


def _pieces_from_ollama_payload(model: str, payload: dict[str, Any]) -> list[ModelTokenPiece]:
    raw_tokens = payload.get("tokens")
    if not isinstance(raw_tokens, list) or not raw_tokens:
        return []

    pieces: list[ModelTokenPiece] = []
    if all(isinstance(item, int) for item in raw_tokens):
        pieces = _detokenize_ids_via_ollama(model, raw_tokens)
        if pieces:
            return pieces

    for item in raw_tokens:
        if isinstance(item, int):
            pieces.append(ModelTokenPiece(id=item, text=""))
        elif isinstance(item, dict):
            token_id = item.get("id", item.get("token"))
            text = item.get("text") or item.get("piece") or item.get("content") or ""
            if isinstance(token_id, int):
                pieces.append(
                    ModelTokenPiece(
                        id=token_id,
                        text=text if isinstance(text, str) else "",
                    )
                )
        elif isinstance(item, str):
            pieces.append(ModelTokenPiece(id=-1, text=item))
    if pieces and any(piece.id >= 0 for piece in pieces):
        return _fill_missing_text_via_detokenize(model, pieces)
    return [piece for piece in pieces if piece.text]


def _detokenize_ids_via_ollama(model: str, token_ids: list[int]) -> list[ModelTokenPiece]:
    if not model or not token_ids:
        return []
    base = ollama_base_url().rstrip("/")
    try:
        response = httpx.post(
            f"{base}/api/detokenize",
            json={"model": model, "tokens": token_ids},
            timeout=float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120")),
        )
        if response.status_code == 404:
            return []
        response.raise_for_status()
    except httpx.HTTPError:
        return []

    payload = response.json()
    content = payload.get("content") or payload.get("response") or ""
    if not isinstance(content, str) or not content:
        return [ModelTokenPiece(id=token_id, text="") for token_id in token_ids]

    # Decoupe uniforme si l'API ne renvoie pas les pieces individuellement.
    if len(token_ids) == 1:
        return [ModelTokenPiece(id=token_ids[0], text=content)]
    return [ModelTokenPiece(id=token_id, text="") for token_id in token_ids]


def _fill_missing_text_via_detokenize(
    model: str,
    pieces: list[ModelTokenPiece],
) -> list[ModelTokenPiece]:
    if not model:
        return pieces
    filled: list[ModelTokenPiece] = []
    for piece in pieces:
        if piece.text:
            filled.append(piece)
            continue
        single = _detokenize_ids_via_ollama(model, [piece.id])
        text = single[0].text if single else ""
        filled.append(ModelTokenPiece(id=piece.id, text=text))
    return filled


def _resolve_gguf_blob_path(model: str, models_dir: Path) -> Path:
    base = ollama_base_url().rstrip("/")
    response = httpx.post(
        f"{base}/api/show",
        json={"name": model},
        timeout=30.0,
    )
    response.raise_for_status()
    payload = response.json()
    modelfile = payload.get("modelfile") if isinstance(payload, dict) else None
    if not isinstance(modelfile, str):
        raise RuntimeError(f"Impossible de resoudre le GGUF pour '{model}'.")

    match = re.search(r"^FROM\s+(\S+)\s*$", modelfile, flags=re.MULTILINE)
    if not match:
        raise RuntimeError(f"Modelfile sans entree FROM pour '{model}'.")

    from_path = Path(match.group(1))
    blob_name = from_path.name
    blob_path = models_dir / "models" / "blobs" / blob_name
    if not blob_path.is_file():
        raise RuntimeError(
            f"GGUF introuvable pour '{model}' : {blob_path}. "
            "Verifier le montage OLLAMA_MODELS_DIR sur le backend."
        )
    return blob_path


def _tokenize_via_llama_cpp(
    model: str,
    content: str,
    models_dir: Path,
) -> ModelTokenizeResult:
    from llama_cpp import Llama

    blob_path = _resolve_gguf_blob_path(model, models_dir)
    cache_key = str(blob_path)
    with _VOCAB_CACHE_LOCK:
        llm = _VOCAB_BY_MODEL.get(cache_key)
        if llm is None:
            llm = Llama(model_path=str(blob_path), vocab_only=True, verbose=False)
            _VOCAB_BY_MODEL[cache_key] = llm

    encoded = content.encode("utf-8")
    token_ids: list[int] = llm.tokenize(encoded, add_bos=False, special=False)
    pieces: list[ModelTokenPiece] = []
    for token_id in token_ids:
        piece_bytes = llm.detokenize([token_id])
        piece_text = piece_bytes.decode("utf-8", errors="replace")
        pieces.append(ModelTokenPiece(id=token_id, text=piece_text))
    return ModelTokenizeResult(model=model, source="llama_cpp", tokens=pieces)
