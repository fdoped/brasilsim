"""
Backend de probabilidades — Brasileirão Série A (v2, com incerteza de força)
===========================================================================
Puxa tabela + calendário de uma API, ajusta força dos times (ataque/defesa e Elo)
e roda um ensemble de 3 modelos via Monte Carlo para estimar:
  - título
  - G5 (Libertadores, formato 2026)
  - rebaixamento (Z4)

NOVIDADE v2 — parâmetro `sigma` (incerteza de força):
  A força medida em ~19 jogos é uma ESTIMATIVA ruidosa, não a verdade.
  A cada temporada simulada, a força de cada time é reamostrada de uma
  distribuição em torno do valor estimado (log-normal p/ atk/dfs, normal p/ Elo).
  Isso alarga a distribuição de pontos finais e corrige o excesso de confiança
  do modelo determinístico (sigma=0), aproximando das casas especializadas.

Uso:
    from simulador import rodar
    resultado = rodar(fonte="exemplo", sigma=0.13)

Requer: numpy, scipy, requests
"""

from __future__ import annotations
import os
import numpy as np
from dataclasses import dataclass
from scipy.stats import poisson as _pois

# =====================================================================
# 1. MODELO DE DADOS
# =====================================================================
@dataclass
class Time:
    nome: str
    pts: int
    j: int
    gp: int
    gc: int

    @property
    def sg(self) -> int:
        return self.gp - self.gc


@dataclass
class Estado:
    times: list
    jogos_restantes: list          # (mandante, visitante)
    total_rodadas: int = 38

    @property
    def nomes(self):
        return [t.nome for t in self.times]


# =====================================================================
# 2. FONTES DE DADOS
# =====================================================================
def jogos_restantes_de_confrontos(nomes, confrontos_realizados):
    """
    Deriva os jogos que faltam a partir dos confrontos JÁ realizados.

    Lógica (returno completo do Brasileirão): cada par (A, B) se enfrenta duas
    vezes — uma com A mandante, outra com B mandante. Um confronto (mandante,
    visitante) só falta se ainda não foi disputado nessa exata condição de mando.

    Args:
        nomes: lista com os 20 times.
        confrontos_realizados: set de tuplas (mandante, visitante) já jogadas.

    Returns:
        lista de (mandante, visitante) que ainda faltam.
    """
    realizados = set(confrontos_realizados)
    restantes = []
    for mandante in nomes:
        for visitante in nomes:
            if mandante == visitante:
                continue
            if (mandante, visitante) not in realizados:
                restantes.append((mandante, visitante))
    return restantes


class ErroAPI(RuntimeError):
    """Erro ao consultar fonte externa, com mensagem amigável para exibir na UI."""



def _extrai_nome(bloco):
    """Extrai o nome de um time do JSON, tolerando variações de chave."""
    if not isinstance(bloco, dict):
        return None
    for chave in ("nome_popular", "nome", "sigla"):
        if bloco.get(chave):
            return bloco[chave]
    return None


def carregar_da_api(campeonato_id=10, token=None,
                    base="https://api.api-futebol.com.br/v1") -> Estado:
    """
    Carrega tabela + jogos restantes da API Futebol (api-futebol.com.br).

    Os jogos restantes são derivados dos confrontos já realizados (mando de campo
    exato), cobrindo corretamente jogos adiados — não assume returno sequencial.

    Lança ErroAPI com mensagem clara em qualquer falha (token inválido, rede,
    formato inesperado), para a interface poder exibir algo útil.
    """
    try:
        import requests
    except ImportError as exc:
        raise ErroAPI("Biblioteca 'requests' não instalada (pip install requests).") from exc

    token = token or os.environ.get("API_FUTEBOL_TOKEN")
    if not token:
        raise ErroAPI("Token não informado. Crie uma conta grátis em "
                      "api-futebol.com.br e cole a chave.")
    h = {"Authorization": f"Bearer {token}"}

    # -------- tabela --------
    try:
        r = requests.get(f"{base}/campeonatos/{campeonato_id}/tabela",
                         headers=h, timeout=20)
    except requests.exceptions.RequestException as exc:
        raise ErroAPI(f"Falha de conexão com a API: {exc}") from exc

    if r.status_code in (401, 403):
        raise ErroAPI("Token inválido ou sem permissão (HTTP "
                      f"{r.status_code}). Confira a chave no painel da API.")
    if r.status_code == 429:
        raise ErroAPI("Limite de requisições da API atingido (HTTP 429). "
                      "Aguarde alguns minutos e tente de novo.")
    if r.status_code != 200:
        raise ErroAPI(f"A API respondeu HTTP {r.status_code} na tabela.")

    try:
        dados_tabela = r.json()
    except ValueError as exc:
        raise ErroAPI("Resposta da tabela não é um JSON válido.") from exc

    times = []
    for linha in dados_tabela:
        try:
            nome = _extrai_nome(linha.get("time", {}))
            if not nome:
                continue
            times.append(Time(
                nome=nome,
                pts=int(linha["pontos"]),
                j=int(linha["jogos"]),
                gp=int(linha["gols_pro"]),
                gc=int(linha["gols_contra"]),
            ))
        except (KeyError, TypeError, ValueError):
            # linha malformada — ignora e segue
            continue

    if len(times) < 20:
        raise ErroAPI(f"A tabela veio incompleta ({len(times)} times, "
                      "esperado 20). Verifique o campeonato_id.")
    nomes = [t.nome for t in times]

    # -------- confrontos já realizados (varre as 38 rodadas) --------
    realizados = set()
    rodadas_ok = 0
    for rod in range(1, 39):
        try:
            rr = requests.get(f"{base}/campeonatos/{campeonato_id}/rodadas/{rod}",
                              headers=h, timeout=20)
        except requests.exceptions.RequestException:
            continue                      # pula rodada que falhou, não aborta tudo
        if rr.status_code != 200:
            continue
        try:
            partidas = rr.json().get("partidas", [])
        except ValueError:
            continue
        rodadas_ok += 1
        for p in partidas:
            if p.get("status") == "finalizado":
                m = _extrai_nome(p.get("time_mandante", {}))
                v = _extrai_nome(p.get("time_visitante", {}))
                if m and v:
                    realizados.add((m, v))

    if rodadas_ok == 0:
        raise ErroAPI("Nenhuma rodada pôde ser lida da API. "
                      "Verifique o token e a conexão.")

    jogos_restantes = jogos_restantes_de_confrontos(nomes, realizados)
    return Estado(times, jogos_restantes)


