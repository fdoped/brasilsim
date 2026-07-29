"""
Atualiza os dados do site — executado 1x/dia via GitHub Actions.

Processa DUAS competições:
  - Série A: título, G5 (Libertadores), Z4 (rebaixamento)
  - Série B: título, acesso direto (G2), playoff (3º-6º), Z4 (rebaixamento)
"""
from __future__ import annotations
import json
import sys
import time
import unicodedata
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import requests

from simulador import (
    calcular_forcas, carregar_exemplo, _extrai_ge_json,
    _gerar_returno_por_contagem, probabilidades_por_jogo,
    Poisson, DixonColes, Elo, Estado, ErroAPI,
)

NSIM = 30_000
SIGMA = 0.40
RAIZ = Path(__file__).resolve().parent.parent / "src/data"

# Configuração de cada competição.
# `faixas`: nome -> (posição inicial, posição final), 1-indexed.
#           valores negativos contam do fim (-4 = quarto de trás para frente).
SERIES = {
    "a": {
        "nome": "Série A",
        "url": "https://ge.globo.com/futebol/brasileirao-serie-a/",
        "saida": RAIZ / "probabilidades.json",
        "historico": RAIZ / "historico.json",
        "faixas": {
            "titulo": (1, 1),
            "g5": (1, 5),
            "z4": (-4, -1),
        },
    },
    "b": {
        "nome": "Série B",
        "url": "https://ge.globo.com/futebol/brasileirao-serie-b/",
        "saida": RAIZ / "probabilidades-b.json",
        "historico": RAIZ / "historico-b.json",
        "faixas": {
            "titulo": (1, 1),
            "acesso_direto": (1, 2),   # 1º e 2º sobem direto
            "playoff": (3, 6),         # 3º a 6º disputam mata-mata
            "z4": (-4, -1),            # 4 últimos caem para a Série C
        },
    },
}


def _slug(nome: str) -> str:
    """Converte 'Atlético-MG' em 'atletico-mg' para usar na URL."""
    s = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s


def baixa_ge(url):
    """Baixa HTML do GE com User-Agent de navegador."""
    headers = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/122.0.0.0 Safari/537.36"),
        "Accept-Language": "pt-BR,pt;q=0.9",
    }
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.text


def carrega_estado(url, permite_fallback=True):
    """Tenta o GE 3 vezes. Se falhar e for permitido, usa dados de exemplo."""
    ultimo_erro = None
    for tentativa in range(3):
        try:
            html = baixa_ge(url)
            times, _confrontos, proximos, extras = _extrai_ge_json(html)
            if len(times) < 20:
                raise ErroAPI(f"Só achei {len(times)} times")
            jogos_restantes = _gerar_returno_por_contagem(times)
            return Estado(times, jogos_restantes), proximos, extras, "ge.globo"
        except Exception as exc:
            ultimo_erro = exc
            print(f"  [tentativa {tentativa+1}/3] falhou: {exc}", file=sys.stderr)
            time.sleep(5)
    if permite_fallback:
        print(f"  AVISO: usando dados de exemplo (GE falhou: {ultimo_erro})", file=sys.stderr)
        return carregar_exemplo(), [], {}, "exemplo (fallback)"
    raise ErroAPI(f"Nao consegui carregar {url}: {ultimo_erro}")


def roda_simulacoes(e: Estado, faixas):
    """Ensemble Poisson + Dixon-Coles + Elo, média simples."""
    f = calcular_forcas(e)
    modelos = [Poisson(e, f, sigma=SIGMA, faixas=faixas),
               DixonColes(e, f, sigma=SIGMA, faixas=faixas),
               Elo(e, f, sigma=SIGMA, faixas=faixas)]
    saidas = {m.nome: m.simular(NSIM) for m in modelos}
    chaves = list(faixas.keys())
    ensemble = {k: np.mean([saidas[m.nome][k] for m in modelos], axis=0) for k in chaves}
    return ensemble, saidas


