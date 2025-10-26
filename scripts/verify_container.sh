#!/usr/bin/env bash
set -euo pipefail


IMAGE_TAGS="${IMAGE_TAGS:-}"

IMAGE="${IMAGE_TAGS%%$'\n'*}"

CONTAINER_NAME="${CONTAINER_NAME:-app-test}"
PORT="${PORT:-8000}"

HEALTH_URL="${HEALTH_URL:-}"
HEALTH_PATH="${HEALTH_PATH:-/health}"
STARTUP_TIMEOUT="${STARTUP_TIMEOUT:-20}"
SLEEP_STEP="${SLEEP_STEP:-1}"

if [[ -z "${IMAGE}" ]]; then
  echo "IMAGE_TAGS is empty — передай теги образа через env IMAGE_TAGS"
  exit 1
fi

if [[ -z "${HEALTH_URL}" ]]; then
  HEALTH_URL="http://localhost:${PORT}${HEALTH_PATH}"
fi

echo "Запуск контейнера ${CONTAINER_NAME} из образа: ${IMAGE}"
docker run -d --rm -p "${PORT}:${PORT}" --name "${CONTAINER_NAME}" "${IMAGE}" >/dev/null


trap 'docker stop "${CONTAINER_NAME}" >/dev/null 2>&1 || true' EXIT

echo "Ожидается запуск сервиса (до ${STARTUP_TIMEOUT}с), health: ${HEALTH_URL}"
elapsed=0
while (( elapsed < STARTUP_TIMEOUT )); do
  if curl -fsS "${HEALTH_URL}" >/dev/null 2>&1 || curl -fsS "http://localhost:${PORT}/" >/dev/null 2>&1; then
    echo "Service is up"
    exit 0
  fi
  sleep "${SLEEP_STEP}"
  elapsed=$((elapsed + SLEEP_STEP))
done

echo "Сервис не поднялся за ${STARTUP_TIMEOUT}с. Логи контейнера ниже:"
docker logs "${CONTAINER_NAME}" || true
exit 1
