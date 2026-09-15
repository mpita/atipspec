# Regras do contrato

`contract.md` é prosa para o modelo mais um bloco cercado que a CLI avalia:

````markdown
```rules
dependencies pyproject.toml django psycopg "pytest*"
forbid-pattern "shop/domain/**" "from shop\.infrastructure"   # DEC-002 layering
forbid-path "web/src/**/*.js"                                 # TypeScript only
require-command "python -m pytest -q"
```
````

Uma regra por linha, aspas ao estilo shell, `#` inicia um comentário que é
exibido como a razão nos relatórios.

## Regras

### `forbid-path <glob>`

Nenhum arquivo pode corresponder ao glob. `check` olha os arquivos que a
entrega alterou; `audit`, todo arquivo rastreado e não rastreado fora de
`.atipspec/`.

### `forbid-pattern <glob> <regex>`

Nenhum arquivo que corresponda ao glob pode conter uma linha que corresponda
à expressão regular (sintaxe Python). A primeira linha correspondente é
reportada com seu número. Use isso para camadas
(`"from shop\.infrastructure|^from django"` no domínio), para bibliotecas
banidas, ou para padrões que suas convenções proíbem.

### `dependencies <manifest> <name-or-glob>...`

O manifesto só pode declarar as dependências listadas. Os nomes são
comparados em minúsculas; globs como `"@types/*"` ou `"pytest*"` são
permitidos. Em `check` a regra roda quando o manifesto está entre os arquivos
que a entrega alterou; em `audit` ela sempre roda. Manifestos suportados:

| Arquivo | Lido de |
| --- | --- |
| `pyproject.toml` | `project.dependencies`, `project.optional-dependencies`, `dependency-groups`, dependências e grupos do Poetry |
| `requirements*.txt` | um requisito por linha, linhas `-r`/`-e` são ignoradas |
| `package.json` | dependencies, devDependencies, peerDependencies, optionalDependencies |
| `Cargo.toml` | dependencies, dev-dependencies, build-dependencies |
| `go.mod` | linhas e blocos `require` |

### `require-command <command>`

O plano de toda entrega deve incluir o comando, literal a menos de espaços em
branco, em pelo menos um `Verify:` de uma tarefa. É assim que os portões de
qualidade do contrato se tornam evidência em cada entrega.

## Globs

`**` atravessa diretórios, `*` e `?` não. Os padrões são ancorados ao
caminho inteiro relativo à raiz do projeto: `src/**/*.js` corresponde a
`src/c.js` e `src/a/b/c.js`; `src/*.js` corresponde só ao primeiro.

## Onde as regras se aplicam

| | `atipspec check <slug>` | `atipspec audit` |
| --- | --- | --- |
| Arquivos | alterados desde a base da entrega, mais não rastreados | todos os rastreados e não rastreados, fora de `.atipspec/` |
| `dependencies` | quando o manifesto mudou | sempre |
| `require-command` | o plano da entrega | não aplicável |
| Resultado | erros no portão da entrega | erros, saída 1 |

## Alterando o contrato

Uma entrega cujo diff toca `.atipspec/contract.md` fica vermelha a menos que
um novo arquivo sob `.atipspec/decisions/` faça parte do mesmo diff. Crie-o
com `atipspec decision <slug> --title ... --affects contract:<section>`, e
defina seu status como `accepted` quando você concordar.
