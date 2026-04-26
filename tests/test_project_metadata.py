import tomllib
from pathlib import Path


def test_project_declares_package_shape_and_console_entry_point():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["name"] == "lid-vocab"
    assert pyproject["project"]["scripts"]["lid-vocab"] == "leben_vocab.cli:main"
    assert pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"] == [
        "src/leben_vocab"
    ]
    assert "pytest>=8" in pyproject["project"]["optional-dependencies"]["dev"]


def test_gitignore_excludes_local_environment_and_build_artifacts():
    gitignore = Path(".gitignore").read_text(encoding="utf-8").splitlines()

    assert ".env" in gitignore
    assert ".venv" in gitignore
    assert "build/" in gitignore
    assert "dist/" in gitignore
    assert ".pytest_cache/" in gitignore
