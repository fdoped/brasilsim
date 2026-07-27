---
titulo: "Como o BrasilSim se compara ao simulador da UFMG"
descricao: "A UFMG é referência acadêmica em simulações do Brasileirão. Explicamos o que o BrasilSim faz igual, e o que faz diferente."
data: 2026-07-26
autor: BrasilSim
tags: [metodologia, comparacao]
---

O laboratório de Matemática da UFMG mantém há anos um dos simuladores mais respeitados do
Brasileirão, publicando probabilidades semanais para clubes e imprensa. É referência.

Ao calibrar o BrasilSim, usamos as probabilidades da UFMG como referência para verificar
sanidade dos números. Quando construímos o motor, o teste era: com os dados da rodada X, o
que a UFMG está publicando? Se batíamos, bom sinal. Se não, algo estava mal calibrado.

## O que fazemos igual

**Ambos usam Monte Carlo.** Simular milhares de vezes o restante do campeonato e contar
quantas vezes cada time termina em cada posição é o método padrão da literatura acadêmica
de esportes. Não tem "truque" — o que muda é como você modela cada jogo dentro da simulação.

**Ambos usam algum modelo de gols do tipo Poisson.** A distribuição de Poisson é o pilar
histórico da modelagem estatística de futebol desde os anos 80, e faz sentido: o número de
gols de uma equipe num jogo se ajusta razoavelmente a essa distribuição, com a taxa
esperada calculada a partir da força de ataque e defesa dos envolvidos.

**Ambos modelam mando de campo.** Jogar em casa dá uma vantagem consistente, historicamente
medida em cerca de 0,2 a 0,3 gols esperados a mais para o mandante.

## O que fazemos diferente

**Ensemble em vez de modelo único.** A UFMG usa uma variação de Poisson bem afinada. O
BrasilSim roda três modelos independentes (Poisson, Dixon-Coles e Elo) e tira a média. Nossa
hipótese é que erros de cada modelo, se independentes entre si, tendem a se cancelar. É a
mesma lógica de ensembles em machine learning.

**Modelagem explícita de incerteza (σ).** Aqui está uma decisão importante do BrasilSim: no
meio da temporada, a força medida de cada time (a partir de gols pró/contra em ~20 jogos)
tem incerteza significativa. Se um time tem taxa de ataque muito alta em 20 jogos, é
provável que essa taxa seja alta *de verdade*, mas também é provável que a taxa "verdadeira"
seja um pouco menos extrema — regressão à média. O BrasilSim reamostra a força a cada
simulação, refletindo essa incerteza. Sem isso, o líder do campeonato aparece com
probabilidades exageradas (algo como 90% de título quando lidera por 6 pontos com folga).

**Somos abertos sobre o método.** A UFMG explica em termos gerais, mas o código é fechado.
Nosso motor é comentado, o cálculo pode ser reproduzido e a decisão de cada parâmetro
(σ = 0,40, ρ = -0,05, mando = 0,25) está justificada na
[página de metodologia](/metodologia/).

## Diferenças esperadas

Nossos números vão bater com os da UFMG na maior parte dos casos, tipicamente dentro de 2-3
pontos percentuais para times relevantes. Quando divergirem mais, provavelmente é porque:

- Os modelos diferem naturalmente perto de faixas competitivas (ex: quando 3-4 times têm
  chances de título parecidas, pequenas diferenças de calibração viram grandes diferenças
  de probabilidade).
- O componente Elo do nosso ensemble captura força de forma um pouco diferente, dando peso
  extra a séries recentes de vitórias.

Nosso objetivo não é competir com a UFMG — a referência acadêmica dela é sólida. É
oferecer uma alternativa aberta, com número claros, para quem quer entender como esses
cálculos funcionam.
