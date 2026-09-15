# Aceitação empresarial

O AtipSpec separa **checked** (verificações estruturais/técnicas locais) de
**verified** (evidência confiável e aceitação humana). `deliver` exige
verified.

## Aceitação local e aceitação confiável

Sem uma política, `atipspec accept` registra o que uma pessoa aceitou (spec,
plan, contrato) e o portão detecta edições posteriores. Isso é detecção de
desvio (drift): o registro prova o conteúdo, não a identidade. Com uma
política, o portão ignora esses registros e exige as aprovações assinadas e
vinculadas a papel descritas abaixo.

## Dois modos de confiança

| | `mode = "ssh"` | `mode = "provider"` |
| --- | --- | --- |
| Aprovações humanas | assinaturas SSH destacadas de chaves cadastradas (`approve`), ou revisões do provedor coletadas e assinadas por uma chave de coletor (`sync-approvals`) | lidas ao vivo do PR ou MR pelo worker protegido com um token somente leitura; sem coletor |
| Evidência de CI | assinada por uma chave de coletor de CI cadastrada (`attest`) | atestada pelo workflow de evidência com atestações de artefato do GitHub e verificada com um `gh` fixado |
| Chaves a cadastrar | uma por papel humano, uma para CI, uma para o coletor | nenhuma |
| Exceções de risco | `approve <slug> exception:Fn --expires` | não disponível: corrija o achado ou use o modo ssh |
| Política | `schema = 1` | `schema = 2`, `[provider.roles]` e `[attestation]` |

O modo provider é a recomendação padrão: precisa de um worker protegido com
`GITHUB_TOKEN`, a política fixada e o `gh` fixado, e nada mais. O portão relê
o provedor a cada execução e falha fechado diante de qualquer erro de API,
revisão revogada, head alterado ou digest divergente. `check`, `deliver` e
`report` recebem o número do PR ou MR com `--number` ou `ATIPSPEC_PR_NUMBER`.
`enterprise-init` escreve `policy.provider.example.toml` e
`github-evidence.yml`. O modo SSH continua sendo a opção estrita para
organizações que precisam de assinaturas sob a própria custódia de chaves,
atestações no GitLab ou exceções de risco.

A política vincula a atestação a um workflow do próprio repositório da
política. Pull requests de forks não recebem token OIDC por padrão, então sua
evidência não carrega atestação e o portão falha fechado; habilite a opção do
GitHub "send write tokens to workflows from pull requests" somente se você a
aceitar, e nunca use `pull_request_target` no workflow de evidência.

## Perímetro de confiança

O repositório candidato é editável pelo seu autor e pelo agente de
programação. Os arquivos nele, incluindo o JSON de evidência, o texto de
revisão e os metadados de aprovação local, não podem ser sua própria
autoridade. Um worker de aceitação protegido usa uma CLI instalada e fixada
(pinned), uma política de confiança externa versionada e chaves públicas
cadastradas. Fixe o SHA-256 da política na configuração protegida
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

## Papéis e assuntos de aprovação

| Fase | Papel | Conteúdo vinculado |
| --- | --- | --- |
| spec | product | especificação e contrato de arquitetura |
| plan | engineering | especificação, plano e contrato de arquitetura |
| decision:DEC-nnn | engineering | documento de decisão e contrato alterado |
| exception:Fn | risk | árvore, revisão, termos de adiamento, expiração |
| acceptance | qa | árvore, revisão, termos de adiamento e artefatos de evidência |

O dono declarado da entrega não pode aprovar o próprio trabalho. Os
adaptadores de provedor também rejeitam o autor real do PR/MR. Para
aprovações via SSH, os administradores devem garantir que `owner`
corresponda ao dono real e que as chaves humanas cadastradas não estejam
acessíveis a agentes de desenvolvedor ou contas de serviço. Uma assinatura
válida prova a posse da chave, não a presença humana nem uma revisão
semântica completa.

