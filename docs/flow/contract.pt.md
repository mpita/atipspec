# contract

**Define e protege a arquitetura.** A primeira fase de um projeto e a que
mantém a quadragésima entrega nos mesmos trilhos da primeira.

| | |
| --- | --- |
| Papel | O guardião do contrato. Descreve a realidade antes das regras, escreve regras que a CLI pode verificar, nunca muda o contrato dentro de uma entrega de feature. |
| Quem decide | Você aceita o contrato com `atipspec accept contract`, e cada decisão ao definir seu status. |
| Produz | `contract.md`, `decisions/DEC-nnn-*.md`, as specs vivas iniciais |

## Como executar

```text
/atipspec-contract
```

O skill executa `atipspec contract`, que imprime o workflow, as regras e o
`contract.md` atual. Até você executar `atipspec accept contract`, `atipspec
spec` se recusa a começar.

## Um novo projeto

Diga o que você já decidiu: "um app web em Django com PostgreSQL e um front
em React". O modelo registra isso como decisões com suas razões, para que
nunca sejam reabertas por acidente:

```bash
atipspec decision stack --title "Django, PostgreSQL and React" --affects contract
```

Depois ele pergunta apenas o que afeta as regras: como front e back
conversam, onde vivem os contratos de API, autenticação, os comandos de
qualidade, o que é proibido. Ele preenche o `contract.md`:

```markdown
## Stack
Python 3.12, Django 5, PostgreSQL 16; React 18 with TypeScript in web/.

## Structure
shop/domain/ has no imports from shop/infrastructure/ or Django. Views are
thin; use cases live in shop/application/.

## Dependencies
New libraries need a decision. Pin exact versions.

## Quality gates
python -m pytest -q, ruff check ., npm test in web/.

## Rules

```rules
dependencies pyproject.toml django psycopg "pytest*" ruff
dependencies web/package.json react react-dom "@types/*" typescript vite
forbid-pattern "shop/domain/**" "from shop\.infrastructure|^from django"   # DEC-001 layering
forbid-path "web/src/**/*.js"                                             # TypeScript only
require-command "python -m pytest -q"
require-command "ruff check ."
```
```

e cria as primeiras specs vivas, uma por capacidade que você nomear. Rode o
audit até ficar limpo e então aceite:

```bash
atipspec audit
atipspec accept contract
```

## Um projeto existente

O modelo lê manifestos, pastas, CI e testes, e propõe um contrato que
**descreve o que existe**; as regras que ele acha que você deveria adicionar
são marcadas como propostas. Depois `atipspec audit`: cada violação é
corrigida agora, aceita por você como uma exceção (a regra é restringida), ou
descartada. Um audit vermelho nunca fica para trás.

## Alterando o contrato

O contrato só muda com uma decisão, e o portão faz isso valer: uma entrega
cujo diff toca `contract.md` sem um novo arquivo em `.atipspec/decisions/`
fica vermelha.

```bash
atipspec decision allow-httpx --title "Use httpx for outbound HTTP" --affects contract:dependencies
```

Preencha a decisão, defina `status: accepted` quando você concordar, edite o
`contract.md` na mesma entrega, rode `atipspec audit`.

!!! info "O que as regras podem e não podem verificar"
    As regras são estruturais de propósito: caminhos proibidos, padrões
    proibidos, dependências declaradas por manifesto, comandos obrigatórios.
    Elas capturam o desvio que realmente acontece em projetos longos, uma
    nova biblioteca, um cruzamento de camadas, um comando de teste pulado. O
    julgamento de design fica com o revisor, que recebe o contrato inteiro no
    pacote. Veja a
    [referência de regras](../reference/contract-rules.md).
