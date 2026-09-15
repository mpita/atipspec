# deliver

**Fusiona los requisitos en la spec viva y archiva la entrega.** Solo cuando
la puerta de confianza está verified. Una comprobación local en verde es
insuficiente.

| | |
| --- | --- |
| Quién decide | `atipspec check --policy` debe salir con 0 y aprobaciones de confianza. Luego tú fusionas la branch. **Punto de parada 2.** |
| Produce | `.atipspec/specs/<capability>.md` actualizado, `.atipspec/archive/<slug>/` |

## Cómo ejecutarla

```text
/atipspec-deliver password-reset --policy /secure/company.toml
```

o directamente:

```bash
atipspec deliver password-reset --policy /secure/company.toml
```

```text
AtipSpec: merged into .atipspec/specs/auth.md and moved to .atipspec/archive/password-reset/
Next: commit, then ask the user to merge the branch
```

## Qué hace

1. Ejecuta la puerta. Cualquier cosa que no sea verde se rechaza con el
   informe completo.
2. Fusiona cada requisito por su **ID** estable con alcance de capacidad. Un
   cambio de título actualiza el mismo requisito. Los IDs de criterio se
   conservan. Los conflictos de baseline concurrentes fallan para una
   reconciliación explícita. Todo requisito necesita un ID.
3. Pone `status: delivered` en la spec de la entrega y mueve la carpeta a
   `archive/`. La evidencia firmada, las aprobaciones, la revisión y un
   recibo de aceptación viajan con ella. El recibo describe la aceptación
   histórica del candidato.

La spec viva después del ejemplo:

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

## Luego

```bash
git add -A
git commit -m "chore: deliver password-reset"
git push -u origin delivery/password-reset
```

Abre el pull request y fusiónalo. Después de la fusión, `atipspec status` en
main muestra la entrega bajo `delivered`, y la fase [curate](curate.md)
refresca el overview.
