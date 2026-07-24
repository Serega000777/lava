ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "user": frozenset({"profile:read", "profile:update", "listing:create"}),
    "specialist": frozenset({"profile:read", "profile:update", "listing:create", "portfolio:update"}),
    "company": frozenset({"profile:read", "profile:update", "listing:create", "organization:update"}),
    "moderator": frozenset({"profile:read", "moderation:read", "moderation:decide"}),
    "admin": frozenset({"*"}),
}


def has_permission(role: str, permission: str) -> bool:
    permissions = ROLE_PERMISSIONS.get(role, frozenset())
    return "*" in permissions or permission in permissions

