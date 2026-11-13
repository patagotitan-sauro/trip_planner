# Especificação

Primeira versão, enxuta. As regras de negócio (`RN-xx`) da primeira versão estão na seção 5. Os requisitos de tela (`RF-xx`) estão na seção 7.

## 1. Objetivo e escopo

Aplicação web para uma família estudar viagens possíveis e decidir qual fazer, gerenciar os gastos da viagem escolhida e manter o histórico das viagens concluídas com seus custos.

Na primeira versão:

- Viagens, com nome, datas de início e fim (exceto em stand-by) e um orçamento total em BRL, opcional.
- Destinos de cada viagem, com país e cidade.
- Roteiro dia a dia, com atividades ligadas a despesas.
- Custos planejados por categoria.
- Despesas realizadas, com IOF quando aplicável.
- Viagens possíveis e planejadas, em estudo antes de decidir. A comparação é avaliação subjetiva do usuário.
- Viagens em stand-by (adiadas ou congeladas), sem datas, editáveis com custos planejados e roteiro por dia numerado, que podem voltar ao planejamento.
- Viagens em planejamento, com os custos planejados somados ao longo da pesquisa.
- Viagens concluídas, agrupadas por ano, com os custos realizados.
- Resumo de custos por ano: planejados (viagens em planejamento) e realizados (viagens concluídas).
- Classificação da viagem como nacional ou internacional (rótulo e filtro).
- Despesas em qualquer moeda, com cotação sugerida por API e editável pelo usuário.

Fora da primeira versão:

- Divisão de despesas entre participantes.
- Checklists de reservas.
- Gráficos e relatórios.
- Orçamento por categoria.
- Spread cambial do banco ou da operadora.

## 2. Usuários e acesso

- Um único espaço compartilhado da família.
- As contas são criadas pelo administrador. Não há cadastro por conta própria.
- Todo membro autenticado vê e edita todas as viagens. Não há papéis por viagem.

## 3. Moeda

- A viagem é gerida e apresentada em BRL.
- Uma despesa pode ser lançada em qualquer moeda. A cotação é sugerida por API e pode ser alterada pelo usuário.
- O valor em BRL é gravado no momento do lançamento. Mudanças posteriores de cotação não alteram relatórios passados.

## 4. Glossário

| Termo | Significado |
|---|---|
| Viagem | Plano com nome, destinos, roteiro, custos planejados e orçamento opcional. Tem data de início e data de fim, exceto em stand-by. |
| Viagem possível | Viagem em planejamento, ainda não escolhida, com data de início e fim, usada para comparar opções. |
| Stand-by | Viagem adiada ou congelada, sem datas de início e fim e fora das telas de planejamento. Pode ser editada com custos planejados e roteiro em dias numerados (dia 1, dia 2 e assim por diante). |
| Destino | Local visitado em uma viagem, com país e cidade. |
| Dia do roteiro | Um dia da viagem com suas atividades. |
| Categoria | Tipo de gasto (por exemplo, hospedagem, transporte, alimentação). |
| Custo planejado | Valor estimado de uma categoria para uma viagem futura. Usado para planejar gastos e alocar saldos. |
| Despesa realizada | Valor efetivamente gasto, lançado antes, durante ou depois da viagem. |
| Cotação | Taxa para converter uma moeda em BRL. Sugerida por API e editável pelo usuário. |
| País | Código ISO 3166-1 alfa-2 de um destino (por exemplo, BR, US). |
| Moeda | Código ISO 4217 de uma despesa (por exemplo, BRL, USD, EUR). |
| Viagem internacional | Viagem com pelo menos um destino fora do Brasil. As demais são nacionais. |
| Forma de pagamento | Cartão de crédito, cartão de débito, cartão pré-pago, dinheiro ou Pix. |
| Cartão pré-pago | Cartão com saldo em uma ou mais moedas, carregado antes de gastar. A carga gera IOF. |
| Saldo | Valor já comprado ou carregado em cartão pré-pago ou em espécie, usado para pagar despesas. |
| IOF | Imposto cobrado em despesas em moeda estrangeira. |
| Orçamento | Valor total em BRL que a família pretende gastar na viagem. Opcional, inclusive para planejar viagens. |

## 5. Regras de negócio

**Viagem e destinos**

