# Referência da CLI

Todos os comandos podem ser executados de qualquer lugar dentro do projeto;
o AtipSpec encontra a raiz procurando `.atipspec/config.yaml`. Erros
imprimem `AtipSpec: error: ...` e saem com 1. Nada é armazenado entre
comandos: `status` e `check` calculam tudo a partir dos arquivos e do git.

## Projeto

### `atipspec init`

```text
atipspec init [--name NAME] [--language LANG] [--client ID]...
```

Cria `.atipspec/` com `config.yaml`, `contract.md`, `overview.md`,
`glossary.md`, as pastas `specs/`, `deliveries/`, `archive/`,
`decisions/`, `initiatives/`, a cópia do framework e os skills dos
clientes selecionados. Pergunta pelo que as flags não fornecem quando
executado em um terminal; caso contrário, usa o nome da pasta, `en` e
nenhum cliente.

Em um projeto já inicializado: mostra o estado e, em um terminal, um menu
para adicionar ou remover clientes, atualizar o framework, ou mudar nome e
idioma. Com flags, aplica-as diretamente.

### `atipspec install`

```text
atipspec install [--client ID]... [--update]
```

Instala o framework e os skills dos clientes informados sem sobrescrever
nada que seja diferente. `--update` substitui os arquivos do framework e
dos skills que diferem da versão instalada da CLI. Sem `--client`,
pergunta em um terminal, ou usa os clientes já instalados com `--update`.

### `atipspec status`

```text
atipspec status [SLUG]
```

Sem um slug: nome do projeto, branch, se o contrato existe, specs vivas,
cada entrega aberta com seu status derivado, owner e próxima ação, avisos
de sobreposição, iniciativas com progresso, slugs entregues. Com um slug:
o mesmo relatório que `check`.

### `atipspec audit`

Verifica todo o repositório contra as regras do contrato (dependências
sempre), a validade de cada spec viva e decisão, os tamanhos dos
documentos contra seus limites, sobreposições entre entregas abertas, e os
roadmaps das iniciativas. Sai com 1 em caso de erros.

### `atipspec curate`

Regenera o bloco de índice de `overview.md`, relata os tamanhos dos
documentos contra seus limites e imprime o workflow do curate, que
reescreve a prosa.

## Fases

