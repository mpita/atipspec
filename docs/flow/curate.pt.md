# curate

**Mantenha o contexto pequeno à medida que o projeto cresce.** O custo de uma
requisição deve depender da entrega, não da idade do projeto.

| | |
| --- | --- |
| Papel | O editor da memória do projeto. Remove, mescla e resume; nunca adiciona histórico. |
| Quem decide | O modelo, dentro dos limites. |
| Produz | `overview.md`, `glossary.md`, propostas de divisão para specs vivas |

## Quando

Depois de uma entrega, quando `atipspec audit` ou `atipspec context` relatam
um tamanho acima do seu limite, ou sempre que você pedir.

## Como executar

```text
/atipspec-curate
```

O skill executa a CLI:

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

`curate` regenera o bloco de índice do `overview.md` (capacidades com suas
contagens de requisitos, decisões aceitas, iniciativas com progresso, entregas
em andamento), relata cada tamanho contra seu limite e imprime o workflow.
Depois o modelo:

1. Reescreve a prosa do `overview.md` acima do índice em menos de 60 linhas:
   o que o produto é, para quem, o mapa do repositório, como rodar e testar
   ele. Nada que viva em uma spec ou em uma decisão.
2. Reescreve o `glossary.md`: uma linha por termo canônico com a spec ou
   decisão que o fixou; mescla sinônimos; remove termos que nenhuma spec usa.
3. Propõe dividir uma spec viva que está acima do seu limite por capacidade,
   feito por meio de uma entrega com `[remove]` e uma nova capacidade, nunca
   editando o histórico manualmente.
4. Marca decisões substituídas; nunca apaga uma.
5. Deixa o `atipspec audit` limpo.

## Limites

| Documento | Limite |
| --- | --- |
| `overview.md` | 150 linhas |
| `glossary.md` | 300 linhas |
| `contract.md` | 400 linhas |
| cada spec viva | 400 linhas |

`context_budget` em `config.yaml` (padrão 800 linhas) é aquilo contra o que
`atipspec context` mede o material de uma entrega.
