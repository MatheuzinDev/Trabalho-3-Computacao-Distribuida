#!/usr/bin/env bash
# Roda a matriz de testes de carga: para cada quantidade de cópias do
# WordPress, executa os 3 cenários com cada quantidade de usuários.
#
# Uso: ./rodar_testes.sh
#
# Os valores abaixo podem ser trocados por variáveis de ambiente, por exemplo
# para um teste rápido:  INSTANCIAS="1" USUARIOS="10" DURACAO=10s ./rodar_testes.sh
#
# Se o script for interrompido, basta rodar de novo: as rodadas que já têm
# CSV em resultados/ são puladas.
set -euo pipefail
cd "$(dirname "$0")"

INSTANCIAS=${INSTANCIAS:-"1 5 10"} # cópias do WordPress
USUARIOS=${USUARIOS:-"10 100 1000"} # usuários simulados pelo Locust
CENARIOS=${CENARIOS:-"1 2 3"}
DURACAO=${DURACAO:-2m}              # duração de cada rodada
PAUSA=${PAUSA:-30}                  # segundos de pausa entre rodadas

# Script do Locust de cada cenário
script_do_cenario() {
  case "$1" in
    1) echo "cenario1_imagem_1mb.py" ;;
    2) echo "cenario2_texto_400kb.py" ;;
    3) echo "cenario3_imagem_300kb.py" ;;
  esac
}

# Usuários que entram por segundo (-r): todos sobem em no máximo 20 s
taxa_de_entrada() {
  if [ "$1" -le 100 ]; then echo 10; else echo 50; fi
}

# Espera o Nginx distribuir as requisições entre exatamente N cópias
esperar_copias() {
  local n=$1 encontradas=0
  for _ in $(seq 30); do
    encontradas=$(for _ in $(seq $((n * 4))); do
      # "|| true": logo após subir o Nginx ainda não responde, e isso não pode encerrar o script
      curl -s -o /dev/null -D - http://localhost/license.txt | grep -i '^X-Upstream' || true
    done | sort -u | wc -l)
    [ "$encontradas" -eq "$n" ] && return 0
    sleep 2
  done
  echo "ERRO: esperava $n cópias respondendo, mas o Nginx mostrou $encontradas." >&2
  exit 1
}

# Espera o WordPress responder um post (só funciona com o MySQL já pronto)
esperar_wordpress() {
  for _ in $(seq 60); do
    [ "$(curl -sL -o /dev/null -w '%{http_code}' 'http://localhost/?p=6')" = 200 ] && return 0
    sleep 2
  done
  echo "ERRO: o WordPress não respondeu o post 6 com 200." >&2
  exit 1
}

total=$(( $(wc -w <<< "$INSTANCIAS") * $(wc -w <<< "$CENARIOS") * $(wc -w <<< "$USUARIOS") ))
rodada=0
mkdir -p resultados/logs

for n in $INSTANCIAS; do
  echo "=== Subindo $n cópia(s) do WordPress"
  if ! ./escalar.sh "$n" > "resultados/logs/escalar_${n}.log" 2>&1; then
    echo "ERRO: ./escalar.sh $n falhou. Veja resultados/logs/escalar_${n}.log" >&2
    exit 1
  fi
  esperar_copias "$n"
  esperar_wordpress
  echo "    Nginx distribuindo entre $n cópia(s)"

  for c in $CENARIOS; do
    for u in $USUARIOS; do
      rodada=$((rodada + 1))
      nome="c${c}_i${n}_u${u}"

      if [ -f "resultados/${nome}_stats.csv" ]; then
        echo "[$rodada/$total] $nome já existe, pulando"
        continue
      fi

      echo "[$rodada/$total] $nome: cenário $c, $n cópia(s), $u usuários, $DURACAO"
      # --no-deps: sem ele, o "run" volta o WordPress para as 3 cópias padrão
      docker compose run --rm --no-deps \
        -e LOCUST_FILE="$(script_do_cenario "$c")" \
        -e LOCUST_OPTS="--headless -u $u -r $(taxa_de_entrada "$u") -t $DURACAO --reset-stats --csv /resultados/$nome" \
        locust > "resultados/logs/${nome}.log" 2>&1

      # Linha "Aggregated" do CSV: requisições, falhas, tempo médio e req/s
      awk -F, '$2 == "Aggregated" {
        printf "    %d requisições, %d falhas, tempo médio %.0f ms, %.1f req/s\n", $3, $4, $6, $10
      }' "resultados/${nome}_stats.csv"

      if [ "$rodada" -lt "$total" ]; then sleep "$PAUSA"; fi
    done
  done
done

echo "=== Fim: CSVs em resultados/ e saída do Locust em resultados/logs/"
