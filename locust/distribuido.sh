#!/bin/sh
# Roda o Locust em modo distribuído dentro de um único contêiner: WORKERS
# processos geram a carga e o master só coordena e grava os CSVs.
# Um processo do Locust usa no máximo 1 núcleo de CPU, o que não é suficiente
# para 2000 ou 5000 usuários.
#
# Usa o próprio entrypoint da imagem (/docker-entrypoint.sh) com LOCUST_MODE
set -e
WORKERS=${WORKERS:-4}

for _ in $(seq "$WORKERS"); do
  # Os workers não recebem LOCUST_OPTS: as opções do teste (-u, -r, -t, --csv)
  # são do master, que repassa os usuários para eles
  LOCUST_MODE=worker LOCUST_MASTER_HOST=127.0.0.1 LOCUST_OPTS="" /docker-entrypoint.sh &
done

LOCUST_MODE=master LOCUST_OPTS="--expect-workers $WORKERS $LOCUST_OPTS" exec /docker-entrypoint.sh
