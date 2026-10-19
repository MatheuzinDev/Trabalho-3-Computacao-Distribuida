"""Gera os gráficos de barras agrupadas do P95 a partir dos CSVs do Locust.

Uso: python3 gerar_graficos.py [pasta]   (padrão: resultados/nginx-otimizado)

Lê a linha "Aggregated" de cada <pasta>/c<cenário>_i<cópias>_u<usuários>_stats.csv
e grava em <pasta>/graficos/, para cada cenário:
  - p95_por_carga_cenarioN.png      X = usuários, uma barra por quantidade de cópias
  - p95_por_instancia_cenarioN.png  X = cópias, uma barra por quantidade de usuários
Acima de cada barra vai o P95 e, embaixo dele, a % de falhas da rodada.
"""
import csv
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # só grava arquivos, sem abrir janela
import matplotlib.pyplot as plt

CENARIOS = {
    1: "Cenário 1 – post com imagem de 1 MB",
    2: "Cenário 2 – post com texto de 400 KB",
    3: "Cenário 3 – post com imagem de 300 KB",
}
NOME_ARQUIVO = re.compile(r"c(\d+)_i(\d+)_u(\d+)_stats\.csv$")


def ler_resultados(pasta):
    """Retorna {(cenário, cópias, usuários): (p95 em ms, % de falhas)}."""
    resultados = {}
    for arquivo in pasta.glob("c*_stats.csv"):
        encontrado = NOME_ARQUIVO.match(arquivo.name)
        if not encontrado:
            continue
        chave = tuple(int(g) for g in encontrado.groups())
        with arquivo.open(newline="") as f:
            for linha in csv.DictReader(f):
                if linha["Name"] == "Aggregated":
                    total = int(linha["Request Count"])
                    falhas = int(linha["Failure Count"])
                    p95 = float(linha["95%"]) if linha["95%"] != "N/A" else 0.0
                    resultados[chave] = (p95, 100 * falhas / total if total else 0.0)
    return resultados


def formatar_ms(ms):
    return f"{ms / 1000:.1f} s".replace(".", ",") if ms >= 1000 else f"{ms:.0f} ms"


def grafico_agrupado(titulo, rotulo_x, valores_x, rotulo_grupo, grupos, dado, arquivo):
    """Barras agrupadas: um grupo de barras por valor de X, uma cor por grupo.
    dado(x, grupo) devolve (p95, % falhas) ou None quando a rodada não existe."""
    largura = 0.8 / len(grupos)
    fig, ax = plt.subplots(figsize=(9, 5.5))
    for i, grupo in enumerate(grupos):
        posicoes, alturas, textos = [], [], []
        for j, x in enumerate(valores_x):
            valor = dado(x, grupo)
            if valor is None:
                continue
            p95, falhas = valor
            posicoes.append(j + (i - (len(grupos) - 1) / 2) * largura)
            alturas.append(p95)
            textos.append(f"{formatar_ms(p95)}\n{falhas:.0f}% falhas")
        barras = ax.bar(posicoes, alturas, largura, label=f"{grupo} {rotulo_grupo}")
        ax.bar_label(barras, labels=textos, fontsize=7, padding=2)

    ax.set_title(titulo)
    ax.set_xlabel(rotulo_x)
    ax.set_ylabel("P95 do tempo de resposta (ms)")
    ax.set_xticks(range(len(valores_x)), [str(x) for x in valores_x])
    ax.margins(y=0.15)  # espaço para os rótulos acima das barras
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(arquivo, dpi=150)
    plt.close(fig)


def main():
    pasta = Path(sys.argv[1] if len(sys.argv) > 1 else "resultados/nginx-otimizado")
    resultados = ler_resultados(pasta)
    if not resultados:
        sys.exit(f"Nenhum CSV c*_i*_u*_stats.csv encontrado em {pasta}/")

    destino = pasta / "graficos"
    destino.mkdir(exist_ok=True)
    copias = sorted({i for _, i, _ in resultados})
    usuarios = sorted({u for _, _, u in resultados})

    for c in sorted({c for c, _, _ in resultados}):
        titulo = CENARIOS.get(c, f"Cenário {c}")
        grafico_agrupado(
            f"{titulo}\nP95 por carga",
            "Usuários simultâneos", usuarios,
            "cópia(s)", copias,
            lambda u, i: resultados.get((c, i, u)),
            destino / f"p95_por_carga_cenario{c}.png",
        )
        grafico_agrupado(
            f"{titulo}\nP95 por quantidade de cópias do WordPress",
            "Cópias do WordPress", copias,
            "usuários", usuarios,
            lambda i, u: resultados.get((c, i, u)),
            destino / f"p95_por_instancia_cenario{c}.png",
        )
    print(f"Gráficos gravados em {destino}/")


if __name__ == "__main__":
    main()
