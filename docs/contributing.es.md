# Contribuir

--8<-- "CONTRIBUTING.md"

## Documentación

El sitio está construido con MkDocs Material a partir de `docs/` y `mkdocs.yml`:

```bash
python -m pip install ".[docs]"
mkdocs serve          # live preview at http://127.0.0.1:8000
mkdocs build --strict # what CI runs
```

Hacer push a `main` lo despliega en GitHub Pages mediante
`.github/workflows/docs.yml`.

## Publicar una versión

1. Sube `version` en `pyproject.toml` y `__version__` en
   `atipspec/__init__.py` al mismo valor.
2. Haz commit, etiqueta con `vX.Y.Z`, sube la etiqueta y publica una GitHub
   release para ella.
3. `.github/workflows/publish.yml` ejecuta los tests, construye el wheel y el
   sdist, comprueba que la etiqueta coincide con la versión, y publica en PyPI
   con trusted publishing. Una ejecución manual del workflow puede apuntar a
   TestPyPI.
