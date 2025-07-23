#!/bin/bash
set -e

SERVICE="airflow-scheduler"

echo "[INFO] ลบ role ProjectA และ ProjectB ถ้ามี"
docker compose exec -T $SERVICE airflow roles delete ProjectA || echo "[INFO] ไม่มี ProjectA"
docker compose exec -T $SERVICE airflow roles delete ProjectB || echo "[INFO] ไม่มี ProjectB"

echo "[INFO] แสดง roles ปัจจุบัน"
docker compose exec -T $SERVICE airflow roles list -o table
