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

# Configuration for role mapping method
# Options: "role" (use roles claim) or "group" (use groups claim)
ROLE_MAPPING_METHOD = os.environ.get("ROLE_MAPPING_METHOD", "role").lower()

missing_env = [name for name, val in {
    "AZURE_TENANT_ID": AZURE_TENANT_ID,
    "AZURE_CLIENT_ID": AZURE_CLIENT_ID,
    "AZURE_CLIENT_SECRET": AZURE_CLIENT_SECRET,
}.items() if not val]

if missing_env:
    raise RuntimeError(f"❌ Missing required Azure env vars: {', '.join(missing_env)}")

if ROLE_MAPPING_METHOD not in ["role", "group"]:
    raise RuntimeError(f"❌ Invalid ROLE_MAPPING_METHOD: {ROLE_MAPPING_METHOD}. Must be 'role' or 'group'")

logger.debug(f"[OAUTH ENV] TENANT={AZURE_TENANT_ID}, CLIENT_ID={'SET' if AZURE_CLIENT_ID else 'NOT SET'}")
logger.debug(f"[OAUTH CONFIG] ROLE_MAPPING_METHOD={ROLE_MAPPING_METHOD}")

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
        logger.debug(f"🔐 Provider: {provider}")
        logger.debug(f"🔐 Using mapping method: {ROLE_MAPPING_METHOD}")
        logger.debug("🔐 " + "="*50)
  
        # แสดงข้อมูลทั้งหมดที่ Azure ส่งกลับมา
        logger.debug("🔐 [RESPONSE] Full Azure OAuth response:")
        for key, value in resp.items():
            logger.debug(f"🔐   {key}: {value!r}")
        logger.debug("🔐 " + "-"*50)

        # Check for roles and groups in both id_token_claims and userinfo
        id_token_claims = resp.get("id_token_claims", {})
        userinfo = resp.get("userinfo", {})
        
        logger.debug("🔐 [TOKEN_CLAIMS] Extracting claims from tokens:")
        logger.debug(f"🔐   id_token_claims keys: {list(id_token_claims.keys())}")
        logger.debug(f"🔐   userinfo keys: {list(userinfo.keys())}")
        logger.debug(f"🔐   id_token_claims (full): {id_token_claims!r}")
        logger.debug(f"🔐   userinfo (full): {userinfo!r}")
        logger.debug("🔐 " + "-"*50)

        # Azure AD App Role to Airflow Role mapping
        role_mapping = {
            "Airflow.Admin": "Admin",
            "Airflow.Viewer": "Viewer",
            "Airflow.ProjectA": "ProjectA",
            "Airflow.ProjectB": "ProjectB",
        }

        # Azure AD Group to Airflow Role mapping
        group_mapping = {
            "87759d0d-0948-4154-b5cc-0d9aa690c0d5" : "Admin",
            "87b76a76-2c08-4c49-aca6-830177ac6ae3" : "ProjectA"
        }


        # Map Azure AD roles to Airflow roles
        logger.debug("🔐 [MAPPING] Starting role/group mapping process:")
        logger.debug(f"🔐   Available role mappings: {role_mapping}")
        logger.debug(f"🔐   Available group mappings: {group_mapping}")
        
        mapped_roles = []
        
        if ROLE_MAPPING_METHOD == "role":
            logger.debug("🔐 [ROLE_MODE] Using role-based mapping")
            # Use role-based mapping
            roles_from_id_token = id_token_claims.get("roles", [])
            roles_from_userinfo = userinfo.get("roles", [])
            roles_from_token = roles_from_id_token or roles_from_userinfo
            
            logger.debug(f"🔐   Roles from id_token_claims: {roles_from_id_token}")
            logger.debug(f"🔐   Roles from userinfo: {roles_from_userinfo}")
            logger.debug(f"🔐   Final roles from token: {roles_from_token!r}")
            
            if not roles_from_token:
                logger.warning("⚠️ [ROLE_MODE] No roles found in token claims!")
            
            for azure_role in roles_from_token:
                logger.debug(f"🔐   Processing Azure role: '{azure_role}'")
                if azure_role in role_mapping:
                    airflow_role = role_mapping[azure_role]
                    mapped_roles.append(airflow_role)
                    logger.debug(f"🔐   ✅ [ROLE] Mapped '{azure_role}' -> '{airflow_role}'")
                else:
                    logger.warning(f"⚠️   [ROLE] Unknown Azure role '{azure_role}' - not in mapping: {list(role_mapping.keys())}")
                    
        elif ROLE_MAPPING_METHOD == "group":
            logger.debug("🔐 [GROUP_MODE] Using group-based mapping")
            # Use group-based mapping
            groups_from_id_token = id_token_claims.get("groups", [])
            groups_from_userinfo = userinfo.get("groups", [])
            groups_from_token = groups_from_id_token or groups_from_userinfo
            
            logger.debug(f"🔐   Groups from id_token_claims: {groups_from_id_token}")
            logger.debug(f"🔐   Groups from userinfo: {groups_from_userinfo}")
            logger.debug(f"🔐   Final groups from token: {groups_from_token!r}")
            
            if not groups_from_token:
                logger.warning("⚠️ [GROUP_MODE] No groups found in token claims!")
            
            for azure_group in groups_from_token:
                logger.debug(f"🔐   Processing Azure group: '{azure_group}'")
                if azure_group in group_mapping:
                    airflow_role = group_mapping[azure_group]
                    mapped_roles.append(airflow_role)
                    logger.debug(f"🔐   ✅ [GROUP] Mapped '{azure_group}' -> '{airflow_role}'")
                else:
                    logger.warning(f"⚠️   [GROUP] Unknown Azure group '{azure_group}' - not in mapping: {list(group_mapping.keys())}")
        
        logger.debug("🔐 " + "-"*50)
        logger.debug(f"🔐 [RESULT] Raw mapped roles (with duplicates): {mapped_roles}")
        
        # Remove duplicates while preserving order
        original_count = len(mapped_roles)
        mapped_roles = list(dict.fromkeys(mapped_roles))
        if original_count != len(mapped_roles):
            logger.debug(f"🔐 [RESULT] Removed {original_count - len(mapped_roles)} duplicate roles")
        
        # If no roles mapped, use default registration role
        if not mapped_roles:
            logger.warning(f"⚠️ [RESULT] No roles mapped! Using default role: {AUTH_USER_REGISTRATION_ROLE}")
            mapped_roles = [AUTH_USER_REGISTRATION_ROLE]
        
        logger.debug(f"🔐 [RESULT] Final mapped Airflow roles: {mapped_roles}")
        logger.debug("🔐 " + "-"*50)

        # Get user info from parent class
        logger.debug("🔐 [PARENT] Calling parent get_oauth_user_info...")
        user_info = super().get_oauth_user_info(provider, resp)
        logger.debug(f"🔐 [PARENT] Parent returned user_info keys: {list(user_info.keys())}")
        logger.debug(f"🔐 [PARENT] Original username from parent: {user_info.get('username')}")
        
        # Fix username mapping - use preferred_username or name instead of OID
        original_username = user_info.get('username')
        
        # Try to get a more readable username from token claims
        preferred_username = id_token_claims.get('preferred_username') or userinfo.get('preferred_username')
        display_name = id_token_claims.get('name') or userinfo.get('name')
        upn = id_token_claims.get('upn') or userinfo.get('upn')
        
        logger.debug(f"🔐 [USERNAME] Available username options:")
        logger.debug(f"🔐   Original (from parent): {original_username}")
        logger.debug(f"🔐   preferred_username: {preferred_username}")
        logger.debug(f"🔐   name: {display_name}")
        logger.debug(f"🔐   upn: {upn}")
        
        # Use preferred_username first, then upn, then name, fallback to original
        if preferred_username:
            user_info['username'] = preferred_username
            logger.debug(f"🔐 [USERNAME] ✅ Using preferred_username: {preferred_username}")
        elif upn:
            user_info['username'] = upn
            logger.debug(f"🔐 [USERNAME] ✅ Using upn: {upn}")
        elif display_name:
            user_info['username'] = display_name
            logger.debug(f"🔐 [USERNAME] ✅ Using display name: {display_name}")
        else:
            logger.warning(f"⚠️ [USERNAME] No readable username found, keeping original: {original_username}")
        
        # Add our mapped roles
        user_info["role_keys"] = mapped_roles
        logger.debug(f"🔐 [FINAL] Added role_keys to user_info: {mapped_roles}")

        logger.debug("🔐 [FINAL] Complete user_info:")
        for key, value in user_info.items():
            logger.debug(f"🔐   {key}: {value!r}")
        logger.debug("🔐 " + "="*50)
        return user_info

    def _log_user_info(self, userinfo):
        """
        Log user information for debugging.
        
        Args:
            userinfo (dict): User information dictionary
        """
        logger.debug("🔐 [auth_user_oauth] " + "="*50)
        logger.debug("🔐 [auth_user_oauth] Starting OAuth user authentication")
        logger.debug(f"🔐 [auth_user_oauth] Input userinfo keys: {list(userinfo.keys())}")
        logger.debug(f"🔐 [auth_user_oauth] Username: {userinfo.get('username')}")
        logger.debug(f"🔐 [auth_user_oauth] Email: {userinfo.get('email')}")
        logger.debug(f"🔐 [auth_user_oauth] First name: {userinfo.get('first_name')}")
        logger.debug(f"🔐 [auth_user_oauth] Last name: {userinfo.get('last_name')}")
        logger.debug(f"🔐 [auth_user_oauth] Role keys: {userinfo.get('role_keys', [])}")
        logger.debug("🔐 [auth_user_oauth] " + "-"*50)
    
    def _assign_roles_to_user(self, user, role_keys):
        """
        Assign roles to user, creating roles if they don't exist.
        
        Args:
            user: User object from database
            role_keys (list): List of role names to assign
            
        Returns:
            tuple: (successfully_assigned, failed_assignments) lists
        """
        # Clear existing roles
        old_roles = [r.name for r in user.roles]
        user.roles = []
        logger.debug(f"🔐 [auth_user_oauth] Cleared existing roles: {old_roles}")
        
        successfully_assigned = []
        failed_assignments = []
        
        # Process each role
        for role_name in role_keys:
            logger.debug(f"🔐 [auth_user_oauth] Processing role: '{role_name}'")
            role = self.find_role(role_name)
            
            # Create role if it doesn't exist
            if not role:
                logger.warning(f"⚠️ [auth_user_oauth] Role '{role_name}' not found, creating...")
                try:
                    role = self.add_role(role_name)
                    if role:
                        logger.debug(f"🔐 [auth_user_oauth] ✅ Created role '{role_name}'")
                    else:
                        logger.error(f"❌ [auth_user_oauth] Failed to create role '{role_name}'")
                        failed_assignments.append(role_name)
                        continue
                except Exception as e:
                    logger.error(f"❌ [auth_user_oauth] Exception creating role '{role_name}': {e}")
                    failed_assignments.append(role_name)
                    continue
            else:
                logger.debug(f"🔐 [auth_user_oauth] Found existing role '{role_name}' (ID: {role.id})")
            
            # Assign role to user
            if role and role not in user.roles:
                user.roles.append(role)
                successfully_assigned.append(role_name)
                logger.debug(f"🔐 [auth_user_oauth] ✅ Added role '{role_name}' to user")
            elif role in user.roles:
                logger.debug(f"🔐 [auth_user_oauth] Role '{role_name}' already assigned")
                successfully_assigned.append(role_name)
        
        return successfully_assigned, failed_assignments
    
    def auth_user_oauth(self, userinfo):
        """
        Override to ensure proper role assignment for OAuth users.
        
        Args:
            userinfo (dict): User information from OAuth provider
            
        Returns:
            User: User object with assigned roles, or None if failed
        """
        # Log user information
        self._log_user_info(userinfo)
        
        # Call parent method to handle user creation/update
        logger.debug("🔐 [auth_user_oauth] Calling parent auth_user_oauth...")
        user = super().auth_user_oauth(userinfo)
        
        if not user:
            logger.error("❌ [auth_user_oauth] Parent method returned None - user creation/authentication failed!")
            return None
            
        logger.debug(f"🔐 [auth_user_oauth] Parent returned user: {user.username} (ID: {user.id})")
        logger.debug(f"🔐 [auth_user_oauth] User's current roles before update: {[r.name for r in user.roles]}")
        
        # Get target roles from userinfo
        role_keys = userinfo.get('role_keys', [AUTH_USER_REGISTRATION_ROLE])
        logger.debug(f"🔐 [auth_user_oauth] Target roles to assign: {role_keys}")
        
        # Assign roles to user
        successfully_assigned, failed_assignments = self._assign_roles_to_user(user, role_keys)
        
        # Log assignment results
        logger.debug(f"🔐 [auth_user_oauth] Successfully assigned roles: {successfully_assigned}")
        if failed_assignments:
            logger.error(f"❌ [auth_user_oauth] Failed to assign roles: {failed_assignments}")
        
        # Save user to database
        try:
            logger.debug("🔐 [auth_user_oauth] Saving user to database...")
            self.get_session.merge(user)
            self.get_session.commit()
            final_roles = [r.name for r in user.roles]
            logger.debug(f"✅ [auth_user_oauth] User {user.username} successfully updated with roles: {final_roles}")
        except Exception as e:
            logger.error(f"❌ [auth_user_oauth] Failed to save user to database: {e}")
            self.get_session.rollback()
            raise
        
        logger.debug("🔐 [auth_user_oauth] " + "="*50)
        return user

SECURITY_MANAGER_CLASS = CustomSecurityManager