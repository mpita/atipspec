# Design do AtipSpec

O AtipSpec separa a assistência de planejamento, as verificações técnicas
locais e a aceitação confiável. Cada uma tem uma autoridade diferente e um
modo de falha diferente.

## Três ciclos de vida

O contrato de arquitetura define regras estruturais locais. As specs vivas
preservam os IDs de requisitos e critérios com escopo de capacidade ao longo
das mudanças. As entregas contêm a especificação proposta, tarefas,
mapeamentos de teste, evidência, revisão técnica, exceções de risco e
aprovações. O arquivamento preserva um recibo de aceitação.

A CLI computa o estado a partir desses artefatos e do Git. Um registro
`task-done` é a declaração de progresso do assistente, não correção
semântica. Um código de saída de comando registra um resultado de execução,
não a cobertura completa de testes. Um ponteiro de prova de revisão é uma
alegação que o revisor técnico e o QA humano devem avaliar.

## Aceitação local

A pessoa decide na conversa; o assistente registra a decisão com
`atipspec accept`. São três decisões: a proposta (cenários, abordagem,
testes e risco; a spec, para entregas antigas), o resultado revisado, e o
contrato com as decisões que o afetam, uma vez por projeto. O mecanismo
descrito abaixo não acrescenta nenhuma; o prompt de permissão do cliente
confirma a mesma decisão.

Cada decisão é apresentada por uma visão que imprime um **código de
aprovação**: `proposal <slug>`, `report <slug>` ou `proposal contract`. O
código são os primeiros 40 bits do sha256 do conteúdo em base32 de Crockford
(`XXXX-XXXX`), fácil de ler e de ditar; a digitação ignora maiúsculas e
minúsculas e o hífen. Não é um segredo. Ele vincula o registro à versão
apresentada: se o conteúdo mudou nesse meio-tempo, `accept --code` recusa
sem revelar o código atual. Faz o prompt de permissão do cliente mostrar o
que está sendo aprovado, e faz o assistente passar pela visão de
apresentação.

O registro armazena o hash do conteúdo aceito, digests por arquivo, o
código, quem (`--by`, um rótulo declarado que usa por padrão a identidade do
git), quando, e o **canal**: `terminal` quando alguém digitou o código no
prompt da CLI em um terminal interativo sem marcador de agente;
`client-permission` quando o Claude Code é o único marcador de agente, ele
não roda pelo Agent SDK nem por `claude -p` (que podem não carregar as
configurações do projeto, e cujos prompts vão para um programa), o
interpretador recebeu a linha de comando à qual sua regra de ask corresponde
(`atipspec accept` ou `python -m atipspec accept`) e a CLI encontrou intactas
as regras de permissão do AtipSpec em `.claude/settings.json`; `assistant`
caso contrário. O Claude Code passa seu marcador para todo processo que
inicia, então o marcador de outro agente ao lado do dele significa que esse
agente executou o comando, fora das regras do Claude Code. Os marcadores de
agente no ambiente (`CLAUDECODE`, `CODEX_SANDBOX`, `CODEX_THREAD_ID`,
`COPILOT_CLI`, `CURSOR_AGENT`, `GEMINI_CLI`, `AI_AGENT`) só podem rebaixar o
canal, nunca elevá-lo. O portão compara o hash com os arquivos a cada
execução, então uma mudança feita depois da aceitação, por um modelo ou por
qualquer pessoa, fica visível, nomeia o arquivo e devolve a entrega para a
pessoa. As entregas guiadas precisam do registro da proposta; um par de spec
e plano não o substitui. O registro do contrato,
`.atipspec/approvals/contract.json`, inclui no hash o contrato e cada decisão
que o afeta, sem suas linhas de status: uma decisão adicionada, editada ou
marcada como aceita à mão depois disso deixa a aceitação desatualizada. As
aprovações de entregas incluem `contract.md` inteiro no hash, como as
aprovações assinadas sempre fizeram, então as linhas de status que
`accept contract` escreve as deixam desatualizadas; `proposal contract`
nomeia essas aprovações antes que a pessoa decida. Os registros ficam fora
da impressão digital da árvore e não carregam assinatura: eles vinculam
conteúdo e informam o canal, não a identidade.

