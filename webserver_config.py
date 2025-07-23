from __future__ import annotations
import os
import logging
import sys

from flask_appbuilder.security.manager import AUTH_OAUTH
from airflow.providers.fab.auth_manager.security_manager.override import FabAirflowSecurityManagerOverride
from airflow.utils.log.logging_mixin import RedirectStdHandler

# ตั้งค่า logger
logger = logging.getLogger(__name__)
# ส่ง log ไป stdout เพื่อให้ docker-compose log เก็บได้
handler = RedirectStdHandler(stream='stdout')
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

logger.debug("✅ logger.debug ถูกเรียกจาก webserver_config.py")


# ตรวจสอบ environment variable
AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID")
AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID")
AZURE_CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET")

missing_env = [name for name, val in {
    "AZURE_TENANT_ID": AZURE_TENANT_ID,
    "AZURE_CLIENT_ID": AZURE_CLIENT_ID,
    "AZURE_CLIENT_SECRET": AZURE_CLIENT_SECRET,
}.items() if not val]

if missing_env:
    raise RuntimeError(f"❌ Missing required Azure env vars: {', '.join(missing_env)}")
logger.debug(f"[OAUTH ENV] TENANT={AZURE_TENANT_ID}, CLIENT_ID={'SET' if AZURE_CLIENT_ID else 'NOT SET'}")

# CSRF
WTF_CSRF_ENABLED = True
WTF_CSRF_TIME_LIMIT = None

# Airflow OAuth config
AUTH_TYPE = AUTH_OAUTH
AUTH_USER_REGISTRATION = True
AUTH_USER_REGISTRATION_ROLE = "Viewer"  # default role
AUTH_ROLES_SYNC_AT_LOGIN = True

OAUTH_PROVIDERS = [
    {
        "name": "azure",
        "token_key": "id_token",  # Important: this determines which token to extract claims from
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
        "role_keys": "roles",  # <-- this will be used in custom security manager
    }
]

# Custom SecurityManager for mapping Azure AD AppRole to Airflow Role
class CustomSecurityManager(FabAirflowSecurityManagerOverride):
    def get_oauth_user_info(self, provider, resp):
        logger.debug("🔐 [CustomSecurityManager] get_oauth_user_info called")
  
        # แสดงข้อมูลทั้งหมดที่ Azure ส่งกลับมา
        for key, value in resp.items():
            logger.debug(f"🔐 Azure resp key: {key} -> value: {value!r}")

        # Check for roles in both id_token_claims and userinfo
        id_token_claims = resp.get("id_token_claims", {})
        userinfo = resp.get("userinfo", {})
        
        logger.debug(f"🔐 id_token_claims (full): {id_token_claims!r}")
        logger.debug(f"🔐 userinfo (full): {userinfo!r}")

        # Try to get roles from id_token_claims first, then from userinfo
        roles_from_token = id_token_claims.get("roles", []) or userinfo.get("roles", [])
        
        logger.debug(f"🔐 Roles from id_token_claims: {id_token_claims.get('roles', [])}")
        logger.debug(f"🔐 Roles from userinfo: {userinfo.get('roles', [])}")
        logger.debug(f"🔐 Final roles from token: {roles_from_token!r}")


        # Azure AD App Role to Airflow Role mapping
        role_mapping = {
            "Airflow.Admin": "Admin",
            "Airflow.Viewer": "Viewer",
            "Airflow.ProjectA": "ProjectA",
            "Airflow.ProjectB": "ProjectB",
        }

        # Map Azure AD roles to Airflow roles
        mapped_roles = []
        for azure_role in roles_from_token:
            if azure_role in role_mapping:
                airflow_role = role_mapping[azure_role]
                mapped_roles.append(airflow_role)
                logger.debug(f"🔐 Mapped '{azure_role}' -> '{airflow_role}'")
            else:
                logger.warning(f"⚠️ Unknown Azure role '{azure_role}' - not mapped to any Airflow role")
        
        # If no roles mapped, use default registration role
        if not mapped_roles:
            mapped_roles = [AUTH_USER_REGISTRATION_ROLE]
            logger.debug(f"🔐 No roles mapped, using default role: {AUTH_USER_REGISTRATION_ROLE}")
        
        logger.debug(f"🔐 Final mapped Airflow roles: {mapped_roles}")

        user_info = super().get_oauth_user_info(provider, resp)
        user_info["role_keys"] = mapped_roles if mapped_roles else [AUTH_USER_REGISTRATION_ROLE]

        logger.debug(f"✅ Final user_info: {user_info}")
        return user_info

    def auth_user_oauth(self, userinfo):
        """Override to ensure proper role assignment for OAuth users"""
        logger.debug(f"🔐 [auth_user_oauth] Processing user: {userinfo.get('username')}")
        logger.debug(f"🔐 [auth_user_oauth] User roles: {userinfo.get('role_keys', [])}")
        
        # Call parent method to handle user creation/update
        user = super().auth_user_oauth(userinfo)
        
        if user:
            # Get the roles from userinfo
            role_keys = userinfo.get('role_keys', [AUTH_USER_REGISTRATION_ROLE])
            logger.debug(f"🔐 [auth_user_oauth] Assigning roles {role_keys} to user {user.username}")
            
            # Clear existing roles and assign new ones
            user.roles = []
            
            for role_name in role_keys:
                role = self.find_role(role_name)
                if not role:
                    logger.warning(f"⚠️ Role '{role_name}' not found, creating it")
                    # Create role if it doesn't exist
                    role = self.add_role(role_name)
                
                if role and role not in user.roles:
                    user.roles.append(role)
                    logger.debug(f"🔐 Added role '{role_name}' to user {user.username}")
            
            # Save the user with updated roles
            self.get_session.merge(user)
            self.get_session.commit()
            logger.debug(f"✅ User {user.username} updated with roles: {[r.name for r in user.roles]}")
        
        return user

SECURITY_MANAGER_CLASS = CustomSecurityManager