def monta_tabela(e: Estado, ensemble, saidas, extras, faixas):
    """Ordena times por probabilidade de título e monta lista para o site."""
    extras = extras or {}
    chaves = list(faixas.keys())
    ordem = np.argsort(-ensemble["titulo"])
    linhas = []
    for i in ordem:
        t = e.times[i]
        ex = extras.get(t.nome, {})
        aprov = ex.get("aproveitamento")
        if aprov is None and t.j > 0:
            aprov = round(100 * t.pts / (t.j * 3))
        linha = {
            "posicao_atual": None,
            "time": t.nome,
            "slug": _slug(t.nome),
            "pts": t.pts, "j": t.j, "gp": t.gp, "gc": t.gc, "sg": t.sg,
            "vitorias": ex.get("vitorias"),
            "empates": ex.get("empates"),
            "derrotas": ex.get("derrotas"),
            "aproveitamento": aprov,
            "ultimos_jogos": ex.get("ultimos_jogos") or [],
            "por_modelo": {
                "poisson": round(float(saidas["poisson"]["titulo"][i]), 1),
                "dixon_coles": round(float(saidas["dixon_coles"]["titulo"][i]), 1),
                "elo": round(float(saidas["elo"]["titulo"][i]), 1),
            },
        }
        for k in chaves:
            linha[k] = round(float(ensemble[k][i]), 1)
        linhas.append(linha)

    ord_atual = sorted(range(len(e.times)),
                       key=lambda i: (-e.times[i].pts, -e.times[i].sg, -e.times[i].gp))
    pos = {e.times[i].nome: k + 1 for k, i in enumerate(ord_atual)}
    for l in linhas:
        l["posicao_atual"] = pos[l["time"]]
    return linhas


def grava_historico(caminho: Path, tabela, chaves, br):
    """Acumula um registro por dia (para o gráfico de evolução)."""
    hoje = datetime.now(br).date().isoformat()
    registro = {
        "data": hoje,
        "times": {l["time"]: {k: l[k] for k in chaves} for l in tabela},
    }
    try:
        historico = json.loads(caminho.read_text(encoding="utf-8"))
        if not isinstance(historico, list):
            historico = []
    except (FileNotFoundError, ValueError):
        historico = []
    historico = [r for r in historico if r.get("data") != hoje]
    historico.append(registro)
    historico = historico[-120:]
    caminho.write_text(json.dumps(historico, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(historico)


def processa_serie(chave: str, cfg: dict, br) -> bool:
    """Roda o pipeline completo de uma competição. Retorna True se deu certo."""
    print(f"\n--- {cfg['nome']} ---")
    permite_fallback = (chave == "a")
    try:
        e, proximos, extras, fonte = carrega_estado(cfg["url"], permite_fallback)
    except ErroAPI as exc:
        print(f"  ERRO: {exc} - mantendo dados anteriores", file=sys.stderr)
        return False

    print(f"  fonte: {fonte} | times: {len(e.times)} | proximos: {len(proximos)}")
    faixas = cfg["faixas"]
    ensemble, saidas = roda_simulacoes(e, faixas)
    tabela = monta_tabela(e, ensemble, saidas, extras, faixas)

    pares = [(p["mandante"], p["visitante"]) for p in proximos]
    probs_jogos = probabilidades_por_jogo(e, pares) if pares else []
    for prob, meta in zip(probs_jogos, proximos):
        prob["data"] = meta.get("data")
        prob["sede"] = meta.get("sede")

    payload = {
        "competicao": cfg["nome"],
        "atualizado_em": datetime.now(br).isoformat(),
        "fonte": fonte,
        "nsim": NSIM,
        "sigma": SIGMA,
        "faixas": {k: list(v) for k, v in faixas.items()},
        "tabela": tabela,
        "proximos_jogos": probs_jogos,
    }
    cfg["saida"].parent.mkdir(parents=True, exist_ok=True)
    cfg["saida"].write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  escrito: {cfg['saida'].name} ({cfg['saida'].stat().st_size:,} bytes)")

    n_hist = grava_historico(cfg["historico"], tabela, list(faixas.keys()), br)
    print(f"  historico: {n_hist} dia(s)")

    print(f"  Top 5 titulo ({cfg['nome']}):")
    for l in tabela[:5]:
        print(f"    {l['time']:<16} {l['titulo']:>5.1f}%")
    return True


def main():
    br = timezone(timedelta(hours=-3))
    print(f"[{datetime.now(br).isoformat()}] iniciando atualizacao")
    ok_a = processa_serie("a", SERIES["a"], br)
    ok_b = processa_serie("b", SERIES["b"], br)
    print(f"\nresumo: Serie A {'ok' if ok_a else 'FALHOU'} | Serie B {'ok' if ok_b else 'FALHOU'}")
    if not ok_a:
        sys.exit(1)


if __name__ == "__main__":
    main()
