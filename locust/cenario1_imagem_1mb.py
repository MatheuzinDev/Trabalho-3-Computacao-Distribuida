# Cenário 1: blog post com uma imagem de ~1 MB (post ID 6)
from locust import HttpUser, task, between

POST = "/?p=6"
IMAGEM = "/wp-content/uploads/2026/10/cenario1_imagem_1mb.jpg"


class LeitorCenario1(HttpUser):
    wait_time = between(1, 2)  # pausa entre as tarefas de cada usuário

    @task
    def ler_post(self):
        self.client.get(POST, name="post (HTML)")
        # O Locust não baixa as imagens da página: o GET da imagem é explícito
        self.client.get(IMAGEM, name="imagem 1 MB")
