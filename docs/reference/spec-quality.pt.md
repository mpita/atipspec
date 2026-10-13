# Escrever critérios

Uma especificação é tão boa quanto seus critérios, e a indústria já definiu
como é um bom critério: a ISO/IEC/IEEE 29148 pede requisitos singulares,
inequívocos e verificáveis; o INCOSE Guide for Writing Requirements lista as
palavras que tornam um requisito não verificável; o EARS (Easy Approach to
Requirements Syntax) dá as formas de frase; o Specification by Example pede
dados concretos; o Volere pede a todo atributo de qualidade um critério de
adequação (fit criterion). O workflow do AtipSpec segue esses guias, e
`check` aplica a parte que uma máquina consegue verificar.

## O que `check` verifica

| Verificação | Onde | Nível |
| --- | --- | --- |
| Estrutura do cenário: WHEN e THEN em ordem, nenhum passo vazio | todo cenário | erro |
| Forma EARS ou de cenário | declarações de critério (`- AC-001: ...`) | estrito |
| Nenhum termo vago | títulos e declarações de requisitos; declarações de critério; títulos de cenário e todo passo | estrito |
| Um número no resultado | critérios de um atributo de qualidade | estrito |
| Como é medido | critérios de um atributo de qualidade | aviso |
| Um valor concreto no resultado | todos os outros critérios | aviso |
| Nenhum termo vago entre aspas | onde quer que a verificação de termos vagos leia | aviso |
| `## Intent`, `## Out of scope` e `## Quality attributes` decididas | o `spec.md` de uma entrega guiada | pendência até que a proposta seja aprovada |

Um achado estrito é um erro com `strict_criteria: true`, o padrão, e um aviso
com `strict_criteria: false`. Um erro ou uma pendência da especificação
bloqueia a proposta: `atipspec proposal` o lista sob "Not ready for approval"
e não mostra nenhum código de aprovação, e `atipspec accept` recusa. Um aviso
nunca bloqueia. `proposal` lista todo aviso de especificação sob seu código
de aprovação; o modelo os resolve ou nomeia cada um que mantém quando
apresenta a proposta.

