from enum import StrEnum

from alloy_api.workspaces.models import WorkspaceRole


class Permission(StrEnum):
    CRM_READ = "crm:read"
    CRM_WRITE = "crm:write"
    MEMBERS_READ = "members:read"
    MEMBERS_MANAGE = "members:manage"
    WORKSPACE_MANAGE = "workspace:manage"
    WORKSPACE_DELETE = "workspace:delete"


_VIEWER = frozenset({Permission.CRM_READ, Permission.MEMBERS_READ})
_MEMBER = _VIEWER | {Permission.CRM_WRITE}
_ADMIN = _MEMBER | {Permission.MEMBERS_MANAGE, Permission.WORKSPACE_MANAGE}
_OWNER = _ADMIN | {Permission.WORKSPACE_DELETE}

ROLE_PERMISSIONS: dict[WorkspaceRole, frozenset[Permission]] = {
    WorkspaceRole.OWNER: _OWNER,
    WorkspaceRole.ADMIN: _ADMIN,
    WorkspaceRole.MEMBER: _MEMBER,
    WorkspaceRole.VIEWER: _VIEWER,
}

# Higher is more powerful. Used to decide who may manage whom.
_RANK = {role: rank for rank, role in enumerate(reversed(list(WorkspaceRole)))}


def permissions_for(role: WorkspaceRole) -> frozenset[Permission]:
    return ROLE_PERMISSIONS[role]


def can_manage_role(actor: WorkspaceRole, target: WorkspaceRole) -> bool:
    """Whether `actor` may assign, change, or remove a seat with role `target`.

    Owners manage everyone; everyone else manages only roles below their own, so an
    admin cannot promote to admin, touch other admins, or reach owners.
    """
    if actor is WorkspaceRole.OWNER:
        return True
    return _RANK[actor] > _RANK[target]
