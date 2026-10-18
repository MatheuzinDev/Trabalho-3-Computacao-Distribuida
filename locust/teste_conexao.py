# Script mínimo da Parte 2: só confirma que o Locust alcança o WordPress
# através do Nginx (ATTACKED_HOST=http://nginx)
from locust import HttpUser, task, between


class UsuarioTeste(HttpUser):
    wait_time = between(1, 2)  # pausa entre as tarefas de cada usuário

    @task
    def pagina_inicial(self):
        self.client.get("/", name="pagina inicial")
