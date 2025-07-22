from __future__ import annotations
import os
import logging

from flask_appbuilder.security.manager import AUTH_OAUTH
from airflow.providers.fab.auth_manager.security_manager.override import FabAirflowSecurityManagerOverride



# ตั้งค่า log ให้ง่ายต่อการ debug
logging.basicConfig(level=logging.DEBUG)

# ตรวจสอบตัวแปรสิ่งแวดล้อมก่อนเริ่ม
AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID")
AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID")
AZURE_CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET")

logging.debug(f"[OAUTH ENV] TENANT={AZURE_TENANT_ID}, CLIENT_ID={'SET' if AZURE_CLIENT_ID else 'NOT SET'}")
if not (AZURE_TENANT_ID and AZURE_CLIENT_ID and AZURE_CLIENT_SECRET):
    missing = [v for v,n in [
        ("AZURE_TENANT_ID", AZURE_TENANT_ID),
        ("AZURE_CLIENT_ID", AZURE_CLIENT_ID),
        ("AZURE_CLIENT_SECRET", AZURE_CLIENT_SECRET),
    ] if not n]
    raise RuntimeError(f"Missing required Azure env vars: {','.join(missing)}")

# เปิดการป้องกัน CSRF สำหรับ OAuth login
WTF_CSRF_ENABLED = True
WTF_CSRF_TIME_LIMIT = None

# ตั้งค่า OAuth ผ่าน Flask AppBuilder
AUTH_TYPE = AUTH_OAUTH
SECURITY_MANAGER_CLASS = FabAirflowSecurityManagerOverride

AUTH_USER_REGISTRATION = True
AUTH_ROLES_SYNC_AT_LOGIN = True

AUTH_USER_REGISTRATION_ROLE = "Viewer"

AUTH_ROLES_MAPPING = {
    "Airflow.Admin": ["Admin"],
    "Airflow.Viewer": ["Viewer"],
    "Airflow.ProjectA": ["ProjectA"],
    "Airflow.ProjectB": ["ProjectB"],
}

OAUTH_PROVIDERS = [
    {
        "name": "azure",
        "token_key": "id_token",
        "icon": "fa-windows",
        "remote_app": {
            "client_id": AZURE_CLIENT_ID,
            "client_secret": AZURE_CLIENT_SECRET,
            "api_base_url": f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2",
            "authorize_url": f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/authorize",
            "access_token_url": f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/token",
            "jwks_uri": f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/discovery/v2.0/keys",
            "client_kwargs": {
                "scope": "openid email profile User.read",
            },
        },
    }
]