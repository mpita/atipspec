# Escrevendo critérios

Uma especificação é tão boa quanto seus critérios, e a indústria já definiu
como é um bom critério: a ISO/IEC/IEEE 29148 pede requisitos singulares,
inequívocos e verificáveis; o INCOSE Guide for Writing Requirements lista as
palavras que tornam um requisito não verificável; o EARS (Easy Approach to
Requirements Syntax) dá as formas de frase; o Specification by Example pede
dados concretos. O template de spec do AtipSpec segue esses guias, e `check`
aplica a parte que uma máquina consegue checar.

## As formas que `check` aceita

Com `criteria_syntax: ears` (o padrão), um critério começa com um gatilho ou
carrega um `shall`:

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
*debe* ou *deberá* perto do início; os gatilhos em inglês contam em todo
idioma, porque os templates são em inglês. Um critério em outra forma recebe
um aviso nomeando-a; defina `criteria_syntax: free` para desligar essa
checagem de forma. Um idioma sem tabelas não recebe checagem de forma e usa a
lista de termos vagos em inglês. A checagem de termos vagos permanece ligada
em todo modo. Um critério pode ser listado sob `Tests:` em mais de uma tarefa
quando várias tarefas o exercitam.

## Termos vagos

A regra do guia do INCOSE: nenhum termo cujo significado dependa do leitor.
`check` avisa quando um critério contém um destes, em inglês ou espanhol:

`fast`, `quickly`, `user-friendly`, `easy`, `appropriate`, `adequate`,
`efficient`, `robust`, `etc.`, `and/or`, `as needed`, `if possible`,
`reasonable`, `sufficient`, `several`, `many`, `some`, `approximately`,
`seamless`, `intuitive`, `optimal`, `flexible`, `scalable`, `timely`,
`minimal`, `maximize`, `minimize`.

A correção é sempre a mesma: substituir o adjetivo pelo valor observável.
"Responds quickly" vira "responds within 300 ms at the 95th percentile".

Com `strict_criteria: true`, ambas as checagens são erros e bloqueiam a
aceitação; por padrão são avisos que a fase spec deve resolver antes de
apresentar a spec.

## Teste ou manual

Todo critério é provado por um teste ou observado por uma pessoa. Marque o
segundo tipo na spec, no momento em que é escrito:

```markdown
- AC-005 [manual]: When the label prints, it shows the order code in Code 128.
```

O plano deve respeitar a marca: um critério `[manual]` listado sob `Tests:` é
um erro, assim como um não marcado sob `Manual:`. Todo critério deve aparecer
sob um dos dois; até que apareça, `check` reporta um pendente e `atipspec
build` recusa. A marca viaja com o critério para a spec viva.

## Suposições

O modelo propõe padrões quando você hesita. Elas não são silenciosas: cada
uma é um requisito e uma entrada sob `## Assumptions`, e o portão lembra você
de confirmá-las na aceitação. Uma suposição que você rejeita vira uma
pergunta ou um requisito diferente.

## Atributos de qualidade

Desempenho, capacidade, disponibilidade e segurança usam o mesmo formato
`REQ`/`AC` sob `## Quality attributes`, com um número e uma forma de medi-lo,
seguindo o Planguage de Gilb e os cenários de atributo de qualidade do SEI:

```markdown
### REQ-004: Response time of the reset request

Acceptance criteria:
- AC-006: When 100 users request a reset within one minute, the p95 response
  time measured at the API gateway is below 300 ms.
```

Um atributo de qualidade sem número é um adjetivo, e a checagem de termos
vagos o trata como tal.

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
- Karl Wiegers and Joy Beatty, Software Requirements, third edition, 2013.
- Tom Gilb, Competitive Engineering (Planguage), 2005.