O que isso cobre: um assistente cooperativo, mas apressado, que registraria
uma aprovação por conta própria pelo caminho normal. Ele não consegue
fazê-lo sem o código, o registro diz como foi feito, e com as regras do
Claude Code o cliente pergunta à pessoa primeiro e nega às suas ferramentas
de edição os registros de aprovação e de evidência. O que não cobre: um
agente que se propõe a contornar as proteções, por exemplo escrevendo
arquivos a partir de um script ou apagando `review-rounds.json` com um
comando de shell, o que recomeça a contagem de rodadas a partir do
`review.md` na pasta, executando `atipspec accept` dentro de um script ou
programa que o Claude Code inicia, como um agente que não define nenhum dos
marcadores (a CLI vê apenas o próprio processo, então o registro ainda diz
`client-permission`), executando o comando em um terminal sem marcador de
agente e digitando ele mesmo o código, iniciando a sessão fora da raiz do
projeto para que as configurações não carreguem, ou por meio de
configurações gerenciadas ou hooks que respondem aos prompts de permissão.
`approval-subject` continua, porque o modo provider precisa dele; calcular
um hash nunca foi a barreira. O caminho autenticado é uma política de
confiança externa.

## Dois portões

Sem confiança externa, `check` valida gramática, cobertura, os registros de
aceitação da pessoa, o escopo declarado, a forma dos critérios, os
comandos/resultados exatos da evidência, os testes nomeados por critério, a
atualidade e as regras locais do contrato. O sucesso é **checked**. Como os
arquivos candidatos são editáveis pelo autor, isso não alega execução
autenticada nem aceitação humana. Sem uma política, `deliver` também exige a
aceitação registrada do resultado atual.

Os dois portões falham fechado. O commit base, as regras do contrato e a
atualidade vêm do git, então sem git `check` é um erro, e não um aviso. Um
plano deve declarar um escopo mais estreito que o repositório
(`strict_scope`), e requisitos e critérios devem passar nas verificações de
forma, de termos vagos e de critério de adequação (`strict_criteria`); ambas
estão ligadas em projetos novos. `trust: required` em `config.yaml`
transforma a falta de uma política em erro e desativa a aceitação local, e
um branch não pode retirá-lo para o seu próprio merge. Valores de política
inválidos param todo comando antes que ele rode.

Com uma política externa versionada, o sucesso é **verified**. O portão
exige adicionalmente evidência de CI assinada, aprovações de produto e de
engenharia anteriores à verificação, aceitação de QA, mapeamentos de critério
para tarefa, conteúdo candidato commitado e regras corporativas. Adiamentos
de blocker/major exigem aprovação de risco assinada com expiração. Mudanças
de contrato exigem novas decisões relacionadas aceitas, com aprovação
confiável da engenharia. Contratos excluídos e histórico ausente falham.

## Modos de confiança

Dois modos carregam o mesmo portão. No modo `ssh`, a autoridade é uma chave
cadastrada: humanos assinam aprovações, um coletor assina a evidência de CI,
e uma chave comprometida é revogada trocando a política. No modo `provider`,
a autoridade é a conta do provedor e a identidade da plataforma de CI: o
worker protegido lê as aprovações do PR ao vivo com um token somente
leitura, e a evidência carrega uma atestação de artefato que vincula seu
digest ao repositório candidato, ao pull request e a um workflow confiável
fora do repositório candidato, fixado em um commit, verificada com a
ferramenta da própria plataforma. O workflow fica fora porque, em um pull
request, a plataforma executa os workflows que o pull request traz: um
workflow do repositório candidato faz parte da mudança que ele atestaria. O
modo provider foi escolhido como recomendação padrão porque remove a
custódia de chaves, o custo que impedia a maioria das organizações de rodar
o portão confiável, mantendo as propriedades que importam: aprovações
vinculadas ao conteúdo, revogação detectada a cada execução, evidência que
não pode ser substituída depois. O que ele não pode carregar é uma
expiração, por isso as exceções de risco ficam no modo ssh.

## Autoridade e criptografia

Assinaturas SSH destacadas vinculam os bytes exatos do artefato a uma
identidade cadastrada em uma política controlada pela organização, fora do
repositório candidato. Cada artefato também vincula o repositório e o digest
da política. O digest da política é fixado na CI protegida. Um arquivo
allowed-signers local ao candidato não seria uma âncora de confiança, então
o portão recusa políticas locais ao candidato.

