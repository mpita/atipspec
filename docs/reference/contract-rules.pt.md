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
branco e das aspas do shell, em pelo menos um `Verify:` de uma tarefa, sozinho
ou seguido de mais argumentos: com `require-command "python -m pytest"` conta
a linha `python -m pytest -q --junitxml .atipspec/tmp/junit.xml`, que escreve
um `Report:`. Não conta uma linha que segue o comando com um operador de
controle (`|`, `||`, `&&`, `;`, `&`), um redirecionamento (`>`, `<`, `2>&1`)
ou uma substituição de comandos (`$(...)`, crases): `python -m pytest || true`
e `python -m pytest | tail -1` passam quer os testes passem, quer não. No
Windows, onde `verify` executa a linha com `cmd.exe`, que não lê como aspas
nem as simples nem as barras invertidas, também não conta uma linha com `&`,
`|`, `<`, `>`, `^`, `%` ou aspas duplas em qualquer lugar depois do comando,
mesmo entre aspas que o sh respeitaria. Os
argumentos não são julgados: um que restringe a execução, como `-k smoke` ou
um único arquivo de testes, conta do mesmo jeito, porque distingui-lo de
`--junitxml` depende da ferramenta; o humano vê cada linha `Verify:` na
proposta. É assim que os portões de qualidade do contrato se tornam evidência
em cada entrega.

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
um novo arquivo sob `.atipspec/decisions/` faça parte do mesmo diff e a
aceitação registrada do contrato o inclua. Crie-o com
`atipspec decision <slug> --title ... --affects contract:<section>`; o
assistente apresenta `atipspec proposal contract` e, depois da sua aprovação
explícita, a registra com `atipspec accept contract --code <code>`, que define
o status da decisão. Um status definido como `accepted` à mão não conta. Com
uma política de confiança externa, a decisão precisa, em vez disso, de sua
aprovação assinada pela engenharia.
