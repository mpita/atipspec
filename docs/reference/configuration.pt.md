# Configuração

`.atipspec/config.yaml`, escrito por `init`:

```yaml
name: shop
language: es
approve_plan: true
review_rounds: 2
context_budget: 800
strict_scope: false
criteria_syntax: ears
strict_criteria: false
max_requirements: 5
max_tasks: 8
max_age_hours: 48
```

| Chave | Padrão | Significado |
| --- | --- | --- |
| `name` | nome da pasta | nome do projeto, exibido por `status` |
| `language` | `en` | idioma em que o modelo escreve os artefatos; `en`, `es` e `pt` também orientam o lint de critérios, os nomes de seção que o parser aceita e o dossiê de aceitação. Outro código funciona com as tabelas em inglês, e `audit` avisa isso |
| `approve_plan` | `true` | `atipspec build` recusa até a pessoa executar `atipspec accept <slug> plan` |
| `review_rounds` | `2` | rodadas de revisão sem um check verde antes de o modelo parar e reportar |
| `context_budget` | `800` | linhas; `atipspec context` avisa acima disso |
| `strict_scope` | `false` | quando verdadeiro, um arquivo alterado fora do `scope` do plano é um erro em vez de um aviso |
| `criteria_syntax` | `ears` | `ears` avisa sobre critérios que não começam com um gatilho ou não trazem um shall; `free` desliga essa checagem |
| `strict_criteria` | `false` | quando verdadeiro, as checagens de forma e de termos vagos nos critérios são erros e bloqueiam a aceitação |
| `max_requirements` | `5` | `check` avisa quando uma spec tem mais requisitos: uma entrega deve caber em um dia de trabalho |
| `max_tasks` | `8` | `check` avisa quando um plano tem mais tarefas |
| `max_age_hours` | `48` | `status` avisa quando uma entrega está aberta há mais tempo que isso, em horas de relógio |
| `system` | não definido | caminho para um checkout do repositório de sistema; seu `contract.md` e `glossary.md` entram em todo contexto |

Apenas `name` e `language` são gerenciados por `atipspec init`; edite o
restante manualmente. `init --language en` em um projeto existente mantém as
outras chaves.

## `.atipspec/.gitignore`

Criado por `init`; ignora `tmp/`, onde os pacotes de revisão são escritos.
Todo o resto sob `.atipspec/` deve ser commitado: o contrato, as specs vivas,
as entregas com suas evidências e revisões, o arquivo.

## Ambiente

| Variável | Efeito |
| --- | --- |
| `NO_COLOR` | desabilita cores na saída do terminal |
| `TERM=dumb` | o mesmo |

## Confiança da organização

As configurações locais do projeto orientam o assistente; elas não podem
flexibilizar a aceitação confiável. `approve_plan: false` pula a cerimônia
conversacional, não a exigência de aprovação de engenharia confiável. A
política TOML externa controla papéis, chaves públicas, regras corporativas e
identidades de provedores. Ela deve viver fora do candidato.

`ATIPSPEC_TRUST_POLICY` seleciona essa política; `ATIPSPEC_POLICY_SHA256`
fixa seu conteúdo. Use a configuração protegida da organização, não valores
fornecidos pelo projeto. Os adaptadores GitHub/GitLab usam `GITHUB_TOKEN` /
`GITLAB_TOKEN` somente leitura no coletor confiável. O executor de verificação
remove essas credenciais dos ambientes de comando. Veja a
[aceitação empresarial](../enterprise.md).
