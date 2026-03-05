#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/compose.dev.yml"
POSTGRES_CONTAINER="dietary_guardian_dev_postgres"
REDIS_CONTAINER="dietary_guardian_dev_redis"
POSTGRES_VOLUME="dietary_guardian_dev_postgres_data"
REDIS_VOLUME="dietary_guardian_dev_redis_data"
POSTGRES_IMAGE="postgres:16-alpine"
REDIS_IMAGE="redis:7-alpine"

docker_daemon_ready() {
  docker info >/dev/null 2>&1
}

ensure_docker_daemon() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "Missing dependency: docker." >&2
    exit 127
  fi
  if ! docker_daemon_ready; then
    echo "Docker daemon is not running. Start Docker Desktop/daemon and retry." >&2
    exit 1
  fi
}

compose_available() {
  docker compose version >/dev/null 2>&1
}

compose() {
  if compose_available; then
    docker compose -f "$COMPOSE_FILE" "$@"
    return
  fi
  if command -v docker-compose >/dev/null 2>&1; then
    docker-compose -f "$COMPOSE_FILE" "$@"
    return
  fi
  echo "Compose is unavailable; falling back to plain docker runtime." >&2
  return 125
}

docker_runtime_up() {
  docker volume create "$POSTGRES_VOLUME" >/dev/null
  docker volume create "$REDIS_VOLUME" >/dev/null

  if ! docker ps -a --format '{{.Names}}' | grep -x "$POSTGRES_CONTAINER" >/dev/null 2>&1; then
    docker run -d \
      --name "$POSTGRES_CONTAINER" \
      --restart unless-stopped \
      -e POSTGRES_DB=dietary_guardian \
      -e POSTGRES_USER=dietary_guardian \
      -e POSTGRES_PASSWORD=dietary_guardian \
      -p 5432:5432 \
      -v "$POSTGRES_VOLUME:/var/lib/postgresql/data" \
      "$POSTGRES_IMAGE" >/dev/null
  else
    docker start "$POSTGRES_CONTAINER" >/dev/null
  fi

  if ! docker ps -a --format '{{.Names}}' | grep -x "$REDIS_CONTAINER" >/dev/null 2>&1; then
    docker run -d \
      --name "$REDIS_CONTAINER" \
      --restart unless-stopped \
      -p 6379:6379 \
      -v "$REDIS_VOLUME:/data" \
      "$REDIS_IMAGE" >/dev/null
  else
    docker start "$REDIS_CONTAINER" >/dev/null
  fi
}

docker_runtime_down() {
  docker rm -f "$POSTGRES_CONTAINER" "$REDIS_CONTAINER" >/dev/null 2>&1 || true
}

docker_runtime_status() {
  docker ps --filter "name=^${POSTGRES_CONTAINER}$" --filter "name=^${REDIS_CONTAINER}$" --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
}

docker_runtime_logs() {
  docker logs --tail 200 "$POSTGRES_CONTAINER" 2>/dev/null || true
  echo "---"
  docker logs --tail 200 "$REDIS_CONTAINER" 2>/dev/null || true
}

run_with_infra_backend() {
  local cmd="$1"
  if compose_available || command -v docker-compose >/dev/null 2>&1; then
    compose "$cmd" "${@:2}"
    return
  fi
  case "$cmd" in
    up)
      docker_runtime_up
      ;;
    down)
      docker_runtime_down
      ;;
    ps)
      docker_runtime_status
      ;;
    logs)
      docker_runtime_logs
      ;;
    *)
      echo "Unsupported infra backend command: $cmd" >&2
      exit 2
      ;;
  esac
}

show_backend_mode() {
  if compose_available || command -v docker-compose >/dev/null 2>&1; then
    echo "Infra backend: compose"
  else
    echo "Infra backend: docker-run fallback"
  fi
}

usage() {
  echo "Usage: ./scripts/dev-infra.sh [up|down|restart|status|logs]" >&2
  exit 127
}

wait_for_port() {
  local host="$1"
  local port="$2"
  local timeout_seconds="${3:-45}"
  local elapsed=0
  while (( elapsed < timeout_seconds )); do
    if uv run --no-project python - <<PY >/dev/null 2>&1
import socket
sock = socket.socket()
sock.settimeout(1.0)
try:
    sock.connect(("$host", int("$port")))
    raise SystemExit(0)
except OSError:
    raise SystemExit(1)
finally:
    sock.close()
PY
    then
      return 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  return 1
}

cd "$ROOT_DIR"

COMMAND="${1:-up}"

case "$COMMAND" in
  up)
    ensure_docker_daemon
    run_with_infra_backend up -d postgres redis
    wait_for_port "127.0.0.1" "5432" "60" || {
      echo "Postgres did not become reachable on 127.0.0.1:5432 within timeout." >&2
      exit 1
    }
    wait_for_port "127.0.0.1" "6379" "60" || {
      echo "Redis did not become reachable on 127.0.0.1:6379 within timeout." >&2
      exit 1
    }
    echo "Infra is ready:"
    show_backend_mode
    run_with_infra_backend ps
    ;;
  down)
    ensure_docker_daemon
    run_with_infra_backend down
    ;;
  restart)
    ensure_docker_daemon
    run_with_infra_backend down
    run_with_infra_backend up -d postgres redis
    show_backend_mode
    run_with_infra_backend ps
    ;;
  status)
    ensure_docker_daemon
    show_backend_mode
    run_with_infra_backend ps
    ;;
  logs)
    ensure_docker_daemon
    show_backend_mode
    run_with_infra_backend logs --tail=200 postgres redis
    ;;
  *)
    usage
    ;;
esac
