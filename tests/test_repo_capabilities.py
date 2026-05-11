from core.contracts import AuditScope, RepoReadLimits, RepoTarget
from core.memory import SharedMemory
from core.repo_capabilities import RepoCapabilities


def test_repo_capabilities_collect_inventory_and_evidence(tmp_path) -> None:
    (tmp_path / "README.md").write_text("# Demo\n\nService overview.\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")

    memory = SharedMemory()
    capabilities = RepoCapabilities(
        RepoTarget(root_path=str(tmp_path)),
        AuditScope(
            analysis_axes=["docs", "tests", "dependencies"],
            read_limits=RepoReadLimits(max_files=10, max_bytes_per_file=2000, max_matches=10),
        ),
        memory=memory,
    )

    inventory, evidence_refs, coverage_map = capabilities.collect_evidence(
        ["docs", "tests", "dependencies"],
        ["demo"],
    )

    assert inventory.total_files_scanned == 3
    assert "README.md" in inventory.important_files
    assert evidence_refs
    assert coverage_map["docs"]
    assert any(event["type"] == "tool" for event in memory.snapshot()["events"])
