#!/usr/bin/env bash
# Roda a matriz de testes de carga: para cada quantidade de cópias do
# WordPress, executa os 3 cenários com cada quantidade de usuários.
#
# Uso: RESULTADOS=resultados-<nome> ./rodar_testes.sh
#
# Cada integrante roda na sua máquina e grava numa pasta própria dentro de
# resultados/, por exemplo RESULTADOS=resultados-matheus-d grava em
# resultados/resultados-matheus-d/. Sem RESULTADOS, a pasta é resultados/resultados-teste/
#
# Os valores abaixo podem ser trocados por variáveis de ambiente, por exemplo
# para um teste rápido:  INSTANCIAS="1" USUARIOS="10" DURACAO=10s ./rodar_testes.sh
#
# PASTA grava numa subpasta dentro dessa pasta, por exemplo para a exploração
# que escolhe as quantidades de usuários:
#   PASTA=exploracao INSTANCIAS="1" USUARIOS="500 2000 5000" ./rodar_testes.sh
#
# Falhas nas requisições NÃO param o script: elas fazem parte do resultado.
# Se o script for interrompido, basta rodar de novo: as rodadas que já têm
# CSV são puladas.
set -euo pipefail
cd "$(dirname "$0")"

INSTANCIAS=${INSTANCIAS:-"1 5 10"} # cópias do WordPress
USUARIOS=${USUARIOS:-"100 500 10000"} # usuários: baixa, média e alta carga
CENARIOS=${CENARIOS:-"1 2 3"}
DURACAO=${DURACAO:-4m}              # duração de cada rodada
PAUSA=${PAUSA:-60}                  # segundos de pausa entre rodadas (o servidor se recupera da alta carga)
PASTA=${PASTA:-}                    # subpasta opcional (ex: exploracao)
RESULTADOS=${RESULTADOS:-resultados-teste} # pasta desta máquina dentro de resultados/

RELATIVO="$RESULTADOS${PASTA:+/$PASTA}" # caminho dentro de resultados/
DESTINO="resultados/$RELATIVO"
# Dentro do contêiner do Locust, a pasta resultados/ aparece como /resultados
CSV_NO_LOCUST="/resultados/$RELATIVO"

# Script do Locust de cada cenário
script_do_cenario() {
  case "$1" in
    1) echo "cenario1_imagem_1mb.py" ;;
    2) echo "cenario2_texto_400kb.py" ;;
    3) echo "cenario3_imagem_300kb.py" ;;
  esac
}

# Usuários que entram por segundo (-r): no mínimo 10/s, e todos sobem em ~20 s
taxa_de_entrada() {
  local taxa=$(( $1 / 20 ))
  if [ "$taxa" -lt 10 ]; then echo 10; else echo "$taxa"; fi
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
mkdir -p "$DESTINO/logs"
echo "Resultados em $DESTINO/"

for n in $INSTANCIAS; do
  echo "=== Subindo $n cópia(s) do WordPress"
  if ! ./escalar.sh "$n" > "$DESTINO/logs/escalar_${n}.log" 2>&1; then
    echo "ERRO: ./escalar.sh $n falhou. Veja $DESTINO/logs/escalar_${n}.log" >&2
    exit 1
  fi
  esperar_copias "$n"
  esperar_wordpress
  echo "    Nginx distribuindo entre $n cópia(s)"

  for c in $CENARIOS; do
    for u in $USUARIOS; do
      rodada=$((rodada + 1))
      nome="c${c}_i${n}_u${u}"

      if [ -f "$DESTINO/${nome}_stats.csv" ]; then
        echo "[$rodada/$total] $nome já existe, pulando"
        continue
      fi

      echo "[$rodada/$total] $nome: cenário $c, $n cópia(s), $u usuários, $DURACAO"
      # --no-deps: sem ele, o "run" volta o WordPress para as 3 cópias padrão.
      # "|| true": o Locust termina com código 1 quando houve falhas, e isso é
      # resultado do teste, não erro do script
      docker compose run --rm --no-deps \
        -e LOCUST_FILE="$(script_do_cenario "$c")" \
        -e LOCUST_OPTS="--headless -u $u -r $(taxa_de_entrada "$u") -t $DURACAO --reset-stats --csv $CSV_NO_LOCUST/$nome" \
        locust > "$DESTINO/logs/${nome}.log" 2>&1 || true

      # Sem CSV, o Locust nem chegou a rodar: aí sim é erro
      if [ ! -f "$DESTINO/${nome}_stats.csv" ]; then
        echo "ERRO: o Locust não gerou o CSV. Veja $DESTINO/logs/${nome}.log" >&2
        exit 1
      fi

      # Linha "Aggregated" do CSV: requisições, falhas, tempo médio e req/s
      awk -F, '$2 == "Aggregated" {
        pct = ($3 > 0) ? 100 * $4 / $3 : 0
        printf "    %d requisições, %d falhas (%.1f%%), tempo médio %.0f ms, %.1f req/s\n", $3, $4, pct, $6, $10
      }' "$DESTINO/${nome}_stats.csv"
      if ! grep -q "All users spawned" "$DESTINO/logs/${nome}.log"; then
        echo "    AVISO: nem todos os $u usuários subiram dentro de $DURACAO; aumente DURACAO"
      fi
      if grep -q "CPU usage above" "$DESTINO/logs/${nome}.log"; then
        echo "    AVISO: a CPU do Locust passou de 90%; ele pode ter gerado menos carga que o pedido"
      fi

      if [ "$rodada" -lt "$total" ]; then sleep "$PAUSA"; fi
    done
  done
done

echo "=== Fim: CSVs em $DESTINO/ e saída do Locust em $DESTINO/logs/"
