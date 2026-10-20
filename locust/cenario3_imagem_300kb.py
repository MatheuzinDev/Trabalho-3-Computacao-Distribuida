# Cenário 3: blog post com uma imagem de ~300 KB (post "Cenário 3 – Imagem 300 KB")
from locust import task, between
# FastHttpUser gasta bem menos CPU que HttpUser: com HttpUser o próprio Locust
# passava de 90% de CPU a partir de 250 usuários e virava o gargalo do teste
from locust.contrib.fasthttp import FastHttpUser

from comum import caminho_da_imagem

POST = "/?name=cenario-3-imagem-300-kb"  # slug do post (ver locust/comum.py)
IMAGEM = caminho_da_imagem(POST, "cenario3_imagem_300kb.jpg")


class LeitorCenario3(FastHttpUser):
    wait_time = between(1, 2)  # pausa entre as tarefas de cada usuário

    @task
    def ler_post(self):
        self.client.get(POST, name="post (HTML)")
        # O Locust não baixa as imagens da página: o GET da imagem é explícito
        self.client.get(IMAGEM, name="imagem 300 KB")
