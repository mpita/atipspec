# deliver

**Fusiona los requisitos en la spec viva y archiva la entrega.** Solo cuando
la puerta está en verde y aceptaste el resultado actual: en local, el
registro que escribe `atipspec accept <slug> result` tras tu aprobación; con
una policy de confianza, la puerta de confianza en verified con aprobaciones
firmadas. El resultado que aceptas es lo que muestra `atipspec report <slug>`:
los criterios con su evidencia y los veredictos de la revisión, y los
ficheros cambiados desde el commit base con el diff.

| | |
| --- | --- |
| Quién decide | Aceptas el resultado revisado en la conversación: **punto de parada 2**. Bajo una policy de confianza, la aceptación firmada de QA, y `atipspec check --policy` debe salir con 0. La fusión sigue la política de tu repositorio, después de `merge-check`. |
| Produce | `.atipspec/specs/<capability>.md` actualizado, `.atipspec/archive/<slug>/` con el recibo |

## Cómo ejecutarla

```text
/atipspec-deliver password-reset
```

El skill ejecuta `atipspec check password-reset`, presenta
`atipspec report password-reset` y, tras tu aceptación, registra
`atipspec accept password-reset result --code <code>`. Luego:

```bash
git add -A && git commit -m "feat: password reset"   # when the repository's policy commits: the accepted code first
atipspec deliver password-reset                      # --policy /secure/company.toml under a trust policy
```

```text
AtipSpec: merged into .atipspec/specs/auth.md and moved to .atipspec/archive/password-reset/
Result archived. Commit, merge and deployment follow the repository's explicit policy.
Before merging, `atipspec merge-check --base <target branch>` confirms the branch still matches this acceptance; any later change outside .atipspec/ requires reopening the delivery: revert the archive commit, then verify, review and accept again.
```

## Qué hace

1. Ejecuta la puerta. Cualquier cosa que no sea verde se rechaza con el
   informe completo.
2. Fusiona cada requisito por su **ID** estable con alcance de capacidad. Un
   cambio de título actualiza el mismo requisito. Los IDs de criterio se
   conservan. Los conflictos de baseline concurrentes fallan para una
   reconciliación explícita. Todo requisito necesita un ID.
3. Escribe el recibo `reports/acceptance.json`, con `code_tree`: el hash de
   todo lo que está fuera de `.atipspec/` que aceptaste. `deliver` y la
   contabilidad posterior de AtipSpec (curate, otras entregas, aprobaciones)
   nunca lo cambian; cualquier cambio de código sí. También registra
   `living_spec`, el digest de la spec viva que escribió, y
   `living_requirements`, el texto de cada requisito que la entrega lista
   tal como quedó escrito ahí, para que se note una edición posterior de los
   requisitos aceptados, y los `changes` del dosier: los ficheros cambiados
   con su estado y el tamaño y el sha256 del diff, sin el texto del diff, que
   conserva el historial de git.
4. Pone `status: delivered` en la spec de la entrega y mueve la carpeta a
   `archive/`. La evidencia, las aprobaciones y la revisión viajan con ella.

Después del ejemplo, la spec viva contiene cada requisito listado tal como lo
escribió la entrega, por ID; un requisito marcado `[remove]` desaparece:

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

## Luego

Cuando la política de tu repositorio permite que el asistente haga commit y
push:

```bash
git add -A
git commit -m "chore: deliver password-reset"   # only .atipspec/ changes: the archive commit
atipspec merge-check --base origin/main
git push -u origin delivery/password-reset
```

`merge-check` bloquea la fusión mientras una entrega que toca la branch no
esté aceptada, cuando el código en el head no es el código que aceptó un
recibo, cuando una spec viva o el contrato aceptado cambiaron fuera de su
aceptación, o cuando la branch cambia un fichero fuera de `.atipspec/` que
ninguna entrega de ella cambió después de su commit base, como el código
commiteado antes de `atipspec new`, y que `exempt_paths` en la branch de
destino no exime. Los ejemplos de CI lo ejecutan como el check del pull request,
cuyo resumen lista cada entrega con su estado y su ticket (consulta
[aceptación empresarial](../enterprise.md#ci-antes-del-merge)). Abre el pull
request con el ticket y la salida de
`atipspec report <slug> --format markdown` en su descripción, y fusiónalo.
Después de la fusión, `atipspec status` en main muestra la entrega bajo
`delivered`, y la fase [curate](curate.md) refresca el overview.

## Después de `deliver`, el código queda fijado

No cambies nada fuera de `.atipspec/` en la branch después de `deliver`, ni
la spec viva que escribió, y no traigas a ella la branch de destino:
cualquiera de las dos cosas cambia lo que aceptó el recibo, y `merge-check`
falla. Trae la branch de destino antes de la verificación final, con una
fusión: lo que trae no anula la propuesta aprobada (consulta
[equipos](../teams.md#cuando-main-avanza)). Cuando hace falta un cambio, reabre
la entrega:

```bash
git revert <the archive commit>          # the delivery returns to deliveries/, the living spec to its previous text
```

luego verifica, revisa, presenta `atipspec report <slug>` para que aceptes el
resultado cambiado y vuelve a entregar. Es la misma aceptación, repetida
porque el resultado cambió. Mantener el código y el archivado en commits
separados hace que el revert solo toque `.atipspec/`.
