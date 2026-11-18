# Especificação

Primeira versão, enxuta. As regras de negócio (`RN-xx`) da primeira versão estão na seção 5. Os requisitos de tela (`RF-xx`) estão na seção 7. Os números de RN e RF removidos não são reaproveitados.

## 1. Objetivo e escopo

Aplicação web para uma família estudar viagens possíveis e decidir qual fazer, gerenciar os gastos da viagem escolhida e manter o histórico das viagens concluídas com seus custos.

Na primeira versão:

- Viagens, com nome e datas de início e fim (exceto em stand-by).
- Destinos de cada viagem, com país e cidade.
- Roteiro dia a dia, com atividades ligadas a gastos.
- Gastos por categoria. Não há separação entre planejado e realizado: tudo é gasto.
- Viagens possíveis e planejadas, em estudo antes de decidir. A comparação é avaliação subjetiva do usuário.
- Viagens em stand-by (adiadas ou congeladas), sem datas, editáveis com gastos e roteiro por dia numerado, que podem voltar ao planejamento.
- Viagens em planejamento, com os gastos somados ao longo da pesquisa.
- Viagens concluídas, agrupadas por ano, com os gastos.
- Resumo de gastos por ano, das viagens em planejamento e das concluídas.
- Classificação da viagem como nacional ou internacional (rótulo e filtro).
- Gastos em qualquer moeda, com cotação sugerida por API e editável pelo usuário.

Fora da primeira versão:

- Divisão de despesas entre participantes.
- Checklists de reservas.
- Gráficos e relatórios.
- Orçamento (total ou por categoria).
- Planejado separado de realizado.
- IOF, calculado ou estimado.
- Spread cambial do banco ou da operadora.

## 2. Usuários e acesso

- Um único espaço compartilhado da família.
- As contas são criadas pelo administrador. Não há cadastro por conta própria.
- Todo membro autenticado vê e edita todas as viagens. Não há papéis por viagem.

## 3. Moeda

- A viagem é gerida e apresentada em BRL.
- Um gasto pode ser lançado em qualquer moeda. A cotação é sugerida por API e pode ser alterada pelo usuário.
- O valor em BRL é gravado no momento do lançamento. Mudanças posteriores de cotação não alteram relatórios passados.

## 4. Glossário

| Termo | Significado |
|---|---|
| Viagem | Plano com nome, destinos, roteiro e gastos. Tem data de início e data de fim, exceto em stand-by. |
| Viagem possível | Viagem em planejamento, ainda não escolhida, com data de início e fim, usada para comparar opções. |
| Stand-by | Viagem adiada ou congelada, sem datas de início e fim e fora das telas de planejamento. Pode ser editada com gastos e roteiro em dias numerados (dia 1, dia 2 e assim por diante). |
| Destino | Local visitado em uma viagem, com país e cidade. |
| Dia do roteiro | Um dia da viagem com suas atividades. |
| Categoria | Tipo de gasto (por exemplo, hospedagem, transporte, alimentação). |
| Gasto | Valor lançado em uma viagem, antes, durante ou depois dela, com categoria, moeda e valor. Não se distingue planejado de realizado. |
| Cotação | Taxa para converter uma moeda em BRL. Sugerida por API e editável pelo usuário. |
| País | Código ISO 3166-1 alfa-2 de um destino (por exemplo, BR, US). |
| Moeda | Código ISO 4217 de um gasto (por exemplo, BRL, USD, EUR). |
| Viagem internacional | Viagem com pelo menos um destino fora do Brasil. As demais são nacionais. |
| Forma de pagamento | Cartão de crédito, cartão de débito, cartão pré-pago, dinheiro ou Pix. |
| Cartão pré-pago | Cartão com saldo em uma ou mais moedas, carregado antes de gastar. |
| Saldo | Valor já comprado ou carregado em cartão pré-pago ou em espécie, usado para pagar gastos. |

## 5. Regras de negócio

Os números das regras não são reaproveitados. As regras RN-09 a RN-12, RN-15, RN-19 e RN-20 (IOF, orçamento e custo cancelável) deixaram de existir com a mudança de escopo.