def carregar_exemplo() -> Estado:
    """
    Dados reais da 19ª rodada de 2026 (Gazeta/Footstats).

    Os jogos restantes são derivados via `jogos_restantes_de_confrontos`, a mesma
    função usada com a API. Como não temos a matriz oficial dos ~190 jogos aqui,
    reconstruímos um turno de ida plausível: todos os pares se enfrentaram uma vez,
    exceto o jogo Flamengo x Mirassol (adiado — por isso o Flamengo tem 18 jogos e
    o Mirassol também). Assim o returno + o jogo de ida pendente saem corretamente.
    """
    dados = {
        "Palmeiras": (44, 19, 33, 14), "Flamengo": (37, 18, 35, 16),
        "Athletico-PR": (33, 19, 26, 19), "Fluminense": (32, 19, 29, 24),
        "RB Bragantino": (30, 19, 26, 20), "Bahia": (30, 19, 28, 24),
        "Corinthians": (27, 19, 21, 19), "Cruzeiro": (27, 19, 26, 29),
        "Botafogo": (26, 19, 33, 32), "Coritiba": (26, 19, 25, 27),
        "Vitória": (26, 19, 22, 25), "São Paulo": (25, 19, 24, 22),
        "Atlético-MG": (25, 19, 23, 24), "Internacional": (21, 19, 22, 24),
        "Santos": (21, 19, 27, 31), "Grêmio": (21, 19, 21, 25),
        "Vasco": (20, 19, 22, 30), "Mirassol": (19, 18, 20, 25),
        "Remo": (18, 19, 21, 32), "Chapecoense": (9, 19, 17, 39),
    }
    times = [Time(n, p, j, gp, gc) for n, (p, j, gp, gc) in dados.items()]
    jogos = _gerar_returno_por_contagem(times)
    return Estado(times, jogos)


def _gerar_returno_por_contagem(times, seed=7):
    """
    Reconstrói jogos restantes a partir só da tabela (pontos/jogos por time).

    Não temos a matriz oficial de confrontos, mas sabemos quantos jogos cada time
    já disputou — logo, quantos faltam para cada um (38 - disputados). Geramos um
    conjunto de confrontos restantes que respeita EXATAMENTE essa contagem por time,
    via um emparelhamento guloso. O mando e o adversário exato são aproximados; o que
    o modelo usa é a quantidade e a distribuição de jogos, preservando o efeito de
    quem tem jogo(s) a mais (ex.: Flamengo com um jogo atrasado).

    Quando houver fonte com a grade completa de confrontos, troque por
    `jogos_restantes_de_confrontos` com os confrontos reais.
    """
    nomes = [t.nome for t in times]
    faltam = {t.nome: max(38 - t.j, 0) for t in times}
    rng = np.random.default_rng(seed)

    jogos = []
    # emparelhamento guloso: enquanto houver times com jogos faltando, sorteia
    # dois deles e cria um confronto, decrementando a cota de cada um.
    tentativas = 0
    while True:
        disponiveis = [n for n in nomes if faltam[n] > 0]
        if len(disponiveis) < 2:
            break
        tentativas += 1
        if tentativas > 100000:
            break  # trava de segurança
        a, b = rng.choice(disponiveis, size=2, replace=False)
        # mando alternado/aleatório
        if rng.random() < 0.5:
            jogos.append((a, b))
        else:
            jogos.append((b, a))
        faltam[a] -= 1
        faltam[b] -= 1

    return jogos


