# Especificação

Primeira versão, enxuta. Os requisitos (`RF-xx`) e as regras de negócio (`RN-xx`) serão acrescentados em uma segunda etapa.

## 1. Objetivo e escopo

Aplicação web para uma família planejar viagens e acompanhar o que foi realmente gasto, comparando o planejado com o realizado.

Na primeira versão:

- Viagens, com nome, datas e um orçamento total em BRL.
- Destinos de cada viagem.
- Roteiro dia a dia.
- Custos planejados por categoria.
- Despesas realizadas.
- Comparação entre planejado e realizado.

Fora da primeira versão:

- Consulta automática de câmbio.
- Divisão de despesas entre participantes.
- Checklists de reservas.
- Gráficos e relatórios além da comparação.
- Orçamento por categoria.

## 2. Usuários e acesso

- Um único espaço compartilhado da família.
- As contas são criadas pelo administrador. Não há cadastro por conta própria.
- Todo membro autenticado vê e edita todas as viagens. Não há papéis por viagem.

## 3. Moeda

- A viagem é gerida e apresentada em BRL.
- Uma despesa pode ser lançada em outra moeda, com a cotação informada manualmente.
- O valor em BRL é gravado no momento do lançamento. Mudanças posteriores de cotação não alteram relatórios passados.

## 4. Glossário

| Termo | Significado |
|---|---|
| Viagem | Plano com nome, datas, destinos, roteiro, custos planejados e orçamento total. |
| Destino | Local visitado em uma viagem. |
| Dia do roteiro | Um dia da viagem com suas atividades. |
| Categoria | Tipo de gasto (por exemplo, hospedagem, transporte, alimentação). |
| Custo planejado | Valor estimado de uma categoria antes da viagem. |
| Despesa realizada | Valor efetivamente gasto, lançado durante ou depois da viagem. |
| Cotação | Taxa informada manualmente para converter uma moeda em BRL. |
| Orçamento | Valor total em BRL que a família pretende gastar na viagem. |

## 5. Decisões em aberto

- O plano é congelado quando a viagem é marcada como concluída? (Proposta: sim, para manter a comparação fiel ao que foi planejado.)
- Quando a viagem não tem orçamento definido, a comparação continua válida, mas sem o valor "restante"?
- Um membro pode excluir dados lançados por outro?
