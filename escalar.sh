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
docker compose exec nginx nginx -s reload # Nginx busca a lista nova de cópias
docker compose ps wordpress
