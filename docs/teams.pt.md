# Equipes e escala

O AtipSpec é construído para projetos que duram meses com várias pessoas e
seus agentes. Duas ideias sustentam tudo: a unidade de atribuição é a
entrega, e o custo de uma requisição é limitado pela entrega, não pelo
projeto.

## Entregas, não tarefas

| Jira | AtipSpec | Unidade de |
| --- | --- | --- |
| Epic | iniciativa | meses de trabalho, várias pessoas |
| Story | entrega | atribuição a uma pessoa, um branch |
| Sub-task | tarefa | uma execução de agente com contexto limpo |

As tarefas dentro de uma entrega compartilham uma spec e um branch e rodam
em sequência. Uma entrega é dimensionada para fechar dentro de um dia de
trabalho: `check` avisa acima de `max_requirements` e `max_tasks`, `status`
mostra o lead time de cada entrega, de sua criação até a aceitação de seu
resultado, e `check`, `status` e o dossiê avisam acima de `max_age_hours` (8
por padrão). Trabalho maior vira várias entregas sob uma iniciativa.
Trabalho que duas pessoas deveriam fazer em paralelo vira duas entregas,
divididas por posse, com a interface entre elas fixada na iniciativa:

```bash
atipspec initiative orders --title "Orders"
atipspec new orders-api    --title "Orders API"    --capability orders    --owner ana  --initiative orders --worktree
atipspec new orders-screen --title "Orders screen" --capability orders-ui --owner luis --initiative orders --worktree --impact orders
```

Criar uma entrega com `--initiative` a lista no roadmap. O roadmap tem uma
seção *Interfaces* para o que os dois lados acordam (o formato de uma API,
um evento, um schema) e o arquivo que é sua fonte da verdade.

```bash
atipspec status
```

```text
- orders-screen [in_progress] tasks 1/3 @luis SHOP-12 (https://example.atlassian.net/browse/SHOP-12), open 1d 3h: Orders screen
    accepted: proposal accepted by luis@example.com at 2026-10-02T09:12:00Z via client-permission (Claude Code) (current)
    next: T2 is not complete: implement it and record `atipspec task-done orders-screen T2 --note <summary>`
initiatives:
- orders 1/2: orders-api delivered; orders-screen in_progress
```

`atipspec status --format json` entrega o mesmo estado a scripts, e
`--format markdown` como tabelas para um pull request ou um resumo de job;
com um slug, a entrada da entrega e suas verificações.

## Uma entrega, um branch, um worktree

```bash
atipspec new orders-api --title "Orders API" --worktree
```

cria o branch `delivery/orders-api` em uma pasta irmã
`../<repo>-orders-api`. Cada pessoa, e cada agente, trabalha na sua própria
árvore; nada é compartilhado até o pull request. `--branch` faz o mesmo na
pasta atual. Uma equipe com seus próprios nomes de branch passa
`--branch-name feature/SHOP-12-orders-api` com qualquer um dos dois, e
`--reuse-branch` com `--branch-name` para começar a entrega em um branch
local que já existe.

Uma entrega que precisa de outra antes a nomeia com `--depends-on`:

```bash
atipspec new orders-screen --title "Orders screen" --capability orders-ui --depends-on orders-api --worktree
```

Até que `orders-api` seja arquivada com um recibo aceito neste checkout,
`check orders-screen` mantém uma pendência
`Waiting for accepted dependency orders-api`, então seu portão não fica
verde e seu resultado não pode ser aceito.

Integrar a main muda a árvore, o que torna a evidência e a revisão
desatualizadas. O portão exige que você verifique e revise de novo depois de
integrar, então não existe "funcionou no meu branch". Integre antes da
verificação final: depois de `deliver`, `merge-check` bloqueia qualquer
mudança no código do branch, integração incluída, até que a entrega seja
reaberta e aceita de novo. Uma entrega por branch mantém isso barato;
entregar outra entrega no mesmo branch também torna as abertas
desatualizadas.

