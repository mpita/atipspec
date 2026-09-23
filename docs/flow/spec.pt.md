# spec

Estes exemplos mostram a sequência legada de spec e plan. Em entregas guiadas,
revise comportamento, abordagem e testes juntos e aprove uma vez na conversa; o
agente registra `accept <slug> proposal`. O agente pode executar todos os comandos
de aprovação local após sua confirmação explícita.

**Da intenção a uma especificação que o revisor pode verificar.** A fase em
que você decide o que será construído.

| | |
| --- | --- |
| Papel | O especificador. Se importa com o resultado observável, não com a solução. Pergunta em lotes curtos, propõe padrões, nunca aceita "funciona bem" como critério. |
| Quem decide | Você, executando `atipspec accept <slug> spec`. **Ponto de parada 1.** |
| Produz | `spec.md` com requisitos e critérios de aceitação; sua aceitação define `status: ready` |

## Como executar

```text
/atipspec-spec password-reset: users should be able to reset a forgotten password by email
```

Se a entrega ainda não existe, o modelo a cria com `atipspec new`. Em
seguida, a skill executa `atipspec spec password-reset`. O comando recusa
até o contrato ter `status: accepted`; caso contrário, imprime o workflow,
as regras e o contexto.

## O que o modelo faz

1. Lê o contexto que o comando imprimiu: o contrato, a visão geral, o
   glossário, as specs vivas na lista de impacto e as decisões que as
   afetam. Usa as palavras do glossário e pergunta antes de aceitar um
   sinônimo.
2. Cobre, perguntando apenas o que o projeto ainda não responde: ator e
   gatilho, caminho feliz, caminhos de falha, dados criados, alterados,
   excluídos ou nunca tocados, fora do escopo, limites não funcionais,
   conflitos com o comportamento existente ou com o contrato.
3. Escreve `spec.md`:

```markdown
---
title: "Password reset"
status: draft
capability: auth
impact: [notifications]
owner: ana
ticket: SHOP-12
initiative: null
base: 9f2c1e...
created: 2026-09-12
---

# Password reset

## Intent

Let a user who forgot the password recover access without support.

## Requirements

### REQ-001: The user can request a reset link

From the sign-in screen the user enters an email and receives a link.

Why: support tickets for forgotten passwords are 40% of the queue.

Acceptance criteria:
- AC-001: When a registered email requests a reset, the system sends a link to that email within 60 seconds.
- AC-002: When an unknown email requests a reset, the system responds exactly like a valid one.

### REQ-002: The link expires

Acceptance criteria:
- AC-003: If a link is older than 30 minutes, then the system shows "link expired" and sends nothing.

## Quality attributes

### REQ-003: Reset requests under load

Acceptance criteria:
- AC-004: When 100 users request a reset within one minute, the p95 response time at the API gateway is below 300 ms.

## Assumptions

- The link is single-use.

## Out of scope

- Password policy changes.

## Open questions

- None
```

4. Executa `atipspec check password-reset` até que o único pendente
   restante seja sua aceitação.
5. Apresenta a spec e pede que você execute
   `atipspec accept password-reset spec`.

## Regras da entrevista

- No máximo cinco perguntas por lote, cada uma vinculada ao requisito que
  ela muda.
- Um padrão que o modelo propõe se torna um requisito e uma suposição que
  você confirma na aceitação, nunca uma escolha silenciosa.
- Todo critério em forma EARS ou de cenário com valores concretos, sem
  termos vagos, e marcado `[manual]` quando uma pessoa o observa; `check`
  avisa caso contrário. Veja [como escrever critérios](../reference/spec-quality.md).
- Atributos de qualidade são números com uma forma de medi-los, ou nada.
- Uma entrega cabe em um dia de trabalho. Acima de `max_requirements` o
  modelo propõe dividi-la em entregas sob uma iniciativa antes de pedir a
  aceitação; `check` avisa de qualquer forma.
- Comportamento, nunca implementação.
- Uma spec com perguntas em aberto não pode ficar pronta. `check` a recusa.
- `capability` é a spec viva que recebe os requisitos no deliver. `impact`
  lista toda outra spec viva ou seção do contrato que a entrega toca:
  `context` as carrega e `status` avisa sobre sobreposições com outras
  entregas abertas.
- `### REQ-003 [remove]: Exact title` exclui essa seção da spec viva no
  deliver. É assim que um comportamento é aposentado: explicitamente.

## Sua parte

Leia como o contrato que ela é. Mude o texto, adicione critérios, corte
escopo. Quando ela disser o que você quer, aprove na conversa. Para uma spec legada, o agente executa:

```bash
atipspec accept password-reset spec
```

Ele recusa enquanto uma pergunta está em aberto ou um requisito não tem
critério; caso contrário, define `status: ready` e registra um hash da
spec e do contrato. A partir daí, qualquer edição em qualquer um dos dois
arquivos transforma a entrega de volta em rascunho até você aceitar de
novo. O agente executa esse comando somente após sua aprovação explícita na conversa.

!!! note "Mudando a spec depois"
    Se o build revelar que um critério não pode ser atendido, o modelo deve
    parar e avisar você. A spec muda com seu acordo, e a entrega passa pelo
    portão de novo. Critérios nunca são enfraquecidos silenciosamente e
    nunca são adiados.