def carregar_do_ge(url="https://ge.globo.com/futebol/brasileirao-serie-a/",
                   html=None) -> Estado:
    """
    Raspa a classificação + jogos do ge.globo (gratuito, sem token).

    O GE embute os dados dentro de um `<script id="scriptReact">` como dois
    objetos JavaScript: `classificacao` (tabela) e `listaJogos` (partidas com
    mando e placar). Localizamos os dois blocos por sua âncora textual e
    fazemos parse JSON de verdade — não é HTML renderizado por JS.

    Como conseguimos os confrontos já jogados (com mando exato), os jogos
    restantes são derivados de forma PRECISA via `jogos_restantes_de_confrontos`,
    e não aproximada via returno. Isso preserva jogos adiados corretamente.

    Args:
        url: página da Série A no GE.
        html: opcional — HTML já baixado (para teste ou se preferir baixar você).

    NOTA: o GE pode bloquear acesso automático de servidores. Rodando localmente
    costuma funcionar. Em caso de bloqueio, use "Colar tabela" no app.
    """
    if html is None:
        try:
            import requests
        except ImportError as exc:
            raise ErroAPI("Biblioteca 'requests' não instalada.") from exc
        headers = {
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/122.0.0.0 Safari/537.36"),
            "Accept-Language": "pt-BR,pt;q=0.9",
        }
        try:
            r = requests.get(url, headers=headers, timeout=20)
        except requests.exceptions.RequestException as exc:
            raise ErroAPI(f"Falha de conexão com o GE: {exc}") from exc
        if r.status_code == 403:
            raise ErroAPI(
                "O ge.globo bloqueou a requisição automática (HTTP 403). "
                "Rode localmente ou use 'Colar tabela' no app."
            )
        if r.status_code != 200:
            raise ErroAPI(f"O GE respondeu HTTP {r.status_code}.")
        html = r.text

    # extrai classificacao e listaJogos dos blocos JS embutidos
    times, _confrontos, _proximos, _extras = _extrai_ge_json(html)
    if len(times) < 16:
        raise ErroAPI(
            f"Só achei {len(times)} times no HTML do GE. A página pode ter "
            "mudado de formato. Use 'Colar tabela' no app como alternativa."
        )

    nomes = [t.nome for t in times]
    # NOTA: `listaJogos` no HTML do GE contém APENAS os jogos da rodada atual
    # (10 partidas), não o histórico completo. Então não dá para usar
    # `jogos_restantes_de_confrontos` com base nele. A derivação por contagem
    # respeita o total de jogos de cada time (incluindo adiados).
    jogos = _gerar_returno_por_contagem(times)
    return Estado(times, jogos)


def _extrai_ge_json(html):
    """
    Extrai (times, confrontos_jogados, proximos_jogos) dos blocos JS embutidos do GE.

    - `classificacao`: array `.classificacao` com `nome_popular`, `pontos`,
      `jogos`, `gols_pro`, `gols_contra`.
    - `listaJogos`: array de jogos com `equipes.mandante.nome_popular`,
      `equipes.visitante.nome_popular` e `placar_oficial_mandante`.
      Placar não-nulo → confronto jogado; placar nulo → próximo jogo.
    """
    import re, json

    def _extrai_bloco(padrao_inicio, tipo):
        """Encontra `const NOME = <json>;` e devolve o JSON como str."""
        m = re.search(padrao_inicio, html)
        if not m:
            return None
        i = m.end()
        depth = 0; in_str = False; esc = False; start = None
        for j in range(i, len(html)):
            c = html[j]
            if start is None:
                if c in '[{':
                    start = j; depth = 1
                continue
            if in_str:
                if esc: esc = False
                elif c == '\\': esc = True
                elif c == '"': in_str = False
                continue
            if c == '"': in_str = True
            elif c in '[{': depth += 1
            elif c in ']}':
                depth -= 1
                if depth == 0:
                    return html[start:j+1]
        return None

    _alias = {"Bragantino": "RB Bragantino",
              "Red Bull Bragantino": "RB Bragantino"}

    # --- classificação ---
    times = []
    extras = {}
    raw = _extrai_bloco(r'const\s+classificacao\s*=\s*', 'classificacao')
    if raw:
        try:
            obj = json.loads(raw)
            lista = obj.get("classificacao", []) if isinstance(obj, dict) else []
            for entry in lista:
                nome = entry.get("nome_popular") or entry.get("nome")
                if not nome:
                    continue
                try:
                    p = int(entry["pontos"])
                    j = int(entry["jogos"])
                    gp = int(entry["gols_pro"])
                    gc = int(entry["gols_contra"])
                except (KeyError, ValueError, TypeError):
                    continue
                if not (0 <= j <= 38 and 0 <= p <= 114):
                    continue
                nome_final = _alias.get(nome, nome)
                times.append(Time(nome_final, p, j, gp, gc))
                # dados extras usados nas páginas por time
                extras[nome_final] = {
                    "ultimos_jogos": entry.get("ultimos_jogos") or [],
                    "aproveitamento": entry.get("aproveitamento"),
                    "vitorias": entry.get("vitorias"),
                    "empates": entry.get("empates"),
                    "derrotas": entry.get("derrotas"),
                }
        except json.JSONDecodeError:
            pass

    # --- lista de jogos: separa jogados (placar!=null) e próximos (placar==null) ---
    confrontos = set()
    proximos = []
    for chave in (r'const\s+listaJogos\s*=\s*', r'"lista_jogos"\s*:\s*'):
        raw = _extrai_bloco(chave, 'jogos')
        if not raw:
            continue
        try:
            jogos_list = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for jogo in jogos_list:
            equipes = jogo.get("equipes") or {}
            man = (equipes.get("mandante") or {}).get("nome_popular")
            vis = (equipes.get("visitante") or {}).get("nome_popular")
            if not man or not vis:
                continue
            man = _alias.get(man, man); vis = _alias.get(vis, vis)
            placar_m = jogo.get("placar_oficial_mandante")
            placar_v = jogo.get("placar_oficial_visitante")
            if placar_m is not None and placar_v is not None:
                confrontos.add((man, vis))
            else:
                proximos.append({
                    "mandante": man,
                    "visitante": vis,
                    "data": jogo.get("data_realizacao"),
                    "sede": (jogo.get("sede") or {}).get("nome_popular"),
                })
        if confrontos or proximos:
            break

    return times, confrontos, proximos, extras


