# spec

**Da intenção a cenários que o revisor pode verificar.** A fase em que você
decide o que será construído.

| | |
| --- | --- |
| Papel | O analista. Se importa com o resultado observável, não com a solução. Faz no máximo três perguntas por rodada, propõe padrões, nunca aceita "funciona bem" como resultado. |
| Quem decide | Você aprova a proposta na conversa: estes cenários junto com a abordagem e os testes do [plano](plan.md); o assistente a registra com `atipspec accept <slug> proposal --code <code>`. **Ponto de parada 1.** |
| Produz | requisitos e cenários em `.atipspec/specs/<capability>.md`; o `spec.md` da entrega com a intenção, o que fica fora do escopo, os limites de qualidade e os IDs que ela lista |

## Como executar

```text
/atipspec-spec password-reset: users should be able to reset a forgotten password by email
```

Se a entrega ainda não existe, o modelo a cria com `atipspec new`. Em
seguida, a skill executa `atipspec spec password-reset`, que imprime o
workflow, as regras e o contexto. Uma entrega guiada não precisa de mais
nada para começar; `check` avisa enquanto o contrato não está aceito. Uma
entrega de fix usa o [fix](fix.md) em vez disso, e uma
[entrega antiga](../reference/legacy.md#aprovacoes) precisa antes da
aceitação do contrato.

## O que o modelo faz

1. Lê o contexto que o comando imprimiu: o contrato, a visão geral, o
   glossário, as specs vivas na lista de impacto e as decisões que as
   afetam. Usa as palavras do glossário e pergunta antes de aceitar um
   sinônimo.
2. Pergunta apenas o que o projeto ainda não responde, em rodadas de no
   máximo três perguntas, as de maior impacto primeiro, cada uma vinculada à
   decisão que ela muda e com um padrão proposto; faz outra rodada enquanto
   uma decisão com consequências estiver em aberto. Resolve, nesta ordem:
   ator e gatilho; caminho feliz; caminhos de falha (entrada inválida, dados
   ausentes, permissões, timeouts); dados criados, alterados ou excluídos;
   fora do escopo; atributos de qualidade como um número com a forma de
   medi-lo, ou nenhum; conflitos com o comportamento existente ou com o
   contrato.
3. Obtém um prefixo de ID uma vez para a entrega com `atipspec ids auth` e
    escreve os requisitos e seus cenários na spec viva da capacidade,
    `.atipspec/specs/auth.md`:

    ```markdown
    ### REQ-AUTH-7KQ2M-001: The user can request a reset link

    From the sign-in screen the user enters an email and receives a link.

    Why: support tickets for forgotten passwords are 40% of the queue.

    #### AC-AUTH-7KQ2M-001: Registered email
    - **GIVEN** a registered user with the email "ana@example.com"
    - **WHEN** the user requests a reset for "ana@example.com"
    - **THEN** the system sends a reset link to "ana@example.com" within 60 seconds

    #### AC-AUTH-7KQ2M-002: Unknown email
    - **WHEN** a reset is requested for "nobody@example.com", which no user has
    - **THEN** the system shows "Check your email" and sends nothing

    ### REQ-AUTH-7KQ2M-002: The link expires

    #### AC-AUTH-7KQ2M-003: Link older than 30 minutes
    - **WHEN** a link issued 31 minutes ago is opened
    - **THEN** the page shows "link expired" and sends nothing

    ### REQ-AUTH-7KQ2M-003: Reset requests under load

    #### AC-AUTH-7KQ2M-004: One hundred requests a minute
    - **WHEN** 100 users request a reset within one minute
    - **THEN** the p95 response time measured at the API gateway is below 300 ms
    ```

4. Preenche o `spec.md` da entrega: `requirements` lista os IDs que esta
    mudança escreve, `## Intent` declara o ator, o gatilho, o resultado
    observável e como você saberá que funcionou, e `## Out of scope` e
    `## Quality attributes` (uma linha `- REQ-...: limit` por requisito que
    declara um limite) ficam decididos, `- None` inclusive:

    ```markdown
    ---
    title: "Password reset"
    status: draft
    capability: auth
    owner: ana
    requirements: [REQ-AUTH-7KQ2M-001, REQ-AUTH-7KQ2M-002, REQ-AUTH-7KQ2M-003]
    risk: normal
    ---

    # Password reset

    ## Intent

    A user who forgot the password requests a reset link by email and sets a new
    password with it, without contacting support.

    ## Out of scope

    - Password policy changes.

    ## Quality attributes

    - REQ-AUTH-7KQ2M-003: p95 below 300 ms with 100 requests per minute

    ## Assumptions

    - The link is single-use.

    ## Open questions

    - None
    ```

    Quando você traz um documento ou uma lista de critérios de aceitação, o
    modelo executa `atipspec spec-bind password-reset --file <path>`, que
    escreve a spec viva e os IDs; com uma lista, mantém o original e lista em
    `## Import review notes` o que verificar.

5. Executa `atipspec check password-reset` e reescreve o que ele aponta até
   que o único pendente restante seja sua aprovação. Cita apenas textos que
   a interface mostra palavra por palavra, e nomeia cada aviso que mantém ao
   apresentar.
6. Propõe o [risco](#risco) da entrega, prepara o [plano](plan.md) e
   apresenta `atipspec proposal password-reset`, que mostra o código de
   aprovação, o tipo e o risco, com que rigor os critérios são verificados,
   os avisos de especificação e o diff da spec viva, e pede sua aprovação na
   conversa.

## Regras da entrevista

- No máximo três perguntas por rodada, cada uma vinculada à decisão que ela
  muda; mais rodadas enquanto uma decisão com consequências estiver em
  aberto.
- Um padrão que o modelo propõe se torna um requisito e uma suposição que
  você confirma na aceitação, nunca uma escolha silenciosa.
- Todo cenário com WHEN e THEN e um valor concreto em cada THEN, sem termos
  vagos, e marcado `[manual]` quando uma pessoa o observa; caso contrário,
  `check` o reporta. Veja [como escrever critérios](../reference/spec-quality.md).
- Um requisito por comportamento que um usuário valoriza, independente de
  outras mudanças abertas, pequeno o bastante para a entrega e testável.
- Atributos de qualidade são números com uma forma de medi-los, ou nada.
- Uma `## Intent` vazia bloqueia a proposta, assim como uma `## Out of
  scope` ou `## Quality attributes` vazia: escreva `- None` quando nada se
  aplica.
- Uma entrega cabe em um dia de trabalho. Acima de `max_requirements` o
  modelo propõe dividi-la em entregas sob uma iniciativa antes de pedir a
  aceitação; `check` avisa de qualquer forma.
- Comportamento, nunca implementação.
- Uma spec com perguntas em aberto não pode ser aprovada: a proposta não
  mostra nenhum código.
- `capability` é a spec viva que contém os requisitos. `impact` lista toda
  outra spec viva ou seção do contrato que a entrega toca: `context` as
  carrega e `status` avisa sobre sobreposições com outras entregas abertas.
- `### REQ-AUTH-7KQ2M-003 [remove]: Exact title` na spec viva, listado em
  `requirements`, exclui esse requisito no deliver. É assim que um
  comportamento é aposentado: explicitamente.
- Requisitos que outra entrega aberta ou a spec viva já contém mantêm seus
  IDs; a entrega lista apenas o que ela escreve.
- Um requisito que a entrega adiciona, altera ou remove em `specs/` sem
  listá-lo, na spec viva da sua capacidade ou em outra, é um erro em todos os
  níveis de risco: a aprovação inclui no hash apenas os listados, e
  `merge-check` bloqueia os demais.

## Risco

O `spec.md` de uma entrega guiada declara `risk: low`, `normal` (o que `new`
escreve) ou `high`. O modelo propõe o nível; você o aprova com a proposta,
que mostra `Kind: ... · Risk: ...` e o que o nível pede do portão. `risk`
faz parte do que a aprovação da proposta inclui no hash, então mudá-lo
depois anula essa aprovação. O nível não adiciona nem remove nenhuma
aprovação.

| Nível | O que o portão pede |
| --- | --- |
| `low` | um critério em `Tests:` cujo teste nomeado em `Proof:` passou na evidência atual não precisa de veredito do revisor (`check` diz isso com um info, e o dossiê mostra `NOT NEEDED` com o motivo); `review.md` continua obrigatório, todo outro critério, inclusive os manuais, precisa do seu veredito e um `FAIL` continua bloqueando. Remover um requisito (marcado `[remove]` ou excluído de `specs/`), mesmo listado, ou mudar `contract.md` é um erro: `check` compara `specs/` com os requisitos que estavam no commit base da entrega e com o que trouxeram desde então o branch de integração e as entregas arquivadas no branch |
| `normal` | um veredito do revisor para cada critério |
| `high` | `plan.md` declara um `scope`, e um arquivo fora dele é um erro, mesmo com `strict_scope: false`; todo critério em `Tests:` nomeia seu teste em `Proof:`, com um `Report:` (um erro que bloqueia a proposta); o review vem de uma sessão isolada (`session: isolated`) |

Uma entrega sem `risk`, as antigas inclusive, é `normal`; uma entrega antiga
que o define manualmente recebe seus efeitos, e `check` registra o nível.
Outro valor é um erro. O pacote de review declara o nível, e o dossiê o
mostra.

## Sua parte

Leia a proposta como o acordo que ela é. Mude o texto, adicione cenários,
corte escopo. Quando ela disser o que você quer, aprove na conversa; o
assistente então executa, com o código que apresentou:

```bash
atipspec accept password-reset proposal --code K7M2-QX4P
```

Ele recusa enquanto uma pergunta está em aberto, um cenário está incompleto
ou o plano tem um erro, e quando o código não corresponde ao conteúdo atual;
caso contrário, define `status: ready` e registra um hash dos cenários, do
`spec.md` da entrega, dos compromissos do plano, do contrato e da
configuração, o código e o canal. A partir daí, qualquer edição neles
transforma a entrega de volta em rascunho até você aprovar de novo, e
`check` nomeia o que mudou. O Claude Code pergunta a você antes de o comando
rodar.

!!! note "Mudando a spec depois"
    Se o build revelar que um critério não pode ser atendido, o modelo deve
    parar e avisar você. A spec muda com seu acordo, e a entrega passa pelo
    portão de novo. Critérios nunca são enfraquecidos silenciosamente e
    nunca são adiados.
