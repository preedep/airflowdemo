from __future__ import annotations
import os
# [Airflow 3.x migration] Legacy import removed in Airflow 3.x:
# from airflow.www.fab_security.manager import AUTH_OAUTH
from airflow.www.fab_security.manager import AUTH_OAUTH


# Robust logging config for Airflow webserver and custom modules
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "airflow": {
            "format": "%(asctime)s %(levelname)s %(name)s: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "airflow",
            "stream": "ext://sys.stdout",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG",
    },
    "loggers": {
        "airflow": {"level": "DEBUG", "handlers": ["console"], "propagate": False},
        "": {"level": "DEBUG", "handlers": ["console"], "propagate": False},
    },
}

# ด้านบนของไฟล์ webserver_config.py
from airflow.www.security import AirflowSecurityManager

class AzureCustomSecurity(AirflowSecurityManager):
    def get_oauth_user_info(self, provider, resp):
        if provider == "azure":
            me = self._azure_jwt_token_parse(resp["id_token"])
            return {
                "id": me["oid"],
                "username": me["oid"],
                "email": me.get("upn") or me.get("email"),
                "first_name": me.get("given_name", ""),
                "last_name": me.get("family_name", ""),
                "role_keys": me.get("roles", []),
            }
        return super().get_oauth_user_info(provider, resp)

SECURITY_MANAGER_CLASS = AzureCustomSecurity

# from customauthprovider.custom_auth_manager import CustomSecurityManager
# SECURITY_MANAGER_CLASS = CustomSecurityManager

# โหลดตัวแปรจาก Environment
TENANT = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")

import logging
logging.basicConfig(level=logging.DEBUG)
logging.warning(f"[OAUTH ENV] CLIENT_ID: {CLIENT_ID}")
logging.warning(f"[OAUTH ENV] CLIENT_SECRET: {'SET' if CLIENT_SECRET else 'NOT SET'}")
logging.warning(f"[OAUTH ENV] TENANT: {TENANT}")

# ตรวจสอบว่าตัวแปรทั้งหมดถูกตั้งค่า
missing = []
if not TENANT:
    missing.append("AZURE_TENANT_ID")
if not CLIENT_ID:
    missing.append("AZURE_CLIENT_ID")
if not CLIENT_SECRET:
    missing.append("AZURE_CLIENT_SECRET")
if missing:
    raise RuntimeError(f"Missing required Azure environment variable(s): {', '.join(missing)}")

# CSRF Protection (ต้องเปิดหากใช้ OAuth)
WTF_CSRF_ENABLED = True
WTF_CSRF_TIME_LIMIT = None


# ใช้ OAuth2
# from airflow.www.fab_security.manager import AUTH_OAUTH
AUTH_TYPE = AUTH_OAUTH  # [Airflow 3.x] Not used; remove legacy FAB config

# อนุญาตให้สมัคร User อัตโนมัติเมื่อ login สำเร็จ
AUTH_USER_REGISTRATION = True
AUTH_USER_REGISTRATION_ROLE = "Unassigned"  # 👈 ปลอดภัยกว่า Viewer

# Sync role ตาม Mapping ด้านล่าง (ขึ้นกับ Group Claim)
AUTH_ROLES_SYNC_AT_LOGIN = True

AUTH_ROLES_MAPPING = {
    "Airflow.Admin": ["Admin"],
    "Airflow.Viewer": ["Viewer"],
    "Airflow.ProjectA": ["ProjectA"],
    "Airflow.ProjectB" : ["ProjectB"]
}

# Provider OAuth2 (Microsoft Entra ID)
# for Airflow 2.11.x
OAUTH_PROVIDERS = [
    {
        "name": "azure",
        "token_key": "id_token",
        "remote_app": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "access_token_url": f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/token",
            "authorize_url": f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/authorize",
            "api_base_url": f"https://login.microsoftonline.com/{TENANT}/v2.0/",
            "jwks_uri": f"https://login.microsoftonline.com/{TENANT}/discovery/v2.0/keys",
            "client_kwargs": {"scope": "openid email profile"}
        }
    }
]
# for Airflow 3.x
AUTHLIB_OAUTH_CLIENTS = {
    "azure": {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "authorize_url": f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/authorize",
        "access_token_url": f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/token",
        "userinfo_endpoint": f"https://graph.microsoft.com/oidc/userinfo",
        "scope": "openid email profile",
    }
}