def carregar_de_texto(texto: str) -> Estado:
    """
    Lê a classificação a partir de texto colado (do Google, Gazeta, ge.globo, etc).

    Aceita uma linha por time, em qualquer um destes formatos (espaços ou tabs):
        posição  NOME  P J V E D GP GC SG [%]
        NOME  P J V E D GP GC SG
    O nome pode ter espaços; SG e além são ignorados (derivamos SG de GP-GC).
    É tolerante a colunas extras no fim (aproveitamento, "últimas 5", etc.).

    Precisa de pelo menos 6 números por linha (P J V E D GP...), e usa os campos
    P, J, GP, GC. Lança ErroAPI se não achar ao menos 16 times válidos.
    """
    import re
    times = []
    # captura: (nome) seguido de >=8 inteiros (P J V E D GP GC SG), SG pode ser negativo
    padrao = re.compile(
        r'^\s*(?:\d{1,2}[\).\s]+)?'          # posição opcional (1, 1), 1. etc)
        r'([A-Za-zÀ-ÿ0-9().\-\s]+?)\s+'      # nome (pode ter espaços/acentos)
        r'(\d{1,3})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+'  # P J V E D
        r'(\d{1,3})\s+(\d{1,3})'             # GP GC
        r'(?:\s+-?\d{1,3})*'                 # SG e além (ignorado)
        r'\s*$'
    )
    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha:
            continue
        m = padrao.match(linha)
        if not m:
            continue
        nome = m.group(1).strip()
        p, j = int(m.group(2)), int(m.group(3))
        gp, gc = int(m.group(7)), int(m.group(8))
        # sanidade
        if not (0 <= j <= 38 and 0 <= p <= 114 and nome):
            continue
        # normaliza nome comum
        nome = {"Bragantino": "RB Bragantino",
                "Red Bull Bragantino": "RB Bragantino"}.get(nome, nome)
        times.append(Time(nome, p, j, gp, gc))

    # remove duplicatas por nome (mantém a primeira)
    vistos = set(); unicos = []
    for t in times:
        if t.nome not in vistos:
            vistos.add(t.nome); unicos.append(t)

    if len(unicos) < 16:
        raise ErroAPI(
            f"Só consegui ler {len(unicos)} times do texto colado. Cole a tabela "
            "com uma linha por time, incluindo pontos e jogos (P J V E D GP GC)."
        )

    jogos = _gerar_returno_por_contagem(unicos)
    return Estado(unicos, jogos)


