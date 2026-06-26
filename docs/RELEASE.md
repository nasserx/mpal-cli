# Release Checklist

This checklist covers local release-readiness verification only.

## Local Checks

Run these commands from the repository root:

```console
python -m pytest
python -m ruff check .
python -m ruff format --check .
git diff --check
python -m build
```

If `twine` is installed, also run:

```console
python -m twine check dist/*
```

After verifying the build, remove generated artifacts:

```console
Remove-Item -Recurse -Force build, dist, src\mpal_cli.egg-info
```

Publishing to TestPyPI or PyPI is a separate manual step. It is not part of
this checklist and is not performed by release-readiness cleanup tasks.