- RN-01: cada destino tem um país, informado pelo código ISO 3166-1 alfa-2, e uma cidade dentro desse país. Ao cadastrar um destino, o país (padrão: Brasil) e a cidade são sempre informados. Destinos importados do banco antigo podem estar sem cidade.
- RN-02: uma viagem é internacional se pelo menos um destino tem país diferente de BR; as demais são nacionais. Viagens com destinos mistos são internacionais. A classificação é derivada dos destinos, serve como rótulo e filtro e não restringe moedas.
- RN-03: toda viagem tem data de início e data de fim, exceto a viagem em stand-by, que pode não ter datas. A data de fim não pode ser anterior à data de início. A data de fim não conclui nem fecha a viagem: isso exige confirmação do usuário.
- RN-04: despesas podem ter data anterior à data de início da viagem.
- RN-05: viagens possíveis podem ser criadas em quantidade para estudo. A comparação entre elas é avaliação subjetiva do usuário; o sistema não define critérios.
- RN-06: viagem concluída fica no histórico, com seus custos totais.

**Moeda e cotação**

- RN-07: cada despesa tem uma moeda ISO 4217. A moeda sugerida é a moeda do país do destino.
- RN-08: a cotação é sugerida por API externa e pode ser alterada pelo usuário. A cotação usada é gravada no lançamento. No cartão de crédito, cada despesa tem a sua própria cotação.

**IOF**

- RN-09: o IOF incide somente em despesa em moeda estrangeira. Despesa em BRL não tem IOF.
- RN-10: alíquotas padrão: cartão de crédito em moeda estrangeira 3,5%; cartão pré-pago e dinheiro (compra de moeda em espécie) 1,1%. Cartão de débito comum e Pix são somente em BRL e não têm IOF.
- RN-11: IOF = valor convertido em BRL × alíquota, arredondado uma única vez para centavos (ROUND_HALF_UP). Não há spread.
- RN-12: as alíquotas são definidas em cada viagem e podem ser alteradas por qualquer membro. Uma alteração vale somente para lançamentos feitos depois dela.
- RN-13: no cartão de crédito em moeda estrangeira, o IOF incide a cada compra. Na compra de moeda em espécie e na carga de cartão pré-pago, o IOF incide no momento da compra ou da carga. Cada um desses lançamentos é uma despesa realizada com IOF.
- RN-14: saldo já comprado ou carregado (cartão pré-pago ou dinheiro) pode ser alocado a custos planejados ou a novas despesas. Essa alocação não gera novo IOF nem novo custo: o custo já foi contado na compra ou na carga. Quando a viagem é marcada como concluída e o usuário confirma, o saldo não alocado é encerrado e vai para as categorias "Outros gastos de cartão pré-pago" ou "Outros gastos com dinheiro", conforme o tipo do saldo. Essa parte entra no realizado dessas categorias, sem contar o custo de novo. Uma despesa paga com saldo é feita na moeda do saldo e usa o custo em BRL definido na RN-22.

**Custo planejado e saldo**

- RN-15: o custo planejado inclui o IOF estimado pela forma de pagamento prevista.
- RN-16: ao lançar uma despesa em uma moeda para a qual há saldo, o sistema pergunta se a despesa será paga com o saldo ou com outra forma de pagamento (por exemplo, cartão de crédito). A resposta define se o IOF é cobrado naquele lançamento.
- RN-17: saldos podem existir em mais de uma moeda. Cada saldo tem uma moeda e um custo em BRL, que inclui o IOF pago na compra ou na carga.
- RN-18: a viagem está em um de três estados: stand-by, em planejamento ou concluída. A viagem em stand-by não tem data obrigatória, não aparece nas telas de planejamento e pode ser editada com custos planejados e roteiro em dias numerados (dia 1, dia 2 e assim por diante). Ela volta ao planejamento quando o usuário a inclui nele.
- RN-19: orçamento é opcional. Os custos planejados são somados à medida que a pesquisa avança. Sem orçamento, não há valor restante a exibir.
- RN-20: uma despesa planejada pode ser marcada como cancelável, com a data limite de cancelamento informada pelo usuário.
- RN-21: qualquer membro autenticado pode excluir dados lançados por outro membro.
- RN-22: o custo em BRL de um gasto pago com saldo é o custo médio por unidade do saldo da mesma moeda e do mesmo tipo (cartão pré-pago ou dinheiro), com o IOF já pago, multiplicado pelo valor gasto. O custo médio é recalculado a cada compra ou carga: (custo em BRL restante + custo da nova compra) ÷ (valor restante + valor comprado).
- RN-23: a página de viagens concluídas é agrupada por ano e mostra o total realizado de cada ano. A página de planejamento mostra o total planejado por ano. O ano de uma viagem é o ano da data de fim. Viagens em stand-by ficam fora desses totais.
- RN-24: uma atividade do roteiro pode ter várias despesas ligadas a ela, para lançar os gastos diretamente na atividade. Cada despesa pode ser ligada a no máximo uma atividade, ou a nenhuma.
- RN-25: cada despesa, planejada ou realizada, tem uma categoria.

