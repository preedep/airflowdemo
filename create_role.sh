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
  local role="$1"; shift
  local dags=("$@")

  # Grant UI menu access
  run_cli roles add-perms "$role" -a menu_access -r DAGs        || warn "menu_access DAGs"
  run_cli roles add-perms "$role" -a menu_access -r Browse      || warn "menu_access Browse"
  run_cli roles add-perms "$role" -a menu_access -r Assets      || warn "menu_access Assets"

  # Required resources with correct names (non-DAG scoped)
  run_cli roles add-perms "$role" -a can_read -r "Task Instances" || warn "can_read Task Instances"
  run_cli roles add-perms "$role" -a can_read -r "Task Logs"      || warn "can_read Task Logs"
  run_cli roles add-perms "$role" -a can_read -r "DAG Code"       || warn "can_read DAG Code"
  run_cli roles add-perms "$role" -a can_read -r "DAG Runs"       || warn "can_read DAG Runs"
  run_cli roles add-perms "$role" -a can_read -r "XComs"          || warn "can_read XComs"

  for dag in "${dags[@]}"; do
    log "🔐 Adding DAG-specific perms for '$dag' to role '$role'"

    run_cli roles add-perms "$role" -a can_read -r "DAG:$dag"    || warn "can_read DAG:$dag"
    run_cli roles add-perms "$role" -a can_edit -r "DAG:$dag"    || warn "can_edit DAG:$dag"
    # No can_trigger, skip or define custom if needed
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
