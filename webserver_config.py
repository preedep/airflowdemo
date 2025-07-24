from __future__ import annotations
import os
import logging
import sys
import json
import time
from pathlib import Path
from typing import Dict, Tuple, Optional

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
ROLE_MAPPING_METHOD = os.environ.get("ROLE_MAPPING_METHOD", "group").lower()

# Configuration for role mapping file
ROLE_MAPPING_FILE = os.environ.get("ROLE_MAPPING_FILE", "role_mapping.json")
ROLE_MAPPING_CACHE_TTL = int(os.environ.get("ROLE_MAPPING_CACHE_TTL", "300"))  # 5 minutes default

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
logger.debug(f"[OAUTH CONFIG] ROLE_MAPPING_FILE={ROLE_MAPPING_FILE}")
logger.debug(f"[OAUTH CONFIG] ROLE_MAPPING_CACHE_TTL={ROLE_MAPPING_CACHE_TTL}s")

# Global cache for role mappings
_role_mapping_cache = {
    'data': None,
    'timestamp': 0,
    'file_mtime': 0
}

def _get_file_path(file_path: str) -> Path:
    """Get absolute path for role mapping file with validation."""
    path = Path(file_path)
    if not path.is_absolute():
        # If relative path, make it relative to this config file's directory
        config_dir = Path(__file__).parent
        path = config_dir / path
    return path

def _validate_role_mapping_structure(data: dict) -> bool:
    """Validate the structure of role mapping JSON."""
    if not isinstance(data, dict):
        return False
    
    # Check for required keys
    if 'role_mapping' not in data and 'group_mapping' not in data:
        logger.warning("🔐 [VALIDATION] Neither 'role_mapping' nor 'group_mapping' found in config")
        return False
    
    # Validate role_mapping structure
    if 'role_mapping' in data:
        if not isinstance(data['role_mapping'], dict):
            logger.error("🔐 [VALIDATION] 'role_mapping' must be a dictionary")
            return False
    
    # Validate group_mapping structure
    if 'group_mapping' in data:
        if not isinstance(data['group_mapping'], dict):
            logger.error("🔐 [VALIDATION] 'group_mapping' must be a dictionary")
            return False
    
    return True

def load_role_mappings(file_path: Optional[str] = None, force_reload: bool = False) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Load role and group mappings from JSON file with caching and validation.
    
    Args:
        file_path: Path to role mapping JSON file. If None, uses ROLE_MAPPING_FILE env var.
        force_reload: If True, bypass cache and reload from file.
    
    Returns:
        Tuple of (role_mapping, group_mapping) dictionaries.
    """
    global _role_mapping_cache
    
    if file_path is None:
        file_path = ROLE_MAPPING_FILE
    
    try:
        file_path_obj = _get_file_path(file_path)
        current_time = time.time()
        
        # Check if file exists
        if not file_path_obj.exists():
            logger.error(f"🔐 [ERROR] Role mapping file not found: {file_path_obj}")
            return {}, {}
        
        file_mtime = file_path_obj.stat().st_mtime
        
        # Check cache validity
        cache_valid = (
            not force_reload and
            _role_mapping_cache['data'] is not None and
            (current_time - _role_mapping_cache['timestamp']) < ROLE_MAPPING_CACHE_TTL and
            _role_mapping_cache['file_mtime'] == file_mtime
        )
        
        if cache_valid:
            logger.debug("🔐 [CACHE] Using cached role mappings")
            data = _role_mapping_cache['data']
        else:
            logger.debug(f"🔐 [LOAD] Loading role mappings from: {file_path_obj}")
            
            with open(file_path_obj, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate structure
            if not _validate_role_mapping_structure(data):
                logger.error("🔐 [ERROR] Invalid role mapping file structure")
                return {}, {}
            
            # Update cache
            _role_mapping_cache.update({
                'data': data,
                'timestamp': current_time,
                'file_mtime': file_mtime
            })
            
            logger.debug("🔐 [CACHE] Role mappings cached successfully")
        
        role_mapping = data.get('role_mapping', {})
        group_mapping = data.get('group_mapping', {})
        
        logger.debug(f"🔐 [CONFIG] Loaded {len(role_mapping)} role mappings, {len(group_mapping)} group mappings")
        
        return role_mapping, group_mapping
        
    except FileNotFoundError:
        logger.error(f"🔐 [ERROR] Role mapping file not found: {file_path}")
        return {}, {}
    except json.JSONDecodeError as e:
        logger.error(f"🔐 [ERROR] Invalid JSON in role mapping file: {e}")
        return {}, {}
    except PermissionError:
        logger.error(f"🔐 [ERROR] Permission denied reading role mapping file: {file_path}")
        return {}, {}
    except Exception as e:
        logger.error(f"🔐 [ERROR] Unexpected error loading role mappings: {e}")
        return {}, {}

# CSRF
WTF_CSRF_ENABLED = True
WTF_CSRF_TIME_LIMIT = None

# Airflow OAuth config
AUTH_TYPE = AUTH_OAUTH
AUTH_USER_REGISTRATION = True
AUTH_USER_REGISTRATION_ROLE = "Unassigned"  # default role
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

        # Load role and group mappings using professional utility function
        role_mapping, group_mapping = load_role_mappings()


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
        role_keys = userinfo.get('role_keys', [])
        
        # If no roles were mapped or role_keys is empty, use default registration role
        if not role_keys:
            role_keys = [AUTH_USER_REGISTRATION_ROLE]
            logger.debug(f"🔐 [auth_user_oauth] No roles mapped, using default role: {AUTH_USER_REGISTRATION_ROLE}")
        
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