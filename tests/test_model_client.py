from core.model_client import DryRunModelClient, OllamaModelClient, build_model_client_from_env


def test_model_client_defaults_to_dry_run(monkeypatch) -> None:
    monkeypatch.delenv("MODEL_BACKEND", raising=False)

    client = build_model_client_from_env()

    assert isinstance(client, DryRunModelClient)


def test_model_client_can_build_ollama_backend(monkeypatch) -> None:
    monkeypatch.setenv("MODEL_BACKEND", "ollama")
    monkeypatch.setenv("OLLAMA_DEFAULT_MODEL", "qwen2.5:0.5b")
    monkeypatch.setenv("OLLAMA_MODEL_VERIFIER", "qwen2.5:1.5b")

    client = build_model_client_from_env()

    assert isinstance(client, OllamaModelClient)
    assert client.model_for_role("Planner") == "qwen2.5:0.5b"
    assert client.model_for_role("Verifier") == "qwen2.5:1.5b"
