"""Funções compartilhadas pelos scripts dos cenários.

Os posts são acessados pelo slug (/?name=<slug>) e não pelo ID (/?p=<ID>):
o ID muda de uma instalação do WordPress para outra, e o slug só depende do
título do post. Assim os mesmos scripts funcionam na máquina de cada integrante.
"""
import os
import re

import requests

HOST = os.environ["ATTACKED_HOST"]  # definido no docker-compose.yml


def caminho_da_imagem(post, arquivo):
    """Procura no HTML do post o caminho da imagem original (ex:
    /wp-content/uploads/2026/10/cenario1_imagem_1mb.jpg). A pasta do ano/mês
    depende do dia em que a imagem foi enviada, por isso não fica fixa no script.
    Roda uma vez quando o Locust carrega o script, antes do teste começar."""
    html = requests.get(HOST + post, timeout=30).text
    encontrado = re.search(r'/wp-content/uploads/[^"\s]*/' + re.escape(arquivo), html)
    if not encontrado:
        raise SystemExit(
            f"A imagem {arquivo} não foi encontrada no post {post}. Confira se o "
            "post existe com o título certo e se a imagem foi inserida em tamanho "
            "completo (veja o README)."
        )
    return encontrado.group(0)
