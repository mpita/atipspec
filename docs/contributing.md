# Contributing

--8<-- "CONTRIBUTING.md"

## Documentation

The site is built with MkDocs Material from `docs/` and `mkdocs.yml`:

```bash
python -m pip install ".[docs]"
mkdocs serve          # live preview at http://127.0.0.1:8000
mkdocs build --strict # what CI runs
```

Pushing to `main` deploys it to GitHub Pages through
`.github/workflows/docs.yml`.

## Releasing

1. Bump `version` in `pyproject.toml` and `__version__` in
   `atipspec/__init__.py` to the same value.
2. Commit, tag `vX.Y.Z`, push the tag, and publish a GitHub release for it.
3. `.github/workflows/publish.yml` runs the tests, builds the wheel and the
   sdist, checks that the tag matches the version, and publishes to PyPI with
   trusted publishing. A manual run of the workflow can target TestPyPI.
