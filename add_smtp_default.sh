#!/bin/bash

# Script to add SMTP default connection to Airflow using .env parameters
# Usage: ./add_smtp_default.sh

set -e

echo "🔧 Adding SMTP default connection to Airflow..."

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create .env file with SMTP configuration:"
    echo "SMTP_HOST=smtp.gmail.com"
    echo "SMTP_PORT=587"
    echo "SMTP_USER=your-email@gmail.com"
    echo "SMTP_PASSWORD=your-app-password"
    echo "SMTP_STARTTLS=true"
    echo "SMTP_SSL=false"
    echo "SMTP_MAIL_FROM=your-email@gmail.com"
    exit 1
fi

# Load environment variables from .env file
echo "📄 Loading environment variables from .env..."
source .env

# Validate required environment variables
if [ -z "$SMTP_HOST" ] || [ -z "$SMTP_PORT" ] || [ -z "$SMTP_USER" ] || [ -z "$SMTP_PASSWORD" ]; then
    echo "❌ Error: Missing required SMTP environment variables!"
    echo "Required variables: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD"
    exit 1
fi

# Set default values if not provided
SMTP_STARTTLS=${SMTP_STARTTLS:-true}
SMTP_SSL=${SMTP_SSL:-false}
SMTP_MAIL_FROM=${SMTP_MAIL_FROM:-$SMTP_USER}

echo "📧 SMTP Configuration:"
echo "  Host: $SMTP_HOST"
echo "  Port: $SMTP_PORT"
echo "  User: $SMTP_USER"
echo "  Password: [HIDDEN]"
echo "  STARTTLS: $SMTP_STARTTLS"
echo "  SSL: $SMTP_SSL"
echo "  Mail From: $SMTP_MAIL_FROM"

# Check if Airflow services are running
echo "🔍 Checking Airflow services..."
if ! docker compose ps airflow-scheduler | grep -q "healthy\|running"; then
    echo "❌ Error: Airflow scheduler is not running!"
    echo "Please start Airflow services first: docker compose up -d"
    exit 1
fi

# Remove existing smtp_default connection if it exists
echo "🗑️  Removing existing smtp_default connection (if exists)..."
docker compose exec airflow-scheduler airflow connections delete smtp_default 2>/dev/null || true

# Create SMTP connection with proper JSON formatting
echo "➕ Adding new smtp_default connection..."

# Convert string boolean to JSON boolean
if [ "$SMTP_STARTTLS" = "True" ]; then
    TLS_JSON="true"
else
    TLS_JSON="false"
fi

if [ "$SMTP_SSL" = "True" ]; then
    SSL_JSON="true"
else
    SSL_JSON="false"
fi

SMTP_EXTRA="{\"use_tls\": $TLS_JSON, \"use_ssl\": $SSL_JSON}"

docker compose exec airflow-scheduler airflow connections add 'smtp_default' \
    --conn-type 'smtp' \
    --conn-host "$SMTP_HOST" \
    --conn-port "$SMTP_PORT" \
    --conn-login "$SMTP_USER" \
    --conn-password "$SMTP_PASSWORD" \
    --conn-extra "$SMTP_EXTRA"

if [ $? -eq 0 ]; then
    echo "✅ SMTP connection 'smtp_default' added successfully!"
    echo ""
    echo "📋 Connection Details:"
    docker compose exec airflow-scheduler airflow connections get smtp_default
    echo ""
    echo "🧪 You can now test email notifications by triggering a DAG."
else
    echo "❌ Failed to add SMTP connection!"
    exit 1
fi

echo "🎉 SMTP setup completed!"
echo "💡 Tip: Make sure your Gmail account has 2FA enabled and use an App Password for SMTP_PASSWORD"