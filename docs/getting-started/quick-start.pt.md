# Primeiros passos

Uma mudança, do seu lado da conversa. Você toma três decisões: o contrato,
uma vez por projeto; a proposta de cada mudança; e seu resultado revisado. O
assistente executa todos os comandos abaixo e registra cada decisão com
`atipspec accept --code <code>`, o código da visão que ele mostrou a você; o
Claude Code, aberto na raiz do projeto, pergunta a você antes de esse
comando rodar. Os exemplos usam o
Claude Code; a [página de clientes](../clients.md) mostra o equivalente nos
outros. A página de [entrega guiada](../flow/guided.md) tem cada passo em
detalhe.

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

O assistente verifica o repositório contra ele e o apresenta com as decisões
que inclui e um código de aprovação. Aprove-o na conversa; o assistente
registra sua aprovação com esse código:

```bash
atipspec audit
atipspec proposal contract
atipspec accept contract --code 11HN-G0QN
git add .atipspec && git commit -m "chore: architecture contract"
```

Até que a aceitação do contrato esteja registrada, `atipspec check` avisa
sobre isso.

## 2. Peça a mudança

```text
/atipspec-spec password-reset: users should be able to reset a forgotten password by email
```

O assistente cria a entrega em sua própria branch:

```bash
atipspec new password-reset --title "Password reset" --capability auth --owner ana --branch
```

`new` cria `.atipspec/deliveries/password-reset/` com `spec.md`, `plan.md`,
`deferred.md` e `baseline.json`, registra o commit atual como a base da
entrega e muda para o branch `delivery/password-reset`. Em seguida, a skill
executa `atipspec spec password-reset`, que imprime a **fase spec**: seu
workflow, as regras e exatamente o contexto que a entrega precisa.

O modelo entrevista você em rodadas de no máximo três perguntas e depois
escreve os requisitos e seus cenários na spec viva,
`.atipspec/specs/auth.md`, com IDs de `atipspec ids auth`:

```markdown
### REQ-AUTH-7KQ2M-001: The user can request a reset link

#### AC-AUTH-7KQ2M-001: Registered email
- **WHEN** a user requests a reset for the registered email "ana@example.com"
- **THEN** the system sends a reset link to "ana@example.com" within 60 seconds
```

No `spec.md` da entrega, ele lista esses IDs em `requirements` e escreve a
intenção, o que fica fora do escopo e os limites de qualidade. Um resultado
vago, como "funciona corretamente", bloqueia a proposta.

## 3. Aprove a proposta

O modelo prepara a abordagem e como cada cenário é testado, em `plan.md`, e
apresenta tudo junto:

```bash
atipspec proposal password-reset
```

A visão mostra os cenários, o escopo, a abordagem, os testes, o nível de
risco, o diff da spec viva e o código de aprovação. Este é o **ponto de
parada 1**: leia, depois peça alterações ou aprove na conversa. O assistente
registra sua aprovação com o código que apresentou:

```bash
atipspec accept password-reset proposal --code K7M2-QX4P
```

O Claude Code, aberto na raiz do projeto, pergunta a você antes de esse
comando rodar. Ele define
`status: ready` e registra o que você aprovou e por qual canal; se alguém
editar os cenários, a abordagem ou os testes depois, o portão nomeia o que
mudou e pergunta a você de novo.

## 4. Build e review

```text
/atipspec-ship password-reset
```

`atipspec ship password-reset` indica a próxima fase em que a entrega pode
entrar, e cada comando de fase recusa enquanto uma etapa obrigatória estiver
faltando. O modo ship executa as fases restantes sem pausar até o resultado:

- **build**: código e testes, tarefa por tarefa, cada uma registrada com
  `atipspec task-done password-reset T1 --note "..."`; depois
  `atipspec verify password-reset` executa as verificações finais uma única
  vez sobre o candidato terminado.
- **review**: `atipspec review password-reset` escreve um pacote; um revisor
  em uma sessão isolada escreve `review.md` com um veredito por critério,
  cada um apontando para um teste que passou, um `file:line` ou um
  `file::test`.

Acompanhe isso de outro terminal a qualquer momento:

```bash
atipspec status password-reset
```

```text
password-reset  [in_progress]  tasks 1/2
  todo    T2 is not complete: implement it and record `atipspec task-done password-reset T2 --note <summary>`
  todo    FINAL: no evidence; run `atipspec verify password-reset`
  todo    No review.md: run `atipspec review password-reset` and give the packet to a reviewer in an isolated session
  info    lead time 3h: since creation, until the result is accepted
  info    risk normal: every criterion needs a reviewer verdict
  info    Local mode: acceptance records detect drift; identity and evidence provenance are not externally authenticated
Next: T2 is not complete: implement it and record `atipspec task-done password-reset T2 --note <summary>`
```

## 5. Aceite o resultado

Quando `atipspec check password-reset` está verde, a entrega está
`checked`. O assistente apresenta o resultado:

```bash
atipspec report password-reset
```

O dossiê mostra cada critério com sua evidência e o veredito do revisor, e
cada arquivo alterado desde o commit base com o diff, e o código de
aprovação do resultado. Este é o **ponto de parada 2**: inspecione-o e
aceite ou peça alterações. O assistente registra sua aceitação e arquiva a
entrega:

```bash
atipspec accept password-reset result --code 3C1Q-4VN7
atipspec deliver password-reset
```

```text
AtipSpec: merged into .atipspec/specs/auth.md and moved to .atipspec/archive/password-reset/
Result archived. Commit, merge and deployment follow the repository's explicit policy.
```

`deliver` não faz commit, push nem merge. Antes do merge, o assistente
executa `atipspec merge-check --base <target>`, que confirma que a entrega
está aceita e que o código ainda é o código que você aceitou; depois do
`deliver`, uma mudança posterior reabre a entrega (veja
[deliver](../flow/deliver.md#depois-do-deliver-o-codigo-fica-fixo)).
Organizações que precisam de aprovações autenticadas configuram a
[aceitação confiável](../enterprise.md) em vez dos registros locais.

## O que você acabou de conseguir

- Cenários que você aprovou, mantidos na spec viva da capacidade `auth`.
- Arquivos de evidência com os comandos exatos, os códigos de saída e o hash
  da árvore da verificação final.
- Uma revisão com um veredito por critério, cada um apontando para uma prova
  que o portão resolve, e a sessão que o revisor declara: `check` avisa
  quando o revisor viu a conversa do autor e bloqueia isso com `risk: high`
  ou com `require_isolated_review`.
- Um registro de cada decisão, vinculado ao conteúdo que você viu, e um
  contrato aplicado em cada arquivo que a entrega tocou.

Próximo: [como funciona](how-it-works.md), ou o [fluxo](../flow/index.md)
fase por fase.
