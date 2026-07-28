# Guia de Conteúdo do Bolaverso

Tudo que você precisa para manter o blog vivo e chegar ao AdSense: calendário de 16
semanas, rascunhos prontos para editar, templates reutilizáveis e SEO básico.

**Meta:** 15-20 artigos em 3-4 meses (1 por semana). Aí aplica para o AdSense.

**Seu fluxo (30 min por artigo):**
1. Abre o rascunho correspondente da semana (estão neste guia)
2. Ajusta os números olhando o bolaverso.com (as probabilidades da semana)
3. Personaliza com sua opinião / o que rolou na rodada
4. Salva como arquivo `.md` na pasta `src/content/blog/`
5. `git pull` → `git add` → `commit` → `push`

---

## Como criar um artigo novo (passo técnico)

Cada artigo é um arquivo `.md` dentro de `src/content/blog/`. O nome do arquivo
vira o endereço (ex: `titulo-do-post.md` → bolaverso.com/blog/titulo-do-post).

Todo artigo começa com este cabeçalho (o "frontmatter"), entre as linhas com `---`:

```markdown
---
titulo: "Título que aparece na página e no Google"
descricao: "Resumo de 1 linha. Importante para SEO — aparece na busca do Google."
data: 2026-08-03
autor: Bolaverso
tags: [analise, rodada]
---

Aqui começa o texto do artigo...
```

Regras do nome do arquivo: tudo minúsculo, sem espaços (use hífens), sem acentos.
Bom: `palmeiras-dispara-na-lideranca.md`. Ruim: `Palmeiras Dispara.md`.

---

## SEO básico (para aparecer no Google)

Não precisa virar especialista. Cinco regras que resolvem 90%:

1. **Título com a palavra que as pessoas buscam.** Pensa no que alguém digitaria no
   Google. "Chances do Flamengo no Brasileirão" é melhor que "A caminhada rubro-negra".
   O termo de busca tem que estar no título.

2. **A descrição (no cabeçalho) vende o clique.** É o textinho que aparece embaixo do
   título no Google. Faça-a informativa e curiosa, até ~155 caracteres.

3. **Primeiro parágrafo direto ao ponto.** O Google (e o leitor) lê as primeiras linhas
   para entender do que se trata. Não enrole na abertura.

4. **Use os nomes por extenso.** "Palmeiras", "Flamengo", "rebaixamento", "Libertadores"
   — as palavras que as pessoas buscam. Evite só apelidos.

5. **Link interno.** Sempre que fizer sentido, aponte para o simulador
   (`[veja as chances atualizadas](/)`) ou para outro artigo. Isso ajuda o SEO e mantém
   a pessoa no site.

---

## Calendário editorial — 16 semanas

Alternamos dois tipos:
- **Rodada** (R): comenta o que mudou nas probabilidades. Rápido, sempre tem assunto.
- **Perene** (P): assunto que traz tráfego constante do Google, não depende da rodada.

| Semana | Tipo | Título sugerido |
|--------|------|-----------------|
| 1 | R | Como a [rodada] mexeu nas chances de título |
| 2 | P | O que significa "chance de rebaixamento" de verdade |
| 3 | R | Os times que mais subiram e caíram nas probabilidades |
| 4 | P | Por que o líder nem sempre é o favorito ao título |
| 5 | R | A luta pela Libertadores: quem está com vantagem |
| 6 | P | Como funciona o modelo que prevê o Brasileirão |
| 7 | R | Zona de rebaixamento: os números da rodada |
| 8 | P | Já aconteceu? Viradas históricas no Brasileirão |
| 9 | R | O jogo da rodada que mais muda probabilidades |
| 10 | P | Mando de campo: quanto vale jogar em casa nos números |
| 11 | R | Reta final: as chances de título a X rodadas do fim |
| 12 | P | O que a estatística acerta (e erra) no futebol |
| 13 | R | Rebaixamento: contas e cenários da rodada |
| 14 | P | Comparando: nossos números vs outras previsões |
| 15 | R | A rodada decisiva: o que está em jogo |
| 16 | P | Retrospecto: o modelo acertou o campeão? |

