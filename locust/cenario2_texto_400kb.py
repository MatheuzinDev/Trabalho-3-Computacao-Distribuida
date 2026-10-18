# Cenário 2: blog post com um texto de ~400 KB (post ID 9)
from locust import HttpUser, task, between

POST = "/?p=9"


class LeitorCenario2(HttpUser):
    wait_time = between(1, 2)  # pausa entre as tarefas de cada usuário

    @task
    def ler_post(self):
        # O texto vem dentro do próprio HTML do post
        self.client.get(POST, name="post (HTML + texto 400 KB)")
