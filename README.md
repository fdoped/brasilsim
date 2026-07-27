# BrasilSim

Site estático que exibe probabilidades diárias no Brasileirão Série A. Simulação de Monte
Carlo com ensemble de três modelos (Poisson + Dixon-Coles + Elo), rodada automaticamente
todo dia pelo GitHub Actions.

## Arquitetura

```
Uma vez por dia (9h UTC / 6h Brasília):
   GitHub Action → baixa GE → roda 30.000 sims → gera JSON → commit
   Vercel/Cloudflare detecta commit → build Astro em 30s → deploy

Quando alguém visita o site:
   CDN serve HTML puro estático → <1s → zero requisição a API
```

**Custo total:** apenas o domínio (~R$40/ano). Hospedagem grátis. Sem servidor Python
rodando 24/7. Sem chance de o GE bloquear (uma requisição por dia, do IP do GitHub).

## Estrutura

```
brasilsim/
├── .github/workflows/atualizar.yml    → cron diário
├── scripts/
│   ├── simulador.py                   → motor Monte Carlo
│   └── atualizar.py                   → orquestra tudo, escreve JSON
├── src/
│   ├── data/probabilidades.json       → gerado pelo Action
│   ├── layouts/Base.astro             → layout global
│   ├── pages/
│   │   ├── index.astro                → simulador
│   │   ├── sobre, metodologia,
│   │   ├── privacidade, termos,
│   │   ├── contato, 404.astro
│   │   └── blog/                      → índice + template
│   ├── content/blog/*.md              → artigos em markdown
│   └── content/config.ts
├── public/                            → favicon, robots.txt
├── astro.config.mjs
└── package.json
```

## Como colocar no ar (passo a passo)

### 1. Criar o repositório

```bash
cd brasilsim/
git init
git add .
git commit -m "primeira versão"
git branch -M main
# criar repositório vazio no github.com/seu-usuario/brasilsim
git remote add origin https://github.com/SEU-USUARIO/brasilsim.git
git push -u origin main
```

### 2. Deploy no Cloudflare Pages (grátis)

Recomendação: Cloudflare Pages em vez de Vercel — mais generoso no plano grátis, CDN
melhor e nunca "dorme".

1. Entre em [pages.cloudflare.com](https://pages.cloudflare.com) → **Create a project**
2. Conecte sua conta do GitHub e escolha o repositório `brasilsim`
3. Configuração de build:
   - Framework preset: **Astro**
   - Build command: `npm run build`
   - Build output directory: `dist`
4. Deploy

Em 1-2 minutos, o site sai em `brasilsim.pages.dev`.

### 3. Comprar domínio e apontar

1. Compre em [Registro.br](https://registro.br) (`.com.br` ~R$40/ano) ou
   [Namecheap](https://namecheap.com) (`.com` ~US$12/ano)
2. No painel do Cloudflare Pages, aba **Custom domains**, adicione seu domínio
3. O Cloudflare mostra os nameservers a configurar no registrar do seu domínio
4. Propagação em algumas horas
5. Edite `astro.config.mjs` trocando `brasilsim.com.br` pelo seu domínio real

### 4. Verificar o GitHub Action

Depois do primeiro push, vá em **Actions** no GitHub. O workflow "Atualizar probabilidades"
aparece. Rode manualmente (botão "Run workflow") para verificar que funciona sem esperar
até 6h da manhã do dia seguinte.

### 5. Google Search Console

Cadastre o site em [Search Console](https://search.google.com/search-console) e submeta o
sitemap `https://SEU-DOMINIO/sitemap-index.xml`. Isso ajuda o Google a indexar as páginas
rapidamente.

## Sobre monetização com AdSense

**Não aplique imediatamente.** Regra prática que funciona:

1. Publicar o site.
2. Escrever pelo menos 15 artigos no blog (frequência ~1/semana ou 2/quinzena).
3. Esperar 3-4 meses com atualização consistente.
4. Ter Google Analytics instalado (mostra tráfego real).
5. Aplicar para AdSense. Chance de aprovação sobe muito.

Aplicar antes disso quase certamente resulta em rejeição, e ficar no radar deles com
histórico de rejeição atrapalha depois. Melhor esperar e aprovar de primeira.

Alternativas de monetização enquanto o AdSense não vem:
- Links de afiliados para livros de estatística no futebol (Amazon Associados).
- "Compre um café" via Pix/PicPay em uma página dedicada.
- Anúncios de casas de apostas (juridicamente arriscado no Brasil sem CNPJ e cadastro, cuidado).

## Rodando localmente

```bash
# Instalar dependências
npm install
pip install numpy scipy requests

# Gerar dados (roda a simulação uma vez)
cd scripts && python atualizar.py && cd ..

# Servir o site local
npm run dev
# abre em http://localhost:4321
```

## Rodada de conteúdo sugerida

Para o AdSense aprovar, você precisa parecer ativo. Cronograma sustentável:

- **Toda segunda-feira** um post curto (500-800 palavras) comentando a rodada. Título tipo
  "O que a rodada X mudou nas chances do seu time" — use o próprio JSON como fonte.
- **Uma vez por mês** um post mais longo (1200+ palavras) sobre metodologia, história, ou
  comparações (ex: "Chance de rebaixamento vs realidade histórica: quantos times sobreviveram").
- **Datas especiais** (fim de turno, últimas 5 rodadas) merecem post próprio.

15 artigos ao longo de 3-4 meses = território de aprovação do AdSense.

## Manutenção

- **Zero atenção diária necessária.** O GitHub Action cuida sozinho.
- **Semanal:** escrever um artigo, revisar se as probabilidades parecem sãs (comparar com
  UFMG/Google como sanity check).
- **Se o GE mudar de layout:** a Action vai começar a usar dados de exemplo (fallback).
  Você percebe porque os números param de mudar. Ajuste `_extrai_ge_json` em `simulador.py`.
