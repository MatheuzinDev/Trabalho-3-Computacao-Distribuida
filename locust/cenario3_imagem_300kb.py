# Cenário 3: blog post com uma imagem de ~300 KB (post ID 11)
from locust import HttpUser, task, between

POST = "/?p=11"
IMAGEM = "/wp-content/uploads/2026/10/cenario3_imagem_300kb.jpg"


class LeitorCenario3(HttpUser):
    wait_time = between(1, 2)  # pausa entre as tarefas de cada usuário

    @task
    def ler_post(self):
        self.client.get(POST, name="post (HTML)")
        # O Locust não baixa as imagens da página: o GET da imagem é explícito
        self.client.get(IMAGEM, name="imagem 300 KB")
