#!/bin/bash

# โหลดตัวแปรจาก .env
set -o allexport
source .env
set +o allexport

# ตรวจสอบว่า AZURE_TENANT_ID ถูกเซ็ตหรือไม่
if [ -z "$AZURE_TENANT_ID" ]; then
  echo "ERROR: ไม่พบ AZURE_TENANT_ID ใน .env"
  exit 1
fi

# กำหนด URL Airflow (แก้ไขถ้าไม่ใช่ localhost:8080)
AIRFLOW_URL="http://localhost:8080"

# 1. Logout Airflow
open "${AIRFLOW_URL}/logout"

# 2. Logout Azure SSO
open "https://login.microsoftonline.com/${AZURE_TENANT_ID}/oauth2/v2.0/logout"

# หมายเหตุ: ถ้าใช้ Linux เปลี่ยน open เป็น xdg-open
# xdg-open "${AIRFLOW_URL}/logout"
# xdg-open "https://login.microsoftonline.com/${AZURE_TENANT_ID}/oauth2/v2.0/logout"