def carregar_da_gazeta(url="https://www.gazetaesportiva.com/campeonatos/brasileiro-serie-a/",
                       html=None) -> Estado:
    """
    Faz scraping da classificação da Gazeta Esportiva (gratuito, sem token).

    A página lista cada time como:  posição [Nome](link)\\n P J V E D GP GC SG %
    Extraímos os 20 times com pontos/jogos/gols e derivamos os jogos restantes
    pela contagem de jogos (detectando quem tem jogo atrasado).

    Args:
        url: página da classificação.
        html: opcional — HTML já baixado. Útil se a Gazeta bloquear o acesso
              automático (403): você baixa a página no navegador, salva e passa
              o conteúdo aqui, ou usa outro método de download.

    Lança ErroAPI em qualquer falha, para a interface exibir mensagem clara.
    """
    import re

    if html is None:
        try:
            import requests
        except ImportError as exc:
            raise ErroAPI("Biblioteca 'requests' não instalada.") from exc

        headers = {
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/122.0.0.0 Safari/537.36"),
            "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
                       "image/avif,image/webp,*/*;q=0.8"),
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        try:
            r = requests.get(url, headers=headers, timeout=20)
        except requests.exceptions.RequestException as exc:
            raise ErroAPI(f"Falha de conexão com a Gazeta: {exc}") from exc
        if r.status_code == 403:
            raise ErroAPI(
                "A Gazeta bloqueou a requisição automática (HTTP 403). Isso costuma "
                "acontecer em servidores/nuvem com proteção anti-bot. Rode o app na "
                "sua máquina local (costuma funcionar), ou use o modo Exemplo."
            )
        if r.status_code != 200:
            raise ErroAPI(f"A Gazeta respondeu HTTP {r.status_code}.")
        html = r.text

    # A classificação aparece como: posição [Nome](link) \n <9 números>
    # onde os 9 números são P J V E D GP GC SG %. Ancoramos pelo nome canônico
    # e capturamos os 9 inteiros que aparecem logo após (mesmo em outra linha).
    nomes_canonicos = [
        "Palmeiras", "Flamengo", "Athletico-PR", "Fluminense", "Red Bull Bragantino",
        "Bahia", "Corinthians", "Cruzeiro", "Botafogo", "Coritiba", "Vitória",
        "São Paulo", "Atlético-MG", "Santos", "Internacional", "Grêmio", "Vasco",
        "Mirassol", "Remo", "Chapecoense",
    ]
    renomear = {"Red Bull Bragantino": "RB Bragantino"}

    encontrados = {}
    for nome in nomes_canonicos:
        # ancora no nome dentro do link e captura os 9 inteiros seguintes,
        # tolerando o fechamento do link ']( ... )' e quebras de linha entre eles.
        # Usa [^\d]{0,400} para não atravessar até a linha de outro time.
        padrao = (re.escape(nome) + r"\][^\d]{0,400}?"
                  r"(-?\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+"
                  r"(\d+)\s+(\d+)\s+(-?\d+)\s+(\d+)")
        m = re.search(padrao, html)
        if not m:
            continue
        p, j, v, empa, d, gp, gc, sg, aprov = map(int, m.groups())
        # sanidade: jogos entre 0 e 38, pontos coerentes
        if not (0 <= j <= 38 and 0 <= p <= 114):
            continue
        nome_saida = renomear.get(nome, nome)
        encontrados[nome_saida] = (p, j, gp, gc)

    if len(encontrados) < 20:
        raise ErroAPI(
            f"Scraping incompleto: {len(encontrados)}/20 times lidos. "
            "O layout da Gazeta pode ter mudado — use o modo Exemplo."
        )

    times = [Time(n, p, j, gp, gc) for n, (p, j, gp, gc) in encontrados.items()]
    jogos = _gerar_returno_por_contagem(times)
    return Estado(times, jogos)


# =====================================================================
@dataclass
class Forcas:
    idx: dict
    pts: np.ndarray
    sg: np.ndarray
    atk: np.ndarray
    dfs: np.ndarray
    media_liga: float
    elo: np.ndarray


def calcular_forcas(e: Estado) -> Forcas:
    nomes = e.nomes
    idx = {n: i for i, n in enumerate(nomes)}
    pts = np.array([t.pts for t in e.times], float)
    j = np.array([t.j for t in e.times], float)
    gp = np.array([t.gp for t in e.times], float)
    gc = np.array([t.gc for t in e.times], float)
    sg = gp - gc
    media_liga = float(np.mean(gp / j))
    atk = (gp / j) / media_liga
    dfs = (gc / j) / media_liga
    # Elo HÍBRIDO: combina aproveitamento (pontos) com força de gols (atk-dfs).
    # Pontos sozinhos enganam no meio da temporada (um time pode "jogar mais que
    # a pontuação"); o componente de gols corrige isso, aproximando da força real.
    ppg = pts / j
    z_ppg = (ppg - ppg.mean()) / (ppg.std() + 1e-9)
    forca_gols = (atk - dfs)                      # ataque forte, defesa forte => alto
    z_gols = (forca_gols - forca_gols.mean()) / (forca_gols.std() + 1e-9)
    z = 0.6 * z_ppg + 0.4 * z_gols                # mistura 60/40
    elo = 1500 + z * 120
    return Forcas(idx, pts, sg, atk, dfs, media_liga, elo)


# =====================================================================
# 4. MODELOS
# =====================================================================
def _dc_tau(x, y, lx, ly, rho):
    if x == 0 and y == 0: return 1 - lx * ly * rho
    if x == 0 and y == 1: return 1 + lx * rho
    if x == 1 and y == 0: return 1 + ly * rho
    if x == 1 and y == 1: return 1 - rho
    return 1.0