**Viagem e destinos**

- RN-01: cada destino tem um país, informado pelo código ISO 3166-1 alfa-2, e uma cidade dentro desse país. Ao cadastrar um destino, o país (padrão: Brasil) e a cidade são sempre informados. Destinos importados do banco antigo podem estar sem cidade.
- RN-02: uma viagem é internacional se pelo menos um destino tem país diferente de BR; as demais são nacionais. Viagens com destinos mistos são internacionais. A classificação é derivada dos destinos, serve como rótulo e filtro e não restringe moedas.
- RN-03: toda viagem tem data de início e data de fim, exceto a viagem em stand-by, que pode não ter datas. A data de fim não pode ser anterior à data de início. A data de fim não conclui nem fecha a viagem: isso exige confirmação do usuário.
- RN-04: gastos podem ter data anterior à data de início da viagem.
- RN-05: viagens possíveis podem ser criadas em quantidade para estudo. A comparação entre elas é avaliação subjetiva do usuário; o sistema não define critérios.
- RN-06: viagem concluída fica no histórico, com seus custos totais.

**Moeda e cotação**

- RN-07: cada gasto tem uma moeda ISO 4217. A moeda sugerida é a moeda do país do destino.
- RN-08: a cotação é sugerida por API externa e pode ser alterada pelo usuário. A cotação usada é gravada no lançamento. No cartão de crédito, cada gasto tem a sua própria cotação.

**Saldo**

- RN-13: a compra de moeda em espécie e a carga de cartão pré-pago são lançadas como saldo, com moeda, valor e cotação. Não há IOF.
- RN-14: a compra de moeda em espécie ou a carga de cartão pré-pago não é um custo em si: é dinheiro que se gasta depois. Ela entra no total como gasto "Compra de moeda estrangeira não alocada" enquanto o saldo não for usado. Um gasto pago com saldo tira o seu valor em BRL do saldo não alocado, assim o custo não é contado duas vezes. O total da viagem é a soma dos gastos, incluindo o saldo não alocado. Ao concluir a viagem e confirmar, o saldo não alocado restante é encerrado e vai para as categorias "Outros gastos de cartão pré-pago" ou "Outros gastos com dinheiro", conforme o tipo do saldo, sem contar o custo de novo. Um gasto pago com saldo é feito na moeda do saldo e usa o custo em BRL definido na RN-22.

- RN-16: ao lançar um gasto em uma moeda para a qual há saldo, o sistema pergunta se será pago com o saldo ou com outra forma de pagamento (por exemplo, cartão de crédito).
- RN-17: saldos podem existir em mais de uma moeda. Cada saldo tem uma moeda e um custo em BRL, que é o valor pago na compra ou na carga.
- RN-18: a viagem está em um de três estados: stand-by, em planejamento ou concluída. A viagem em stand-by não tem data obrigatória, não aparece nas telas de planejamento e pode ser editada com gastos e roteiro em dias numerados (dia 1, dia 2 e assim por diante). Ela volta ao planejamento quando o usuário a inclui nele. As mudanças de estado permitidas são: stand-by para em planejamento; em planejamento para stand-by ou para concluída; concluída para em planejamento (reabrir). Uma viagem em stand-by só é concluída depois de voltar ao planejamento. Ao ir para stand-by, as datas da viagem são apagadas e a data de cada atividade vira o número do dia (dia 1 é a data de início); atividades anteriores à data de início mantêm a data. Ao voltar ao planejamento, o usuário informa as datas de início e fim, e o dia N de cada atividade vira a data de início mais N − 1 dias.
- RN-21: qualquer membro autenticado pode excluir dados lançados por outro membro.
- RN-22: o custo em BRL de um gasto pago com saldo é o custo médio por unidade do saldo da mesma moeda e do mesmo tipo (cartão pré-pago ou dinheiro) multiplicado pelo valor gasto. O custo médio é recalculado a cada compra ou carga: (custo em BRL restante + custo da nova compra) ÷ (valor restante + valor comprado).
- RN-23: a página de viagens concluídas é agrupada por ano e mostra o total gasto de cada ano. A página de planejamento mostra o total gasto por ano nas viagens em planejamento. O ano de uma viagem é o ano da data de fim. Viagens em stand-by ficam fora desses totais.
- RN-24: uma atividade do roteiro pode ter vários gastos ligados a ela, para lançar os valores diretamente na atividade. Cada gasto pode ser ligado a no máximo uma atividade, ou a nenhuma.
- RN-25: cada gasto tem uma categoria.

