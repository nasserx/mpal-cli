"""Project identity and packaging regressions."""

import tomllib
from pathlib import Path

from mpal import __version__

ROOT = Path(__file__).resolve().parents[1]


def test_project_metadata_uses_only_mpal_entry_point() -> None:
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = metadata["project"]
    scripts = project["scripts"]
    old_name = "fund" + "log"

    assert project["name"] == "mpal-cli"
    assert project["version"] == __version__ == "0.5.2"
    assert project["description"] == (
        "Multi-Portfolio Asset Ledger (mpal) - A minimal CLI tool for manual "
        "asset tracking and capital management."
    )
    assert project["readme"] == "README.md"
    assert project["requires-python"] == ">=3.11"
    assert project["license"] == "MIT"
    assert scripts == {"mpal": "mpal.cli:app"}
    assert old_name not in scripts


def test_only_mpal_import_package_exists() -> None:
    old_name = "fund" + "log"

    assert (ROOT / "src" / "mpal" / "__init__.py").is_file()
    assert not (ROOT / "src" / old_name).exists()
