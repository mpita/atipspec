# build

**Do plano aprovado ao código, aos registros de tarefa e à evidência.**
Tarefa por tarefa, e depois uma verificação final.

| | |
| --- | --- |
| Papel | O implementador. Pequenas mudanças, testes que exercitam os critérios, as convenções desta base de código. Avisa agora quando um critério não pode ser atendido. |
| Quem decide | O desenvolvedor, com o modelo, dentro do acordo aprovado. |
| Produz | código e testes, `progress.json` com as tarefas registradas como implementadas, `evidence/*.json` |

## Como executar

```text
/atipspec-build password-reset
```

A skill executa `atipspec build password-reset`, que recusa até a proposta
estar aceita para seu conteúdo atual e, caso contrário, imprime o workflow,
as regras, o contexto e a próxima tarefa ainda não registrada. Depois de
cada tarefa, `atipspec build password-reset --no-context` nomeia a seguinte.

## O ciclo, para cada tarefa

1. Leia a tarefa, seus requisitos e cenários, as seções do contrato que ela
   toca, o código.
2. Faça a menor mudança que satisfaça os cenários dentro do contrato e do
   `scope` do plano. Adicione ou atualize testes para que exercitem os
   critérios; rode testes focados enquanto trabalha, ou o `Verify:` próprio
   da tarefa com `atipspec verify password-reset --task T1`.
3. Registre a tarefa:

    ```bash
    atipspec task-done password-reset T1 --note "request() sends the link to registered emails only"
    ```

    ```text
    AtipSpec: T1 of password-reset recorded as implemented (progress, not verification) in .atipspec/deliveries/password-reset/progress.json
    Next: T2 is not complete: implement it and record `atipspec task-done password-reset T2 --note <summary>`
    ```

4. Siga para a próxima tarefa. Os commits seguem a política do seu
   repositório; o AtipSpec não exige nenhum.

## O que torna uma tarefa concluída

