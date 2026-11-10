import pytest

from artic.tools import Repo, SuiteResult, ToolError


def make_repo(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "mod.py").write_text("x = 1\n", encoding="utf-8")
    return Repo(tmp_path)


def test_read_inside_repo(tmp_path):
    assert "x = 1" in make_repo(tmp_path).read("pkg/mod.py")


def test_read_outside_repo_is_denied(tmp_path):
    with pytest.raises(ToolError):
        make_repo(tmp_path).read("../outside.txt")


def test_build_and_env_paths_are_denied(tmp_path):
    repo = make_repo(tmp_path)
    with pytest.raises(ToolError):
        repo.read("core/build/artic_core.cpp")
    with pytest.raises(ToolError):
        repo.read(".env")


def test_diff_shows_change(tmp_path):
    diff = make_repo(tmp_path).propose("pkg/mod.py", "x = 2\n").diff()
    assert "-x = 1" in diff and "+x = 2" in diff


def test_write_requires_approval(tmp_path):
    repo = make_repo(tmp_path)
    result = repo.propose("pkg/mod.py", "x = 2\n").apply(approve=lambda c: False, run_tests=False)

    assert "rejected" in result
    assert (tmp_path / "pkg" / "mod.py").read_text(encoding="utf-8") == "x = 1\n"


def test_write_applies_when_tests_pass(tmp_path):
    repo = make_repo(tmp_path)
    repo.run_tests = lambda: SuiteResult(True, "1 passed")

    result = repo.propose("pkg/mod.py", "x = 2\n").apply(approve=lambda c: True)

    assert "tests passed" in result
    assert (tmp_path / "pkg" / "mod.py").read_text(encoding="utf-8") == "x = 2\n"


def test_failed_tests_roll_back_existing_file(tmp_path):
    repo = make_repo(tmp_path)
    repo.run_tests = lambda: SuiteResult(False, "boom")

    result = repo.propose("pkg/mod.py", "x = 2\n").apply(approve=lambda c: True)

    assert "rolled back" in result
    assert (tmp_path / "pkg" / "mod.py").read_text(encoding="utf-8") == "x = 1\n"


def test_failed_tests_remove_new_file(tmp_path):
    repo = make_repo(tmp_path)
    repo.run_tests = lambda: SuiteResult(False, "boom")

    result = repo.propose("pkg/new.py", "y = 1\n").apply(approve=lambda c: True)

    assert "rolled back" in result
    assert not (tmp_path / "pkg" / "new.py").exists()
