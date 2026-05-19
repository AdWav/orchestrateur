#!/usr/bin/env bash
set -euo pipefail

RUN_ID=""
TEAM=""
RUN_DEMO=0

usage() {
  echo "Usage: $0 --run-id <id> --team <team-tdd|team-classic> [--demo]"
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --run-id) RUN_ID="$2"; shift 2 ;;
    --team) TEAM="$2"; shift 2 ;;
    --demo) RUN_DEMO=1; shift ;;
    *) usage ;;
  esac
done

[[ -n "$RUN_ID" && -n "$TEAM" ]] || usage

TEAM_PATH="/workspaces/${RUN_ID}/${TEAM}"
if [[ "$RUN_DEMO" -eq 1 ]]; then
  CMD="cd ${TEAM_PATH} && python -m src.fizzbuzz"
else
  CMD="cd ${TEAM_PATH} && pytest -q"
fi

echo "workspace-runner: ${CMD}"
docker compose exec workspace-runner bash -lc "${CMD}"
