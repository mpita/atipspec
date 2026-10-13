# Aceitação empresarial

O AtipSpec separa **checked** (verificações estruturais/técnicas locais) de
**verified** (evidência confiável e aceitação humana). Sob uma política de
confiança, `deliver` exige verified; `trust: required` torna a política
obrigatória.

## Aceitação local e aceitação confiável

Sem uma política, `atipspec accept --code <code>` registra o que uma pessoa
aprovou na conversa (a proposta, o resultado, o contrato; a spec e o plano
das entregas antigas) e o portão detecta edições posteriores. O registro
informa seu canal: `terminal` (o código foi digitado no prompt da CLI),
`client-permission` (o Claude Code foi configurado para perguntar à pessoa
antes do comando) ou `assistant` (nada perguntou). Mesmo o canal local mais
forte diz como o cliente foi configurado, não quem confirmou: isso é
detecção de desvio (drift) mais um relato honesto do caminho, não
identidade. Com uma política, o portão ignora esses registros e exige as
aprovações assinadas e vinculadas a papéis descritas abaixo, que autenticam
cada aprovador com uma chave cadastrada ou com a própria revisão do
provedor.

## Exigir a política de confiança

A política fica fora do repositório; o repositório só pode declarar que ela
é exigida. Defina `trust: required` em `.atipspec/config.yaml` e proteja esse
arquivo com CODEOWNERS. Sem uma política (`--policy` ou
`ATIPSPEC_TRUST_POLICY`), `check` fica vermelho, o `accept` local fica
desativado exceto para o contrato do projeto, `deliver` recusa e `run` não
inicia. `verify` continua rodando para a iteração local; o check confiável
exige evidência atestada de qualquer forma. `merge-check` aplica a exigência
quando o head, o branch de destino ou a base de merge a definem, de modo que
um branch não pode removê-la para o seu próprio merge, nem escapar dela
partindo de um commit anterior a ela. Então ele bloqueia um recibo aceito
localmente, e um recibo confiável que a política não autentica (veja [CI
antes do merge](#ci-antes-do-merge)).

## Dois modos de confiança

| | `mode = "ssh"` | `mode = "provider"` |
| --- | --- | --- |
| Aprovações humanas | assinaturas SSH destacadas de chaves cadastradas (`approve`), ou revisões do provedor coletadas e assinadas por uma chave de coletor (`sync-approvals`) | lidas ao vivo do pull request pelo worker protegido com um token somente leitura; sem coletor |
| Evidência de CI | assinada por uma chave de coletor de CI cadastrada (`attest`) | atestada com atestações de artefato do GitHub pelo workflow de evidência confiável, em um repositório separado e fixado em um commit, e verificada com um `gh` fixado |
| Chaves a cadastrar | uma por papel humano, uma para a CI, uma para o coletor | nenhuma |
| Exceções de risco | `approve <slug> exception:Fn --expires` | não disponível: corrija o achado ou use o modo ssh |
| Política | `schema = 1` | `schema = 2`, `[provider.roles]` e `[attestation]` |

O modo provider é a recomendação padrão: precisa de um worker protegido com
`GITHUB_TOKEN`, a política fixada e o `gh` fixado, e de um repositório
confiável da organização que contenha o workflow de evidência, e nada mais.
O modo provider é exclusivo do GitHub. O portão relê o provedor a cada
execução e falha fechado diante de qualquer erro de API, revisão revogada,
head alterado ou digest divergente. `check`, `deliver`, `report` e
`merge-check` recebem o número do PR com `--number` ou `ATIPSPEC_PR_NUMBER`.
`enterprise-init` escreve `policy.provider.example.toml`,
`github-evidence-trusted.yml` e `github-evidence-caller.yml`. O modo SSH
continua sendo a opção estrita para organizações que precisam de
assinaturas sob a própria custódia de chaves, do GitLab ou de exceções de
risco.

Em um pull request, o GitHub executa os workflows que o pull request traz,
então um workflow do repositório candidato pode ser reescrito pela mudança
que ele atesta. Por isso a política vincula cada atestação de evidência a
quatro coisas: o repositório candidato (`repository`, verificado com
`--repo`), o pull request (`refs/pull/<number>/merge`, a ref que o GitHub
registra para uma execução de `pull_request`), o workflow confiável em um
repositório separado da mesma organização (`[attestation] signer_workflow`)
em um commit (`signer_digest`), e runners hospedados pelo GitHub
(`allow_self_hosted_runners = true` remove esta condição). Uma política cujo
workflow vive no repositório candidato, ou cujo commit não está fixado, não
carrega. O portão também exige que o `head` de cada registro seja o commit do
qual o worker fez checkout. Pull requests de forks não recebem token OIDC por
padrão, então sua evidência não carrega atestação e o portão falha fechado;
habilite a opção do GitHub "send write tokens to workflows from pull
requests" somente se você a aceitar, e nunca use `pull_request_target` no
workflow de evidência.

## Perímetro de confiança

O repositório candidato é editável pelo seu autor e pelo agente de
programação. Os arquivos nele, incluindo o JSON de evidência, o texto de
revisão e os metadados de aprovação local, não podem ser sua própria
autoridade. Um worker de aceitação protegido usa uma CLI instalada e fixada,
uma política de confiança externa versionada e chaves públicas cadastradas.
Fixe o SHA-256 da política na configuração protegida
(`ATIPSPEC_POLICY_SHA256`).

`enterprise-init` gera exemplos de configuração e um guia de adoção. Mova e
configure a política fora do checkout; não use o template diretamente. O
template contém propositalmente chaves de placeholder inválidas. Os papéis
de assinatura de CI e de coletor de provedor não podem também deter papéis
de aprovação humana.

As `contract_rules` corporativas são avaliadas em todo o repositório, além
do contrato do projeto. Um projeto não pode dispensar uma regra corporativa
com uma decisão de arquitetura local. Atualize e aprove a política
corporativa separadamente.

A política também pode impor dois mínimos ao portão, booleanos de nível
superior ao lado de `contract_rules`: `require_proof = true` (todo critério
sob `Tests:` nomeia seu teste JUnit em `Proof:`, e a verificação tem um
`Report:`) e `require_isolated_review = true` (uma revisão cuja `session:`
não é `isolated` é um erro). Qualquer outro valor faz a política falhar ao
carregar. O portão aplica uma exigência quando a política ou o `config.yaml`
do projeto a define, de modo que um projeto pode acrescentá-la, mas não
retirá-la.

## Papéis e assuntos de aprovação

| Fase | Papel | Conteúdo vinculado |
| --- | --- | --- |
| spec | product | especificação e contrato de arquitetura |
| plan | engineering | especificação, plano e contrato de arquitetura |
| decision:DEC-nnn | engineering | documento de decisão e contrato alterado |
| exception:Fn | risk | árvore, revisão, termos de adiamento, expiração |
| acceptance | qa | árvore, revisão, termos de adiamento e artefatos de evidência |

Em uma entrega guiada, spec e plan vinculam um a um os requisitos que a
entrega lista, não o resto da spec viva da sua capacidade, cujos demais
requisitos `check` e `merge-check` mantêm como estavam (versão 2 do assunto;
veja [quando a main avança](teams.md#quando-a-main-avanca)). O que o branch
de integração trouxe não é mudança da entrega; sob uma política, apenas sua
chave `integration` nomeia esse branch, como
`integration = "refs/remotes/origin/main"`: `teams.json` faz parte do
candidato. Sem a chave, nada é atribuído, e o que incorporar o branch de
destino traz conta como mudança da entrega em `check`. As
aprovações assinadas antes da 0.3.0, e as revisões do provedor que carregam
seu marcador, são comparadas com o assunto da versão 1 para o qual foram
feitas. Um assunto lê finais de linha CRLF como LF, e o mesmo fazem as
verificações de assinatura de aprovações e de registros de evidência e os
digests dos logs de saída dos comandos e das cópias de relatórios de teste:
um checkout com `core.autocrlf` (o padrão do Git for Windows) e um sem ele
dão o mesmo assunto e verificam as mesmas assinaturas.

O dono declarado da entrega não pode aprovar o próprio trabalho, seja qual
for a combinação de maiúsculas e minúsculas em que esteja escrito: um dono
`Engineering` é a identidade ou conta `engineering`. O dono é escrito como as
identidades, em letras ASCII, dígitos, `_`, `.`, `@` e `-`: `check` e
`approve` recusam um que apenas se parece com uma identidade, com uma letra
cirílica ou um caractere invisível. Os adaptadores de provedor também
rejeitam o autor real do PR/MR. No modo ssh, `spec.md` é a palavra do autor,
então o aprovador de produto confirma o dono:
`approve <slug> spec --owner <identity>` falha a menos que seja o `owner` que
`spec.md` declara, e o assina com a aprovação. Uma aprovação de spec que não
confirma nenhum dono (assinada antes da 0.3.0), ou que confirma outro, não
conta: assine-a de novo com `--owner`. Mudar o dono muda o assunto da spec,
então o produto aprova de novo, e o novo dono não pode assinar as fases
posteriores. Os administradores ainda devem garantir que as chaves humanas
cadastradas não estejam acessíveis a agentes de desenvolvedor ou contas de
serviço. Uma assinatura válida prova a posse da chave, não a presença humana
nem uma revisão semântica completa.

Obtenha o assunto com `approval-subject`. Cada aprovador revisa o assunto
real e executa `approve` em uma máquina confiável com sua chave cadastrada.
O comando não cria chaves nem fabrica identidade. Aprovações de risco exigem
um timestamp ISO futuro via `--expires`; mudar os termos exige nova
aprovação.

A aprovação de plan e spec deve preceder a execução da evidência. Um novo
digest de política, assunto alterado, signatário desconhecido, assinatura
alterada ou aprovação expirada falha fechado. Para revogar um signatário
SSH, remova a chave dele da política externa e distribua a nova política
fixada. Isso invalida os artefatos da política anterior; colete novas
aprovações/evidências sob a nova política.

## GitHub e GitLab

Os adaptadores são somente leitura. Configure o tipo de provedor, a URL da
API HTTPS, o repositório e as listas de papel para conta na política
externa. Forneça GITHUB_TOKEN ou GITLAB_TOKEN somente ao worker protegido de
coleta/verificação.

Para o GitHub, um humano cadastrado envia uma revisão APPROVED contendo o
marcador exato de `approval-subject` em uma linha separada. A revisão deve
ter como alvo o head atual. Para o GitLab, o humano posta esse marcador em
uma nota que não seja de sistema e aprova o MR; ambos devem existir e a
conta deve estar ativa e não ser um bot.

```sh
atipspec sync-approvals reset acceptance --number 42 \
  --identity approval-collector --key /secure/collector-key \
  --policy /secure/company.toml
```

O coletor assina o registro normalizado, e todo portão confiável lê o
provedor novamente. Revisões revogadas ou alteradas falham. Um head
desatualizado, erro de API, endpoint de aprovação não suportado ou acesso de
token insuficiente falha fechado. O acesso à API de aprovação do GitLab
depende da implantação/tier. Origens de API self-hosted devem ser
configuradas explicitamente pelo administrador da política.

As integrações são cobertas por testes de contrato de API simulados
(mocked). A conexão real e a proteção de branch devem ser configuradas e
testadas na sua organização real.

Referências de API: [GitHub reviews](https://docs.github.com/en/rest/pulls/reviews),
[GitLab approvals](https://docs.gitlab.com/api/merge_request_approvals/).

## CI antes do merge

`github-local.yml` e `gitlab-local.yml`, de `enterprise-init`, executam
`atipspec merge-check` como o check do pull request: torne esse job
obrigatório no branch de destino. Ele falha enquanto uma entrega que o branch
toca está em draft ou não aceita, quando o código no head difere do código
que um recibo aceitou, quando o branch reescreve um arquivamento anterior,
altera uma spec viva fora de `deliver`, altera o contrato aceito sem sua
nova aceitação, ou altera código fora de `.atipspec/` que nenhuma entrega do
branch alterou depois de seu commit base, como o código commitado antes de
`atipspec new`, a menos que `exempt_paths`, no `config.yaml` do branch de
destino, isente esses arquivos (veja a [referência da
CLI](reference/cli.md#atipspec-merge-check)). Ele também falha enquanto
`.atipspec/framework/` não for o que a versão fixada instala, porque cada fase
imprime ao agente essas regras e esses workflows: execute
`atipspec install --update` com essa versão. Ele avisa, sem bloquear, quando o
branch relaxa uma política do `config.yaml` em relação ao branch de destino,
ou altera `overview.md`, `glossary.md`, uma decisão (e nomeia cada decisão
com seu status), `adapter.json` ou `teams.json`; e quando o branch altera o contrato ou uma decisão que o
afeta, o resultado mostra a aceitação do contrato e seu canal. O job faz checkout do head do
branch, não do commit de merge sintético do provedor, com o histórico
completo, e nada pode escrever no checkout antes de `merge-check`, que julga
o head commitado. Ele instala o verificador fixado de fora do checkout com
`python -I`, de modo que um pacote `pip/` ou um wheel que o candidato commite
nunca é carregado, não executa nenhum comando do candidato e não precisa de
credenciais; os testes do projeto rodam em seu próprio job. O job do GitLab
faz fetch do branch de destino, para que seu `trust: required` se aplique. O
job do GitHub escreve o resultado no resumo do job (`--format markdown`): uma
tabela das entregas que o branch toca com seu estado e ticket, e depois as
verificações. Quando o agente abre o pull request a pedido do usuário, a
descrição traz o ticket e `atipspec report <slug> --format markdown`. No
modo local, um recibo não é autenticado: o check mostra que o branch
corresponde ao que foi aceito, não quem o aceitou, e como cada aprovação foi
registrada (seu canal), não quem a deu.

Um limite que se fecha com o provedor, não com o AtipSpec: o provedor
executa o workflow que o branch traz, então um branch pode reescrever ou
remover o check. Exija-o de fora do candidato: no GitHub, com um ruleset que
exija o workflow de um repositório protegido, ou com CODEOWNERS em
`.github/workflows/` e a revisão de code owners obrigatória; no GitLab, com
uma pipeline execution policy ou um compliance pipeline. Localmente, o Claude
Code pergunta antes que suas ferramentas de edição alterem
`.github/workflows/**`, `.gitlab-ci.yml` ou suas próprias configurações (veja
as [regras de permissão de
aprovação](clients.md#regras-de-permissao-de-aprovacao)); isso não é um
controle sobre o branch.

`exempt_paths` no branch de destino deixa um branch alterar os arquivos que
ele cobre sem nenhuma entrega nem aceitação, também sob uma política.
Restrinja-o a arquivos que não precisam dela, como a documentação, e revise
uma mudança nele como uma mudança na CI: ele não isenta nada até ser
integrado ao branch de destino, e `merge-check` avisa no branch que o altera.
Quais arquivos não precisam de entrega é decisão da pessoa: as regras
instaladas dizem ao agente que só altere `exempt_paths` quando ela pedir.
Nenhuma aprovação o inclui no hash, então defini-lo na main não devolve a
draft a proposta de nenhuma entrega aberta; um branch que o integra verifica e
revisa de novo, como após qualquer mudança da árvore.

Uma lista de partida, que a pessoa adapta. Cada entrada é código que nenhum
humano aprova em uma entrega: um branch altera os arquivos que ela cobre sem
nenhuma entrega.

```yaml
exempt_paths:
  - "docs/**"
  - "README.md"
  - "CHANGELOG.md"
  - "LICENSE"
  - "package-lock.json"
  - "uv.lock"
```

A documentação e os lockfiles são os candidatos habituais. Um lockfile fixa
as versões das dependências com que o código é executado: isente-o só onde
outra coisa revisa as atualizações de dependências, como uma revisão
obrigatória dos pull requests do bot de atualizações. Nunca inclua código,
testes, `.github/**`, `.claude/**` nem arquivos que o agente lê como
instruções, como `AGENTS.md` ou `CLAUDE.md`; um glob amplo como `**/*.md`
também os cobre.

O arquivo que adiciona o job também é código fora de `.atipspec/`, e nenhuma
entrega o cobre: o pull request que o adiciona falha no seu próprio
`merge-check`, enquanto o branch de destino ainda não tem `exempt_paths`,
então integre-o antes de tornar o job obrigatório. Uma mudança posterior
nesse arquivo, como um novo pin de `ATIPSPEC_PACKAGE`, falha do mesmo jeito:
faça-a em uma entrega ou, se a pessoa decidir que ela não precisa de uma,
adicione só esse arquivo a `exempt_paths` no branch de destino antes, sob os
owners que revisam a CI; `.github/**` deixaria um branch alterar qualquer
workflow sem entrega.

Com `trust: required`, esses jobs falham fechado: execute
`merge-check --base <ref> --policy /secure/company.toml` no worker protegido
e exija esse resultado em seu lugar. Com uma política, `merge-check` exige
aceitação confiável mesmo onde `trust: required` não está definido, de modo
que um recibo aceito localmente bloqueia. Um recibo é um arquivo no branch,
então com a política `merge-check` não o lê como prova: verifica de novo cada
entrega que o branch arquiva tal como `deliver` a encontrou. Em um clone
temporário com as refs do repositório, faz checkout do commit anterior ao
commit de arquivamento, restaura a evidência, a revisão, os termos de
adiamento e as aprovações arquivados com a entrega, e exige que seu check
confiável ali seja `verified` (as aprovações de produto, engenharia e QA e a
evidência atestada que `deliver` exige; as revisões do provedor coletadas
com `sync-approvals` são lidas de novo), que esse commit contenha o código do
head, e que a spec viva no head seja o que `deliver` escreve a partir dele,
inclusive cada requisito que a entrega lista.
Faça o commit do arquivamento sozinho, logo depois de `deliver`. No modo
provider, ele lê as revisões do pull request sobre esse commit, ou sobre o
novo head quando elas carregam as mesmas linhas de marcador: se o push do
arquivamento descartar revisões obsoletas, os revisores aprovam o novo head
de novo com as mesmas linhas. Sob uma política, o contrato e as decisões que
o afetam só mudam em uma entrega verificada dessa forma, `contract.md` com
uma nova decisão que o afeta, aceita e aprovada pela engenharia; um contrato
em draft é aceito pela primeira vez com uma entrega assim, cuja aprovação do
plano o nomeia. Um branch que os altera de outra forma bloqueia, diga o que
disser o registro local do contrato.

## Execução e coleta de CI

Os jobs de evidência executam os comandos candidatos sem chaves de
assinatura. Use o histórico completo. Proteja o pin do pacote verificador e
os workflows. Um orquestrador protegido deve autenticar o workflow produtor,
o repositório, o head de origem, a execução bem-sucedida e o download do
artefato antes de atestar.

No modo provider, `github-evidence-trusted.yml` é esse orquestrador.
Copie-o para o repositório confiável; cada repositório candidato o chama no
commit fixado com `github-evidence-caller.yml`, somente em `pull_request`.
Seu job `produce` faz checkout do head do pull request, apaga a evidência
commitada no branch, executa os comandos Verify apenas com acesso de leitura
e envia os registros que escreveu. Seu job `attest` não executa nenhum
comando candidato: pega esses registros pelo ID do artefato, de modo que um
artefato que outro job da execução substituiu faz o download falhar, exige
exatamente um registro aprovado por tarefa verificada de cada entrega ativa,
escrito nesse head e nessa árvore, e atesta apenas esses. O worker protegido
também apaga a evidência commitada, baixa da última execução bem-sucedida no
head o artefato da tentativa dessa execução, `atipspec-evidence-<attempt>`,
copia apenas suas pastas `evidence/` e executa `check` ou `deliver` com
`--number`, que falham diante de um registro que `attest` não atestou;
`ADOPTION.md` lista os comandos. A verificação vem depois das aprovações de
spec e plan: execute o workflow de novo no head assim que elas forem dadas,
e o QA aprova depois dele. A atestação prova onde, quando e em qual head a
evidência foi produzida, não que o código sob teste é honesto: ele roda em
`produce` e poderia falsificar ali seus próprios resultados, o que a revisão
e as aprovações no head cobrem.

Execute os comandos candidatos em um worker efêmero sem chaves de
assinatura. Colete e assine em um worker protegido separado, usando um
checkout novo e higienizado e `python -I -m atipspec` a partir de um pacote
instalado e fixado. `attest` assina, para cada tarefa, o registro em
`evidence/` que terminou por último: apague a evidência que o branch
commitou (`atipspec.verify.clear_evidence`) antes que o produtor verifique e
antes que o coletor restaure seus registros. Não instale nem importe a
implementação do AtipSpec do candidato. Nunca execute comandos candidatos no
coletor. Isolar credenciais em outro passo em um worker persistente
comprometido não é suficiente.

Cada comando tem um log de saída completo cujo hash é verificado contra o
registro de evidência assinado, assim como o relatório JUnit copiado quando
uma tarefa nomeia um. Mantenha esses logs e relatórios junto com a
evidência.

`attest` valida e assina registros em nome desse coletor confiável. Ele não
consulta nem autentica de forma independente a URL de execução de CI
alegada. Assinar um JSON arbitrário fornecido pelo autor derrotaria o
perímetro de confiança. A integração nativa do provedor de atestação de
artefato/orquestrador é específica de cada implantação e deve ser
configurada antes de usar o script de aceitação protegido em produção.

Exija o resultado da aceitação protegida com proteção de branch ou regras de
MR. As verificações locais permanecem diagnósticas e podem reportar um
blocker aguardando uma exceção de risco confiável. A CLI não pode impedir um
administrador de contornar as regras do repositório.

## Dossiê e piloto

`report --format json|markdown|html` exporta uma matriz de rastreabilidade,
ponteiros de prova com aquilo a que cada um foi resolvido, o revisor e a
sessão da revisão, referências de execução de CI, aprovações verificadas,
achados, informações de política/versão, e as mudanças que o QA assina:
todo arquivo alterado desde o commit base com seu status, linhas e se está
fora do escopo do plano, e o diff (até 200 KB, 50 KB em markdown, com o
tamanho e o sha256 do diff completo). O HTML escapa texto não confiável. Os
artefatos assinados são a evidência; os próprios hashes de um relatório são
um índice, não uma certificação separada. Mantenha ambos.

`pilot init <name>` cria um protocolo sem medições. A equipe completa
coortes, elegibilidade, janela de observação, limiares e humanos
responsáveis. `pilot record` exige medições reais com fonte e coletor;
`pilot report` fornece comparações descritivas e sinaliza janelas
incompatíveis. Alegações reais de desempenho exigem um piloto concluído;
exemplos gerados não são medições. Use uma linha de base equivalente e a
mesma janela de observação de defeitos.