## 6. Decisões em aberto

- Nenhuma decisão em aberto no momento.

## 7. Requisitos funcionais

Cada requisito cita as regras de negócio em que se baseia. Todas as telas exigem usuário autenticado (RF-02).

**Acesso**

- RF-01: o usuário entra com nome de usuário e senha. As contas são criadas pelo administrador (seção 2).
- RF-02: qualquer tela, sem login, redireciona para a tela de login.
- RF-03: o usuário autenticado pode sair, encerrando a sessão.

**Viagens**

- RF-04: lista de viagens em planejamento e concluídas, estas agrupadas por ano, em tabelas com uma linha por viagem: nome, data de início, data de fim e total gasto em BRL, com o link "Editar" apenas nas viagens em planejamento (as concluídas e as em stand-by não têm; elas são editadas pela página da viagem). Dentro de cada tabela, a viagem que termina por último vem primeiro. As viagens em stand-by ficam em uma página própria, "Viagens em stand-by", acessível por um link na lista, com a mesma tabela e as mais recentemente criadas primeiro. As duas páginas podem ser filtradas por viagens nacionais ou internacionais. O total não conta de novo a compra ou a carga de saldo (RN-02, RN-14, RN-18, RN-23).
- RF-05: criar e editar viagem com nome e datas de início e fim (opcionais em stand-by). Ao criar, o usuário informa também o primeiro destino, com país (padrão: Brasil) e cidade (RN-01, RN-03).
- RF-06: acrescentar outros destinos de uma viagem pelo botão "Acrescentar novo destino", sempre com país (padrão: Brasil) e cidade, e remover destinos (RN-01).
- RF-07: montar o roteiro por data, ou por dia numerado em stand-by, com atividades em cada dia (RN-18, RN-24).
- RF-08: mudar o estado da viagem pela página da viagem, com uma página de confirmação que explica o efeito: mover para stand-by, voltar ao planejamento (informando as datas), concluir e reabrir. A conclusão exige confirmação do usuário (RN-03, RN-14, RN-18).
- RF-09: excluir uma viagem em planejamento ou em stand-by, somente após confirmação do usuário, que vê quantos destinos, atividades e despesas serão apagados com ela. Viagens concluídas ficam no histórico e não podem ser excluídas. Qualquer membro pode excluir, inclusive o que foi lançado por outro (RN-06, RN-21).

**Despesas**

- RF-10: lançar gasto com data (opcional), categoria, moeda sugerida pelo país do destino, valor, forma de pagamento e cotação sugerida e editável. O gasto pode ser ligado a uma atividade (RN-04, RN-07, RN-08, RN-24, RN-25).
- RF-12: listar os gastos de uma viagem, com o total em BRL.

**Saldos**

- RF-13: registrar compra de moeda em espécie e carga de cartão pré-pago, com moeda, valor e cotação (RN-13, RN-17).
- RF-14: ao lançar gasto em moeda com saldo, perguntar se será pago com o saldo. Pago com saldo, o custo em BRL usa o custo médio (RN-14, RN-16, RN-22).
- RF-16: ao concluir a viagem, mostrar o saldo não alocado e encerrá-lo nas categorias de "Outros gastos" somente após confirmação (RN-14).

**Planejamento e histórico**

- RF-17: mostrar o total gasto por ano, nas viagens em planejamento (RN-23).
- RF-19: mostrar as viagens concluídas por ano, com o total gasto de cada viagem e de cada ano (RN-06, RN-23).
