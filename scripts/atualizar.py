"""
Atualiza os dados do site — executado 1x/dia via GitHub Actions.

Fluxo:
  1. Baixa o HTML da página do Brasileirão no ge.globo (fonte gratuita).
  2. Parseia classificação e próximos jogos.
  3. Roda 30.000 simulações Monte Carlo (ensemble Poisson + Dixon-Coles + Elo).
  4. Calcula probabilidades de resultado (M/E/V) para os próximos jogos.
  5. Escreve tudo em src/data/probabilidades.json (lido pelo Astro no build).

Como o site é totalmente estático (SSG), este script é o único ponto que consome
recursos e faz rede. Roda uma vez por dia, gera JSON, faz commit — pronto.
"""
from __future__ import annotations
import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import requests

from simulador import (
    calcular_forcas, carregar_exemplo, _extrai_ge_json,
    jogos_restantes_de_confrontos, _gerar_returno_por_contagem,
    probabilidades_por_jogo, Poisson, DixonColes, Elo, Estado, ErroAPI,
)

GE_URL = "https://ge.globo.com/futebol/brasileirao-serie-a/"
NSIM = 30_000
SIGMA = 0.40
SAIDA = Path(__file__).resolve().parent.parent / "src/data/probabilidades.json"
SAIDA_HIST = Path(__file__).resolve().parent.parent / "src/data/historico.json"


def baixa_ge():
    """Baixa HTML do GE com User-Agent de navegador. Levanta em caso de bloqueio."""
    headers = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/122.0.0.0 Safari/537.36"),
        "Accept-Language": "pt-BR,pt;q=0.9",
    }
    r = requests.get(GE_URL, headers=headers, timeout=30)
    r.raise_for_status()
    return r.text


def carrega_estado():
    """Tenta GE 3 vezes; se falhar, usa exemplo (fallback para não quebrar site)."""
    ultimo_erro = None
    for tentativa in range(3):
        try:
            html = baixa_ge()
            times, _confrontos, proximos, extras = _extrai_ge_json(html)
            if len(times) < 20:
                raise ErroAPI(f"Só achei {len(times)} times")
            jogos_restantes = _gerar_returno_por_contagem(times)
            return Estado(times, jogos_restantes), proximos, extras, "ge.globo"
        except Exception as exc:
            ultimo_erro = exc
            print(f"[tentativa {tentativa+1}/3] falhou: {exc}", file=sys.stderr)
            time.sleep(5)
    print(f"AVISO: usando dados de exemplo (GE falhou: {ultimo_erro})", file=sys.stderr)
    return carregar_exemplo(), [], {}, "exemplo (fallback)"


def roda_simulacoes(e: Estado):
    """Ensemble Poisson + Dixon-Coles + Elo, média simples."""
    f = calcular_forcas(e)
    modelos = [Poisson(e, f, sigma=SIGMA),
               DixonColes(e, f, sigma=SIGMA),
               Elo(e, f, sigma=SIGMA)]
    saidas = {m.nome: m.simular(NSIM) for m in modelos}
    metr = ("titulo", "g5", "z4")
    ensemble = {k: np.mean([saidas[m.nome][k] for m in modelos], axis=0) for k in metr}
    return ensemble, saidas


def _slug(nome: str) -> str:
    """Converte 'Atlético-MG' em 'atletico-mg' para usar na URL."""
    import unicodedata, re
    s = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s


