# Primeiros passos

Comece com especificação e verificação locais, depois configure a aceitação
confiável. Os exemplos usam o Claude Code; a [página de clientes](../clients.md)
mostra o equivalente nos outros.

## 1. Defina o contrato

A primeira coisa a fazer em um projeto é a **fase contract**. Abra uma
sessão no projeto e diga:

```text
/atipspec-contract
```

A skill executa `atipspec contract`, que imprime o workflow e o contrato
atual. O modelo registra o que você já decidiu (digamos, Django e
PostgreSQL) como decisões, pergunta apenas o que afeta as regras, preenche
`.atipspec/contract.md` e escreve as regras que a CLI vai verificar:

```text
dependencies pyproject.toml django psycopg "pytest*"
forbid-pattern "shop/domain/**" "from shop\.infrastructure"
require-command "python -m pytest -q"
```

Verifique o repositório contra ele, aceite-o quando concordar, e faça
commit:

```bash
atipspec audit
atipspec accept contract
git add .atipspec && git commit -m "chore: architecture contract"
```

Até que o contrato seja aceito, `atipspec spec` recusa iniciar uma entrega.

## 2. Inicie uma entrega

```bash
atipspec new password-reset --title "Password reset" --capability auth --owner ana --branch
```

Isso cria `.atipspec/deliveries/password-reset/` com `spec.md`, `plan.md` e
`deferred.md`, registra o commit atual como a base da entrega, e muda para a
branch `delivery/password-reset`.

## 3. Faça o spec e aprove-o

```text
/atipspec-spec password-reset: users should be able to reset a forgotten password by email
```

A skill executa `atipspec spec password-reset`, que imprime a **fase
spec**: seu workflow, as regras e exatamente o contexto que a entrega
precisa. O modelo te entrevista em lotes curtos e escreve requisitos com
critérios de aceitação:

```markdown
### REQ-001: The user can request a reset link

Acceptance criteria:
- AC-001: A request with a registered email sends a link to that email.
- AC-002: A request with an unknown email responds like a valid one.
```

Quando o portão diz que a spec está completa, o modelo a apresenta e
espera. Este é o **ponto de parada 1**: leia-a, corrija-a, e aceite-a você
mesmo:

```bash
atipspec accept password-reset spec
```

Isso define `status: ready` e registra o que você aceitou; se alguém editar
a spec depois, o portão pergunta a você novamente. O modelo nunca executa
esse comando.

## 4. Plan, build, review

```text
/atipspec-ship password-reset
```

`atipspec ship password-reset` indica a próxima fase que a entrega pode
iniciar, e cada comando de fase recusa enquanto uma etapa obrigatória
estiver faltando. O modo ship executa as fases restantes sem pausar, exceto
onde você pediu que pausasse:

- **plan**: abordagem e tarefas, cada uma com os requisitos que cobre e os
  comandos que a comprovam. Se `approve_plan` estiver ativado, ele mostra o
  plan e espera por `atipspec accept password-reset plan`.
- **build**: tarefa por tarefa. Código, testes, `atipspec verify`, um
  commit por tarefa carregando `[password-reset:T1]`.
- **review**: `atipspec review` escreve um pacote; um revisor em um
  contexto limpo escreve `review.md` com um veredito por critério.

Acompanhe isso de outro terminal a qualquer momento:

```bash
atipspec status password-reset
```

```text
AtipSpec: shop (en)
git: branch delivery/password-reset
contract: accepted
living specs: none
- password-reset [in_progress] tasks 1/2 @ana, open 3h: Password reset
    accepted: spec accepted by ana@example.com at 2026-09-13T12:39:09Z (current)
    accepted: plan accepted by ana@example.com at 2026-09-13T13:02:41Z (current)
    next: T2 is not committed: build it, run `atipspec verify password-reset --task T2` and commit with [password-reset:T2]
```

## 5. Deliver

Um check local verde significa `checked`. Configure a
[aceitação confiável](../enterprise.md), colete as aprovações de
produto/engenharia antes da verificação de CI, obtenha a atestação de CI e
a aprovação de QA, depois execute:

```bash
atipspec check password-reset --policy /secure/company.toml
atipspec deliver password-reset --policy /secure/company.toml
```

Os requisitos são mesclados em `.atipspec/specs/auth.md`, a pasta se move
para `.atipspec/archive/`, e o modelo pede que você faça o merge da branch.
Este é o **ponto de parada 2**.

## O que você acabou de conseguir

- Uma spec que você aprovou, mantida para sempre na spec viva da capacidade
  `auth`.
- Arquivos de evidência com os comandos exatos, códigos de saída e hash da
  árvore para cada tarefa.
- Uma revisão por um contexto que nunca viu o raciocínio do autor.
- Um commit por tarefa, e um contrato que foi aplicado em cada arquivo que
  a entrega tocou.

Próximo: [como funciona](how-it-works.md), ou o [fluxo](../flow/index.md)
fase por fase.
