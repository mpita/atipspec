# plan

**Dos cenários à abordagem, às tarefas e aos testes que o portão pode
comprovar.** A fase em que a conformidade com a arquitetura é decidida.

| | |
| --- | --- |
| Papel | O designer e o testador: quem vai manter isso daqui a um ano. Prefere a forma mais simples dentro do contrato, reaproveita o que já existe, conta a você as escolhas com consequências antes de fazê-las e escolhe os testes pelo risco. |
| Quem decide | Você, como parte da proposta: cenários, abordagem e testes são aprovados juntos (**ponto de parada 1**). Uma [entrega antiga](../reference/legacy.md#aprovacoes) aprova seu plano à parte quando `approve_plan: true`. |
| Produz | `plan.md`: escopo, abordagem, tarefas e a verificação final |

## Como executar

```text
/atipspec-plan password-reset
```

A skill executa `atipspec plan password-reset`. Uma entrega guiada pode
planejar antes da sua aprovação, assim que seus cenários estão completos sem
um achado bloqueante, sua intenção está declarada, suas seções de fora do
escopo e de qualidade estão decididas e nenhuma pergunta está em aberto; o
comando recusa com a primeira coisa que faltar e, caso contrário, imprime o
workflow, as regras e o contexto.

## O que o modelo faz

1. Lê o contexto que o comando imprimiu, e as áreas de código envolvidas.
2. Verifica o contrato. Se os cenários precisam de algo que o contrato
   proíbe, ele para: isso exige uma [decisão](contract.md#alterando-o-contrato),
   nunca uma solução alternativa.
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

    Covers: REQ-AUTH-7KQ2M-001
    Tests: AC-AUTH-7KQ2M-001, AC-AUTH-7KQ2M-002

    ### T2: Expire links after 30 minutes

    Covers: REQ-AUTH-7KQ2M-002
    Tests: AC-AUTH-7KQ2M-003

    ### T3: Reset requests under load

    Covers: REQ-AUTH-7KQ2M-003
    Tests: AC-AUTH-7KQ2M-004

    ## Final verification

    Report: .atipspec/tmp/junit.xml
    Proof:
    - AC-AUTH-7KQ2M-001: tests/auth/test_reset.py::test_registered_email_sends_link
    - AC-AUTH-7KQ2M-002: tests/auth/test_reset.py::test_unknown_email_same_answer
    - AC-AUTH-7KQ2M-003: tests/auth/test_reset.py::test_link_expires_after_30_minutes
    - AC-AUTH-7KQ2M-004: tests/auth/test_load.py::test_p95_below_300_ms
    Verify:
    - `python -m pytest -q --junitxml .atipspec/tmp/junit.xml`
    ```

4. `atipspec check password-reset` até não haver mais erros de plano.
5. Apresenta o plano com os cenários em `atipspec proposal password-reset` e
   pede sua aprovação na conversa; o assistente a registra com
   `atipspec accept password-reset proposal --code <code>`, e
   `atipspec build` recusa até lá. A aprovação vincula o escopo, a abordagem
   e a verificação final do plano. Dividir ou adicionar uma tarefa dentro
   deles não exige nova aprovação, já que a verificação final cobre todas as
   tarefas, embora `check` continue verificando a cobertura e o escopo; um
   escopo mais amplo, outra abordagem ou uma verificação final alterada é
   apresentado a você de novo.

## O que `check` exige de um plano

- Todo requisito ativo é coberto por pelo menos uma tarefa (`Covers:`), e
  todo critério é listado uma vez em `Tests:` ou `Manual:`, seguindo sua
  marca `[manual]` na spec; até lá, `atipspec build` recusa.
- Todo `require-command` do contrato aparece nos comandos de
  `## Final verification` ou, em um plano sem ela, no `Verify:` de pelo
  menos uma tarefa.
- Os comandos são comandos reais do projeto. `verify` os executa a partir
  da raiz do projeto pelo shell: a verificação final uma única vez para o
  candidato terminado; o `Verify:` próprio de uma tarefa é uma verificação
  de desenvolvimento.
- Uma tarefa só com critérios `Manual:` pode dizer `Verify: none`, com uma
  nota do que o revisor deve observar.
- Um `Report:` nomeia um caminho que o git ignora, como
  `.atipspec/tmp/junit.xml`, que os comandos de Verify escrevem. Com
  `require_proof: true` ou `risk: high`, todo critério em `Tests:` tem uma
  entrada em `Proof:` que nomeia seu teste, e sua verificação tem um
  `Report:`; `proposal` mostra essa exigência ao lado da verificação dos
  critérios (veja [build](build.md)). Com `risk: low`, um critério em
  `Tests:` cujo teste nomeado em `Proof:` passou não precisa de veredito do
  revisor (veja [risco](spec.md#risco)).
- `scope` nomeia os arquivos que as tarefas vão mudar, com a sintaxe de glob
  das [regras do contrato](../reference/contract-rules.md#globs): `**`
  atravessa diretórios, `*` não. Com `strict_scope: true`, o padrão, ou
  `risk: high`, um plano sem `scope`, ou com globs que juntos correspondem a
  todos os caminhos (`**`, `**/*`, `*` com `*/**`), é um erro que bloqueia a
  aprovação, para que você veja o escopo antes de aprovar. Um arquivo tocado
  fora dele, uma exclusão inclusive, é um erro (um aviso com
  `strict_scope: false` e um risco diferente de `high`); o pacote de review
  os lista sempre que é escrito. As skills e as regras de permissão que o
  AtipSpec instala não contam enquanto contêm apenas o conteúdo dele;
  remover uma dessas regras conta. Trabalho imprevisto amplia o `scope` na
  mesma edição que adiciona sua tarefa, e um escopo mais amplo muda o que
  você aprovou, então é apresentado a você de novo.

## Tarefas, não histórias

Uma tarefa é uma mudança coerente que deixa o projeto funcionando,
registrada com `task-done` quando está implementada. As tarefas rodam em
sequência dentro de uma entrega, e acima de `max_tasks` o plano é grande
demais para um dia de trabalho: `check` avisa e o modelo propõe uma
iniciativa. Trabalho que você quer rodar em paralelo entre pessoas pertence a
entregas separadas; veja [equipes e escala](../teams.md).