Um comando por fase. Cada um verifica o que a fase exige e sai com 1 com
uma linha nomeando a etapa faltante; caso contrário, imprime
`Phase <name>: <title>`, o status derivado, o workflow da fase a partir de
`.atipspec/framework/workflows/`, as regras compartilhadas e, para
`explore`, `spec`, `plan` e `build`, a saída de `atipspec context`.
Veja [o fluxo](../flow/index.md#o-que-cada-fase-exige) para os
pré-requisitos.

```text
atipspec explore SLUG [--no-context]
atipspec spec SLUG [--no-context]
atipspec fix SLUG [--no-context]        only for a delivery created with --kind fix
atipspec plan SLUG [--no-context]
atipspec build SLUG [--no-context]      also names the next task without a commit
atipspec review SLUG [--out FILE]       writes the reviewer packet when the prerequisites hold
atipspec deliver SLUG --policy PATH     see below
atipspec contract                       prints the workflow and the current contract.md
atipspec curate                         regenerates the overview index, reports sizes, prints the workflow
atipspec ship SLUG                      prints the next phase the delivery can enter
```

`--no-context` imprime o workflow sem o material de contexto, para
reentrar em uma fase na mesma sessão.

## Aceitação

### `atipspec accept`

```text
atipspec accept SLUG proposal [--by WHO]
atipspec accept SLUG result [--by WHO]
atipspec accept SLUG spec [--by WHO]
atipspec accept SLUG plan [--by WHO]
atipspec accept contract
```

A pessoa aprova na conversa e o agente executa o comando. O uso manual continua disponível. `spec` recusa enquanto um
requisito não tiver critério ou uma pergunta estiver aberta; caso
contrário, define `status: ready` e escreve `approvals/local-spec.json`
com um hash de `spec.md` e do contrato. `plan` exige uma spec aceita e um
plan sem erros, e registra o hash do spec, do plan e do contrato.
`contract` define `status: accepted` em `contract.md`. `--by` usa por
padrão o `user.email` do git.

`check` compara o hash registrado com os arquivos: depois de qualquer
edição, a entrega volta a ser draft (ou o plan fica não aceito) até que a pessoa aprove o conteúdo alterado e a aceitação seja registrada novamente. Com `--policy`, as aprovações
assinadas prevalecem e esses registros são ignorados.

## Entregas

### `atipspec new`

```text
atipspec new SLUG --title TITLE [--capability NAME] [--impact NAME]...
                  [--owner WHO] [--ticket ID] [--initiative SLUG]
                  [--branch | --worktree] [--kind feature|fix]
```

Cria `deliveries/SLUG/` com `spec.md` (status draft, base = commit
atual), `plan.md` e `deferred.md`. `--kind fix` cria um reparo de defeito:
uma spec com um critério de regressão a preencher, um plan de uma única
tarefa cujo `Verify:` lista os comandos obrigatórios do contrato, sem
aceitação de plan, e `atipspec fix` como sua fase (veja
[fix](../flow/fix.md)). `--branch` cria e muda para `delivery/SLUG`;
`--worktree` cria essa branch em `../<repo>-SLUG` e escreve a entrega lá.
`--initiative` registra a entrega no roadmap.

### `atipspec check`

```text
atipspec check SLUG
```

O portão. Sai com 0 quando verde, 1 com erros, 2 incompleto. Veja
[como funciona](../getting-started/how-it-works.md#o-portao) para os
níveis.

### `atipspec context`

```text
atipspec context SLUG [--out FILE] [--summary]
```

Imprime o material para a entrega com um resumo de tamanho contra
`context_budget`. `--out` escreve em um arquivo; `--summary` imprime
apenas os tamanhos.

### `atipspec verify`

```text
atipspec verify SLUG [--task Tn]... [--timeout SECONDS]
```

Executa os comandos `Verify` de cada tarefa a partir da raiz do projeto
através do shell, imprime a cauda da saída deles, e escreve
`evidence/Tn-<timestamp>.json`. Sai com 1 se algum comando falhar. Requer
git.

### `atipspec review`

```text
atipspec review SLUG [--out FILE]
```

Recusa, sem escrever nada, enquanto uma tarefa não tiver commit, a
evidência estiver ausente ou desatualizada, ou o contrato for violado.
Caso contrário, escreve o pacote do revisor em
`.atipspec/tmp/SLUG-review-packet.md`: rubrica, contrato, as specs vivas
na lista de impact, as decisões aceitas que as afetam, spec, plan,
deferred, resumo de evidência, arquivos fora do `scope` do plan, o diff
contra a base (limitado a 200 KB, com `--stat` quando truncado) e
arquivos não rastreados; depois imprime o workflow de review.

### `atipspec deliver`

```text
atipspec deliver SLUG --policy /secure/company.toml
```

Exige um check confiável verde, evidência autenticada e aprovações
humanas. Mescla os requisitos na spec viva da capacidade, define
`status: delivered`, move a pasta para `archive/`.

## Decisões e iniciativas

### `atipspec decision`

```text
atipspec decision SLUG --title TITLE [--affects NAME]...
```

Cria `decisions/DEC-nnn-SLUG.md` com status `proposed`. `--affects`
recebe nomes de capacidades, `contract`, `contract:<section>` ou `*`.

### `atipspec initiative`

```text
atipspec initiative SLUG --title TITLE
```

Cria `initiatives/SLUG/roadmap.md`.

## Códigos de saída

| Código | Significado |
| --- | --- |
| 0 | concluído; para `check`, verde |
| 1 | erro, ou para `check` e `audit`, vermelho |
| 2 | `check`: incompleto, trabalho restante |
| 130 | cancelado pelo teclado |

## Aceitação confiável

| Comando | Finalidade |
| --- | --- |
| `enterprise-init [--out directory]` | Escreve exemplos de política, CI e adoção sem ativá-los |
| `approval-subject <slug> <phase>` | Imprime o marcador de aprovação vinculado a conteúdo/head |
| `approve <slug> <phase> --identity id --key path --policy path` | Assina a partir de uma identidade humana registrada |
| `sync-approvals <slug> <phase> --number n --identity id --key path --policy path` | Coleta aprovação humana existente do GitHub/GitLab, somente leitura |
| `attest <slug> --identity id --key path --run-url url --policy path` | O coletor protegido assina a evidência de CI |
| `check <slug> --policy path [--policy-sha256 hash] [--number n] [--json]` | Portão confiável; o padrão sem política é apenas um check local; `--number` indica o PR ou MR no modo provider |
| `report <slug> --format json\|markdown\|html [--out path] [--policy path]` | Dossiê e matriz de rastreabilidade |
| `ids <capability>` | Mostra os próximos IDs de requisito/critério |
| `pilot init <name>` | Cria um protocolo vazio de avaliação no mundo real |
| `pilot record <name> ...` | Registra uma observação completa e referenciada; veja `--help` |
| `pilot report <name>` | Compara coortes registradas, com tamanhos de amostra e limitações |

Fases: `spec`, `plan`, `acceptance`, `decision:DEC-nnn`, `exception:Fn`.
Exceções exigem `--expires` com um timestamp ISO futuro com timezone.
`verify` aceita `--policy` e exige aprovação de spec/plan antes de
executar. `deliver` exige uma política e aceitação confiável completa.
`ATIPSPEC_TRUST_POLICY`, `ATIPSPEC_POLICY_SHA256` e `ATIPSPEC_PR_NUMBER` são
alternativas de ambiente protegidas às flags de comando. Nunca as derive de documentos
candidatos.

Veja [adoção empresarial](../enterprise.md) para o perímetro de
confiança, isolamento de CI, custódia de chaves e integração somente
leitura com provedores.