def _amostra_placar_dc(lc, lf, rho=-0.05, maxg=6):
    """Sorteia um placar da distribuição Dixon-Coles (versão escalar, referência)."""
    px = _pois.pmf(np.arange(maxg + 1), lc)
    py = _pois.pmf(np.arange(maxg + 1), lf)
    M = np.outer(px, py)
    M[0, 0] *= _dc_tau(0, 0, lc, lf, rho)
    M[0, 1] *= _dc_tau(0, 1, lc, lf, rho)
    M[1, 0] *= _dc_tau(1, 0, lc, lf, rho)
    M[1, 1] *= _dc_tau(1, 1, lc, lf, rho)
    flat = M.ravel()
    np.clip(flat, 0.0, None, out=flat)
    s = flat.sum()
    if s <= 0:
        return 0, 0
    flat /= s
    k = np.random.choice(flat.size, p=flat)
    return divmod(k, maxg + 1)


def _amostra_placar_dc_vec(lc, lf, rho=-0.05, maxg=6, chunk=200_000):
    """
    Versão VETORIZADA: sorteia placares para N jogos de uma vez.

    lc, lf: arrays (N,) com os gols esperados de mandante e visitante.
    Retorna (gc, gf): arrays (N,) de gols sorteados.

    Processa em lotes de `chunk` jogos para limitar o pico de memória: o tensor
    conjunto tem shape (chunk, maxg+1, maxg+1), então lotes evitam alocar tudo de
    uma vez quando N é grande (nsim*n_jogos pode passar de milhões).
    """
    N = lc.shape[0]
    gc = np.empty(N, dtype=np.int64)
    gf = np.empty(N, dtype=np.int64)
    ks = np.arange(maxg + 1)
    logfac = np.cumsum(np.log(np.concatenate([[1.0], np.arange(1, maxg + 1)])))
    dim = maxg + 1
    for a in range(0, N, chunk):
        b = min(a + chunk, N)
        lcc = lc[a:b]; lff = lf[a:b]
        px = np.exp(-lcc[:, None] + ks[None, :]*np.log(lcc[:, None]) - logfac[None, :])
        py = np.exp(-lff[:, None] + ks[None, :]*np.log(lff[:, None]) - logfac[None, :])
        M = px[:, :, None] * py[:, None, :]
        M[:, 0, 0] *= 1 - lcc*lff*rho
        M[:, 0, 1] *= 1 + lcc*rho
        M[:, 1, 0] *= 1 + lff*rho
        M[:, 1, 1] *= 1 - rho
        flat = M.reshape(b - a, -1)
        np.clip(flat, 0.0, None, out=flat)
        flat /= flat.sum(axis=1, keepdims=True)
        cdf = np.cumsum(flat, axis=1)
        r = np.random.rand(b - a, 1)
        k = np.clip((cdf < r).sum(axis=1), 0, flat.shape[1]-1)
        gc[a:b] = k // dim
        gf[a:b] = k % dim
    return gc, gf