def monta_tabela(e: Estado, ensemble, saidas, extras=None):
    """Ordena times por probabilidade de título e monta lista para o site."""
    extras = extras or {}
    ordem = np.argsort(-ensemble["titulo"])
    linhas = []
    for i in ordem:
        t = e.times[i]
        ex = extras.get(t.nome, {})
        # aproveitamento: usa o do GE se veio, senão calcula
        aprov = ex.get("aproveitamento")
        if aprov is None and t.j > 0:
            aprov = round(100 * t.pts / (t.j * 3))
        linhas.append({
            "posicao_atual": None,  # preenchido depois
            "time": t.nome,
            "slug": _slug(t.nome),
            "pts": t.pts, "j": t.j, "gp": t.gp, "gc": t.gc, "sg": t.sg,
            "vitorias": ex.get("vitorias"),
            "empates": ex.get("empates"),
            "derrotas": ex.get("derrotas"),
            "aproveitamento": aprov,
            "ultimos_jogos": ex.get("ultimos_jogos") or [],
            "titulo": round(float(ensemble["titulo"][i]), 1),
            "g5": round(float(ensemble["g5"][i]), 1),
            "z4": round(float(ensemble["z4"][i]), 1),
            "por_modelo": {
                "poisson": round(float(saidas["poisson"]["titulo"][i]), 1),
                "dixon_coles": round(float(saidas["dixon_coles"]["titulo"][i]), 1),
                "elo": round(float(saidas["elo"]["titulo"][i]), 1),
            },
        })
    # posições atuais (ordenadas por pontos → SG → GP)
    ord_atual = sorted(range(len(e.times)),
                       key=lambda i: (-e.times[i].pts, -e.times[i].sg, -e.times[i].gp))
    pos = {e.times[i].nome: k+1 for k, i in enumerate(ord_atual)}
    for l in linhas:
        l["posicao_atual"] = pos[l["time"]]
    return linhas


def main():
    print(f"[{datetime.now(timezone.utc).isoformat()}] iniciando atualização")
    e, proximos, extras, fonte = carrega_estado()
    print(f"fonte: {fonte} | times: {len(e.times)} | próximos: {len(proximos)}")

    ensemble, saidas = roda_simulacoes(e)
    tabela = monta_tabela(e, ensemble, saidas, extras)

    # probabilidades por próximo jogo
    pares = [(p["mandante"], p["visitante"]) for p in proximos]
    probs_jogos = probabilidades_por_jogo(e, pares) if pares else []
    for prob, meta in zip(probs_jogos, proximos):
        prob["data"] = meta.get("data")
        prob["sede"] = meta.get("sede")

    # fuso Brasília para "atualizado em"
    br = timezone(timedelta(hours=-3))
    payload = {
        "atualizado_em": datetime.now(br).isoformat(),
        "fonte": fonte,
        "nsim": NSIM,
        "sigma": SIGMA,
        "tabela": tabela,
        "proximos_jogos": probs_jogos,
    }

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"escrito: {SAIDA} ({SAIDA.stat().st_size:,} bytes)")

    # ---- histórico: acumula um registro por dia (para o gráfico de evolução) ----
    hoje = datetime.now(br).date().isoformat()
    registro = {
        "data": hoje,
        "times": {l["time"]: {"titulo": l["titulo"], "g5": l["g5"], "z4": l["z4"]}
                  for l in tabela},
    }
    # carrega histórico existente (se houver)
    try:
        historico = json.loads(SAIDA_HIST.read_text(encoding="utf-8"))
        if not isinstance(historico, list):
            historico = []
    except (FileNotFoundError, ValueError):
        historico = []
    # se já existe registro de hoje, substitui; senão, adiciona
    historico = [r for r in historico if r.get("data") != hoje]
    historico.append(registro)
    # mantém só os últimos 120 dias (evita crescer sem limite)
    historico = historico[-120:]
    SAIDA_HIST.write_text(json.dumps(historico, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"histórico: {len(historico)} dia(s) registrado(s)")

    # resumo no stdout (aparece no log do Action)
    print("\nTop 5 título:")
    for l in tabela[:5]:
        print(f"  {l['time']:<15} {l['titulo']:>5.1f}%  (G5 {l['g5']:.0f}%)")
    if probs_jogos:
        print(f"\n{len(probs_jogos)} próximos jogos com probabilidades calculadas")


if __name__ == "__main__":
    main()