Depois da semana 16, você repete o ciclo com a temporada em andamento, sempre
comentando rodadas + inserindo perenes novos. Nunca falta assunto.

---

## RASCUNHO 1 — Semana 1 (Rodada)

Copie, ajuste os números olhando o site, publique.

```markdown
---
titulo: "Como a última rodada mexeu nas chances de título do Brasileirão"
descricao: "Palmeiras e Flamengo disparam, mas os números ainda guardam surpresas. Veja o que mudou nas probabilidades."
data: 2026-08-03
autor: Bolaverso
tags: [analise, rodada, titulo]
---

A cada rodada do Brasileirão, as chances de título mudam — às vezes pouco, às vezes
de forma decisiva. Depois dos jogos deste fim de semana, o cenário na briga pela taça
ficou assim.

## O líder segue firme

O Palmeiras se mantém como favorito, com cerca de XX% de chance de título segundo a
simulação. [Comente aqui o que aconteceu com o líder na rodada — venceu? empatou?
o que isso fez com o número?]

## O perseguidor não desiste

Logo atrás, o Flamengo aparece com XX%. [Comente o jogo do Flamengo e como a distância
para o líder afeta a conta. Lembre que jogo a menos ou a mais muda bastante.]

## Ainda dá para sonhar?

Do terceiro colocado para baixo, as chances caem rápido. [Cite o terceiro e quarto
colocados e seus percentuais. Explique por que, mesmo com poucos pontos de diferença,
a probabilidade despenca — cada rodada que passa reduz o número de jogos para virar.]

## O que esperar

[Uma ou duas frases sobre a próxima rodada: algum confronto direto? algum jogo que
pode mudar muito as contas?]

Você pode acompanhar as [probabilidades atualizadas diariamente](/) aqui no Bolaverso.
Os números mudam sozinhos a cada rodada.
```

---

## RASCUNHO 2 — Semana 2 (Perene)

```markdown
---
titulo: "O que significa 'chance de rebaixamento' de verdade"
descricao: "Seu time tem 30% de chance de cair. Isso é muito ou pouco? Entenda o que os números realmente dizem."
data: 2026-08-10
autor: Bolaverso
tags: [metodologia, rebaixamento]
---

"Seu time tem 30% de chance de rebaixamento." Essa frase assusta muita gente — mas o
que ela significa exatamente? Vamos destrinchar, porque entender o número muda a forma
de encarar a tabela.

## Probabilidade não é destino

30% de chance de cair quer dizer que, se o restante do campeonato fosse disputado 100
vezes, em cerca de 30 delas o time terminaria no Z4. Nas outras 70, se salvaria. Ou
seja: é mais provável escapar do que cair — mas o risco é real e não dá para relaxar.

## Por que o número muda tanto de uma rodada para outra

Uma única vitória pode derrubar a chance de rebaixamento de 40% para 25%. Parece
exagero, mas faz sentido: quando faltam poucas rodadas, cada resultado pesa muito mais.
Três pontos ganhos são três pontos que os concorrentes não têm como recuperar.

## O perigo dos "pontos de conforto"

Torcedores costumam achar em uma certa pontuação a salvação garantida. A estatística é
menos generosa: depende de quantos times estão na briga e do calendário de cada um. Por
isso a simulação olha todos os cenários possíveis, não uma regra fixa.

## Como ler nossa tabela

No [simulador do Bolaverso](/), a coluna Z4 mostra a chance de rebaixamento de cada
time, atualizada diariamente. Quanto mais vermelha a barra, maior o perigo.

Rebaixamento se decide no detalhe — e acompanhar as probabilidades ajuda a enxergar o
tamanho real do risco, sem pânico e sem falsa tranquilidade.
```

---

## RASCUNHO 3 — Semana 3 (Rodada)

