#!/usr/bin/env bash
# Uso: ./escalar.sh <quantidade>   (ex: ./escalar.sh 5)
set -euo pipefail
cd "$(dirname "$0")"

N="${1:-}"
if ! [[ "$N" =~ ^[1-9][0-9]*$ ]]; then
  echo "Uso: $0 <quantidade de WordPress, ex: 5>"
  exit 1
fi

# Primeira execução: sobe só 1 cópia até os arquivos do WordPress
# serem copiados para ./wordpress (evita várias cópias escrevendo ao mesmo tempo)
if [ ! -f wordpress/wp-config.php ]; then
  echo "Primeira execução: preparando os arquivos do WordPress..."
  docker compose up -d --scale wordpress=1
  until [ -f wordpress/wp-config.php ]; do sleep 2; done
fi

docker compose up -d --scale wordpress="$N"
# Nginx busca a lista nova de cópias. Se o Nginx acabou de subir, o reload
# pode falhar por alguns instantes; por isso tenta até 10 vezes
for tentativa in $(seq 10); do
  docker compose exec -T nginx nginx -s reload && break
  [ "$tentativa" -eq 10 ] && exit 1
  sleep 1
done
docker compose ps wordpress
