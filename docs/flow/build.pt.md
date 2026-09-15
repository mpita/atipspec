# build

**Do plano ao código, evidência e commits.** Tarefa por tarefa.

| | |
| --- | --- |
| Papel | Quem assina o commit. Pequenas mudanças, testes que exercitam os critérios, as convenções desta base de código. Avisa agora quando um critério não pode ser atendido. |
| Quem decide | O desenvolvedor, com o modelo. |
| Produz | código e testes, `evidence/*.json`, um commit por tarefa |

## Como executar

```text
/atipspec-build password-reset
```

O skill executa `atipspec build password-reset`, que se recusa sem um plan
válido e, caso contrário, imprime o workflow, as regras, o contexto e a
próxima tarefa que não tem commit. Depois de cada commit, `atipspec build
password-reset --no-context` nomeia a seguinte.

## O ciclo, para cada tarefa

1. Leia a tarefa, seus requisitos e critérios, as seções do contrato que ela
   toca, o código.
2. Faça a menor mudança que satisfaça os critérios dentro do contrato.
   Adicione ou atualize testes para que os comandos de Verify realmente
   exercitem os critérios.
3. Execute a evidência:

    ```bash
    atipspec verify password-reset --task T1
    ```

    ```text
    [T1] $ python -m pytest -q tests/auth/test_reset.py
        3 passed in 0.21s
    [T1] ok (0.6s)
    T1: pass -> .atipspec/deliveries/password-reset/evidence/T1-20260913T154145Z-3f9a1c2e.json
    ```

4. Quando o framework de testes escreve JUnit XML, nomeie o arquivo no
   `Report:` da tarefa e o teste de cada critério em `Proof:`; `verify` copia
   o relatório para perto da evidência e `check` exige que o teste nomeado
   tenha rodado e passado:

    ```markdown
    ### T1: Request a reset link

    Covers: REQ-001
    Tests: AC-001, AC-002
    Report: .atipspec/tmp/junit.xml
    Proof:
    - AC-001: tests/auth/test_reset.py::test_registered_email_sends_link
    - AC-002: tests/auth/test_reset.py::test_unknown_email_same_response
    Verify:
    - `python -m pytest -q tests/auth --junitxml .atipspec/tmp/junit.xml`
    ```

    Um id de teste é o nome do caso, `Class.name`, `module.Class.name` ou
    `path/to/file.py::Class::name`. Sem `Proof:`, um critério em `Tests:` é
    provado pelo revisor, como antes.

5. Faça o commit com o marcador na mensagem, evidência incluída:

    ```bash
    git add -A
    git commit -m "feat(auth): request password reset link [password-reset:T1]"
    ```

6. `atipspec status password-reset` e siga para a próxima tarefa.

## O que torna uma tarefa concluída

Um commit na branch atual cuja mensagem carrega `[<slug>:Tn]`. Nada mais. Não
é uma checkbox, não é uma frase do modelo. Vários ids em um marcador são
aceitáveis: `[password-reset:T1,T2]`.

## O que a evidência contém

```json
{
  "delivery": "password-reset",
  "task": "T1",
  "result": "pass",
  "tree": "cd03ae507b3605b12a497fcbcf590894a0073076",
  "head": "9f2c1e4...",
  "started": "2026-09-12T15:41:45Z",
  "finished": "2026-09-12T15:41:46Z",
  "commands": [
    {"command": "python -m pytest -q tests/auth/test_reset.py", "exit_code": 0,
     "duration_s": 0.58, "output_tail": "3 passed in 0.21s"}
  ]
}
```

`tree` é a impressão digital da árvore de trabalho contra a qual os comandos
rodaram. O portão aceita a evidência apenas enquanto a árvore ainda
corresponde. Com um `Report:`, o arquivo também carrega `reports` (a cópia em
`evidence/logs/` com seu hash) e `tests` (cada caso com seu status), e alterar
a cópia é detectado como um log de comando alterado. Se um comando modifica a
árvore (um formatador, um arquivo gerado), `verify` avisa e a evidência já
está obsoleta: faça o commit ou descarte e execute de novo.

## Regras

- Nunca toque em `evidence/` manualmente.
- Trabalho imprevisto vira uma nova tarefa com `Covers` e `Verify`, nunca
  escondido dentro de outra; um arquivo fora do `scope` do plan é adicionado
  ao `scope` na mesma edição que adiciona a tarefa que precisa dele.
- Nenhum refactoring além da tarefa.
- Uma violação do contrato relatada por `check` é corrigida no código ou
  escalada como uma decisão, nunca silenciada.
- Se um critério não pode ser atendido, pare e avise o usuário antes de mudar
  a spec.
- Somente saída real. Se um comando não pôde rodar neste ambiente, diga isso.
