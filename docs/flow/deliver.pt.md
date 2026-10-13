# deliver

**Mescla os requisitos na spec viva e arquiva a entrega.** Somente quando o
portão está verde e você aceitou o resultado atual: localmente, o registro
que `atipspec accept <slug> result` escreve após sua aprovação; com uma
política de confiança, o portão confiável verificado com aprovações
assinadas. O resultado que você aceita é o que `atipspec report <slug>`
mostra: os critérios com sua evidência e os vereditos do review, e os
arquivos alterados desde o commit base com o diff.

| | |
| --- | --- |
| Quem decide | Você aceita o resultado revisado na conversa: **ponto de parada 2**. Sob uma política de confiança, a aceitação assinada de QA, e `atipspec check --policy` precisa sair com 0. O merge segue a política do seu repositório, depois do `merge-check`. |
| Produz | `.atipspec/specs/<capability>.md` atualizado, `.atipspec/archive/<slug>/` com o recibo |

## Como executar

```text
/atipspec-deliver password-reset
```

A skill executa `atipspec check password-reset`, apresenta
`atipspec report password-reset` e, após sua aceitação, registra
`atipspec accept password-reset result --code <code>`. Depois:

```bash
git add -A && git commit -m "feat: password reset"   # when the repository's policy commits: the accepted code first
atipspec deliver password-reset                      # --policy /secure/company.toml under a trust policy
```

```text
AtipSpec: merged into .atipspec/specs/auth.md and moved to .atipspec/archive/password-reset/
Result archived. Commit, merge and deployment follow the repository's explicit policy.
Before merging, `atipspec merge-check --base <target branch>` confirms the branch still matches this acceptance; any later change outside .atipspec/ requires reopening the delivery: revert the archive commit, then verify, review and accept again.
```

## O que faz

1. Executa o portão. Qualquer coisa que não seja verde é recusada com o
   relatório completo.
2. Mescla cada requisito por um **ID** estável, delimitado à capacidade. Uma
   mudança de título atualiza o mesmo requisito. Os IDs de critério são
   mantidos. Conflitos de baseline concorrente falham para reconciliação
   explícita. Todo requisito precisa de um ID.
3. Escreve o recibo `reports/acceptance.json`, com `code_tree`: o hash de
   tudo o que está fora de `.atipspec/` e que você aceitou. O `deliver` e a
   contabilidade posterior do AtipSpec (curate, outras entregas, aprovações)
   nunca o mudam; qualquer mudança de código o muda. Ele também registra
   `living_spec`, o digest da spec viva que escreveu, e
   `living_requirements`, o texto de cada requisito que a entrega lista tal
   como foi escrito ali, para que uma edição posterior nos requisitos
   aceitos apareça, e as `changes` do dossiê: os arquivos alterados com seu
   status e o tamanho e o sha256 do diff, sem o texto do diff, que o
   histórico do git guarda.
4. Define `status: delivered` na spec da entrega e move a pasta para
   `archive/`. Evidência, aprovações e review viajam com ela.

A spec viva depois do exemplo contém cada requisito listado como a entrega o
escreveu, por ID; um requisito marcado `[remove]` desaparece:

```markdown
# auth

## Requirements

### REQ-AUTH-7KQ2M-001: The user can request a reset link

From the sign-in screen the user enters an email and receives a link.

#### AC-AUTH-7KQ2M-001: Registered email
- **WHEN** a user requests a reset for the registered email "ana@example.com"
- **THEN** the system sends a reset link to "ana@example.com" within 60 seconds

### REQ-AUTH-7KQ2M-002: The link expires

#### AC-AUTH-7KQ2M-003: Link older than 30 minutes
- **WHEN** a link issued 31 minutes ago is opened
- **THEN** the page shows "link expired" and sends nothing
```

## Em seguida

Quando a política do seu repositório permite que o assistente faça commit e
push:

```bash
git add -A
git commit -m "chore: deliver password-reset"   # only .atipspec/ changes: the archive commit
atipspec merge-check --base origin/main
git push -u origin delivery/password-reset
```

`merge-check` bloqueia o merge enquanto uma entrega que o branch toca não
está aceita, quando o código no head não é o código que um recibo aceitou,
quando uma spec viva ou o contrato aceito mudaram fora da sua aceitação, ou
quando o branch altera um arquivo fora de `.atipspec/` que nenhuma entrega
dele alterou depois de seu commit base, como o código commitado antes de
`atipspec new`, e que `exempt_paths` no branch de destino não isenta. Os
exemplos de CI o executam como o check do pull request, cujo resumo lista
cada entrega com seu estado e seu ticket (veja
[aceitação empresarial](../enterprise.md#ci-antes-do-merge)). Abra o pull
request com o ticket e a saída de `atipspec report <slug> --format markdown`
na descrição, e faça o merge dele. Depois do merge, `atipspec status` na main
mostra a entrega em `delivered`, e a fase [curate](curate.md) atualiza o
overview.

## Depois do `deliver`, o código fica fixo

Não mude nada fora de `.atipspec/` no branch depois do `deliver`, nem a spec
viva que ele escreveu, e não traga o branch de destino para ele: qualquer
uma dessas coisas muda o que o recibo aceitou, e `merge-check` falha. Traga o
branch de destino antes da verificação final, com um merge: o que ele traz
não anula a proposta aprovada (veja
[equipes](../teams.md#quando-a-main-avanca)). Quando uma mudança for
necessária, reabra a entrega:

```bash
git revert <the archive commit>          # the delivery returns to deliveries/, the living spec to its previous text
```

depois verifique, revise, apresente `atipspec report <slug>` para sua
aceitação do resultado alterado e faça o deliver de novo. É a mesma
aceitação, repetida porque o resultado mudou. Manter o código e o archive em
commits separados faz com que o revert toque apenas `.atipspec/`.
