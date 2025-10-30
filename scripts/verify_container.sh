#!/usr/bin/env bash
set -euo pipefail


IMAGE_TAGS="${IMAGE_TAGS:-}"
IMAGE="${IMAGE_TAGS%%$'\n'*}"

CONTAINER_NAME="${CONTAINER_NAME:-app-test}"
PORT="${PORT:-8000}"
HEALTH_URL="${HEALTH_URL:-}"
HEALTH_PATH="${HEALTH_PATH:-/health}"
STARTUP_TIMEOUT="${STARTUP_TIMEOUT:-30}"
SLEEP_STEP="${SLEEP_STEP:-2}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"


if [[ -z "${IMAGE}" ]]; then
  echo "IMAGE_TAGS is empty — передай теги образа через env IMAGE_TAGS"
  exit 1
fi

if [[ -z "${HEALTH_URL}" ]]; then
  HEALTH_URL="http://localhost:${PORT}${HEALTH_PATH}"
fi

echo "Проверка контейнера через docker compose"
echo "Образ: ${IMAGE}"
echo "Compose file: ${COMPOSE_FILE}"
echo "Health check: ${HEALTH_URL}"
echo


echo "Поднимаем сервисы (app + db)..."
docker compose -f "${COMPOSE_FILE}" up -d --build --wait


echo "Ожидаем запуск приложения (до ${STARTUP_TIMEOUT}с)..."
elapsed=0
while (( elapsed < STARTUP_TIMEOUT )); do
  if curl -fsS "${HEALTH_URL}" >/dev/null 2>&1 || curl -fsS "http://localhost:${PORT}/" >/dev/null 2>&1; then
    echo "Сервис доступен!"
    docker compose ps
    docker compose down -v
    exit 0
  fi
  echo "⌛ ${elapsed}/${STARTUP_TIMEOUT}с..."
  sleep "${SLEEP_STEP}"
  elapsed=$((elapsed + SLEEP_STEP))
done

echo "Сервис не поднялся за ${STARTUP_TIMEOUT}с. Логи ниже:"
docker compose logs --no-color app db | tail -n 200 || true
docker compose down -v
exit 1