Um registro que `atipspec task-done` escreve em `progress.json`: a nota, a
hora, o hash do acordo aprovado e o da tarefa sem seu título. É a declaração
de progresso do assistente, nunca uma prova: a verificação final e o review
verificam o trabalho. Ele recusa antes de a proposta ser aprovada, e um
registro continua válido enquanto o acordo aprovado e a tarefa não mudarem;
renomear a tarefa o mantém. Uma [entrega
antiga](../reference/legacy.md#conclusao-de-tarefas) também conta um
marcador de commit `[<slug>:Tn]`.

## A verificação final

Quando todas as tarefas estão registradas, o candidato está terminado:

```bash
atipspec verify password-reset
```

```text
[FINAL] $ python -m pytest -q --junitxml .atipspec/tmp/junit.xml
    4 passed in 0.31s
[FINAL] ok (0.9s)
[FINAL] report .atipspec/tmp/junit.xml: 4 test(s), 0 failed
FINAL: pass -> .atipspec/deliveries/password-reset/evidence/FINAL-20260913T154145.218304Z-3f9a1c2e.json
```

Ele executa uma única vez os comandos de `## Final verification` do plano e
escreve a evidência. Quando o framework de testes escreve JUnit XML, o plano
nomeia o arquivo em `Report:` e o teste de cada critério em `Proof:`;
`verify` copia o relatório para junto da evidência e `check` exige que cada
teste nomeado tenha rodado e passado. O próprio comando de Verify escreve o
relatório, em um caminho que o git ignora:

```markdown
## Final verification

Report: .atipspec/tmp/junit.xml
Proof:
- AC-AUTH-7KQ2M-001: tests/auth/test_reset.py::test_registered_email_sends_link
- AC-AUTH-7KQ2M-002: tests/auth/test_reset.py::test_unknown_email_same_answer
Verify:
- `python -m pytest -q tests/auth --junitxml .atipspec/tmp/junit.xml`
```

Um id de teste é o nome do caso, `Class.name`, `module.Class.name` ou
`path/to/file.py::Class::name`. Quando ele nomeia vários casos (um teste
parametrizado, ou o mesmo nome em várias classes), todos precisam passar.
Sem `Proof:`, um critério em `Tests:` é provado pelo revisor, a menos que o
projeto defina `require_proof: true` (ou que a política de confiança o
faça), ou que a entrega defina `risk: high`: então todo critério em
`Tests:` precisa da sua entrada em `Proof:` e a verificação precisa de um
`Report:`, um erro que bloqueia a proposta até o plano nomeá-los.

Só conta um relatório que esta execução escreve. Antes de os comandos
rodarem, `verify` apaga o arquivo nomeado em `Report:`; depois, o arquivo
precisa existir e ter sido modificado após essa exclusão (dois segundos de
tolerância), ou a evidência falha com `test report not found` ou
`predates this verification`. É por isso que o caminho precisa ser um que o
git ignora, como `.atipspec/tmp/junit.xml`: um relatório commitado ou escrito
à mão é justamente o que poderia substituir uma execução, e `check` reporta
como erro de plano um `Report:` em um caminho que o git não ignora. Nunca
aponte `Report:` para um arquivo que você quer manter: `verify` o apaga.

Se o código mudar depois da verificação final, rode-a de novo sobre o
candidato terminado. Depois, `atipspec review password-reset`.

## O que a evidência contém

```json
{
  "delivery": "password-reset",
  "task": "FINAL",
  "result": "pass",
  "tree": "cd03ae507b3605b12a497fcbcf590894a0073076",
  "head": "9f2c1e4...",
  "started": "2026-09-12T15:41:45Z",
  "finished": "2026-09-12T15:41:46Z",
  "commands": [
    {"command": "python -m pytest -q tests/auth --junitxml .atipspec/tmp/junit.xml", "exit_code": 0,
     "duration_s": 0.58, "output_tail": "4 passed in 0.31s",
     "output_path": "logs/FINAL-5d0c...-1.log", "output_sha256": "8a1f..."}
  ]
}
```

`tree` é a impressão digital da árvore de trabalho contra a qual os comandos
rodaram. O portão aceita a evidência apenas enquanto a árvore ainda
corresponde. Renomear uma tarefa em `plan.md` (o texto depois de `### T1:`)
é a única mudança que ele tolera: a evidência e o review continuam válidos,
e em um plano guiado com verificação final, cuja aprovação deixa as tarefas
de fora, a tarefa também continua concluída: a impressão digital lê cada
cabeçalho de tarefa reduzido ao seu id, então isso vale também em um clone
novo, como na CI. Com um `Report:`, o arquivo também
carrega `reports` (a cópia em `evidence/logs/` com seu hash, o caminho de
onde foi lida e `fresh: true`) e `tests` (cada caso com seu status), e alterar
a cópia é detectado como um log de comando alterado. Uma evidência com um
relatório escrito pelo AtipSpec 0.2.x não tem a marca `fresh`: `check` pede
para verificar de novo. Se um comando modifica a árvore (um formatador, um
arquivo gerado), `verify` avisa, sai com 1 e a evidência já está obsoleta:
mantenha ou descarte a mudança e rode de novo.

## Regras

- Nunca toque em `evidence/` manualmente.
- `check` nunca executa os testes: `verify` é o único comando que os
  executa, e o portão julga a evidência que ele escreveu.
- Trabalho imprevisto vira uma nova tarefa com `Covers` e `Tests` ou
  `Manual`, nunca escondido dentro de outra; um arquivo fora do `scope` do
  plano é adicionado ao `scope` na mesma edição que adiciona a tarefa que
  precisa dele, e um escopo mais amplo volta para você como uma proposta
  alterada.
- Nenhum refactoring além da tarefa.
- Uma violação do contrato relatada por `check` é corrigida no código ou
  escalada como uma decisão, nunca silenciada.
- Se um critério não pode ser atendido, pare e avise o usuário antes de
  mudar a spec.
- Somente saída real. Se um comando não pôde rodar neste ambiente, diga isso.
