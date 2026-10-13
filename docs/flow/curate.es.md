# curate

**Mantén el contexto pequeño a medida que crece el proyecto.** El coste de
una petición debe depender de la entrega, no de la edad del proyecto.

| | |
| --- | --- |
| Rol | El editor de la memoria del proyecto. Elimina, fusiona y acorta; nunca añade historia. |
| Quién decide | El modelo, dentro de los topes. |
| Produce | `overview.md`, `glossary.md`, propuestas de división para las specs vivas |

## Cuándo

Después de una entrega, cuando `atipspec audit` o `atipspec context` informan
de un tamaño por encima de su tope, o cuando tú lo pidas.

## Cómo ejecutarla

```text
/atipspec-curate
```

El skill ejecuta el CLI:

```bash
atipspec curate
```

```text
curate  [done]
  info    overview.md index regenerated
  info    overview.md: 58 lines (cap 150)
  warning glossary.md: 312 lines (cap 300)
  info    contract.md: 96 lines (cap 400)

Phase curate
...
```

`curate` regenera el bloque de índice de `overview.md` (capacidades con su
recuento de requisitos, decisiones aceptadas, iniciativas con progreso,
entregas en curso), informa de cada tamaño contra su tope e imprime el
workflow. Luego el modelo:

1. Reescribe la prosa de `overview.md` por encima del índice en menos de 60
   líneas: qué es el producto, para quién, el mapa del repositorio, cómo
   ejecutarlo y probarlo. Nada que viva en una spec o una decisión.
2. Reescribe `glossary.md`: una línea por término canónico con la spec o la
   decisión que lo fijó; fusiona sinónimos; elimina términos que ninguna spec
   usa.
3. Propone dividir por capacidad una spec viva que está por encima de su
   tope, hecho a través de una entrega con `[remove]` y una capacidad nueva,
   nunca editando la historia a mano.
4. Marca las decisiones superadas; nunca borra ninguna.
5. Deja `atipspec audit` limpio.

## Topes

| Documento | Tope |
| --- | --- |
| `overview.md` | 150 líneas |
| `glossary.md` | 300 líneas |
| `contract.md` | 400 líneas |
| cada spec viva | 400 líneas |

`context_budget` en `config.yaml` (por defecto 800 líneas) es contra lo que
`atipspec context` mide el material de una entrega.
