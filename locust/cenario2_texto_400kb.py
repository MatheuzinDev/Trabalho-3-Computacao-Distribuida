# Cenário 2: blog post com um texto de ~400 KB (post "Cenário 2 – Texto 400 KB")
from locust import task, between
# FastHttpUser gasta bem menos CPU que HttpUser: com HttpUser o próprio Locust
# passava de 90% de CPU a partir de 250 usuários e virava o gargalo do teste
from locust.contrib.fasthttp import FastHttpUser

POST = "/?name=cenario-2-texto-400-kb"  # slug do post (ver locust/comum.py)


class LeitorCenario2(FastHttpUser):
    wait_time = between(1, 2)  # pausa entre as tarefas de cada usuário

    @task
    def ler_post(self):
        # O texto vem dentro do próprio HTML do post
        self.client.get(POST, name="post (HTML + texto 400 KB)")
