# fix

**De um relatório de defeito ao requisito aceito que ele quebra, corrigido,
a um plano de uma tarefa e ao mesmo portão.** Sem entrevista e sem contrato
para aceitar antes; uma aprovação de proposta, e nenhum atalho na evidência
ou no review.

| | |
| --- | --- |
| Papel | Quem conserta sem ampliar. Reproduz primeiro, corrige o requisito para que um teste falhe hoje e passe amanhã, não muda nada que o defeito não exija. |
| Quem decide | Você aprova a proposta na conversa: o defeito, o requisito corrigido e o plano; o assistente a registra com `atipspec accept <slug> proposal --code <code>`, o código que `atipspec proposal <slug>` mostrou. **Ponto de parada 1.** Depois você aceita o resultado, como em qualquer entrega. |
| Produz | o requisito em `specs/<capability>.md` corrigido, `spec.md` com o defeito, `plan.md` com uma tarefa, código, evidência |

## Como executar

```bash
atipspec new bug-123 --title "Reset link never expires" --capability auth --ticket SHOP-9 --kind fix
```

```text
/atipspec-fix bug-123: a reset link created yesterday still works
```

A skill executa `atipspec fix bug-123`, que recusa em uma entrega que não é
um fix e, caso contrário, imprime o workflow, as regras e o contexto. Um
fix, como uma entrega de feature, não precisa da aceitação do contrato para
começar; enquanto o contrato não está aceito, `check` mostra um aviso.

## O que `new --kind fix` cria

Uma entrega guiada (`schema: 2`), como uma feature, com `kind: fix`,
`requirements: []`, `risk: normal` e `baseline.json`, que registra o commit
de onde parte; `new` recusa enquanto a spec viva da capacidade tem mudanças
sem commit. Seu `spec.md` contém o defeito, não um
requisito:

```markdown
---
title: "Reset link never expires"
status: draft
kind: fix
capability: auth
ticket: SHOP-9
schema: 2
requirements: [REQ-002]
risk: normal
---

# Reset link never expires

## Defect

Observed: a link created 26 hours ago still opens the reset form.

Expected: the page shows "link expired", as REQ-002 states.

Reproduction: `python -m pytest tests/auth/test_reset.py -k expired`
```

O plano tem uma tarefa, `T1: Regression test and fix`, e uma
`## Final verification` cujo `Verify:` lista todo `require-command` do
contrato e um marcador de posição para o comando que executa o teste de
regressão.

## O que o modelo faz

1. Reproduz o defeito e preenche `## Defect`: `Observed:` e `Expected:` são
   obrigatórios, `Reproduction:` é recomendado.
2. Encontra o requisito que o defeito quebra em `.atipspec/specs/auth.md`,
   lista seu ID em `requirements` e o corrige ali, mantendo seu ID:
   adiciona um critério de regressão sob ele, ou reescreve o critério que
   deixou o defeito passar.

    ```markdown
    ### REQ-002: The link expires

    #### AC-003: Link older than 30 minutes
    - **WHEN** a link issued 31 minutes ago is opened
    - **THEN** the page shows "link expired"

    #### AC-007: Link issued the day before
    - **GIVEN** a link issued 26 hours ago
    - **WHEN** the user opens it
    - **THEN** the page shows "link expired" and sends nothing
    ```

3. Preenche o plano: `scope`, a abordagem, `Covers: REQ-002`, os critérios
   do requisito em `Tests:`, o de regressão inclusive, e o comando de teste
   em `Verify:` no lugar do marcador de posição.
