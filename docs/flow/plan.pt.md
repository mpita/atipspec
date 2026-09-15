# plan

**De uma spec pronta a tarefas que o portão pode comprovar.** A fase em que
a conformidade com a arquitetura é decidida.

| | |
| --- | --- |
| Papel | Quem vai manter isso daqui a um ano. Prefere a forma mais simples dentro do contrato, reaproveita o que já existe, conta a você as escolhas com consequências antes de fazê-las. |
| Quem decide | Você, com `atipspec accept <slug> plan`, quando `approve_plan: true` em `config.yaml` (o padrão). |
| Produz | `plan.md`: abordagem e tarefas |

## Como executar

```text
/atipspec-plan password-reset
```

A skill executa `atipspec plan password-reset`, que recusa enquanto a spec
não está pronta e, caso contrário, imprime o workflow, as regras e o
contexto.

## O que o modelo faz

1. Lê o contexto que o comando imprimiu, e as áreas de código envolvidas.
2. Verifica o contrato. Se a spec precisa de algo que o contrato proíbe, ele
   para: isso exige uma [decisão](contract.md#alterando-o-contrato), nunca
   uma solução alternativa.
3. Escreve `plan.md`:

```markdown
---
scope: ["shop/auth/**", "tests/auth/**"]
---

# Plan: Password reset

## Approach

A `reset` module under `shop/auth/` with `request()` and `consume()`,
following the contract's structure (domain must not import infrastructure,
DEC-002). Tokens stored in the existing `auth_token` table.

## Tasks

### T1: Request a reset link

Covers: REQ-001
Verify:
- `python -m pytest -q tests/auth/test_reset.py`

### T2: Expire links after 30 minutes

Covers: REQ-002
Verify:
- `python -m pytest -q tests/auth/test_reset.py`
- `python -m pytest -q`
```

4. `atipspec check password-reset` até não haver mais erros de plano.
5. Mostra o plano a você se `approve_plan` estiver ativo e pede que você
   execute `atipspec accept password-reset plan`; `atipspec build` recusa
   até lá. Uma tarefa adicionada durante o build muda o plano, então você o
   aceita de novo.

## O que `check` exige de um plano

- Todo requisito ativo é coberto por pelo menos uma tarefa (`Covers:`), e
  todo critério é listado uma vez em `Tests:` ou `Manual:`, seguindo sua
  marca `[manual]` na spec; até lá, `atipspec build` recusa.
- Todo `require-command` do contrato aparece no `Verify:` de pelo menos uma
  tarefa.
- Os comandos são comandos reais do projeto. `verify` vai executá-los a
  partir da raiz do projeto pelo shell.
- `Verify: none` é permitido quando a única prova é observação, com uma
  nota do que o revisor deve observar.
- `scope` nomeia os arquivos que as tarefas vão mudar, com a sintaxe de glob
  das [regras do contrato](../reference/contract-rules.md#globs): `**`
  atravessa diretórios, `*` não. Um arquivo tocado fora dele, uma exclusão
  inclusive, é um aviso em `check` e um erro com `strict_scope: true`; o
  pacote de review os lista sempre que é escrito. Trabalho imprevisto amplia
  o `scope` na mesma edição que adiciona sua tarefa.

## Tarefas, não histórias

Uma tarefa é uma mudança coerente que pode ser commitada sozinha e deixa o
projeto funcionando. As tarefas rodam em sequência dentro de uma entrega, e
acima de `max_tasks` o plano é grande demais para um dia de trabalho:
`check` avisa e o modelo propõe uma iniciativa. Trabalho que você quer
rodar em paralelo entre pessoas pertence a entregas separadas; veja
[equipes e escala](../teams.md).
