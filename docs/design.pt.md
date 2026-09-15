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

A CLI computa o estado a partir desses artefatos e do Git. Um marcador de
commit registra a atribuição do trabalho, não a correção semântica. Um
código de saída de comando registra um resultado de execução, não a
cobertura completa de testes. Um ponteiro de prova de revisão é uma
alegação que o revisor técnico e o QA humano devem avaliar.

## Aceitação local

`atipspec accept` grava, sob o comando de uma pessoa, o hash do que ela
aceitou: a spec e o contrato, ou a spec, o plano e o contrato. O portão
compara isso com os arquivos a cada execução, então uma mudança feita depois
da aceitação, por um modelo ou por qualquer pessoa, fica visível e devolve a
entrega para a pessoa. Os registros ficam em `approvals/`, fora da impressão
digital da árvore, e não carregam assinatura: eles vinculam conteúdo, não
identidade. Eles existem para que os dois pontos de parada sejam fatos que a
CLI pode verificar, em vez de frases em uma conversa.

## Dois portões

Sem confiança externa, `check` valida gramática, cobertura, os registros de
aceitação da pessoa, o escopo declarado, a forma dos critérios, os
comandos/resultados exatos de evidência, os testes nomeados por critério, a
atualidade e as regras locais do contrato. O sucesso é **checked**.
Como os arquivos candidatos são editáveis pelo autor, isso não alega
execução autenticada nem aceitação humana. `deliver` recusa um check apenas
local.

Com uma política externa versionada, o sucesso é **verified**. O portão
exige adicionalmente evidência de CI assinada, aprovações de produto e
engenharia precedendo a verificação, aceitação de QA, mapeamentos de
critério para tarefa, conteúdo candidato commitado e regras corporativas.
Adiamentos de bloqueador/maior exigem aprovação de risco assinada com
expiração. Mudanças de contrato exigem novas decisões relacionadas aceitas,
com aprovação de engenharia confiável. Contratos excluídos e histórico
ausente falham.

## Modos de confiança

Dois modos carregam o mesmo portão. No modo `ssh`, a autoridade é uma chave
cadastrada: humanos assinam aprovações, um coletor assina a evidência de CI, e
uma chave comprometida é revogada trocando a política. No modo `provider`, a
autoridade é a conta do provedor e a identidade da plataforma de CI: o worker
protegido lê as aprovações do PR ao vivo com um token somente leitura, e a
evidência carrega uma atestação de artefato que vincula seu digest ao workflow
que a produziu, verificada com a ferramenta da própria plataforma. O modo
provider foi escolhido como recomendação padrão porque remove a custódia de
chaves, o custo que impedia a maioria das organizações de rodar o portão
confiável, mantendo as propriedades que importam: aprovações vinculadas ao
conteúdo, revogação detectada a cada execução, evidência que não pode ser
substituída depois. O que ele não pode carregar é um prazo de validade, por
isso as exceções de risco ficam no modo ssh.

## Autoridade e criptografia

Assinaturas SSH destacadas vinculam os bytes exatos do artefato a uma
identidade cadastrada em uma política controlada pela organização, fora do
repositório candidato. Cada artefato também vincula o repositório e o
digest da política. O digest da política é fixado (pinned) na CI protegida.
Um arquivo allowed-signers local ao candidato não seria uma âncora de
confiança, então o portão recusa políticas locais ao candidato.

Uma chave humana só é tão independente quanto sua custódia. Um agente com
essa chave pode assinar; nenhuma CLI consegue inferir presença humana a
partir de uma assinatura. O cadastro de identidade humana, o isolamento de
chaves, a integridade do verificador instalado e a configuração de branch
protegido pertencem ao perímetro de confiança da organização.

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

## Identidades duráveis

As specs vivas fazem merge por ID de requisito, mantendo os IDs de critério.
Títulos podem mudar sem mudar a identidade. Novos IDs são alocados acima do
máximo encontrado nos artefatos vivos, ativos e arquivados. A comparação de
três vias detecta edições concorrentes ao mesmo requisito ou colisões de
posse de critério. Todo requisito e critério de aceitação recebe um ID
estável desde o início.

## Limites operacionais

As regras do contrato verificam caminhos, padrões, dependências e comandos
obrigatórios; elas não provam a correção arquitetural. Mapeamentos de teste
e ponteiros de prova precisam de revisão semântica. O Git exclui arquivos
ignorados das impressões digitais de origem, então mantenha as entradas de
build e os lockfiles rastreados e reproduza o ambiente de execução.
Relatórios são índices e resumos de evidência assinada, não certificações.
Relatórios arquivados descrevem aceitação histórica. Pilotos relatam
observações reais com fonte, tamanhos de amostra e limitações; eles não
inventam ROI.
