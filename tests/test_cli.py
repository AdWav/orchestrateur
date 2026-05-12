import json

from serve.cli import main


def _create_repo_fixture(tmp_path) -> None:
    (tmp_path / "README.md").write_text("# Demo\n\nArchitecture overview.\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    (tmp_path / ".env.example").write_text("API_TOKEN=\n", encoding="utf-8")
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "architecture.md").write_text("System architecture notes.\n", encoding="utf-8")
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_smoke.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")


def test_demo_command_runs_end_to_end(tmp_path, capsys) -> None:
    _create_repo_fixture(tmp_path)

    exit_code = main(
        [
            "demo",
            "--repo-path",
            str(tmp_path),
            "--company-name",
            "Acme Delivery",
            "--client-name",
            "Client Polaris",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["mode"] == "local"
    assert payload["business_story"]["company"]["name"] == "Acme Delivery"
    assert payload["business_story"]["client"]["name"] == "Client Polaris"
    assert payload["team"]["name"] == "Specification Team"
    assert payload["specification"]["verification_passed"] is True
    assert payload["repo_audit"]["verification_passed"] is True
    assert payload["repo_audit"]["inventory"]["root_path"] == str(tmp_path)


def test_demo_command_supports_due_diligence_story(tmp_path, capsys) -> None:
    _create_repo_fixture(tmp_path)

    exit_code = main(
        [
            "demo",
            "--repo-path",
            str(tmp_path),
            "--company-name",
            "Northbridge Capital",
            "--client-name",
            "BlueVector",
            "--scenario",
            "tech-due-diligence",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["business_story"]["scenario"] == "tech-due-diligence"
    assert payload["business_story"]["mission"]["title"] == "Comite d'investissement technique"
    assert payload["business_story"]["role_projection"][0]["business_role"] == "Partner investissement tech"
    assert payload["repo_audit"]["verification_passed"] is True


def test_specification_command_accepts_context_pairs(capsys) -> None:
    exit_code = main(
        [
            "specification",
            "--objective",
            "Produire un plan d'execution local",
            "--context",
            "repo=orchestrateur",
            "--context",
            "mode=local",
            "--constraint",
            "Rester en local",
            "--success-criterion",
            "Le plan doit etre actionnable.",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["request"]["context"]["repo"] == "orchestrateur"
    assert payload["request"]["context"]["mode"] == "local"
    assert payload["verification_passed"] is True


def test_team_command_can_query_remote_api(monkeypatch, capsys) -> None:
    calls: list[tuple[str, float]] = []

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "name": "Specification Team",
                "purpose": "demo",
                "use_case_ids": ["specification-factory"],
                "roles": [],
                "handoff_contracts": [],
                "guardrails": [],
            }

    def fake_get(url: str, timeout: float):
        calls.append((url, timeout))
        return FakeResponse()

    monkeypatch.setattr("serve.cli.httpx.get", fake_get)

    exit_code = main(["team", "--api-url", "http://localhost:8000"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert calls == [("http://localhost:8000/team", 30.0)]
    assert payload["name"] == "Specification Team"
