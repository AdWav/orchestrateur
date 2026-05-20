from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.services.ollama_tokenize import _resolve_gguf_blob_path


def test_resolve_gguf_blob_path_from_modelfile(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    blob = tmp_path / "models" / "blobs" / "sha256-deadbeef"
    blob.parent.mkdir(parents=True)
    blob.write_bytes(b"gguf")

    modelfile = "FROM /root/.ollama/models/blobs/sha256-deadbeef\nTEMPLATE foo"

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"modelfile": modelfile}

    monkeypatch.setattr(
        "app.services.ollama_tokenize.httpx.post",
        lambda *args, **kwargs: FakeResponse(),
    )

    resolved = _resolve_gguf_blob_path("demo", tmp_path)
    assert resolved == blob


def test_modelfile_from_regex() -> None:
    modelfile = "# comment\nFROM /root/.ollama/models/blobs/sha256-abc\n"
    match = re.search(r"^FROM\s+(\S+)\s*$", modelfile, flags=re.MULTILINE)
    assert match is not None
    assert Path(match.group(1)).name == "sha256-abc"