4. Propõe o [risco](#risco) em `spec.md`.
5. Apresenta `atipspec proposal bug-123`, que mostra
   `Kind: fix · Risk: ...`, `Corrects: REQ-002 (accepted requirement)` e o
   diff da spec viva contra os requisitos aceitos no commit base da entrega,
   e pede sua aprovação.
6. Após a aprovação, escreve o teste de regressão, vê-o falhar, faz a menor
   mudança, registra `task-done`, executa `verify` e entrega o pacote de
   review a um revisor.
7. Apresenta `atipspec report bug-123` para sua aceitação do resultado, e
   então `deliver` escreve o requisito corrigido na spec viva. A história do
   defeito fica na entrega arquivada.

Cerca de dez comandos: `new`, `fix`, `proposal`, `accept proposal`,
`task-done`, `verify`, `review`, `report`, `accept result`, `deliver`.

## O que `check` exige de um fix

- `base` em `spec.md` é o id completo do commit que `atipspec new`
  registrou: um commit no histórico de `HEAD`, e o head que `baseline.json`
  registra. Um nome como `HEAD` ou um branch, ou outro commit, é um erro: um
  posterior deixaria os commits entre o registrado e ele fora da
  comparação, da verificação de escopo e do diff do dossiê, e um anterior
  compararia com requisitos que ainda não estavam aceitos. Uma entrega
  migrada a partir de uma antiga mantém sua base anterior, que não pode ser
  posterior a esse head.
- `requirements` lista pelo menos um requisito, e cada um está entre os
  requisitos que `specs/<capability>.md` continha no commit base da entrega,
  ou que chegaram a ele desde então por meio do branch de integração (veja
  [equipes](../teams.md#quando-a-main-avanca)) ou de uma entrega arquivada no
  branch depois da base, tal como seu recibo registra que essa entrega o
  escreveu: um fix corrige um requisito que a capacidade já aceitou. O arquivo de trabalho e `baseline.json` não mudam
  essa lista, e `capability` é a que o `spec.md` nomeia, mesmo quando `new`
  recebeu outra. Um requisito que não está ali é um erro, já que um
  comportamento que nenhum requisito cobre é uma entrega de feature. Somente
  em um projeto cujas specs vivas não continham nenhum requisito na base (um
  projeto existente sem specs) o fix pode escrever o primeiro, com um info;
  um fix cuja capacidade não tem nenhum enquanto outras têm é um erro que
  pede a `capability` correta.
- Um fix muda apenas os requisitos que lista, e não remove nenhum: um
  requisito adicionado, alterado, excluído ou marcado `[remove]` na spec
  viva da sua capacidade sem estar listado é um erro, assim como um listado
  marcado `[remove]` ou qualquer requisito alterado na spec viva de outra
  capacidade, que a proposta também mostra como um diff. O que o branch de
  integração ou uma entrega arquivada desde a base trouxe não é mudança do
  fix; o que um merge de qualquer outro branch traz é. Quando a mudança está
  commitada no branch, a mensagem diz que outra mudança pode tê-la feito, e
  então ela precisa de uma entrega própria.
- `merge-check` verifica o mesmo contra o branch de destino: um fix
  arquivado no branch cujo requisito não estava na spec viva na base do
  merge, nem foi escrito por uma entrega anterior do branch, bloqueia o
  merge, assim como um requisito alterado fora das entregas que o listam.
- Pelo menos um critério dos requisitos corrigidos está em `Tests:`: o teste
  de regressão automatizado.
- `## Defect` declara `Observed:` e `Expected:`.
- Mais de 2 requisitos é um aviso (`max_requirements` quando for menor): um
  reparo que precisa de mais não é um fix.

Todo o resto é o de uma entrega guiada: uma aprovação de proposta, evidência
vinculada à árvore, o review em uma sessão isolada (declarada em
`session:`), sua aceitação do resultado, `deliver` e `merge-check`.

## Risco

`risk` em `spec.md` define quanta cerimônia o portão pede, para um fix como
para qualquer entrega: `low` para um reparo local cujo teste de regressão o
plano nomeia em `Proof:`, que então não precisa de veredito do revisor;
`high` para segurança, dinheiro, dados ou permissões. Você o aprova com a
proposta; mudá-lo anula essa aprovação. Veja [risco](spec.md#risco).

## Fixes criados antes da 0.3.0

Um fix sem `schema: 2` em seu `spec.md` mantém seu próprio fluxo até ser
arquivado: ele precisa da aceitação do contrato para começar, do seu
requisito embutido e de `accept <slug> spec`, e não tem aceitação de plano.
`deliver` mescla seu requisito na spec viva como antes.