Comece uma entrega a partir de uma main atualizada, e incorpore a main com
um merge apenas quando o branch precisar. O que a main traz não anula a
proposta aprovada, nem conta como mudança da entrega em `check`, no pacote
de revisão e no dossiê, uma vez que o AtipSpec sabe qual branch é a main:
veja [quando a main avança](#quando-a-main-avanca). Um
rebase sobre a main reescreve o branch: quando `new` rodou depois de commits
do próprio branch, ele reescreve o commit a partir do qual a entrega
começou, e `check` então para até que você restaure o histórico de antes do
rebase (`git reflog` o lista) e faça um merge em vez disso.

## Quando a main avança

Várias entregas costumam alterar a mesma capacidade, cada uma em seu branch.
Quando uma é integrada à main e outro branch incorpora a main, a spec viva
da segunda entrega passa a conter também os requisitos da primeira. O
AtipSpec os atribui ao **branch de integração**:

- `integration` em `teams.json`, como `"refs/remotes/origin/main"`;
- sem ele, a primeira de `refs/remotes/origin/HEAD`, que `git clone` define,
  `refs/remotes/origin/main` e `refs/remotes/origin/master` que resolver,
  então um checkout de CI sem `origin/HEAD` encontra o mesmo branch; declare
  `integration` quando a main tem outro nome, porque um checkout de CI não
  tem `origin/HEAD`; `status` e `audit` avisam quando `origin/HEAD` nomeia um
  branch assim e `integration` não está definido;
- sob uma política de confiança, apenas o `integration` da política:
  `teams.json` faz parte do candidato e ali não nomeia nada.

O que a main trouxe é o que mudou entre o commit onde a base da entrega
encontra a main e a base de merge de `HEAD` com a main, como no diff de um
pull request: cada arquivo que a entrega não alterou desde então, e cada
requisito tal como essa base de merge o contém. Não importa se a main
integrou as outras entregas com merge, squash ou rebase. Então:

- A aprovação da proposta continua atual, assim como os registros
  `task-done`: ela inclui no hash os requisitos que a entrega lista, não o
  resto da spec viva. O texto fora dos requisitos, antes do primeiro ou sob
  um cabeçalho entre eles, o frontmatter, e um comentário HTML ou um bloco de
  código cercado num requisito que a entrega não lista não estão em nenhuma
  aprovação: `check` avisa quando eles mudam, em relação ao que a main
  contém onde a main os alterou, e só os cobre a aceitação do resultado, que
  vincula a árvore inteira.
- `check` e o diff da proposta comparam a spec viva com o que a main
  contém, então um requisito que a main trouxe não é mudança da entrega.
  Editá-lo, removê-lo ou devolvê-lo ao que era é: um requisito que a entrega
  altera sem listá-lo é um erro, em todos os níveis de risco, e `merge-check`
  também o bloqueia.
- Os arquivos que a main trouxe não ficam fora do `scope` do plano, e o pacote
  de revisão e o dossiê os listam à parte em vez de no diff. Um arquivo que a
  entrega também altera continua sendo dela, esteja no índice ou não, assim
  como um que ela devolve ao que a base tinha, como um arquivo que a main
  apagou: o pacote de revisão e o dossiê o mostram em relação à base de merge,
  como o diff de um pull request, e `check` avisa quando a entrega desfaz
  nele, no todo ou em parte, o que a main alterou: uma linha que a main
  adicionou e que a entrega tira ou reescreve, ou uma que a main tirou e que a
  entrega volta a pôr onde estava, ou em qualquer lugar se a main não deixou
  nenhuma igual no arquivo.
- A evidência e a revisão ficam desatualizadas, como depois de qualquer
  mudança da árvore: verifique e revise de novo.

Nada é atribuído sem uma ref que resolva, nem quando a main contém a pasta
da própria entrega, como quando ela foi commitada na própria main. O
`merge-check` cobre o que o dossiê mostra, então sem ref, ou quando o pull
request vai para um branch que não é o de integração, como um branch de
release, uma mudança desse branch que o branch devolve ao que a base tinha é
código fora de qualquer entrega. Conta o dossiê que a pessoa aceitou.
Quando uma entrega aberta devolve o que o branch de integração mudou, a
aceitação do seu resultado nomeia a base de merge em relação à qual o seu
dossiê mostra esses arquivos, então integrar esse branch de novo depois a
anula, mesmo mantendo a árvore, como `git merge -s ours` a mantém. Uma
entrega arquivada cobre os arquivos que o seu dossiê mostrava quando foi
entregue, como o seu recibo os lista (sob uma política de confiança, como o
seu dossiê os mostra no commit a partir do qual foi entregue), não o que um
dossiê mostraria no head, nem um arquivo que o branch de destino mudou
depois do commit que a arquivou: ao manter o código entregue, o branch desfaz
essa mudança. O risco aceito: uma mudança que a main fez
fora de uma entrega, como um hotfix,
também conta como trazida, como no diff de um pull request: ela é julgada onde
entrou na main, no seu próprio pull request, cujo `merge-check` bloqueia o
código fora de qualquer entrega, a menos que `exempt_paths` na main o isente. Um arquivo que uma entrega arquivada antes
no mesmo branch alterou, e que a main também alterou, deixa de coincidir com
o que a main contém quando o branch integra a main, então conta como mudança
da entrega aberta, inclusive fora do seu scope: uma entrega por branch evita
isso. No modo local, a ref e os recibos das entregas arquivadas no branch
são arquivos locais que poderiam ser movidos ou escritos, e um recibo escrito
à mão e commitado avaliza os requisitos que sua spec lista, e cobre os
arquivos que lista, como um escrito por `deliver`: isso detecta desvio. Uma política de confiança autentica no
`merge-check`, cuja ref o worker protegido busca: ele verifica de novo cada
entrega arquivada no branch onde ela foi entregue e só toma os requisitos
das que autentica; `check` lê os recibos como foram commitados.

Um merge com conflitos que ainda não foi commitado conta como mudança da
entrega até o commit de merge: a atribuição lê `HEAD`. Duas entregas que
adicionam requisitos à mesma capacidade entram em conflito no git onde ambas
acrescentam no final; mantenha os dois blocos ao resolver.

## Configuração da equipe

`.atipspec/teams.json` é opcional e escrito à mão:

```json
{
  "schema": 1,
  "refs": ["refs/remotes/origin/delivery/*", "refs/heads/release"],
  "owners": {"orders": ["ana"], "orders-ui": ["luis", "marta"]},
  "repositories": {"api": "../shop-api"},
  "integration": "refs/remotes/origin/main",
  "ticket_url": "https://example.atlassian.net/browse/{ticket}"
}
```

| Chave | Significado |
| --- | --- |
| `refs` | nomes completos de refs que o quadro e `check` leem; um `*` no final pega toda ref que corresponde a ele nesse último segmento |
| `owners` | de capacidade para seus donos humanos: uma entrega guiada de uma capacidade com dono precisa de um `owner` em `spec.md` |
| `repositories` | de nome para um checkout local, para `contract-pin`; `system` tem como padrão `system` em `config.yaml` |
| `integration` | o branch de integração, como nome de ref completo; veja [quando a main avança](#quando-a-main-avanca) |
| `ticket_url` | um endereço https com `{ticket}` onde vai a chave do ticket ou o número da issue |

A aprovação de uma proposta guiada inclui no hash apenas os donos da sua
capacidade e `integration`, também sob uma política de confiança; editar as
outras chaves não anula nenhuma aprovação.

## O quadro: `atipspec team`

```bash
atipspec team [--fetch] [--json]
```

lista toda entrega aberta do checkout de trabalho e de cada ref em `refs`:
seu status, dono, ticket, ref, capacidade, requisitos e dependências.
Execute-o antes de tocar em uma capacidade que outros possam estar
alterando. `check` reporta um requisito que duas entregas declaram de forma
diferente. Ele lê apenas refs locais e nunca faz fetch; a primeira linha diz
quando o repositório fez fetch pela última vez. `--fetch` primeiro faz fetch,
sem pedir credenciais, de cada remote que uma entrada
`refs/remotes/<remote>/...` nomeia: git e ssh rodam sem um terminal nem um
programa askpass, então um remote que precisa de uma senha ou de uma
passphrase que o credential helper ou o ssh-agent não guarda falha. Um
remote que falha recebe um aviso e o quadro mostra o que foi buscado por
último. É o único comando que usa a rede.

## Tickets

`atipspec new --ticket` aceita uma chave como `SHOP-12` (Jira, Linear), um
número de issue como `#42`, ou uma URL https; qualquer outra coisa é
recusada. Com `ticket_url` em `teams.json`, uma chave ou um número vira um
link em `status`, `team`, na proposta, no dossiê (`ticket_url` no seu JSON,
um link em Markdown e HTML) e em `merge-check`. O ticket não faz parte do
que a aprovação da proposta inclui no hash: adicione-o ou corrija-o em
`spec.md` a qualquer momento. O AtipSpec cria o link para o ticket; nunca
escreve no rastreador. Um ticket de texto livre escrito antes da 0.3.0 é
mostrado como está, sem link.

## Pull requests

`github-local.yml` e `gitlab-local.yml`, de `atipspec enterprise-init`,
executam `merge-check` como o check do pull request; o resumo do seu job
lista cada entrega que o branch toca com seu estado e ticket. Quando o
usuário pede ao agente que abra um pull request, o agente coloca na
descrição o ticket da entrega e a saída de
`atipspec report <slug> --format markdown`. No modo local, um recibo aceito
não é autenticado: o check confirma que o branch corresponde ao que foi
aceito, não quem o aceitou.

## Sobreposições

`status` e `audit` avisam quando duas entregas abertas declaram a mesma spec
viva em seu `impact`:

```text
  warning: orders-api and orders-screen both touch orders
```

Esse é o conflito que vale a pena pegar antes que o código exista. Conflitos
do Git continuam sendo problema do Git.

## Vários repositórios

Cada repositório tem seu próprio `.atipspec/`, porque as aprovações e a
evidência estão vinculadas à árvore do seu repositório. Para as partes
compartilhadas, um pequeno repositório **system** contém o contrato do
sistema, o glossário compartilhado, os contratos de API e schemas, e as
iniciativas que atravessam repositórios. Aponte cada projeto para um
checkout dele:

```yaml
# .atipspec/config.yaml
system: ../shop-system
```

`atipspec new` então fixa o `contract.md` do system, e seu `glossary.md`
quando ele tem um, no commit atual do checkout, no `contracts.json` da
entrega:

```text
Pinned system contract.md at 3f2a9c41d0e7 as system-contract (contracts.json)
```

O contexto da entrega os lê desse commit, então o avanço do system não muda
nem o que o agente lê nem a proposta aprovada. Quando o checkout não está
disponível, `new` avisa e a proposta não pode ser aprovada até que a fixação
exista:

```bash
atipspec contract-pin <slug> system-contract --repository system --ref HEAD --path contract.md
```

Qualquer outro contrato, como um schema de API em outro repositório, é
fixado da mesma forma depois de nomear seu checkout em `repositories` de
`teams.json`:

```bash
atipspec contract-pin orders-screen orders-api --repository api --ref main --path openapi.yaml
```

`--ref` é resolvido uma vez para um id de commit completo; `check` recusa uma
fixação que nomeia um branch ou uma tag, ou cujo conteúdo já não tem o
digest registrado. Fixar de novo altera `contracts.json`, o que anula a
aprovação da proposta: um contrato compartilhado mudou, e a pessoa aprova a
entrega contra o novo. As entregas antigas continuam lendo o checkout como
está.

## Mantendo o contexto pequeno

Todo comando de fase imprime a saída de `atipspec context <slug>`, que
carrega o contrato, a visão geral, o glossário, as specs vivas na lista de
impacto, as decisões aceitas que as afetam, e os próprios arquivos da
entrega. Ele imprime o tamanho:

```text
Context for orders-api: 184 lines (budget 800)
     43  contract (.atipspec/contract.md)
     22  overview (.atipspec/overview.md)
     10  glossary (.atipspec/glossary.md)
     37  decision DEC-001
     48  spec (.atipspec/deliveries/orders-api/spec.md)
     24  plan (.atipspec/deliveries/orders-api/plan.md)
```

Duas coisas mantêm isso limitado ao longo do tempo: a fase
[curate](flow/curate.md) com seus limites, e a lista de impacto, que é o
motivo pelo qual uma spec declara o que ela toca em vez de o modelo
adivinhar.

## Políticas por projeto

A cerimônia é um dial em `config.yaml`, e no [`risk`](flow/spec.md#risco) de
cada entrega, não uma propriedade da ferramenta:

```yaml
approve_plan: true      # legacy deliveries: build waits for the plan's own approval
review_rounds: 3        # reviews per approved proposal, the first included, before `review` refuses and you decide
context_budget: 800     # lines; context warns above it
max_requirements: 5     # check warns above it: split the delivery
max_tasks: 8            # same, for the plan
max_age_hours: 8        # check and status warn when a delivery has been open longer
```

Os dois pontos de parada, a proposta e o resultado, continuam em todo
projeto: os dials mudam o que o portão pede entre eles. Um projeto regulado
acrescenta `require_proof: true`, `require_isolated_review: true`, um
orçamento baixo e, para aprovações autenticadas, `trust: required` com uma
política externa.