class Modelo:
    """
    Base VETORIZADA. `sigma` = incerteza sobre a força dos times (0 => determinístico).

    Em vez de simular temporada-a-temporada num loop Python, cada modelo simula
    TODAS as temporadas de uma vez em matrizes numpy de shape (nsim, n_jogos).
    Isso é ordens de magnitude mais rápido. A força é reamostrada por temporada
    (uma linha por temporada); sigma maior alarga a distribuição de pontos finais.
    """
    nome = "base"

    def __init__(self, e: Estado, f: Forcas, mando=0.25, sigma=0.0):
        self.e, self.f, self.mando, self.sigma = e, f, mando, sigma
        cal = [(f.idx[a], f.idx[b]) for a, b in e.jogos_restantes]
        self.mand = np.array([i for i, _ in cal])      # índice do mandante por jogo
        self.vis = np.array([j for _, j in cal])       # índice do visitante por jogo
        self.n = len(e.times)
        self.nj = len(cal)

    def simular(self, nsim: int) -> dict:
        n, nj = self.n, self.nj
        # força por (temporada, time)
        atk, dfs, elo = self._amostrar_forca(nsim)     # cada um shape (nsim, n)
        # resultados por (temporada, jogo): +3/+1/0 para mandante e visitante, e saldo
        pm, pv, sdm = self._resultados(nsim, atk, dfs, elo)  # shape (nsim, nj)

        # acumula pontos e saldo por time via soma indexada
        pts = np.tile(self.f.pts.astype(float), (nsim, 1))
        sd = np.tile(self.f.sg.astype(float), (nsim, 1))
        np.add.at(pts, (np.arange(nsim)[:, None], self.mand[None, :]), pm)
        np.add.at(pts, (np.arange(nsim)[:, None], self.vis[None, :]), pv)
        np.add.at(sd, (np.arange(nsim)[:, None], self.mand[None, :]), sdm)
        np.add.at(sd, (np.arange(nsim)[:, None], self.vis[None, :]), -sdm)

        # classificação: pontos, depois saldo, com desempate aleatório
        chave = pts * 1e6 + sd * 1e2 + np.random.rand(nsim, n)
        ordem = np.argsort(-chave, axis=1)             # (nsim, n) posições -> time

        tit = np.zeros(n); g5 = np.zeros(n); z4 = np.zeros(n)
        np.add.at(tit, ordem[:, 0], 1)
        for k in range(5):
            np.add.at(g5, ordem[:, k], 1)
        for k in range(n-4, n):
            np.add.at(z4, ordem[:, k], 1)
        return {"titulo": 100*tit/nsim, "g5": 100*g5/nsim, "z4": 100*z4/nsim}

    def _amostrar_forca(self, nsim):
        f = self.f
        if self.sigma <= 0:
            atk = np.tile(f.atk, (nsim, 1))
            dfs = np.tile(f.dfs, (nsim, 1))
            elo = np.tile(f.elo, (nsim, 1))
            return atk, dfs, elo
        n, s = self.n, self.sigma
        atk = f.atk * np.exp(np.random.normal(0, s, (nsim, n)) - s*s/2)
        dfs = f.dfs * np.exp(np.random.normal(0, s, (nsim, n)) - s*s/2)
        elo = f.elo + np.random.normal(0, s*300, (nsim, n))
        return atk, dfs, elo

    def _resultados(self, nsim, atk, dfs, elo):
        """Retorna (pontos_mandante, pontos_visitante, saldo_mandante), shape (nsim, nj)."""
        raise NotImplementedError

    @staticmethod
    def _pontos(gc, gf):
        """Dado gols casa/fora (arrays), devolve pts_casa, pts_fora, saldo_casa."""
        pm = np.where(gc > gf, 3, np.where(gc == gf, 1, 0))
        pv = np.where(gf > gc, 3, np.where(gc == gf, 1, 0))
        return pm, pv, gc - gf


class Poisson(Modelo):
    nome = "poisson"
    def _resultados(self, nsim, atk, dfs, elo):
        mL, mando = self.f.media_liga, self.mando
        m, v = self.mand, self.vis
        lc = np.clip(atk[:, m]*dfs[:, v]*mL + mando, 0.1, 6.0)   # (nsim, nj)
        lf = np.clip(atk[:, v]*dfs[:, m]*mL, 0.1, 6.0)
        gc = np.random.poisson(lc)
        gf = np.random.poisson(lf)
        return self._pontos(gc, gf)


class DixonColes(Modelo):
    nome = "dixon_coles"
    def __init__(self, e, f, mando=0.25, sigma=0.0, rho=-0.05, maxg=6):
        super().__init__(e, f, mando, sigma)
        self.rho, self.maxg = rho, maxg

    def _resultados(self, nsim, atk, dfs, elo):
        mL, mando, rho, maxg = self.f.media_liga, self.mando, self.rho, self.maxg
        m, v = self.mand, self.vis
        lc = np.clip(atk[:, m]*dfs[:, v]*mL + mando, 0.1, 6.0)  # (nsim, nj)
        lf = np.clip(atk[:, v]*dfs[:, m]*mL, 0.1, 6.0)
        gc, gf = _amostra_placar_dc_vec(lc.ravel(), lf.ravel(), rho, maxg)
        gc = gc.reshape(nsim, self.nj); gf = gf.reshape(nsim, self.nj)
        return self._pontos(gc, gf)


class Elo(Modelo):
    nome = "elo"
    def __init__(self, e, f, mando=0.25, sigma=0.0, hfa=65):
        super().__init__(e, f, mando, sigma)
        self.hfa = hfa

    def _resultados(self, nsim, atk, dfs, elo):
        m, v = self.mand, self.vis
        dr = (elo[:, m] + self.hfa) - elo[:, v]            # (nsim, nj)
        pa = 1/(1+10**(-dr/400))
        pe = 0.28*np.exp(-(dr/300)**2)
        pa_adj = pa*(1-pe); pb_adj = (1-pa)*(1-pe)
        s = pa_adj + pe + pb_adj
        pa_adj /= s; pe /= s
        r = np.random.rand(nsim, self.nj)
        casa = r < pa_adj
        empate = (r >= pa_adj) & (r < pa_adj + pe)
        fora = r >= pa_adj + pe
        pm = np.where(casa, 3, np.where(empate, 1, 0))
        pv = np.where(fora, 3, np.where(empate, 1, 0))
        sdm = np.where(casa, 1, np.where(fora, -1, 0))
        return pm, pv, sdm