## 6. Decisões em aberto

- Nenhuma decisão em aberto no momento.

## 7. Requisitos funcionais

Cada requisito cita as regras de negócio em que se baseia. Todas as telas exigem usuário autenticado (RF-02).

**Acesso**

- RF-01: o usuário entra com nome de usuário e senha. As contas são criadas pelo administrador (seção 2).
- RF-02: qualquer tela, sem login, redireciona para a tela de login.
- RF-03: o usuário autenticado pode sair, encerrando a sessão.

**Viagens**

- RF-04: lista de viagens em três grupos: stand-by, em planejamento e concluídas, estas agrupadas por ano. Cada viagem mostra o rótulo nacional ou internacional, e a lista pode ser filtrada por ele (RN-02, RN-18, RN-23).
- RF-05: criar e editar viagem com nome, datas de início e fim (opcionais em stand-by), orçamento opcional e alíquotas de IOF. Ao criar, o usuário informa também o primeiro destino, com país (padrão: Brasil) e cidade (RN-01, RN-03, RN-12, RN-19).
- RF-06: acrescentar outros destinos de uma viagem pelo botão "Acrescentar novo destino", sempre com país (padrão: Brasil) e cidade, e remover destinos (RN-01).
- RF-07: montar o roteiro por data, ou por dia numerado em stand-by, com atividades em cada dia (RN-18, RN-24).
- RF-08: mudar o estado da viagem: incluir uma viagem em stand-by no planejamento e marcar uma viagem como concluída, esta somente após confirmação do usuário (RN-03, RN-14, RN-18).
- RF-09: excluir uma viagem em planejamento ou em stand-by, somente após confirmação do usuário, que vê quantos destinos, atividades e despesas serão apagados com ela. Viagens concluídas ficam no histórico e não podem ser excluídas. Qualquer membro pode excluir, inclusive o que foi lançado por outro (RN-06, RN-21).

**Despesas**

- RF-10: lançar custo planejado com categoria, moeda, valor e forma de pagamento prevista, com IOF estimado, e marcá-lo como cancelável com data limite (RN-15, RN-20, RN-25).
- RF-11: lançar despesa realizada com data, categoria, moeda sugerida pelo país do destino, valor, forma de pagamento e cotação sugerida e editável. O IOF é calculado e gravado no lançamento. A despesa pode ser ligada a uma atividade (RN-04, RN-07 a RN-11, RN-24, RN-25).
- RF-12: listar as despesas de uma viagem, com as planejadas separadas das realizadas.

**Saldos**

- RF-13: registrar compra de moeda em espécie e carga de cartão pré-pago, com moeda, valor e IOF pago (RN-13, RN-17).
- RF-14: ao lançar despesa em moeda com saldo, perguntar se será paga com o saldo. Pago com saldo, o custo em BRL usa o custo médio e não gera novo IOF (RN-14, RN-16, RN-22).
- RF-15: alocar saldo a custos planejados (RN-14).
- RF-16: ao concluir a viagem, mostrar o saldo não alocado e encerrá-lo nas categorias de "Outros gastos" somente após confirmação (RN-14).

**Planejamento e histórico**

- RF-17: mostrar o total planejado por ano e, nas viagens com orçamento, o valor restante (RN-19, RN-23).
- RF-18: listar as despesas planejadas canceláveis, em ordem da data limite (RN-20).
- RF-19: mostrar as viagens concluídas por ano, com o total realizado de cada viagem e de cada ano (RN-06, RN-23).
