# Reorientación: seguimiento de implementación

La implementación está autorizada por el usuario. No hacer commits ni push en
este repositorio. La propuesta de producto es el alcance; esta lista registra
evidencia y pendientes, sin convertir hitos parciales en una entrega completa.

- [ ] A. Flujo local completo: aprobación conjunta, aceptación final explícita,
  cierre sin firmas, tareas sin commits obligatorios, verificación compartida,
  specs canónicas completas y propuesta/resultado breves.
- [ ] B. Roles selectivos, contexto por rol, estados y checkpoints, adaptador
  ejecutable, recuperación, límites, revisión separada y decisiones materiales.
- [ ] C. Identidades concurrentes, ramas existentes, ownership, dependencias,
  contratos inmutables entre repositorios y reconciliación de conflictos.
- [ ] D. Importación y migración revisables, comentarios por escenario,
  configuración por stack/organización, ejemplos y matriz de adaptadores.
- [ ] Validación transversal: cambios pequeños y visuales, fallos e interrupciones,
  cambios de alcance, dos equipos y compatibilidad con confianza externa.

Los pilotos con equipos externos y la clasificación competitiva requieren uso
real posterior. No se presentarán pruebas automatizadas como evidencia de
adopción, productividad o superioridad comercial.

## Implementado y comprobado parcialmente

- Parser de escenarios GIVEN/WHEN/THEN, español/portugués, invariantes e IDs
  con namespace. Mantiene el formato antiguo.
- Aprobación conjunta y aceptación final local, con invalidación por cambios;
  registro de tareas sin commits y cierre sin firmas.
- Verificación final compartida, JUnit real y fallo ante tests fallidos aunque
  su comando termine con cero. Las verificaciones dirigidas no sustituyen la final.
- Entregas nuevas de funcionalidad con requisitos canónicos en specs/, referencias
  en la entrega, baseline de creación y vista de propuesta con diff.
- Separación del acuerdo aprobado y descomposición operativa para planes con
  verificación final; contexto seleccionable por rol/tarea con digests.
- Runner POSIX con protocolo de proceso, checkpoints, un escritor por checkout,
  límites, reanudación conservadora y detección de cambios del acuerdo.
- IDs nuevos independientes de contadores compartidos; IDs existentes preservados.

Evidencia observada el 23 de septiembre de 2026:

- Suite completa: **119 pruebas pasadas en 172,266 s**; salida en
  `/tmp/atipspec-reorientation-full.log`. Incluye compatibilidad de confianza externa.
- Recorrido dirigido: 26 pruebas pasadas en
  `/tmp/atipspec-guided-runner-tests.log`.
- Las 11 habilidades distribuidas pasan `skill-creator/scripts/quick_validate.py`.
  Se corrigió además una descripción YAML antigua con dos puntos sin comillas.
- `git diff --check` y compilación de módulos pasan. HEAD continúa en `cf2d82c`;
  no se han creado commits ni hecho push en el repositorio.

El runner se ensaya con procesos deterministas; esto no prueba integración con
un modelo real. Las pruebas de Git crean commits únicamente en repositorios
desechables de fixtures. La distribución instalada debe verificarse después de
terminar los cambios pendientes; el entorno `.venv` actual no incluye pip ni
setuptools, por lo que aún no se ha reconstruido el paquete.

## Pendientes que impiden considerar terminada la propuesta

- Adaptador nativo de un cliente y validación de sus capacidades reales; funciones
  de guía/roles antes de aprobar y elección de profundidad más integrada.
- Coordinación de equipos: refs publicados, ownership, dependencias, contratos
  inmutables, reconciliación y vista compartida.
- Importación de formatos externos sin IDs, migración optativa con diff y respaldo,
  comentarios por escenario y configuración organizativa/stack.
- Simplificar y migrar el recorrido de fixes, unificar estados visibles, retención
  de logs y ejemplos completos; actualizar documentación en sus idiomas.
- Pruebas de casos reales equivalentes a my-site y corrección visual, dos equipos,
  distribución instalada y auditoría requisito por requisito.

La propuesta sigue siendo el alcance. No marcar el objetivo completo por tener
una suite verde parcial ni sustituir los pilotos externos por datos inventados.
