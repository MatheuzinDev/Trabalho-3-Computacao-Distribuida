import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PASTA_A = sys.argv[1] if len(sys.argv) > 1 else "resultados-matheus-d"
PASTA_B = sys.argv[2] if len(sys.argv) > 2 else "resultados-matheus-h"
NOME_A = "Matheus D."
NOME_B = "Matheus H."
COR_A = "#2b6cb0"
COR_B = "#dd6b20"
CENARIOS = {1: "Imagem 1 MB", 2: "Texto 400 KB", 3: "Imagem 300 KB"}
COPIAS = [1, 5, 10]
USUARIOS = [100, 500, 10000]
BASE = Path("resultados")
DESTINO = BASE / "comparacao"
DESTINO.mkdir(parents=True, exist_ok=True)


def agregado(pasta, c, i, u):
    arquivo = BASE / pasta / f"c{c}_i{i}_u{u}_stats.csv"
    if not arquivo.exists():
        return None
    with open(arquivo, newline="", encoding="utf-8") as f:
        for linha in csv.DictReader(f):
            if linha["Name"] == "Aggregated":
                return linha
    return None


def p95(pasta, c, i, u):
    linha = agregado(pasta, c, i, u)
    return float(linha["95%"]) / 1000 if linha else 0


def falhas(pasta, c, i, u):
    linha = agregado(pasta, c, i, u)
    if not linha or float(linha["Request Count"]) == 0:
        return 0
    return 100 * float(linha["Failure Count"]) / float(linha["Request Count"])


def rotulo_tempo(v):
    if v == 0:
        return "-"
    return f"{v * 1000:.0f} ms" if v < 1 else f"{v:.1f} s"


def barras(eixo, valores_a, valores_b, formatar):
    largura = 0.38
    xs = range(len(USUARIOS))
    ba = eixo.bar([x - largura / 2 for x in xs], valores_a, largura, color=COR_A, label=NOME_A)
    bb = eixo.bar([x + largura / 2 for x in xs], valores_b, largura, color=COR_B, label=NOME_B)
    for grupo in (ba, bb):
        for b in grupo:
            eixo.annotate(formatar(b.get_height()), (b.get_x() + b.get_width() / 2, b.get_height()),
                          ha="center", va="bottom", fontsize=8, xytext=(0, 2), textcoords="offset points")
    eixo.set_xticks(list(xs))
    eixo.set_xticklabels([f"{u:,}".replace(",", ".") for u in USUARIOS])
    eixo.grid(axis="y", alpha=0.3)


for c, nome in CENARIOS.items():
    fig, eixos = plt.subplots(1, 3, figsize=(15, 5), sharey=True)
    for eixo, i in zip(eixos, COPIAS):
        a = [p95(PASTA_A, c, i, u) for u in USUARIOS]
        b = [p95(PASTA_B, c, i, u) for u in USUARIOS]
        barras(eixo, a, b, rotulo_tempo)
        eixo.set_yscale("log")
        eixo.set_ylim(top=300)
        eixo.set_title(f"{i} cópia(s) do WordPress")
        eixo.set_xlabel("Usuários simultâneos")
    eixos[0].set_ylabel("P95 do tempo de resposta (escala log, menor é melhor)")
    eixos[0].legend()
    fig.suptitle(f"Cenário {c} - {nome}: tempo de resposta por máquina")
    fig.tight_layout()
    fig.savefig(DESTINO / f"p95_cenario{c}.png", dpi=150)
    plt.close(fig)

fig, eixos = plt.subplots(1, 3, figsize=(15, 5), sharey=True)
larg = 0.38
for eixo, c in zip(eixos, CENARIOS):
    xs = range(len(COPIAS))
    a = [falhas(PASTA_A, c, i, 10000) for i in COPIAS]
    b = [falhas(PASTA_B, c, i, 10000) for i in COPIAS]
    ba = eixo.bar([x - larg / 2 for x in xs], a, larg, color=COR_A, label=NOME_A)
    bb = eixo.bar([x + larg / 2 for x in xs], b, larg, color=COR_B, label=NOME_B)
    for grupo in (ba, bb):
        for barra in grupo:
            eixo.annotate(f"{barra.get_height():.0f}%", (barra.get_x() + barra.get_width() / 2, barra.get_height()),
                          ha="center", va="bottom", fontsize=9, xytext=(0, 2), textcoords="offset points")
    eixo.set_xticks(list(xs))
    eixo.set_xticklabels([str(i) for i in COPIAS])
    eixo.set_ylim(0, 110)
    eixo.set_title(f"Cenário {c} - {CENARIOS[c]}")
    eixo.set_xlabel("Cópias do WordPress")
    eixo.grid(axis="y", alpha=0.3)
eixos[0].set_ylabel("Requisições com falha (%)")
eixos[0].legend()
fig.suptitle("Taxa de falhas com 10.000 usuários, por máquina")
fig.tight_layout()
fig.savefig(DESTINO / "falhas_10000_usuarios.png", dpi=150)
plt.close(fig)

print(DESTINO)