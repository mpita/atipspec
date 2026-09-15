# Contribuindo

--8<-- "CONTRIBUTING.md"

## Documentação

O site é construído com MkDocs Material a partir de `docs/` e `mkdocs.yml`:

```bash
python -m pip install ".[docs]"
mkdocs serve          # live preview at http://127.0.0.1:8000
mkdocs build --strict # what CI runs
```

Um push para `main` faz o deploy dele no GitHub Pages através de
`.github/workflows/docs.yml`.

## Lançamentos

1. Atualize `version` em `pyproject.toml` e `__version__` em
   `atipspec/__init__.py` para o mesmo valor.
2. Faça commit, crie a tag `vX.Y.Z`, dê push na tag, e publique um GitHub
   release para ela.
3. `.github/workflows/publish.yml` executa os testes, constrói o wheel e o
   sdist, verifica que a tag corresponde à versão, e publica no PyPI com
   trusted publishing. Uma execução manual do workflow pode ter como alvo o
   TestPyPI.