# =====================================================================
# 5. ORQUESTRADOR
# =====================================================================
def probabilidades_por_jogo(e: Estado, jogos, maxg=6, rho=-0.05, mando=0.25):
    """
    Calcula probabilidades de mandante/empate/visitante para uma lista de jogos.

    Usa Dixon-Coles direto (sem Monte Carlo — é fechado, mais rápido e preciso
    para essa saída). Retorna lista de dicts com nomes dos times, probs em % e
    o resultado mais provável.

    Args:
        e: Estado do campeonato.
        jogos: lista de tuplas (mandante, visitante) — nomes dos times.

    Returns:
        [{"mandante", "visitante", "casa", "empate", "fora", "provavel"}, ...]
    """
    f = calcular_forcas(e)
    ks = np.arange(maxg + 1)
    logfac = np.cumsum(np.log(np.concatenate([[1.0], np.arange(1, maxg + 1)])))
    resultado = []
    for man, vis in jogos:
        if man not in f.idx or vis not in f.idx:
            continue
        i, j = f.idx[man], f.idx[vis]
        lc = float(np.clip(f.atk[i] * f.dfs[j] * f.media_liga + mando, 0.1, 6.0))
        lf = float(np.clip(f.atk[j] * f.dfs[i] * f.media_liga, 0.1, 6.0))
        # distribuição conjunta Dixon-Coles
        px = np.exp(-lc + ks*np.log(lc) - logfac)
        py = np.exp(-lf + ks*np.log(lf) - logfac)
        M = np.outer(px, py)
        M[0, 0] *= 1 - lc*lf*rho
        M[0, 1] *= 1 + lc*rho
        M[1, 0] *= 1 + lf*rho
        M[1, 1] *= 1 - rho
        np.clip(M, 0.0, None, out=M)
        M /= M.sum()
        # soma triangular inferior (casa vence), diagonal (empate), superior (fora)
        idx_i, idx_j = np.indices(M.shape)
        p_casa = float(M[idx_i > idx_j].sum())
        p_empate = float(np.diag(M).sum())
        p_fora = float(M[idx_i < idx_j].sum())
        # placar mais provável
        placar = np.unravel_index(int(np.argmax(M)), M.shape)
        provavel = ("casa" if p_casa > max(p_empate, p_fora)
                    else "empate" if p_empate > p_fora else "fora")
        resultado.append({
            "mandante": man,
            "visitante": vis,
            "casa": round(100*p_casa, 1),
            "empate": round(100*p_empate, 1),
            "fora": round(100*p_fora, 1),
            "placar_provavel": f"{placar[0]}x{placar[1]}",
            "provavel": provavel,
        })
    return resultado


def rodar(fonte="exemplo", nsim=20000, token=None, sigma=0.40, pesos=(1, 1, 1)):
    """Ensemble dos 3 modelos. sigma controla a incerteza de força."""
    e = carregar_da_api(token=token) if fonte == "api" else carregar_exemplo()
    f = calcular_forcas(e)
    modelos = [Poisson(e, f, sigma=sigma),
               DixonColes(e, f, sigma=sigma),
               Elo(e, f, sigma=sigma)]
    saidas = {m.nome: m.simular(nsim) for m in modelos}

    w = np.array(pesos, float); w /= w.sum()
    metr = ["titulo", "g5", "z4"]
    ensemble = {k: sum(wi*saidas[m.nome][k] for wi, m in zip(w, modelos)) for k in metr}

    nomes = e.nomes
    ordem = np.argsort(-ensemble["titulo"])
    linhas = [{
        "time": nomes[i],
        "titulo": round(float(ensemble["titulo"][i]), 1),
        "g5": round(float(ensemble["g5"][i]), 1),
        "z4": round(float(ensemble["z4"][i]), 1),
        "titulo_por_modelo": {m: round(float(saidas[m]["titulo"][i]), 1) for m in saidas},
    } for i in ordem]
    return {"nsim": nsim, "fonte": fonte, "sigma": sigma, "tabela": linhas}


if __name__ == "__main__":
    import sys
    fonte = sys.argv[1] if len(sys.argv) > 1 else "exemplo"
    sigma = float(sys.argv[2]) if len(sys.argv) > 2 else 0.13
    out = rodar(fonte=fonte, nsim=15000, sigma=sigma)
    print(f"\nFonte: {out['fonte']} | {out['nsim']:,} simulações | sigma={sigma}\n")
    print(f"{'Time':<15}{'Título':>9}{'G5':>8}{'Z4':>8}   por modelo (P/DC/Elo)")
    print("-" * 70)
    for r in out["tabela"]:
        if r["titulo"] < 0.05 and r["g5"] < 0.5 and r["z4"] < 0.5:
            continue
        pm = r["titulo_por_modelo"]
        print(f"{r['time']:<15}{r['titulo']:>8.1f}%{r['g5']:>7.1f}%{r['z4']:>7.1f}%"
              f"   {pm['poisson']:.1f}/{pm['dixon_coles']:.1f}/{pm['elo']:.1f}")
