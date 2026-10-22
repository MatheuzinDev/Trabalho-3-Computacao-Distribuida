import csv
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

CENARIOS = {
    1: "Cenário 1 – post com imagem de 1 MB",
    2: "Cenário 2 – post com texto de 400 KB",
    3: "Cenário 3 – post com imagem de 300 KB",
}
NOME_ARQUIVO = re.compile(r"c(\d+)_i(\d+)_u(\d+)_stats\.csv$")


def ler_resultados(pasta):
    resultados = {}
    for arquivo in pasta.glob("c*_stats.csv"):
        m = NOME_ARQUIVO.match(arquivo.name)
        if not m:
            continue
        chave = tuple(int(g) for g in m.groups())
        with arquivo.open(newline="") as f:
            for linha in csv.DictReader(f):
                if linha["Name"] == "Aggregated":
                    total = int(linha["Request Count"])
                    falhas = int(linha["Failure Count"])
                    rps = float(linha["Requests/s"])
                    resultados[chave] = {
                        "rps": rps,
                        "rps_ok": rps * (1 - falhas / total) if total else 0.0,
                        "media": float(linha["Average Response Time"]),
                        "falhas": 100 * falhas / total if total else 0.0,
                    }
    return resultados


def grafico(titulo, rotulo_x, valores_x, rotulo_grupo, grupos, dado, rotulo_y, formato, arquivo, log=False):
    largura = 0.8 / len(grupos)
    fig, ax = plt.subplots(figsize=(9, 5.5))
    for i, g in enumerate(grupos):
        pos, alt, txt = [], [], []
        for j, x in enumerate(valores_x):
            v = dado(x, g)
            if v is None:
                continue
            pos.append(j + (i - (len(grupos) - 1) / 2) * largura)
            alt.append(v)
            txt.append(formato(v))
        barras = ax.bar(pos, alt, largura, label=f"{g} {rotulo_grupo}")
        ax.bar_label(barras, labels=txt, fontsize=7, padding=2)
    ax.set_title(titulo)
    ax.set_xlabel(rotulo_x)
    ax.set_ylabel(rotulo_y)
    ax.set_xticks(range(len(valores_x)), [str(x) for x in valores_x])
    if log:
        ax.set_yscale("log")
    ax.set_ylim(top=ax.get_ylim()[1] * (4 if log else 1.15))
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=len(grupos))
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(arquivo, dpi=150, bbox_inches="tight")
    plt.close(fig)


def fmt_ms(ms):
    return f"{ms / 1000:.1f} s".replace(".", ",") if ms >= 1000 else f"{ms:.0f} ms"


def main():
    if len(sys.argv) != 2:
        sys.exit("Uso: python gerar_graficos_rps.py <nome>")
    pasta = Path(sys.argv[1])
    if not pasta.is_dir():
        pasta = Path("resultados") / sys.argv[1]
    r = ler_resultados(pasta)
    if not r:
        sys.exit(f"Nenhum CSV encontrado em {pasta}/")
    destino = Path("resultados") / "graficos-rps" / pasta.name
    destino.mkdir(parents=True, exist_ok=True)
    copias = sorted({i for _, i, _ in r})
    usuarios = sorted({u for _, _, u in r})

    metricas = [
        ("rps", "Requisições por segundo (todas, inclui erros)", lambda v: f"{v:.1f}", False, "rps"),
        ("rps_ok", "Requisições bem-sucedidas por segundo", lambda v: f"{v:.1f}", False, "rps_ok"),
        ("media", "Tempo médio de resposta (ms, escala log)", fmt_ms, True, "media"),
    ]
    for c in sorted({c for c, _, _ in r}):
        titulo = CENARIOS.get(c, f"Cenário {c}")
        for chave, rotulo_y, fmt, log, nome in metricas:
            grafico(
                f"{titulo}\n{rotulo_y} por quantidade de cópias",
                "Cópias do WordPress", copias, "usuários", usuarios,
                lambda i, u, c=c, k=chave: r[(c, i, u)][k] if (c, i, u) in r else None,
                rotulo_y, fmt, destino / f"{nome}_por_instancia_cenario{c}.png", log,
            )
            grafico(
                f"{titulo}\n{rotulo_y} por carga",
                "Usuários simultâneos", usuarios, "cópia(s)", copias,
                lambda u, i, c=c, k=chave: r[(c, i, u)][k] if (c, i, u) in r else None,
                rotulo_y, fmt, destino / f"{nome}_por_carga_cenario{c}.png", log,
            )
    print(f"Gráficos gravados em {destino}/")


if __name__ == "__main__":
    main()