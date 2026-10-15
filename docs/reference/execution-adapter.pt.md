# Adaptador de execução

As skills guiadas funcionam dentro do assistente de programação ativo do
usuário. Para uma execução retomável, `atipspec run <slug>` usa um adaptador
de processo configurado explicitamente. Ele nunca aceita a proposta nem o
resultado, e nunca faz commit, push, merge ou deploy. Executa apenas entregas
guiadas, e recusa sob uma política de confiança externa, selecionada ou
exigida.

O executor de processo precisa de um sistema POSIX para encerrar os processos
de um adaptador: Linux, macOS ou WSL. Em outros sistemas, `run` recusa antes de ler
a entrega ou escrever qualquer coisa; continue a entrega na conversa guiada,
que tem as mesmas fases e o mesmo portão. O executor é um processo em
primeiro plano com checkpoints, não um serviço instalado em segundo plano.
Um supervisor pode iniciá-lo, mas o AtipSpec não alega persistência depois
que o processo hospedeiro para.

## Configuração

Crie `.atipspec/adapter.json` antes de aprovar a proposta:

```json
{
  "schema": 1,
  "name": "my-agent-wrapper",
  "command": ["/absolute/path/to/wrapper"],
  "isolated_review": false
}
```

O executável roda na raiz do projeto com uma requisição JSON no stdin. Ele
deve escrever exatamente uma resposta JSON no stdout; a saída de diagnóstico
vai para o stderr. O comando é um array argv, não código de shell. Mudanças
na configuração do adaptador invalidam a aprovação da proposta guiada. O
wrapper deve impor as permissões solicitadas e usar uma nova conversa de
modelo para a revisão antes de declarar `isolated_review: true`. Um processo
novo do sistema operacional, por si só, não prova o isolamento do contexto
do modelo. Este protocolo não é um sandbox para programas arbitrários.

O executor confronta a `session:` da revisão com essa declaração. Uma revisão
que diz `session: isolated` vinda de um adaptador sem `isolated_review: true`
reprova a execução. Quando a entrega exige uma revisão isolada (`risk: high`,
ou `require_isolated_review: true` em `config.yaml`) e o adaptador não a
declara, a execução para em `needs_decision` antes de chamar qualquer papel,
de modo que não se faz nenhum trabalho que só uma revisão isolada poderia
aceitar: execute a entrega no modo guiado e revise-a em uma sessão isolada
com `atipspec review <slug>`, ou configure um adaptador que isole o revisor.

As requisições incluem `schema`, `delivery`, `role`, `instruction`,
`agreement`, `context` versionado, a `task` atribuída, os `findings`
anteriores, um contrato de resposta e as permissões. As requisições de
revisão incluem `review_packet`. O wrapper integra o modelo e as ferramentas
de programação que escolher; o núcleo do AtipSpec controla a verificação.

Respostas:

```json
{"schema": 1, "status": "done", "summary": "Implemented the approved behavior"}
```

`needs_decision`, `blocked` e `failed` também são status válidos e devem
explicar o problema concreto em `summary`. A conclusão de uma revisão também
retorna `review_markdown`, correspondente aos IDs de critério e à árvore
candidata do pacote. O revisor não deve modificar arquivos do projeto. O
núcleo valida a forma da resposta, detecta desvio do acordo e executa seu
próprio portão de evidência e revisão. Uma mensagem `done` não estabelece
correção nem aceitação humana.

## Operação e recuperação

```sh
atipspec adapter
atipspec proposal my-change                       # shows the approval code
atipspec accept my-change proposal --code <code>  # after the human approves
atipspec run my-change --budget 900 --timeout 300   # --max-rounds: at most, and by default, review_rounds less one
atipspec report my-change                         # shows the result's code
atipspec accept my-change result --code <code>    # after the human accepts
atipspec deliver my-change
```

`atipspec run` imprime seu estado como JSON e sai com 0 em
`ready_for_acceptance` ou `accepted`, e com 2 em qualquer outro estado:
`awaiting_approval`, `needs_decision`, `blocked` ou `failed`, com o motivo.
`run.json` registra a fase, o tempo decorrido acumulado, as rodadas de
correção e o digest do acordo. `progress.json` registra as definições das
tarefas concluídas. Ambos são metadados operacionais excluídos da impressão
digital do candidato; a evidência e as aprovações continuam sendo verificadas
de forma independente. Travas do sistema operacional permitem um executor
por checkout.

Executar de novo um candidato concluído reutiliza a evidência final e a
revisão atuais. Depois de resolver uma falha reportada, use `--resume`.
Mutações de agente interrompidas ou que excederam o tempo exigem inspecionar
o trabalho parcial e selecionar explicitamente `--retry-interrupted`; elas
não são repetidas às cegas. A mesma versão aprovada mantém seu orçamento de
tempo decorrido e de correções entre invocações. Novos compromissos
aprovados começam um novo orçamento. Aumentar os limites de tempo é uma
escolha explícita na CLI. `--max-rounds` conta toda correção automática,
seja uma revisão ou um check que a tenha pedido; tem como padrão
`review_rounds` em `config.yaml` menos um, porque cada correção é revisada de
novo, e não pode excedê-lo, já que mais rodadas são decisão da pessoa. As
revisões que o executor pede contam em `review-rounds.json`, como
`atipspec review` as conta: cada revisão de outro candidato, contando a
primeira; quando `review_rounds` já foram contadas, o executor para em
`needs_decision`.

As políticas de confiança externas usam seu workflow protegido de execução e
aceitação; este executor inicial não as contorna com registros de aprovação
locais. As métricas de tokens e de custo são reportadas como indisponíveis,
não como zero.

## Limites da validação

Os testes usam fixtures reais de subprocesso para verificar a execução, a
recusa antes da aprovação, as verificações compartilhadas, a revisão, a
reutilização, a interrupção, o desvio, os timeouts, as novas tentativas e a
trava. Essas fixtures são programas determinísticos, não testes com modelos
reais. Um wrapper nativo de cliente de programação e uma validação de
integração real ainda são necessários antes de alegar uma integração de
modelo autônoma de ponta a ponta.
