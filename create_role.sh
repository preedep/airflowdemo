#!/usr/bin/env bash
set -e

DOCKER_SERVICE="airflow-scheduler"
SCRIPT_NAME=$(basename "$0")

log()   { echo -e "\033[34m[INFO]  $* \033[0m"; }
warn()  { echo -e "\033[33m[WARN]  $* \033[0m"; }
error() { echo -e "\033[31m[ERROR] $* \033[0m"; }

run_cli() {
  log "airflow $*"
  docker compose exec -T "$DOCKER_SERVICE" airflow "$@"
}

check_running() {
  if ! docker compose ps | grep -q "$DOCKER_SERVICE.*Up"; then
    error "Service '$DOCKER_SERVICE' is not running."
    exit 1
  fi
}

create_role() {
  local role=$1
  run_cli roles create "$role" || warn "Role '$role' may already exist"
  run_cli roles add-perms "$role" -a can_read -r Website || warn "Permission Website already set"
}

add_dag_perms() {
  local role=$1; shift
  for dag in "$@"; do
    log "Adding perms for DAG '$dag' to role '$role'"
    run_cli roles add-perms "$role" -a can_read -r "DAG:$dag" || warn "can_read DAG:$dag"
    run_cli roles add-perms "$role" -a can_edit -r "DAG:$dag" || warn "can_edit DAG:$dag"
    run_cli roles add-perms "$role" -a can_read -r "DagRun:$dag" || warn "can_read DagRun:$dag"
    run_cli roles add-perms "$role" -a can_edit -r "DagRun:$dag" || warn "can_edit DagRun:$dag"
    run_cli roles add-perms "$role" -a can_read -r "TaskInstance:$dag" || warn "can_read TaskInstance:$dag"
    run_cli roles add-perms "$role" -a can_edit -r "TaskInstance:$dag" || warn "can_edit TaskInstance:$dag"
  done
}

list_roles() {
  run_cli roles list -o table -p || warn "Cannot list roles"
}

usage() {
  cat <<EOF
Usage: $SCRIPT_NAME ROLE DAG_ID [DAG_ID...]
Example: $SCRIPT_NAME ProjectA scb_ap1234_simple_dag scb_ap1234_other_dag
EOF
  exit 1
}

main() {
  if [ $# -lt 2 ]; then usage; fi
  check_running
  local role=$1; shift
  create_role "$role"
  add_dag_perms "$role" "$@"
  echo
  list_roles
}

main "$@"