Uma chave humana só é tão independente quanto sua custódia. Um agente com
essa chave pode assinar; nenhuma CLI consegue inferir presença humana a
partir de uma assinatura. O cadastro de identidades humanas, o isolamento de
chaves, a integridade do verificador instalado e a configuração de branches
protegidos pertencem ao perímetro de confiança da organização.

Para GitHub/GitLab, um coletor lê as aprovações humanas existentes, verifica
papel, separação de autor e o marcador de head/conteúdo, depois assina o
registro normalizado. O portão busca novamente o estado do provedor a cada
verificação, para que uma resposta assinada em cache não possa sobrepor uma
revogação. Falhas do provedor falham fechado.

A coleta de CI tem um perímetro separado: o orquestrador autentica o
workflow produtor, o SHA de origem, o resultado da execução e a proveniência
do artefato antes de o coletor usar `attest`. Esse comando não autentica uma
URL de CI arbitrária. O código candidato nunca deve executar com chaves de
assinatura. Use execução efêmera e um coletor protegido separado; um segundo
passo em um worker comprometido é isolamento insuficiente.

## Atualidade sem hashes circulares

A impressão digital de origem/especificação exclui os arquivos de evidência
da entrega, revisão, adiamento, aprovação e relatório. Esses arquivos
descrevem o candidato e não devem se invalidar recursivamente. Os assuntos
de aprovação resolvem o problema de dependência restante: a aprovação de
risco vincula a revisão e os termos de adiamento; a aceitação de QA vincula
esses mais o conjunto de evidência assinada. Mudar os arquivos excluídos,
portanto, invalida a aceitação relevante mesmo quando o hash de origem
permanece constante.

`deliver` altera a própria impressão digital da entrega (a pasta se move e a
spec viva a absorve), então o recibo também armazena `code_tree`: o hash de
tudo o que está fora de `.atipspec/`. Nada do que o AtipSpec escreve depois o
altera, e qualquer mudança de código o altera. `merge-check` o compara com o
head do branch antes do merge, e verifica que toda entrega aberta que o
branch toca está aceita: a lacuna entre a aceitação e o merge é fechada pelo
mesmo hash, não pela confiança no branch.

## Identidades duráveis

As specs vivas fazem merge por ID de requisito, mantendo os IDs de critério.
Títulos podem mudar sem mudar a identidade. `atipspec ids` dá a cada entrega
um prefixo aleatório curto que nenhum ID visível no checkout ou nas refs da
equipe usa, de modo que branches paralelos não colidem; os IDs numerados das
entregas antigas, alocados acima do máximo encontrado nos artefatos vivos,
ativos e arquivados, continuam válidos. A comparação de três vias detecta
edições concorrentes ao mesmo requisito ou colisões de posse de critério, e
`check` reporta IDs duplicados. Todo requisito e critério de aceitação
recebe um ID estável desde o início.

## Limites operacionais

As regras do contrato verificam caminhos, padrões, dependências e comandos
obrigatórios; elas não provam a correção arquitetural. Mapeamentos de teste
e ponteiros de prova precisam de revisão semântica. O Git exclui arquivos
ignorados das impressões digitais de origem, então mantenha as entradas de
build e os lockfiles rastreados e reproduza o ambiente de execução.
Relatórios são índices e resumos de evidência assinada, não certificações.
Relatórios arquivados descrevem aceitação histórica. `merge-check` compara a
árvore de código inteira, então trazer o branch de destino para um branch
entregue, ou qualquer correção posterior, reabre a entrega: reverta o commit
de arquivamento e depois verifique, revise, aceite e entregue de novo. Traga
o branch de destino com um merge antes da verificação final; uma entrega por
branch mantém isso barato. No modo local, o recibo é uma declaração no
branch: uma edição do seu `code_tree` aparece no diff do pull request. Com
uma política de confiança, `merge-check` não aceita a palavra do recibo:
verifica a entrega de novo no commit anterior ao commit de arquivamento, com
os arquivos arquivados com ela, como `deliver` fez (no modo provider, com as
revisões do pull request sobre esse commit), exige que esse commit contenha
o código do head e compara a spec viva, inclusive cada requisito que a entrega
lista, com o que `deliver` escreve a partir dele. Pilotos relatam observações reais com fonte, tamanhos de amostra e
limitações; eles não inventam ROI.