`check` lê os requisitos que a entrega define ou referencia, nunca o resto da
spec viva. Em uma entrega guiada, um requisito da capacidade que difere do
que a spec viva continha no commit base da entrega, adicionado, editado,
apagado ou marcado `[remove]`, mas que não está listado sob `requirements`, é
um erro em todos os níveis de risco, já que a aprovação inclui no hash apenas
os listados e `merge-check` bloqueia um requisito alterado fora das entregas
que o listam: liste-o se esta mudança o escreve, para que `check` o leia, ou
desfaça a mudança. `new` não começa enquanto essa spec viva tem mudanças sem
commit, então o commit base a tem como a entrega parte dela; uma feature
criada antes da 0.3.0 é comparada, em vez disso, com seu `baseline.json`. Um requisito
alterado na spec viva de outra capacidade também é um erro: a entrega não o
entrega, e `merge-check` o bloqueia. O que o branch de integração trouxe
(veja [quando a main avança](../teams.md#quando-a-main-avanca)) ou uma
entrega arquivada no branch depois da base escreveu, tal como seu recibo
registra, e o que outra entrega aberta da capacidade lista, não é mudança da
entrega; o que um merge de qualquer outro branch traz é. Um recibo avaliza
apenas os requisitos que sua entrega lista, tal como o commit que a arquivou
os adicionou, ou, ainda sem commit, enquanto `HEAD` contiver essa entrega
aberta. O texto da spec viva fora dos seus requisitos, antes do primeiro ou
sob um cabeçalho que encerra um, o seu frontmatter, e um comentário HTML ou
um bloco de código cercado num requisito que a entrega não lista não estão
em nenhuma aprovação: uma mudança neles é um warning, em relação à base de
merge onde o branch de integração os alterou, e só os cobre a aceitação do
resultado, que vincula a árvore inteira.

## As formas que `check` aceita

Com `criteria_syntax: ears` (o padrão), uma declaração de critério começa com
um gatilho ou carrega um `shall`:

| Forma | Formato | Exemplo |
| --- | --- | --- |
| Orientada a evento | When *gatilho*, the system *resultado* | When a registered email requests a reset, the system sends a link to that email within 60 seconds. |
| Orientada a estado | While *estado*, the system shall *resultado* | While the account is locked, the system shall reject every login with "account locked". |
| Comportamento indesejado | If *condição*, then the system *resultado* | If a link is older than 30 minutes, then the system returns "link expired" and sends nothing. |
| Funcionalidade opcional | Where *funcionalidade*, the system *resultado* | Where two-factor is enabled, the system asks for the code before showing the form. |
| Ubíqua | The system shall *resultado* | The system shall reject passwords shorter than 12 characters. |
| Cenário | Given *contexto*, when *ação*, then *resultado* | Given an order of 3 items at 10.00, when a 10% coupon is applied, then the total is 27.00. |

Os gatilhos que `check` reconhece são *when*, *whenever*, *while*, *if*,
*where*, *given* e *after* no início do critério, ou *shall* ou *must* na sua
oração principal, antes de qualquer vírgula. Em espanhol: *cuando*,
*mientras*, *si*, *donde*, *dado* (e suas formas), *después de*, *tras*, e
*debe* ou *deberá* na oração principal. Em português: *quando*, *enquanto*,
*se*, *onde*, *dado* (e suas formas), *depois de*, *após*, e *deve* ou
*deverá*. Os gatilhos em inglês contam em todo idioma, porque os templates
são em inglês. Defina `criteria_syntax: free` para desligar a verificação de
forma; as outras verificações continuam ligadas. Um idioma sem tabelas não
recebe verificação de forma e usa a lista de termos vagos em inglês. Uma
declaração de critério pode continuar em linhas recuadas.

## Cenários

Um cenário é um cabeçalho de critério sob seu requisito, com um passo por
linha:

```markdown
### REQ-001: The user can request a reset link

#### AC-001: Registered email
- **GIVEN** a registered user on the "Sign in" page
- **WHEN** the user requests a reset for that email
- **THEN** the system sends a link to that email within 60 seconds
```

O parser verifica a estrutura, diga o que disser `strict_criteria`: WHEN e
THEN são obrigatórios, os passos seguem GIVEN, WHEN, THEN, AND e BUT
estendem o passo anterior, e nenhum passo fica vazio. Um critério
`[invariant]` afirma com INVARIANT ou THEN e não precisa de gatilho. Em
seguida, o lint lê o título do cenário e todo passo em busca de termos vagos.
As palavras de passo em espanhol e português (*DADO*, *CUANDO*, *ENTONCES*,
*QUANDO*, *ENTÃO*, ...) também funcionam, e um cenário escrito com elas
também é lido com os termos vagos desse idioma, seja qual for o idioma do
projeto.

## Termos vagos

A regra do guia do INCOSE: nenhum termo cujo significado dependa do leitor.
`check` reporta um requisito ou um critério que contenha um deles. Em inglês:

`fast`, `quick`, `quickly`, `slow`, `user-friendly`, `user friendly`, `easy`,
`easily`, `easy-to-use`, `appropriate`, `appropriately`, `adequate`,
`adequately`, `efficient`, `efficiently`, `effectively`, `robust`, `etc.`,
`and/or`, `and so on`, `as needed`, `if possible`, `if necessary`,
`when necessary`, `as soon as possible`, `reasonable`, `reasonably`,
`sufficient`, `sufficiently`, `several`, `a few`, `many`, `some`,
`approximately`, `seamless`, `seamlessly`, `intuitive`, `intuitively`,
`optimal`, `optimally`, `flexible`, `scalable`, `as appropriate`,
`where possible`, `timely`, `minimal`, `maximize`, `minimize`, `relevant`,
`typically`, `usually`, `correctly`, `properly`, `as expected`, `as intended`,
`works well`, `work well`.

Em espanhol, junto com a lista em inglês:

`rápido`, `rápida`, `rápidos`, `rápidas`, `rápidamente`, `fácil`, `fáciles`,
`fácilmente`, `amigable`, `amigables`, `adecuado`, `adecuada`, `adecuados`,
`adecuadas`, `adecuadamente`, `apropiado`, `apropiada`, `apropiados`,
`apropiadas`, `apropiadamente`, `eficiente`, `eficientes`, `eficientemente`,
`robusto`, `robusta`, `robustos`, `robustas`, `etc.`, `y/o`,
`y así sucesivamente`, `según sea necesario`, `si es necesario`,
`cuando sea necesario`, `si es posible`, `lo antes posible`, `razonable`,
`razonables`, `razonablemente`, `suficiente`, `suficientes`, `suficientemente`,
`varios`, `varias`, `unos pocos`, `unas pocas`, `muchos`, `muchas`, `algunos`,
`algunas`, `aproximadamente`, `intuitivo`, `intuitiva`, `intuitivos`,
`intuitivas`, `intuitivamente`, `óptimo`, `óptima`, `óptimos`, `óptimas`,
`flexible`, `flexibles`, `escalable`, `escalables`, `cuando sea posible`,
`oportuno`, `oportuna`, `lo mínimo`, `al mínimo`, `mínimo posible`,
`maximizar`, `minimizar`, `relevante`, `relevantes`, `normalmente`,
`habitualmente`, `correctamente`, `como se espera`, `como es de esperar`,
`según lo previsto`, `funciona bien`, `funcione bien`, `sin problemas`.

Em português, junto com a lista em inglês:

`rápido`, `rápida`, `rápidos`, `rápidas`, `rapidamente`, `fácil`, `fáceis`,
`facilmente`, `amigável`, `amigáveis`, `adequado`, `adequada`, `adequados`,
`adequadas`, `adequadamente`, `apropriado`, `apropriada`, `apropriados`,
`apropriadas`, `apropriadamente`, `eficiente`, `eficientes`, `eficientemente`,
`robusto`, `robusta`, `robustos`, `robustas`, `etc.`, `e/ou`,
`e assim por diante`, `conforme necessário`, `se necessário`,
`quando necessário`, `se possível`, `o mais rápido possível`, `o quanto antes`,
`razoável`, `razoáveis`, `razoavelmente`, `suficiente`, `suficientes`,
`suficientemente`, `vários`, `várias`, `alguns poucos`, `muitos`, `muitas`,
`alguns`, `algumas`, `aproximadamente`, `intuitivo`, `intuitiva`, `intuitivos`,
`intuitivas`, `intuitivamente`, `ótimo`, `ótima`, `ótimos`, `ótimas`,
`flexível`, `flexíveis`, `escalável`, `escaláveis`, `quando possível`,
`oportuno`, `oportuna`, `o mínimo`, `ao mínimo`, `mínimo possível`,
`maximizar`, `minimizar`, `relevante`, `relevantes`, `normalmente`,
`geralmente`, `habitualmente`, `corretamente`, `como esperado`,
`conforme esperado`, `conforme previsto`, `funciona bem`, `funcione bem`,
`sem problemas`.

Um termo corresponde a palavras inteiras, também dentro de um composto com
hífen ou de ênfase Markdown: `fast-loading` e `_quickly_` correspondem. Um
token com dois-pontos no meio, como `theme:slow-unresponsive`, e uma
cardinalidade, como `many-to-many`, são identificadores e passam. O texto
entre aspas (`"..."`, `“...”`, `«...»`) ou crases não é lido pela verificação
estrita: cite entre aspas o texto literal da interface, como o botão
`"Fast checkout"`, em vez de reformulá-lo. Uma citação que contém um termo
vago recebe, em vez disso, um aviso, para que a pessoa o veja na proposta, e
não é um valor concreto. Palavras com usos precisos frequentes ficam fora das
listas: *correct* (the correct password), *expected* (`Expected:`), *well*
(well-formed), *significant* (significant digits), *effective* (effective
date) e *a minimum of 12*.

A correção é sempre a mesma: substituir o adjetivo pelo valor observável.
"Responds quickly" vira "responds within 300 ms at the 95th percentile".

## Valores concretos

O Specification by Example pede a cada resultado os dados que um teste
compara. O resultado é o passo THEN ou INVARIANT e os passos AND e BUT depois
dele, ou, em uma declaração de critério, o que vem depois da primeira vírgula
quando o gatilho vem primeiro, e a declaração inteira caso contrário. `check`
avisa quando o resultado não nomeia nenhum valor concreto:

- um número, como `27.00`, `60 seconds` ou `HTTP 404` (o 95 em `p95` nomeia
  um percentil, não um valor);
- texto entre aspas sem termo vago, como `"link expired"`;
- um caminho, como `/orders/paid`, ou um endereço, como `billing@example.com`;
- um nome com maiúscula que não abre a frase, como a página `Sign-in`.

Um número em GIVEN não torna THEN concreto: "Given an order of 3 items at
10.00 ... then the discount is applied" recebe o aviso; "then the total is
27.00" não. Essa verificação é uma heurística, por isso continua sendo um
aviso em todo modo.

## Requisitos

Escreva um requisito por comportamento que um usuário valoriza, independente
de outras mudanças abertas, pequeno o bastante para a entrega e testável: os
critérios INVEST de uma história. `check` lê o título de um requisito e as
linhas que o declaram em busca de termos vagos. Deixa de fora seus critérios,
o rótulo `Acceptance criteria:` (o texto depois dele é lido), um parágrafo
`Why:` (*Por qué:*, *Motivo:*, *Por quê:*), que dá a razão, e um parágrafo
`Observed:` (*Observado:*), que descreve um defeito, não o requisito. Cada um
vai, com a lista sob ele, até uma linha em branco, um critério ou outro
rótulo como `Expected:`; um rótulo sozinho na sua linha também pega o bloco
seguinte. Um item de lista recuado sob uma declaração de critério não faz
parte do critério, então é lido como texto do requisito. Um requisito
marcado `[remove]` mantém o título da spec viva, então apenas seus critérios
são lidos. Um fix guarda a história do defeito sob `## Defect` no seu
`spec.md`, fora de qualquer requisito, e corrige um requisito aceito em
`specs/`, que é lido como qualquer outro.

## Atributos de qualidade e critérios de adequação

Desempenho, capacidade, disponibilidade e segurança são requisitos com
critérios, como qualquer outro comportamento, seguindo o critério de
adequação do Volere e o Planguage de Gilb: o resultado do critério declara o
número com sua unidade, e o critério diz como ele é medido.

Em uma entrega guiada, o requisito vive em `specs/<capability>.md`, e o
`spec.md` da entrega o nomeia sob `## Quality attributes`, uma linha por
requisito:

```markdown
## Quality attributes

- REQ-004: p95 below 300 ms with 100 requests per minute
```

Uma linha que não nomeia nenhum requisito desta mudança é uma pendência
enquanto a proposta é um rascunho e um erro depois disso: o limite deve ser
um requisito com um critério, para que uma tarefa o teste, a revisão lhe dê
um veredito e a evidência o prove. `- None` diz que a mudança não tem
atributo de qualidade. Em uma entrega antiga, o requisito é escrito sob
`## Quality attributes` no seu `spec.md`:

```markdown
### REQ-004: Response time of the reset request

Acceptance criteria:
- AC-006: When 100 users request a reset within one minute, the p95 response
  time measured at the API gateway is below 300 ms.
```

Um critério de um atributo de qualidade sem número no seu resultado é um
achado estrito. Sem uma palavra que diga como é medido (*measured*,
*medido*, *medida*, *medição*), é um aviso: nomeie onde e com o quê.

## Intenção e escopo de uma entrega guiada

`atipspec new` escreve um `spec.md` guiado com `## Intent`,
`## Out of scope` e `## Quality attributes`, e os lista sob `sections` no
`baseline.json` da entrega. Até que a proposta seja aprovada, uma Intent
vazia, ou que só diga `TBD`, `TODO` ou `...`, é uma pendência que bloqueia a
proposta: declare o ator, o gatilho, o resultado observável e como o usuário
saberá que funcionou. Uma seção Out of scope ou Quality attributes sem
nenhum item está indecidida, e também é uma pendência: liste os itens, ou
escreva `- None`. Apagar um desses cabeçalhos também é uma pendência.
Aprovado significa um registro de aprovação local do conteúdo atual; editar
a linha `status` não muda nada. Sob uma política de confiança, cujas
assinaturas são a aprovação, `check` considera em vez disso o `status` que as
pessoas definem; `proposal` e `accept proposal` continuam considerando apenas
o registro local. Uma entrega criada antes da 0.3.0 sem essas duas seções
recebe apenas um aviso, assim como uma entrega cuja proposta está aprovada
para seu conteúdo atual. Esses avisos em uma entrega aprovada esperam a
próxima mudança da sua proposta: editar `spec.md` só por causa deles anula a
aprovação.

## Rigor

Projetos novos têm `strict_criteria: true`: um achado estrito é um erro que
bloqueia a proposta. Projetos inicializados antes da 0.3.0 mantêm o
`strict_criteria: false` que `init` escreveu, em que os achados estritos são
avisos que a fase spec resolve antes de apresentar. `proposal` mostra o modo
antes da aprovação: "Criteria check: strict" ou "warnings only", e diz quando
`criteria_syntax: free` deixa a forma sem verificação. `config.yaml` faz
parte do que a aprovação de uma proposta guiada inclui no hash, então baixar
o modo depois da aprovação deixa essa aprovação desatualizada.

## Teste ou manual

Todo critério é provado por um teste ou observado por uma pessoa. Marque o
segundo tipo na spec, no momento em que é escrito:

```markdown
#### AC-SHIP-4TQ8N-005 [manual]: Printed label
- **WHEN** the label prints
- **THEN** it shows the order code in Code 128
```

A declaração de critério de uma entrega antiga recebe a marca da mesma forma:
`- AC-005 [manual]: When the label prints, it shows the order code in Code 128.`

O plano deve respeitar a marca: um critério `[manual]` listado sob `Tests:` é
um erro, assim como um não marcado sob `Manual:`. Todo critério deve aparecer
sob um dos dois; até que apareça, `check` reporta uma pendência e
`atipspec build` recusa. A marca viaja com o critério para a spec viva. Um
critério pode ser listado sob `Tests:` em mais de uma tarefa quando várias
tarefas o exercitam.

## Suposições

O modelo propõe padrões quando você hesita. Elas não são silenciosas: cada
uma é um requisito e uma entrada sob `## Assumptions`, e o portão lembra você
de confirmá-las na aceitação. Uma suposição que você rejeita vira uma
pergunta ou um requisito diferente.

## Por quê e exemplos

Uma linha `Why:` sob um requisito registra a razão, como pede a ISO 29148;
ela impede que o requisito seja apagado por alguém que já não sabe por que
ele existe. Um exemplo com dados reais, quando o resultado envolve um
cálculo, um formato ou uma data, é o que o Specification by Example chama de
exemplo-chave: o teste e o revisor partem ambos dele.

## Referências

- ISO/IEC/IEEE 29148:2018, Systems and software engineering, requirements engineering.
- INCOSE, Guide for Writing Requirements.
- Alistair Mavin et al., Easy Approach to Requirements Syntax (EARS), 2009.
- Gojko Adzic, Specification by Example, 2011.
- Suzanne Robertson and James Robertson, Mastering the Requirements Process (Volere), third edition, 2012.
- Bill Wake, INVEST in Good Stories, and SMART Tasks, 2003.
- Karl Wiegers and Joy Beatty, Software Requirements, third edition, 2013.
- Tom Gilb, Competitive Engineering (Planguage), 2005.