Obtenha o assunto com `approval-subject`. Cada aprovador revisa o assunto
real e executa `approve` em uma máquina confiável com sua chave cadastrada.
O comando não cria chaves nem fabrica identidade. Aprovações de risco exigem
um timestamp ISO futuro via `--expires`; mudar os termos exige nova
aprovação.

A aprovação de plan e spec deve preceder a execução da evidência. Um novo
digest de política, assunto alterado, signatário desconhecido, assinatura
alterada ou aprovação expirada falha fechado. Para revogar um signatário
SSH, remova a chave dele da política externa e distribua a nova política
fixada. Isso invalida artefatos da política anterior; colete novas
aprovações/evidências sob a nova política.

## GitHub e GitLab

Os adaptadores são somente leitura. Configure o tipo de provedor, a URL da
API HTTPS, o repositório e as listas de papel para conta na política
externa. Forneça GITHUB_TOKEN ou GITLAB_TOKEN somente ao worker protegido de
coleta/verificação.

Para o GitHub, um humano cadastrado envia uma review APPROVED contendo o
marcador exato de `approval-subject` em uma linha separada. A review deve
ter como alvo o head atual. Para o GitLab, o humano posta esse marcador em
uma nota que não seja de sistema e aprova o MR; ambos devem existir e a
conta deve estar ativa e não ser um bot.

```sh
atipspec sync-approvals reset acceptance --number 42 \
  --identity approval-collector --key /secure/collector-key \
  --policy /secure/company.toml
```

O coletor assina o registro normalizado, e todo portão confiável lê o
provedor novamente. Reviews revogadas ou alteradas falham. Um head
desatualizado, erro de API, endpoint de aprovação não suportado ou acesso de
token insuficiente falha fechado. O acesso à API de aprovação do GitLab
depende da implantação/tier. Origens de API self-hosted devem ser
configuradas explicitamente pelo administrador da política.

As integrações são cobertas por testes de contrato de API simulados
(mocked). A conexão ao vivo e a proteção de branch devem ser configuradas e
testadas na sua organização real.

Referências de API: [GitHub reviews](https://docs.github.com/en/rest/pulls/reviews),
[GitLab approvals](https://docs.gitlab.com/api/merge_request_approvals/).

## Execução e coleta de CI

Os jobs gerados do GitHub e GitLab executam a verificação local sem chaves
de assinatura. Use histórico completo. Proteja o pin do pacote verificador e
os workflows. Um orquestrador protegido deve autenticar o workflow produtor,
o repositório, o head de origem, a execução bem-sucedida e o download do
artefato antes de atestar.

Execute os comandos candidatos em um worker efêmero sem chaves de
assinatura. Colete e assine em um worker protegido separado, usando um
checkout novo e higienizado e `python -I -m atipspec` a partir de um pacote
instalado e fixado. Não instale nem importe a implementação candidata do
AtipSpec. Nunca execute comandos candidatos no coletor. Isolar credenciais
em outro passo em um worker persistente comprometido não é suficiente.

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
bloqueador aguardando uma exceção de risco confiável. A CLI não pode impedir
um administrador de contornar as regras do repositório.

## Dossiê e piloto

`report --format json|markdown|html` exporta uma matriz de rastreabilidade,
ponteiros de prova, referências de execução de CI, aprovações verificadas,
achados e informações de política/versão. O HTML escapa texto não confiável.
Os artefatos assinados são a evidência; os próprios hashes de um relatório
são um índice, não uma certificação separada. Mantenha ambos.

`pilot init <name>` cria um protocolo sem medições. A equipe completa
coortes, elegibilidade, janela de observação, limiares e humanos
responsáveis. `pilot record` exige medições reais com fonte e coletor;
`pilot report` fornece comparações descritivas e sinaliza janelas
incompatíveis. Alegações reais de desempenho exigem um piloto concluído;
exemplos gerados não são medições. Use uma linha de base equivalente e a
mesma janela de observação de defeitos.
