from core.model_client import DryRunModelClient, OllamaModelClient, build_model_client_from_env
from core.runtime_ollama_settings import RuntimeOllamaSettings


def test_model_client_defaults_to_dry_run(monkeypatch) -> None:
    monkeypatch.delenv("MODEL_BACKEND", raising=False)

    rt = RuntimeOllamaSettings.bootstrap_from_environment()

    client = build_model_client_from_env(rt)

    assert isinstance(client, DryRunModelClient)


def test_model_client_can_build_ollama_backend(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("MODEL_BACKEND", "ollama")
    monkeypatch.setenv("OLLAMA_DEFAULT_MODEL", "qwen2.5:0.5b")

    monkeypatch.setenv("OLLAMA_MODEL_VERIFY", "qwen2.5:1.5b")

    rt = RuntimeOllamaSettings.bootstrap_from_environment(persistence_path=tmp_path / "ollama-models.json")

    client = build_model_client_from_env(rt)

    assert isinstance(client, OllamaModelClient)
    assert client.model_for_role("plan") == "qwen2.5:0.5b"
    assert client.model_for_role("verify") == "qwen2.5:1.5b"