```markdown
---
titulo: "Os times que mais subiram e caíram nas probabilidades esta semana"
descricao: "A rodada mexeu com as contas do Brasileirão. Veja quem ganhou e quem perdeu chances de título, Libertadores e permanência."
data: 2026-08-17
autor: Bolaverso
tags: [analise, rodada]
---

Nem sempre o placar conta a história toda. Às vezes uma vitória magra vale mais em
probabilidade do que uma goleada — depende de contra quem, e de como os concorrentes se
saíram. Veja quem mais mexeu os ponteiros nesta rodada.

## Maior alta da rodada

[Time que mais subiu] foi o que mais ganhou pontos percentuais. [Explique: em qual
métrica subiu — título, G5 ou permanência —, de quanto para quanto, e por quê.]

## Maior queda

Do outro lado, [time que mais caiu] viu suas chances despencarem. [Explique o que
aconteceu: perdeu jogo direto? os concorrentes venceram?]

## A rodada dos concorrentes

Às vezes um time nem joga bem, mas sobe nas probabilidades porque os rivais tropeçaram.
[Comente algum caso assim na rodada, se houve.]

## Panorama

[Frase de fechamento sobre como fica a tabela e o que observar na próxima rodada.]

Acompanhe as [chances atualizadas](/) todos os dias no Bolaverso.
```

---

## TEMPLATE — Artigo de Rodada (reutilizável)

Toda semana de rodada, use esta estrutura. Troca só o conteúdo:

```markdown
---
titulo: "[O que aconteceu] — chances do Brasileirão após a rodada"
descricao: "[Uma frase sobre a mudança principal da rodada]."
data: AAAA-MM-DD
autor: Bolaverso
tags: [analise, rodada]
---

[Abertura: 2 frases sobre o clima da rodada — teve zebra? confronto direto? líder
tropeçou?]

## [Subtítulo sobre o topo da tabela]
[O que mudou na briga pelo título / Libertadores]

## [Subtítulo sobre o meio ou a base]
[O que mudou na luta contra o rebaixamento]

## [Subtítulo sobre um destaque]
[Um time específico que chamou atenção nos números]

## O que vem por aí
[1-2 frases sobre a próxima rodada]

Veja as [probabilidades atualizadas](/) no Bolaverso.
```

---

## TEMPLATE — Artigo Perene (reutilizável)

Para os assuntos que não dependem da rodada:

```markdown
---
titulo: "[Pergunta ou afirmação curiosa sobre futebol e dados]"
descricao: "[Provocação de 1 linha que dá vontade de clicar]."
data: AAAA-MM-DD
autor: Bolaverso
tags: [metodologia]
---

[Abertura: apresente a dúvida ou curiosidade. Por que isso é interessante?]

## [Primeiro ponto]
[Explique com clareza, linguagem simples]

## [Segundo ponto]
[Aprofunde ou traga um exemplo]

## [Terceiro ponto]
[Um dado surpreendente, uma comparação, um mito derrubado]

## [Fechamento]
[Conclusão + link para o simulador ou outro artigo]

[Frase final conectando ao Bolaverso.]
```

---

## Ideias extras de perenes (banco de pauta)

Quando faltar assunto, puxe daqui. Todos são buscados no Google e atemporais:

- Quantos pontos, historicamente, garantem o título do Brasileirão?
- Quantos pontos, historicamente, livram do rebaixamento?
- O que é o modelo de Poisson e por que ele prevê futebol
- Por que jogar em casa dá vantagem (e quanto, em números)
- Os maiores azarões que se salvaram do rebaixamento na história
- Os maiores vice-campeonatos perdidos na reta final
- Como as casas de aposta calculam odds (e a diferença para probabilidade)
- Por que um empate às vezes ajuda mais que uma vitória (cenários de tabela)
- O impacto de um jogo adiado nas contas do campeonato
- Título simbólico do primeiro turno: vale alguma coisa estatisticamente?

---

## Ritmo sustentável (o mais importante)

Não tente escrever 5 artigos numa tacada e sumir por um mês. O Google valoriza
**regularidade**. Melhor 1 por semana, sempre, do que 8 num dia e nada depois.

Sugestão prática: escolha um dia fixo (ex: toda segunda, depois da rodada) e reserve os
30 minutos. Vira hábito. Em 4 meses você tem os ~16 artigos e o histórico de site ativo
que o AdSense quer ver.

Quando chegar lá, é só aplicar — e aí a gente vê a parte do AdSense com calma.
```

