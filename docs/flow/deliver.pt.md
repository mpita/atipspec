# deliver

**Mescla os requisitos na spec viva e arquiva a entrega.** Somente quando o
portão confiável está verified. Um check local verde é insuficiente.

| | |
| --- | --- |
| Quem decide | `atipspec check --policy` precisa sair com 0 e aprovações confiáveis. Depois você faz o merge da branch. **Ponto de parada 2.** |
| Produz | `.atipspec/specs/<capability>.md` atualizado, `.atipspec/archive/<slug>/` |

## Como executar

```text
/atipspec-deliver password-reset --policy /secure/company.toml
```

ou diretamente:

```bash
atipspec deliver password-reset --policy /secure/company.toml
```

```text
AtipSpec: merged into .atipspec/specs/auth.md and moved to .atipspec/archive/password-reset/
Next: commit, then ask the user to merge the branch
```

## O que faz

1. Executa o portão. Qualquer coisa que não seja verde é recusada com o
   relatório completo.
2. Mescla cada requisito por um **ID** estável, delimitado à capacidade. Uma
   mudança de título atualiza o mesmo requisito. Os IDs de critério são
   mantidos. Conflitos de baseline concorrente falham para reconciliação
   explícita. Todo requisito precisa de um ID.
3. Define `status: delivered` na spec da entrega e move a pasta para
   `archive/`. Evidência assinada, aprovações, review e um recibo de
   aceitação viajam com ela. O recibo descreve a aceitação histórica do
   candidato.

A spec viva depois do exemplo:

```markdown
# auth

## Requirements

### REQ-001: The user can request a reset link

From the sign-in screen the user enters an email and receives a link.

Acceptance criteria:
- AC-001: A request with a registered email sends a link to that email within 60 seconds.
- AC-002: A request with an unknown email responds exactly like a valid one.

### REQ-002: The link expires

Acceptance criteria:
- AC-003: A link older than 30 minutes shows "link expired" and sends nothing.
```

## Em seguida

```bash
git add -A
git commit -m "chore: deliver password-reset"
git push -u origin delivery/password-reset
```

Abra o pull request e faça o merge dele. Depois do merge, `atipspec status`
na main mostra a entrega em `delivered`, e a fase [curate](curate.md) atualiza
o overview.
