# Release Checklist

This checklist covers local release-readiness verification only.

## Local Checks

Install release tooling in your local environment:

```console
python -m pip install -e ".[release]"
```

Run these commands from the repository root:

```console
python -m pytest
python -m ruff check .
python -m ruff format --check .
git diff --check
python -m build
python -m twine check dist/*
```

Run the manual Windows QA workflow to inspect real CLI output and table
formatting:

```console
.\scripts\manual_qa.ps1
```

To keep the isolated QA data directory for debugging:

```console
.\scripts\manual_qa.ps1 -KeepData
```

After verifying the build, remove generated artifacts:

```console
Remove-Item -Recurse -Force build, dist, src\mpal_cli.egg-info
```

Publishing to TestPyPI or PyPI is a separate manual step. It is not part of
this checklist and is not performed by release-readiness cleanup tasks.
