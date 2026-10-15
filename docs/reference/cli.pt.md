# Referência da CLI

Todos os comandos podem ser executados de qualquer lugar dentro do projeto; o
AtipSpec encontra a raiz procurando `.atipspec/config.yaml`. Todo comando,
exceto `init`, valida esse arquivo primeiro (veja
[configuração](configuration.md)). Erros imprimem `AtipSpec: error: ...` e
saem com 1 (veja [códigos de saída](#codigos-de-saida)). O estado de uma
entrega é derivado: `status` e `check` o calculam a partir dos arquivos e do
git a cada execução. O que a CLI registra, ela escreve como arquivos no
repositório: registros de aprovação, `progress.json`, evidência,
`review-rounds.json`, o `run.json` do executor e o recibo do arquivamento
(veja [artefatos](artifacts.md)).

**Quem executa o quê.** Na conversa guiada, o assistente executa os comandos;
você aprova na conversa, e o assistente registra sua decisão com `accept`
(veja [três decisões humanas](../flow/guided.md#tres-decisoes-humanas)). Cada
seção diz quando um comando é da pessoa, da CI ou de um worker protegido.
`atipspec <command> --help` imprime as opções.

## Projeto

### `atipspec init`

```text
atipspec init [--name NAME] [--language LANG] [--client ID]...
```

Cria `.atipspec/` com `config.yaml`, `contract.md`, `overview.md`,
`glossary.md`, as pastas `specs/`, `deliveries/`, `archive/`,
`decisions/`, `initiatives/`, a cópia do framework e as skills dos clientes
selecionados. Para o Claude Code, também mescla as regras de permissão do
AtipSpec em `.claude/settings.json` (veja [regras de permissão de
aprovação](../clients.md#regras-de-permissao-de-aprovacao)). Pergunta pelo
que as flags não fornecem quando executado em um terminal; caso contrário,
usa o nome da pasta, `en` e nenhum cliente. `--client` aceita `claude`,
`codex`, `cursor`, `github-copilot`, `antigravity` ou `gemini` e pode ser
repetido. `config.yaml` recebe todas as políticas escritas por extenso,
incluindo `trust: optional`. Fora de um repositório git, avisa: o portão
precisa do git e permanece vermelho sem ele. Também avisa quando o
repositório não tem `.gitignore`.

Em um projeto já inicializado: mostra o estado e, em um terminal, um menu
para adicionar ou remover clientes, atualizar o framework, ou mudar nome e
idioma. Com flags, aplica-as diretamente. Você o executa uma vez por
projeto.

### `atipspec install`

```text
atipspec install [--client ID]... [--update]
```

Instala o framework e as skills dos clientes informados sem sobrescrever
nada que seja diferente, e mescla as regras de permissão do Claude Code.
`--update` substitui os arquivos do framework e das skills que diferem da
versão instalada da CLI, remove os arquivos de `.atipspec/framework/` que essa
versão não instala (exceto os que o git ignora) e repara as regras de
permissão ausentes. Também
lista as políticas de `config.yaml` que diferem dos padrões desta versão ou
que não estão definidas, e nunca as edita. Sem `--client`, pergunta em um
terminal, ou usa os clientes já instalados com `--update`. Execute-o depois
de atualizar o AtipSpec.

### `atipspec status`

```text
atipspec status [SLUG] [--format text|json|markdown]
```

Sem um slug: nome do projeto, branch, a aceitação do contrato (quem, quando,
canal, código e decisões, ou o que mudou desde então), uma linha
`approvals:` com o estado das regras de permissão do cliente, specs vivas,
cada entrega aberta com seu status derivado, dono, ticket (com seu link, veja
[tickets](../teams.md#tickets)), lead time (`open 5h`, ou `accepted after 5h`
quando seu resultado já foi aceito), aprovações registradas com seu canal e
próxima ação, um aviso acima de `max_age_hours`, avisos de sobreposição,
iniciativas com progresso, slugs entregues com seu lead time, uma linha
`trust:` quando `config.yaml` define `trust: required`, e um aviso quando
`origin/HEAD` nomeia um branch de integração que não é main nem master e
`teams.json` não declara nenhum, porque um checkout de CI não o encontraria:
o aviso pede para declará-lo em `teams.json`, e na política de confiança
quando uma julga o merge (veja [quando a main
avança](../teams.md#quando-a-main-avanca)). Com um slug: o mesmo
relatório que `check`, seguido do ticket, das aprovações registradas com seu
canal, como o status do projeto as mostra, de `review N of M` quando
`atipspec review` já escreveu um pacote, e da próxima ação.

`--format json` imprime o mesmo estado como dados (`schema: 1`): cada entrega
aberta com seu slug, título, tipo, estado, o código de saída que `check`
daria, dono, ticket e `ticket_url`, tarefas, lead time, aprovações
registradas e próxima ação, as iniciativas, cada entrega arquivada com seu
dono, ticket e se seu recibo registra um resultado aceito, e
`integration_warning` (esse aviso, ou `null`); com um slug, a
entrada dessa entrega e suas verificações. `--format markdown` imprime as
entregas como tabelas (Delivery, Ticket, Owner, State, Next), para um pull
request ou um resumo de job. `status` sempre sai com 0; `check` e
`merge-check` são os portões.

### `atipspec audit`

```text
atipspec audit
```

Verifica todo o repositório contra as regras do contrato (dependências
sempre), a validade de cada spec viva e decisão, os tamanhos dos documentos
contra seus limites, sobreposições entre entregas abertas e os roadmaps das
iniciativas. Falha enquanto `.atipspec/framework/` não for o que a versão
instalada instala (um arquivo alterado, ausente, ou adicionado e não ignorado
pelo git): cada fase imprime ao agente essas regras e esses workflows, e
nenhuma aprovação de uma entrega os cobre, então
`atipspec install --update` os restaura. Avisa quando a aceitação do contrato não está registrada ou está
desatualizada, quando as regras de permissão do Claude Code estão ausentes ou
incompletas, nomeando as que faltam, e, como `status`, quando `origin/HEAD`
nomeia um branch de
integração que não é main nem master e `teams.json` não declara nenhum, e
aponta um `strict_scope: false` ou `strict_criteria: false`
mantido de um projeto mais antigo. Sai com 1 em caso de erros.

### `atipspec curate`

```text
atipspec curate
```

Regenera o bloco de índice de `overview.md`, relata os tamanhos dos
documentos contra seus limites e imprime o workflow do curate, que reescreve
a prosa (veja [curate](../flow/curate.md)).

## Entrega guiada

Os comandos de uma entrega na ordem em que o [fluxo
guiado](../flow/guided.md) os usa. Os comandos de fase (`spec`, `plan`,
`build`, e `explore` e `fix` mais abaixo) verificam o que a fase exige e
saem com 1 com uma linha nomeando a etapa faltante; caso contrário, imprimem
`Phase <name>: <title> (<slug>)`, o status derivado, o workflow da fase a
partir de `.atipspec/framework/workflows/`, as regras compartilhadas e a
saída de `atipspec context`. `--no-context` deixa o contexto de fora, para
reentrar em uma fase na mesma sessão. Veja [o que cada fase
exige](../flow/index.md#o-que-cada-fase-exige).

### `atipspec new`

```text
atipspec new SLUG --title TITLE [--capability NAME] [--impact NAME]...
                  [--owner WHO] [--ticket TICKET] [--initiative SLUG]
                  [--depends-on SLUG]... [--kind feature|fix]
                  [--branch | --worktree] [--branch-name NAME] [--reuse-branch]
```

Cria uma entrega guiada em `deliveries/SLUG/`: `spec.md` (`schema: 2`,
`status: draft`, `base` com o id completo do commit atual, `created`,
`change_id`, `requirements: []`, `risk: normal`), `plan.md`, `deferred.md` e
`baseline.json`, que registra esse commit. `check` e a proposta comparam a
spec viva da capacidade com a que esse commit tem, então `new` recusa enquanto
`specs/<capability>.md` tem mudanças sem commit: descarte-as ou, para fazê-las
na entrega, guarde-as à parte e escreva-as de novo quando `new` terminar; com
um commit próprio, fora de uma entrega, `merge-check` as bloqueia. O `spec.md` de uma feature tem `## Intent`, `## Out of scope` e `## Quality attributes`, as
duas últimas com `- None`; seus requisitos vão para `specs/<capability>.md`
(veja [artefatos](artifacts.md#specmd)). `--capability` nomeia essa spec viva
e tem o slug como padrão; `--impact` lista outras specs vivas ou seções do
contrato que a entrega toca. `--kind fix` cria um reparo de defeito guiado:
um `spec.md` com `## Defect` a preencher e `requirements` a apontar para o
requisito aceito que ele corrige na spec viva de `--capability`, um plano de
uma única tarefa cuja `## Final verification` lista os comandos obrigatórios
do contrato e um espaço reservado para o do teste de regressão, e
`atipspec fix` como sua fase (veja [fix](../flow/fix.md)).

`--owner` nomeia quem é o dono (obrigatório quando `teams.json` lista donos
para a capacidade). `--ticket` aceita uma chave como `PROJ-123`, um número de
issue como `#42`, ou uma URL https, e recusa qualquer outra coisa (veja
[tickets](../teams.md#tickets)). `--initiative` registra a entrega nesse
roadmap. `--depends-on` nomeia uma entrega cujo recibo aceito deve estar no
arquivamento antes que o check desta fique verde. `--branch` cria e muda para
`delivery/SLUG`; `--worktree` cria esse branch em `../<repo>-SLUG` e escreve a
entrega lá. `--branch-name` usa outro nome de branch com qualquer um dos
dois, e `--reuse-branch` muda para esse branch local existente em vez de
criá-lo; ambos precisam de `--branch` ou `--worktree`, e `--reuse-branch`
precisa de `--branch-name`.

Com `system` em `config.yaml`, `new` fixa o `contract.md` do repositório de
sistema, e seu `glossary.md` quando ele tem um, no `contracts.json` da
entrega, e imprime cada fixação; quando esse checkout não está disponível,
avisa e nomeia o comando `contract-pin` de que a proposta então precisa.
Recusa um slug existente e o slug `contract`, reservado para
`proposal contract` e `accept contract`.

### `atipspec spec`

```text
atipspec spec SLUG [--no-context]
```

Abre a fase spec: a entrevista, os requisitos e cenários na spec viva, e a
intenção da entrega. Recusa para uma entrega de fix (use `atipspec fix`), e
para uma entrega antiga enquanto a aceitação do contrato não estiver
registrada para seu conteúdo atual. Uma entrega guiada não precisa de mais
nada; `check` avisa enquanto o contrato não estiver aceito. Veja
[spec](../flow/spec.md).

### `atipspec ids`

```text
atipspec ids CAPABILITY [--legacy]
```

Imprime um prefixo de ID de requisito e de critério para uma entrega, como
`REQ-PRICING-7KQ2M-001` e `AC-PRICING-7KQ2M-001`: um token aleatório de cinco
caracteres que nenhum ID visível neste checkout usa (a spec viva, todas as
entregas e o arquivamento, e a spec viva em cada ref que `teams.json` lista),
e pede para numerar com ele os demais requisitos e critérios da entrega,
`-002`, `-003`. O assistente o executa uma vez por entrega. Dois branches que
sortearam o mesmo token antes que algum deles fosse publicado obtêm IDs
duplicados, que `check` reporta. IDs mais longos de versões anteriores
continuam válidos. `--legacy` imprime os próximos IDs numéricos a partir do
histórico local, o que não é seguro para trabalho concorrente (veja
[entregas antigas](legacy.md#ids)).

### `atipspec spec-bind`

```text
atipspec spec-bind SLUG --file PATH
```

Instala requisitos na spec viva da entrega guiada, `specs/<capability>.md`,
mantendo os demais que estão ali, lista seus IDs sob `requirements` em
`spec.md` e o devolve a draft; não aprova nada. Um documento com IDs de
requisito é vinculado como está. Um sem eles é importado quando tem uma
seção `Acceptance Criteria`: seu título vira um requisito e cada item
numerado ou com marcador, um de seus critérios, um cenário quando o item tem
passos `**When**` e `**Then**`. Os IDs importados são curtos e derivados da
capacidade e do título, de modo que importar o mesmo documento de novo dá os
mesmos IDs; um documento que já nomeie um requisito com outro título na spec
viva é recusado. O original é guardado em `sources/<sha256>.md` da entrega,
listado sob `sources` em `spec.md`, e `## Import review notes` em `spec.md`
lista o que a pessoa verifica antes de aprovar. Um documento em qualquer
outra forma é recusado, sem nada escrito. Uma remoção nunca é inferida de uma
importação. Recusa uma entrega antiga.

### `atipspec plan`

```text
atipspec plan SLUG [--no-context]
```

Abre a fase plan: abordagem, escopo, tarefas e verificação final. Uma entrega
guiada pode planejar antes de sua aprovação, assim que seus cenários
estiverem completos sem um achado de especificação bloqueante, sua intenção
estiver declarada, suas seções de fora do escopo e de qualidade estiverem
decididas (para um fix, seu defeito declarado e listados os requisitos que
ele corrige) e nenhuma pergunta estiver aberta. Uma entrega antiga precisa da
spec aceita para seu conteúdo atual. Veja [plan](../flow/plan.md).

### `atipspec proposal`

```text
atipspec proposal SLUG
atipspec proposal contract
```

Apresenta o que a pessoa aprova, com seu código de aprovação.
`proposal SLUG` mostra o escopo, os cenários, a abordagem, os testes e o diff
da especificação de uma entrega, com seu ticket e link, uma linha
`Kind: ... · Risk: ...` que diz o que o nível de risco pede ao portão, para
um fix uma linha `Corrects:` que diz se cada requisito que ele lista é um
requisito aceito, uma linha `Pinned contracts:` com cada contrato fixado de
outro repositório (nome, repositório, commit e caminho), uma linha
`Capability decisions` com as decisões aceitas sobre uma capacidade que
`context` e o pacote de revisão carregam (são marcadas aceitas na conversa,
sem código nem registro); o diff da especificação deixa de fora os
requisitos que o branch de integração trouxe (veja [quando a main
avança](../teams.md#quando-a-main-avanca)). Para
uma entrega antiga, incluído um fix criado antes da 0.3.0, a aprovação ainda
pendente (a spec; a spec e o plano juntos como uma só proposta quando uma
feature tem os dois prontos; ou o plano), ou que nenhuma está pendente (o
plano de um fix antigo, um plano com `approve_plan: false` ou um já aceito).
`proposal contract` mostra o contrato, suas regras, os achados do audit e as
decisões cujo `affects` nomeia `contract`, `contract:<section>` ou `*`, ou
está vazio (uma cujo Context ou Decision continua como no template não está
pronta para aprovação), e nomeia as aprovações atuais de entregas que registrá-lo
deixaria desatualizadas, porque as linhas de status que ele escreve entram no
hash delas. O código e o comando `accept` exato só aparecem quando `accept`
registraria esse conteúdo; caso contrário, a visão lista o que falta sob
"Not ready for approval". Abaixo deles, a visão de uma entrega diz com que
rigor os critérios são verificados (`Criteria check: strict` ou
`warnings only`, observando quando `criteria_syntax: free` desliga a
verificação de forma), o que a evidência e a revisão precisam
(`Evidence check:` com `require_proof` ou `risk: high` e se a revisão deve
vir de uma sessão isolada), uma linha `Policy changes since the base commit`
com cada política que `config.yaml` muda desde a base da entrega, e lista os
avisos da spec, do plano (como seu tamanho frente a `max_tasks`) e do
contrato (como uma aceitação que não está vigente) que o modelo resolve ou
nomeia ao apresentar. Apresentar não concede nada; com
`trust: required`, não mostra nenhum código local.

### `atipspec accept`

```text
atipspec accept SLUG proposal [--code CODE] [--by WHO]
atipspec accept SLUG result [--code CODE] [--by WHO]
atipspec accept SLUG spec [--code CODE] [--by WHO]     legacy deliveries
atipspec accept SLUG plan [--code CODE] [--by WHO]     legacy deliveries
atipspec accept contract [--code CODE] [--by WHO]
```

A pessoa aprova na conversa; o assistente então executa este comando com o
código do conteúdo que apresentou. O código é `XXXX-XXXX`: os primeiros 40
bits do sha256 do conteúdo em base32 de Crockford (dígitos e letras sem I, L,
O e U). A digitação ignora maiúsculas e minúsculas, espaços e o hífen, e lê
O, I e L como 0, 1 e 1. Quando o código não nomeia o conteúdo atual, o
comando não registra nada e diz que o conteúdo mudou, sem revelar o código
atual. Sem uma fase para uma entrega, recusa e nomeia as formas.

Em um terminal interativo sem marcador de agente no ambiente, a CLI sempre
pede para digitar o código no seu prompt; quando `--code` também é
informado, os dois devem coincidir. Em qualquer outro lugar, `--code` é
obrigatório. O registro informa o canal:

| Canal | Quando |
| --- | --- |
| `terminal` | o código foi digitado no prompt da CLI em um terminal interativo, sem marcador de agente |
| `client-permission` | o Claude Code é o único marcador de agente (`CLAUDECODE`, ou `AI_AGENT` nomeando o Claude Code), fora do Agent SDK e de `claude -p` (`CLAUDE_CODE_ENTRYPOINT` diferente de `sdk-*`), o interpretador recebeu a linha de comando à qual sua regra de ask corresponde (o `atipspec accept` instalado ou `python -m atipspec accept`), `.claude/settings.json` mantém intactas as regras do AtipSpec, e nenhum hook de `.claude/settings.json` nem de `.claude/settings.local.json` pode responder à pergunta para Bash, de modo que o Claude Code, em uma sessão aberta na raiz do projeto, pergunta à pessoa primeiro |
| `assistant` | qualquer outra coisa: um agente sem essas regras, regras alteradas, um cliente sem mecanismo de permissão, o marcador de outro agente ao lado do marcador do Claude Code (o Claude Code passa seu marcador para os agentes que inicia), o Claude Code executado pelo Agent SDK ou por `claude -p`, `python -m atipspec.cli`, `python -m atipspec.__main__` ou `python -c`, a CI. Registrado, com um aviso |

O canal é o que o próprio processo do comando declara, não uma prova de
quem aprovou; a CLI vê apenas esse processo:

- `client-permission` diz que as regras estão neste projeto, não que a
  sessão as carregou nem que a CLI viu a pessoa confirmar. O Claude Code só
  as lê em uma sessão aberta na raiz do projeto, a pasta que contém
  `.claude/settings.json`: uma sessão aberta em uma pasta pai ou em outro
  repositório que entra no projeto com `cd`, como fazem algumas sessões de
  workflows e de subagentes, não pergunta e mesmo assim registra
  `client-permission`. O mesmo vale para um script ou programa que o Claude
  Code inicia e que executa `atipspec accept` por conta própria, incluindo
  um agente que não define nenhum dos marcadores, embora a regra do Claude
  Code tenha perguntado apenas sobre o script. Depois de registrá-lo,
  `accept` imprime uma nota com a raiz.
- `terminal` diz que o código foi digitado em um terminal sem marcadores de
  agente. Um agente pode remover seus marcadores e responder ao prompt a
  partir de um pseudoterminal que ele cria, então este canal não é mais
  forte que os outros.
- Um registro escrito à mão em `approvals/` é lido como um que a CLI
  escreveu.

Os marcadores de agente (`CLAUDECODE`, `CODEX_SANDBOX`, `CODEX_THREAD_ID`,
`COPILOT_CLI`, `CURSOR_AGENT`, `GEMINI_CLI`, `AI_AGENT`) só rebaixam o canal.
Só uma política de confiança externa (`trust: required`) autentica quem
aprovou.

O que cada forma faz:

- `proposal` valida cenários, plano, contrato, base e coordenação e recusa
  perguntas abertas; define `status: ready` e escreve
  `approvals/local-proposal.json` (entregas antigas: também
  `local-spec.json` e `local-plan.json`, com o código de uma visão que
  apresentou a proposta, não a spec ou o plano sozinhos).
- `result` exige um check local verde e nenhuma política de confiança, e
  escreve `approvals/local-result.json`; `deliver` o exige quando não há
  política.
- `spec` recusa em entregas guiadas, e enquanto um requisito não tiver
  critério ou uma pergunta estiver aberta; caso contrário, define
  `status: ready` e registra o hash de `spec.md` e do contrato.
- `plan` recusa em entregas guiadas; exige uma spec aceita e um plano sem
  erros, e registra o hash da spec, do plano e do contrato.
- `contract` valida as regras, define `status: accepted` em `contract.md` e
  em cada decisão que `proposal contract` listou, e escreve
  `.atipspec/approvals/contract.json` com seus hashes. As aprovações de
  entregas que incluíram no hash as linhas de status anteriores ficam
  desatualizadas; ele as nomeia.

Com `trust: required` em `config.yaml`, toda forma exceto `contract` recusa:
a aceitação local fica desativada e os aprovadores assinam com
`atipspec approve`.

`--by` é um rótulo declarado que usa por padrão o `user.email` do git; o
assistente só o passa com o nome que o usuário deu. Os registros armazenam o
hash e seu `subject_version`, o digest de cada parte, o código, quem, quando,
o commit e o canal.

`check` compara o hash registrado com os arquivos: depois de qualquer edição,
a entrega volta a ser draft (ou o plano fica não aceito), com uma pendência
que nomeia os arquivos, ou os requisitos da spec viva, que mudaram, até que a
pessoa aprove o conteúdo alterado e ele seja registrado de novo. Incorporar o
branch de integração não é uma edição desse tipo (veja [quando a main
avança](../teams.md#quando-a-main-avanca)). Com uma política de confiança, as
aprovações assinadas prevalecem e esses registros são ignorados.
`approval-subject` imprime o digest que os modos de confiança assinam; não é
um código de aprovação local.

### `atipspec build`

```text
atipspec build SLUG [--no-context]
```

Abre a fase build e nomeia a próxima tarefa: a primeira não registrada com
`task-done` (ou, em uma entrega antiga, sem um marcador de commit), ou diz
que todas as tarefas estão completas. Uma entrega guiada precisa da proposta
aceita para seu conteúdo atual; uma antiga, de um plano com tarefas, aceito
quando `approve_plan` está ativo. Recusa enquanto o plano, a spec, a base, a
definição do contrato ou a coordenação com outras entregas tiver um erro ou
uma etapa pendente; um arquivo que viola uma regra do contrato é o que o
build corrige, então não recusa por isso. Veja [build](../flow/build.md).

### `atipspec task-done`

```text
atipspec task-done SLUG TASK --note TEXT
```

Registra que uma tarefa do plano está implementada, com a nota: o que mudou.
Escreve `progress.json` na pasta da entrega, com a hora, o hash do acordo
aprovado e o da tarefa sem seu título, e imprime a próxima ação. Recusa antes
da aprovação, ou enquanto o plano, a spec, a definição do contrato, a base ou
a coordenação tiver um erro, para uma tarefa desconhecida e para uma nota
vazia. Um registro é progresso, não verificação: `verify` e a revisão
verificam o trabalho. Ele continua válido enquanto o acordo aprovado e a
tarefa, exceto seu título, permanecerem inalterados. Nenhum commit é
necessário.

### `atipspec verify`

```text
atipspec verify SLUG [--task Tn]... [--timeout SECONDS]
                [--policy PATH] [--policy-sha256 HASH] [--number N]
```

Executa, a partir da raiz do projeto e através do shell, os comandos da
`## Final verification` do plano uma vez para o candidato finalizado, ou, em
um plano sem ela, os comandos Verify de cada tarefa; `--task` executa apenas
os comandos próprios das tarefas nomeadas, uma verificação de
desenvolvimento. Imprime a cauda da saída de cada comando e escreve
`evidence/<task or FINAL>-<time>.json` com os comandos, os códigos de saída,
os logs completos da saída e a impressão digital da árvore de trabalho.
`--timeout` limita cada comando (padrão de 1800 segundos). Sai com 1 quando um
comando falha ou os comandos alteraram a árvore, o que torna essa evidência
desatualizada na hora. Requer git. Sem uma política, não precisa de
aprovação; execute-o no candidato finalizado, depois da aprovação da
proposta.

Com um `Report:`, o caminho deve ser um que o git ignore, como
`.atipspec/tmp/junit.xml`. `verify` apaga esse arquivo antes de os comandos
rodarem e o lê depois: um relatório ausente (`test report not found`) ou um
modificado antes da exclusão (`predates this verification`, com dois
segundos de tolerância) reprova a evidência, assim como um teste que falhou
nele. A evidência registra a cópia do relatório com `fresh: true`.

Com `--policy` (ou `ATIPSPEC_TRUST_POLICY`), primeiro exige a spec pronta e
suas aprovações confiáveis de spec e de plano, e quem o executa é o produtor
protegido (veja [aceitação confiável](#aceitacao-confiavel)).

### `atipspec review`

```text
atipspec review SLUG [--out FILE]
```

Recusa, sem escrever nada, enquanto uma tarefa não estiver completa, a
evidência estiver ausente ou desatualizada, ou o contrato for violado. Caso
contrário, conta a revisão e escreve o pacote do revisor em
`.atipspec/tmp/SLUG-review-packet.md` (ou em `--out`): rubrica, contrato, as
specs vivas na lista de impact, as decisões aceitas que as afetam, spec,
plano, deferred, resumo da evidência, arquivos fora do `scope` do plano, o
diff contra a base (limitado a 200 KB, com `--stat` quando truncado) e
arquivos não rastreados; depois imprime `review N of M` e o workflow de
review. Uma revisão é contada cada vez que o pacote é de um candidato
diferente do candidato do pacote anterior, contando a primeira, diga o que
disser `review.md`: uma revisão que passou também conta, já que a CLI não
consegue distinguir os vereditos de um revisor de vereditos editados depois.
Quando as `review_rounds` revisões já foram contadas para o acordo aprovado atual e o
candidato mudou de novo, recusa, sem contar nada, e pede para apresentar
`atipspec check SLUG` ao usuário: mudar a proposta, aumentar `review_rounds`
ou parar; `check` o reporta como erro até lá. Um pacote que não pode ser
montado não conta nada. `check` considera apenas a revisão do último pacote
contado: um `review.md` escrito sem executar `review` fica esperando por ele.
A contagem fica em `review-rounds.json`, que a CLI escreve a partir de
`accept <slug> proposal`; sem ele, `review` recusa em uma entrega guiada
criada desde a 0.3.0, conta de novo a partir do `review.md` na pasta, como
primeira revisão, em uma aprovada sob uma política de confiança, e começa no
próximo pacote em uma criada antes da 0.3.0, cujo `review.md` nomeia uma
árvore da impressão digital anterior. O diff mostra o conteúdo
armazenado: sem filtro textconv, e um arquivo de texto que um atributo local
marca como binário, ou texto UTF-8 com um byte NUL, é mostrado como texto,
cada NUL como `␀`; um byte que não é UTF-8 aparece como `�`. Um revisor em
uma sessão isolada lê o pacote e escreve `review.md` (veja
[review](../flow/review.md)).

### `atipspec check`

```text
atipspec check SLUG [--json] [--policy PATH] [--policy-sha256 HASH] [--number N]
```

O portão. Sai com 0 quando verde, 1 com erros, 2 incompleto. Veja [como
funciona](../getting-started/how-it-works.md#o-portao) para os níveis.
Imprime o status derivado, cada achado e a próxima ação; `--json` imprime o
mesmo relatório como dados. Falha fechado: sem git é um erro (o commit base,
as regras do contrato e a atualidade da evidência vêm do git), e com
`trust: required` e sem política também é um erro, assim como um
`.atipspec/framework/` que não é o que a versão instalada instala (veja
[`audit`](#atipspec-audit)), que bloqueia a proposta, as tarefas, o build e
a revisão até `atipspec install --update`. Nunca executa os testes:
julga a evidência que `verify` escreveu e a revisão que o revisor escreveu.
Um veredito PASS precisa de um ponteiro que ele consiga resolver, e
`review.md` precisa de `reviewer:` e declara sua `session:` (veja
[review](../flow/review.md#o-que-o-portao-verifica-em-reviewmd)). O nível de
`risk` no `spec.md` de uma entrega muda o que ele pede (veja
[risco](../flow/spec.md#risco)). Mostra o lead time da entrega, de sua
criação até a aceitação de seu resultado, e avisa, sem bloquear, quando ele
passa de `max_age_hours`. Em uma entrega guiada em draft também lista o que
ainda falta à proposta no plano e no contrato, e seus avisos; quando não falta
nada, seu único todo é apresentar a proposta para aprovação. Sem uma política, verde é `checked`, e `accepted`
quando a aceitação do resultado atual está registrada; com `--policy`, o
verde do portão confiável é `verified`.

### `atipspec report`

```text
atipspec report SLUG [--format json|markdown|html] [--out FILE]
                [--policy PATH] [--policy-sha256 HASH] [--number N]
```

O dossiê de aceitação que o assistente apresenta para a aceitação do
resultado: status, o código de aprovação do resultado enquanto a entrega está
`checked` e nenhuma política está definida, o tipo, o risco e o lead time, a
matriz de rastreabilidade com cada veredito e aquilo a que seu ponteiro foi
resolvido, o revisor e a sessão da revisão (com um aviso quando
compartilhada), `Revisão N de M` depois que `atipspec review` contou uma
revisão, aprovações, verificações, evidência, e as mudanças desde o commit
base: todo arquivo alterado exceto a própria pasta da entrega, com seu
status, as linhas adicionadas e removidas e se está fora do `scope` do plano,
e o diff desses arquivos, incluídos `config.yaml`, o contrato e as decisões,
como armazenados, igual ao do pacote. Compara a base com a árvore candidata à
qual a evidência, a revisão e a aceitação do resultado estão vinculadas,
incluídos os arquivos não rastreados. Um arquivo listado como `binary` não
tem texto no diff, e o dossiê nomeia os arquivos binários que o candidato
adiciona ou altera: inspecione-os no repositório antes de aceitar. Também
nomeia, como o pacote de revisão, os arquivos alterados que configuram como
os testes rodam e informam (`conftest.py`, `pytest.ini`, `pyproject.toml`,
`package.json`, `jest.config.*` e similares), cuja mudança pode alterar o que
a evidência diz. Os formatos JSON e HTML mantêm até 200 KB de diff, o markdown (o padrão) até
50 KB; um diff mais longo é cortado, com seu tamanho completo e sha256 e a
base a partir da qual inspecionar o resto. O recibo arquivado guarda os
arquivos e o tamanho e o sha256 do diff, não seu texto. `--out` escreve fora
do repositório, sob `.atipspec/tmp/` ou em `reports/` da entrega, de modo que
uma exportação não altera nada que a aceitação vincula. O relatório de uma
entrega arquivada lê seu recibo. Com `--policy`, mostra as aprovações
confiáveis que o QA assina.

### `atipspec deliver`

```text
atipspec deliver SLUG [--policy PATH] [--policy-sha256 HASH] [--number N]
```

Exige um check verde e a aceitação humana do resultado atual: sem uma
política, o registro que `accept SLUG result` escreve; com uma, um check
confiável verde com evidência e aprovações autenticadas. Mescla os requisitos
na spec viva da capacidade por ID, escreve o recibo `reports/acceptance.json`
com `code_tree`, o hash de tudo o que está fora de `.atipspec/`,
`living_spec`, o digest da spec viva que escreveu, e `living_requirements`, o
texto de cada requisito que lista como escrito ali, define
`status: delivered`, move a pasta para `archive/` e nomeia `merge-check` como
o passo anterior ao merge. Não faz commit, push nem merge.

### `atipspec merge-check`

```text
atipspec merge-check --base REF [--format text|markdown] [--policy PATH] [--policy-sha256 HASH] [--number N]
```

O portão de um branch antes do seu merge em `REF` (um branch ou commit, como
`origin/main`), executado pelo assistente antes de pedir o merge e pelo job
de CI do pull request. Encontra as entregas que o branch altera desde sua
base de merge com `REF`, nas pastas de `deliveries/` e `archive/` cujo nome
é um slug, lista cada uma com seu estado e ticket (uma tabela em Markdown,
com o link do ticket) e bloqueia quando:

- uma entrega aberta não está `accepted` (localmente) ou `verified` (com uma
  política);
- uma entrega arquivada no branch tem um recibo sem resultado aceito ou sem
  `code_tree` (entregue antes da 0.3.0), ou seu `code_tree` difere do código
  no head: qualquer mudança fora de `.atipspec/` depois de `deliver`, inclusive
  trazer o branch de destino (merge ou rebase). Nomeia os arquivos alterados
  quando a árvore aceita ou o commit de arquivamento está disponível, e diz
  como seguir: reabrir a entrega revertendo o commit que a arquivou, e
  verificá-la, revisá-la, aceitá-la e entregá-la de novo (reverter os arquivos
  só serve para uma mudança do próprio branch), e trazer o branch de destino
  antes de `deliver` da próxima vez. Localmente também bloqueia um recibo que mudou depois do
  commit que o arquivou; um removido e adicionado de novo, a menos que o
  commit anterior tenha a entrega aberta, como depois de reverter o commit de
  arquivamento para reabri-la, ou que um arquivamento anterior tenha
  adicionado esse mesmo recibo; e um cujo `code_tree` nem o commit de
  arquivamento nem o anterior contêm. Assim, reescrever `code_tree` depois de
  uma mudança do código aparece, mas um recibo não é autenticado: um
  histórico reescrito de forma coerente, ou uma reabertura feita à mão (sua
  pasta em `archive/` removida e a entrega restaurada em um commit, e depois
  arquivada de novo com um recibo escrito à mão), ainda passa; só uma política de
  confiança verifica a entrega de novo;
- o branch altera ou remove uma entrega arquivada antes dele;
- o branch altera uma spec viva em `specs/` por outro caminho que não
  `deliver` (o `living_spec` do recibo; com uma política, o que `deliver`
  escreve a partir do commit de onde foi entregue) ou a proposta aprovada de
  uma entrega guiada aberta. Também compara cada requisito: o head o mantém
  como a base de merge o tinha, como a última entrega arquivada no branch que
  o lista o escreveu (o texto que o `living_requirements` do seu recibo
  registra, tal como o commit que a arquivou o adicionou; com uma política, o
  que `deliver` escreve a partir do commit de onde foi entregue, e só de uma
  entrega que a política autentica), ou como uma
  entrega guiada aberta o lista, de modo que um recibo não responde por um
  requisito que sua entrega não listou, nem por uma edição posterior de um que
  ela listou, nem por uma edição posterior do recibo;
- um fix guiado arquivado no branch, ou aberto nele, lista um requisito que a
  spec viva não continha na base de merge e que nenhuma entrega anterior do
  branch escreveu: um fix corrige um requisito aceito;
- o branch altera o contrato, ou uma decisão que o afeta, e a aceitação do
  contrato não está atual; com uma política, o branch altera `contract.md` ou
  uma decisão desse tipo fora de uma entrega verificada sob a política
  (`contract.md` com uma nova decisão que afeta o contrato, aprovada pela
  engenharia), ou aceita um contrato em draft com o qual nenhuma entrega
  desse tipo foi verificada;
- o branch altera um arquivo fora de `.atipspec/` que nenhuma entrega que ele
  arquiva ou deixa aberta cobre e que `exempt_paths` não cobre. Uma entrega
  cobre os arquivos que seu dossiê mostra: os que mudaram entre seu commit
  base e o head, e os que o branch de integração alterou e o branch tem de
  outra forma, inclusive devolvidos a como a base os tinha (veja [quando a
  main avança](../teams.md#quando-a-main-avanca)), exceto os que o branch já
  tinha alterado antes dessa base. O dossiê de uma entrega aberta é o do
  head, que a aceitação do seu resultado vincula: quando a entrega devolve o
  que o branch de integração alterou, essa aceitação nomeia a base de merge,
  então integrar o branch de novo a anula. O de uma entrega arquivada é o que
  ela tinha ao ser entregue, como o seu recibo o lista (com uma política, como
  estava no commit a partir do qual foi entregue), menos os arquivos que o
  branch de destino alterou depois do commit que a arquivou, cuja mudança o
  branch desfaz. O código commitado antes de `atipspec new`,
  ou alterado em um arquivo que a entrega altera de novo, fica fora, assim
  como uma mudança de um branch de destino que não é o de integração, ou de
  qualquer branch sem ref de integração, que o branch devolve a como a base a
  tinha, e todo código de um branch que não toca nenhuma entrega ou só remove
  alguma. Uma entrega arquivada no branch cujo commit base não está no
  histórico de `HEAD`, como em um clone raso ou após um squash ou um rebase
  do branch, também bloqueia: sem ele, o `merge-check` não consegue saber
  quais arquivos a entrega cobre, e diz que não procurou código fora das
  entregas. `exempt_paths`,
  uma lista de globs, é lido do `config.yaml` em `REF`, nunca do branch, de
  modo que um branch não pode isentar as próprias mudanças: a pessoa decide
  quais arquivos não precisam de entrega e adiciona os globs antes no branch
  de destino. Não contam os arquivos do cliente que só contêm o que o
  AtipSpec instala, como uma skill desta versão ou um `.claude/settings.json`
  ao qual só foram adicionadas suas regras;
- a árvore de trabalho difere de `HEAD`: ele julga o head commitado;
- `.atipspec/framework/` não é o que a versão do AtipSpec que executa
  `merge-check` instala (veja [`audit`](#atipspec-audit));
- `.atipspec/` não está na raiz do repositório git;
- `trust: required` está definido no head, em `REF` ou na base de merge e
  nenhuma política é fornecida. Com uma política, com ou sem
  `trust: required`, um recibo aceito localmente bloqueia, assim como um
  recibo confiável cuja entrega não passa de novo em seu check confiável: no
  commit anterior ao commit de arquivamento, em um checkout de um clone
  temporário com as refs do repositório e a evidência, a revisão, os termos
  de adiamento e as aprovações arquivados com ela, o check deve ser
  `verified` (aprovações e evidência atestada; no modo provider, as revisões
  do pull request sobre esse commit, ou sobre o head com as mesmas linhas de
  marcador, lidas com `--number`), e esse commit deve conter o código do
  head. Faça o commit do arquivamento sozinho, logo depois de `deliver`.

A linha de cada entrega entregue ou aceita nomeia o canal que `accept`
declarou para cada aprovação local: como o comando rodou, não quem aprovou.
Um branch que não toca nenhuma entrega está pronto, a menos que altere uma
spec viva, o contrato ou um arquivo fora de `.atipspec/` que `exempt_paths`
não cobre; o resultado lista os arquivos que `exempt_paths` deixou passar, e
avisa quando o branch altera `exempt_paths`, que nenhuma aprovação inclui no
hash. Também avisa, sem bloquear, quando o branch relaxa em relação a `REF`
uma política do `config.yaml` entre `strict_scope`, `strict_criteria`,
`criteria_syntax`, `review_rounds`, `max_tasks`, `max_requirements`,
`max_age_hours`, `require_proof`, `require_isolated_review` e `trust`, listada como a proposta lista suas
mudanças de políticas, por exemplo `review_rounds 3 → 99`, porque toda
entrega iniciada depois do merge as herda e nenhuma proposta as lista; e
quando adiciona, altera ou remove `overview.md`, `glossary.md` ou uma
decisão, nomeada com o status de cada decisão, porque o agente as lê como
contexto em cada fase e nenhuma aprovação de uma entrega as cobre; e quando
altera `adapter.json`, que nomeia o programa que `atipspec run` executa e se
suas revisões contam como isoladas, ou `teams.json`. Quando o
branch altera o contrato ou uma decisão que o afeta, o resultado mostra a
aceitação do contrato com o canal que `accept contract` declarou. Não executa nenhum comando do candidato, apenas git
e leituras de arquivos, de modo que um job de pull request o executa sem
credenciais. `--format markdown` imprime o resultado para um resumo de job de
CI. Sai com 0 pronto, 1 bloqueado. Os exemplos de CI de `enterprise-init` o
executam (veja [aceitação
empresarial](../enterprise.md#ci-antes-do-merge)).

### `atipspec ship`

```text
atipspec ship SLUG
```

O guia do modo ship: nomeia a próxima fase em que a entrega pode entrar, por
quê, o ponto de parada que vem a seguir (a aprovação da proposta, ou a da
spec para uma entrega antiga, antes do build; a aceitação do resultado antes
de `deliver`) e o comando a executar. A fase que ele nomeia sempre cumpre
seus próprios pré-requisitos. Veja [modo ship](../flow/index.md#modo-ship).

### `atipspec context`

```text
atipspec context SLUG [--out FILE] [--summary]
                 [--role guide|analyst|designer|tester|implementer|reviewer] [--task Tn]
```

Imprime o material da entrega com um resumo de tamanho contra
`context_budget`: o contrato, a visão geral, o glossário, as specs vivas na
lista de impact, as decisões aceitas que as afetam e os próprios arquivos da
entrega, nunca `archive/`. `--out` o escreve em um arquivo; `--summary`
imprime apenas os tamanhos. `--role` adiciona a instrução desse papel,
ajustada ao `risk` da entrega, como o executor a envia; `--task` limita o
material a essa tarefa e aos requisitos que ela cobre. Os comandos de fase
imprimem sua saída.

## Outras entregas

### `atipspec explore`

```text
atipspec explore SLUG [--no-context]
```

Abre a fase explore para uma entrega que já existe: o modelo escreve um
`brief.md` de uma página com o problema, o que existe, opções e uma
recomendação, e para. Veja [explore](../flow/explore.md).

### `atipspec fix`

```text
atipspec fix SLUG [--no-context]
```

Abre a fase fix de uma entrega criada com `--kind fix`: reproduzir o defeito,
corrigir o requisito aceito que ele quebra com um critério de regressão,
planejar uma tarefa, apresentar a proposta. Recusa em uma entrega que não é
um fix, e em um fix criado antes da 0.3.0 enquanto a aceitação do contrato
não estiver registrada para seu conteúdo atual. Veja [fix](../flow/fix.md).

### `atipspec migrate`

```text
atipspec migrate SLUG [--apply]
```

Mostra, como um diff, como uma entrega antiga se torna uma guiada, e não
escreve nada: seus requisitos passam para `specs/<capability>.md`, `spec.md`
os lista sob `requirements` sem seu cabeçalho vazio `## Requirements`, e
recebe `schema: 2`, `status: draft` e um novo `baseline.json`. `--apply` o
escreve depois de fazer backup dos originais e dos registros de aprovação em
`.atipspec/migrations/<digest>/`. Não é uma aprovação: a entrega volta a
draft e precisa ter sua proposta aprovada. Um fix antigo mantém seu fluxo até
ser entregue: `migrate` o recusa. Veja [entregas antigas](legacy.md).

## Contrato e decisões

### `atipspec contract`

```text
atipspec contract
```

Abre a fase contract: imprime o workflow, as regras e o `contract.md` atual.
Nunca recusa. O assistente então apresenta `atipspec proposal contract` e
registra sua aprovação com `atipspec accept contract --code <code>`. Veja
[contract](../flow/contract.md).

### `atipspec decision`

```text
atipspec decision SLUG --title TITLE [--affects NAME]...
```

Cria `decisions/DEC-nnn-SLUG.md` com status `proposed`. `--affects` recebe
nomes de capacidades, `contract`, `contract:<section>` ou `*`; sem ele, a
decisão afeta tudo. Uma decisão que afeta o contrato, ou tudo, é aceita com o
contrato: `atipspec accept contract` define seu status; nunca o edite à mão.

### `atipspec initiative`

```text
atipspec initiative SLUG --title TITLE
```

Cria `initiatives/SLUG/roadmap.md`; `new --initiative SLUG` lista uma entrega
nele.

## Automação

### `atipspec run`

```text
atipspec run SLUG [--resume] [--retry-interrupted] [--budget SECONDS] [--timeout SECONDS] [--max-rounds N]
```

Executa uma entrega guiada aprovada através do adaptador de processo
configurado e imprime seu estado como JSON; veja [o adaptador de
execução](execution-adapter.md). Precisa da proposta aceita para seu conteúdo
atual; caso contrário, registra `awaiting_approval` e para; nunca aceita
nada. `--budget` limita os segundos decorridos para esta versão aprovada
(padrão de 900), `--timeout` cada chamada ao adaptador ou comando de
verificação (padrão de 300). `--max-rounds` limita as correções automáticas;
tem como padrão `review_rounds` em `config.yaml` menos um, porque cada
correção é revisada de novo, e não pode excedê-lo. As revisões que o executor
pede contam como `atipspec review` as conta, e ele para em `needs_decision` quando elas se esgotam.
`--resume` continua depois que você resolveu uma decisão ou falha reportada;
`--retry-interrupted` tenta de novo depois que você inspecionou uma mutação
de agente interrompida. Sai com 0 quando o estado é `ready_for_acceptance` ou
`accepted`, e com 2 para qualquer outro estado. Recusa uma entrega antiga e,
com uma política de confiança, selecionada ou exigida. O executor precisa de
um sistema POSIX (Linux, macOS ou WSL) para encerrar os processos de um adaptador; em outros
sistemas, recusa antes de ler a entrega ou escrever qualquer coisa, e a
entrega continua na conversa guiada, que tem as mesmas fases e o mesmo
portão.

### `atipspec adapter`

```text
atipspec adapter
```

Imprime, como JSON, o que o adaptador em `.atipspec/adapter.json` declara e o
que o executor fornece: se a revisão roda isolada, checkpoints, que não é um
serviço em segundo plano, e que as métricas de tokens e de custo não estão
disponíveis. Recusa quando nenhum adaptador está configurado.

## Equipes

### `atipspec team`

```text
atipspec team [--fetch] [--json]
```

O quadro: toda entrega aberta do checkout de trabalho e de cada ref que
`teams.json` lista (um `*` no final pega toda ref que corresponde a ele), com
seu status, dono, ticket, ref, capacidade, requisitos e dependências. Lê
apenas refs locais; sua primeira linha diz quando o repositório fez fetch
pela última vez. `--fetch` primeiro faz fetch de cada remote que uma entrada
`refs/remotes/<remote>/...` nomeia, sem pedir credenciais (git e ssh rodam
sem um terminal nem um programa askpass); um remote que falha recebe um aviso
e o quadro mostra o que foi buscado por último. `--json` imprime o quadro
como dados, com o `ticket_url` de cada ticket. Veja [o
quadro](../teams.md#o-quadro-atipspec-team).

### `atipspec contract-pin`

```text
atipspec contract-pin SLUG NAME --repository NAME --ref REV --path PATH
```

Fixa o arquivo `PATH` do checkout de outro repositório, nomeado em
`repositories` de `teams.json` (`system` tem como padrão `system` em
`config.yaml`), no commit para o qual `REV` resolve, no `contracts.json` da
entrega sob `NAME` com seu digest, e imprime esse commit. O contexto da
entrega lê o arquivo desse commit; `check` recusa uma fixação que nomeia um
branch ou uma tag, ou cujo conteúdo difere de seu digest. `contracts.json`
faz parte do que a aprovação da proposta inclui no hash, então fixar de novo
a anula. Veja [vários repositórios](../teams.md#varios-repositorios).

## Aceitação confiável

Estes comandos servem a uma política de confiança externa (veja [aceitação
empresarial](../enterprise.md)). Pessoas com chaves cadastradas, um worker de
CI protegido e um coletor os executam; o assistente nunca assina. `check`,
`verify`, `report`, `deliver` e `merge-check` recebem a política com:

- `--policy PATH`: o TOML da política de confiança da organização, fora do
  repositório candidato (ou `ATIPSPEC_TRUST_POLICY`);
- `--policy-sha256 HASH`: o digest que a política deve ter, fixado em
  configuração protegida (ou `ATIPSPEC_POLICY_SHA256`);
- `--number N`: o pull request, para uma política no modo provider (ou
  `ATIPSPEC_PR_NUMBER`).

Com uma política, `check` exige as aprovações assinadas e a evidência
atestada, e seu verde é `verified`; `verify` exige as aprovações de spec e de
plano antes de executar; `deliver` exige o portão confiável verde; os
registros locais de `accept` são ignorados. Com `trust: required` em
`config.yaml`, `check`, `accept` (exceto `accept contract`), `deliver` e
`run` se recusam a funcionar sem uma. Nunca derive esses valores de
documentos candidatos.

### `atipspec enterprise-init`

```text
atipspec enterprise-init [--out DIRECTORY]
```

Escreve os exemplos de política de confiança (`policy.example.toml` para o
modo ssh, `policy.provider.example.toml` para o modo provider), os jobs de CI
que executam `merge-check` (`github-local.yml`, `gitlab-local.yml`), os
workflows de evidência do modo provider (`github-evidence-trusted.yml`,
`github-evidence-caller.yml`), um script de aceitação protegido e
`ADOPTION.md` em `DIRECTORY` (padrão `.atipspec/enterprise`). Não ativa nada,
e recusa quando os arquivos já existem ali.

### `atipspec approval-subject`

```text
atipspec approval-subject SLUG PHASE
```

Imprime o marcador que um aprovador coloca em uma revisão de pull request,
`ATIPSPEC-APPROVE <slug> <phase> <subject> <head>`: o digest do conteúdo da
fase e o commit head. Lê a política de `ATIPSPEC_TRUST_POLICY`. Não é um
código de aprovação local.

### `atipspec approve`

```text
atipspec approve SLUG PHASE --identity ID --key PATH --policy PATH
                 [--policy-sha256 HASH] [--expires TIME] [--owner ID]
```

Assina uma aprovação humana a partir de uma identidade cadastrada, na máquina
confiável dessa pessoa. `PHASE` é `spec`, `plan`, `acceptance`,
`decision:DEC-nnn` ou `exception:Fn`. `--key` é a chave privada, fora do
repositório. Exceções exigem `--expires` com um timestamp ISO futuro com fuso
horário. A aprovação da spec confirma o dono da entrega: `--owner` deve ser o
`owner` que `spec.md` declara, e é assinado com ela; é obrigatório para
`spec` e recusado para qualquer outra fase. Esse dono não pode aprovar as
fases posteriores, e uma aprovação de spec que não confirma nenhum dono, ou
que confirma outro, não conta; uma assinada antes da 0.3.0 é assinada de novo
com `--owner`. `approve` recusa um dono que não esteja escrito em letras
ASCII, dígitos, `_`, `.`, `@` e `-`, como as identidades.

### `atipspec sync-approvals`

```text
atipspec sync-approvals SLUG PHASE --number N --identity ID --key PATH --policy PATH
                        [--policy-sha256 HASH] [--expires TIME]
```

Coleta as aprovações humanas do pull request ou merge request `N` que
carregam o marcador `approval-subject` da fase, em modo somente leitura pela
API do GitHub ou do GitLab, e assina o registro normalizado com a identidade
de coletor cadastrada. Uma fase `exception:Fn` precisa de `--expires` com um
timestamp futuro. O portão lê o provedor de novo a cada execução, então uma
revisão revogada falha.

### `atipspec attest`

```text
atipspec attest SLUG --identity ID --key PATH --run-url URL --policy PATH [--policy-sha256 HASH]
```

O coletor protegido assina a evidência de cada tarefa, o registro em
`evidence/` que terminou por último, com a URL da execução de CI. Não
autentica essa execução: o orquestrador verifica o produtor, o head e o
artefato antes de chamá-lo, e antes apaga a evidência que o branch commitou
(`atipspec.verify.clear_evidence`). Recusa evidência cujo relatório de teste
não tem a marca `fresh`.

## Pilotos

### `atipspec pilot`

```text
atipspec pilot init NAME
atipspec pilot record NAME --delivery SLUG --cohort baseline|atipspec --source SOURCE --collector WHO
                      [--lead-hours H] --human-review-minutes M --rework-minutes M
                      --escaped-defects N --criteria-total N --criteria-tested N --observation-days N
atipspec pilot report NAME
```

`pilot init` cria um protocolo vazio de avaliação no mundo real em
`.atipspec/pilots/NAME/`. `pilot record` adiciona uma observação completa e
com fonte; valores desconhecidos não são inseridos como zero. Para a coorte
`atipspec`, `--lead-hours` pode ser omitido: é lido do recibo arquivado da
entrega, ou dos registros arquivados com ela, e a observação o indica em
`lead_hours_origin`; nunca é estimado. A coorte `baseline` precisa dele
medido. `pilot report` compara as coortes registradas, com tamanhos de
amostra, medianas e limitações, e sinaliza janelas de observação desiguais.

## Códigos de saída

| Código | Significado |
| --- | --- |
| 0 | concluído; para `check`, verde; para `merge-check`, pronto; para `run`, `ready_for_acceptance` ou `accepted` |
| 1 | erro; para `check` e `audit`, vermelho; para `merge-check`, bloqueado; para `verify`, um comando falhou ou alterou a árvore |
| 2 | `check`: incompleto, resta trabalho; `run`: qualquer estado exceto `ready_for_acceptance` e `accepted` |
| 130 | cancelado pelo teclado |

## Ambiente

| Variável | Efeito |
| --- | --- |
| `ATIPSPEC_TRUST_POLICY` | seleciona a política de confiança externa para todo comando, como `--policy` |
| `ATIPSPEC_POLICY_SHA256` | o digest que a política deve ter, como `--policy-sha256` |
| `ATIPSPEC_PR_NUMBER` | o pull request no modo provider, como `--number` |
| `GITHUB_TOKEN`, `GITLAB_TOKEN` | tokens somente leitura para os adaptadores de provedor no worker protegido; `verify` os remove dos comandos que executa, junto com toda variável `ATIPSPEC_`, `SSH_AUTH_SOCK`, `GIT_ASKPASS`, os tokens dos jobs de CI (`CI_JOB_TOKEN`, `ACTIONS_RUNTIME_TOKEN`) e o token de solicitação OIDC (`ACTIONS_ID_TOKEN_REQUEST_TOKEN`) |
| `NO_COLOR`, `TERM=dumb` | desligam as cores na saída do terminal |
| marcadores de agente e `CLAUDE_CODE_ENTRYPOINT` | decidem o canal que `accept` registra; veja [ambiente](configuration.md#ambiente) |

Defina as variáveis de confiança na configuração protegida da organização,
nunca a partir de valores que o repositório candidato fornece.
