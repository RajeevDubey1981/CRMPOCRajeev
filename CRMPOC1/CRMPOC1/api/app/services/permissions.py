"""Per-role permission resolution.

A permission row with ``sub_module=None`` is module-wide (legacy semantics).
A row with ``sub_module="<value>"`` scopes the action to records where the
relevant sub-module discriminator (e.g. complaint query_type) equals that value.

A user is "unrestricted" for an action when ANY of their role's rows for the
module has ``sub_module=None`` AND the action flag is true, unless the role also
has sub-module rows where the flag is ticked for some and unticked for others. That
mix means someone ticked the whole module and then unticked a sub-module on purpose
(for example Complaints ticked, but Sales unticked), so only the ticked sub-modules
are in scope. A role whose sub-module rows are all unticked (the engineer) or all
ticked (the admin) keeps the whole-module meaning.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.role import Permission, Role
from app.models.user import User
from app.services.role_access import permission_role_name

Flag = str  # one of can_view / can_create / can_edit / can_delete / can_export


def _role_for(db: Session, user: User) -> Role | None:
    """Resolve a user's role to its permission record.

    ``indcool_service`` is the canonical permission role, while older users may
    have the display name ``Indcool Service`` stored on their account.  Treat
    the two spellings as the same operational role so permissions do not vary
    between the Complaint, Service, and Installation workflows.
    """
    key = permission_role_name(user.role)
    return db.scalar(select(Role).where(func.lower(func.trim(Role.name)) == key))


def sub_module_scope(db: Session, user: User, module: str, flag: Flag) -> set[str] | None:
    """Return the set of sub-module values the user is allowed to act on.

    Returns ``None`` if the user has an unrestricted (sub_module=None) permission
    for the flag — meaning every record is in scope, regardless of its sub-module.

    Returns an empty set if the user cannot act on any record (no permission at all).
    """
    role = _role_for(db, user)
    if role is None:
        return set()
    everything = db.scalars(select(Permission).where(Permission.role_id == role.id, Permission.module == module)).all()
    rows = [r for r in everything if getattr(r, flag)]
    if not rows:
        return set()
    if any(r.sub_module is None for r in rows):
        ticked = {r.sub_module for r in rows if r.sub_module is not None}
        unticked = {r.sub_module for r in everything if r.sub_module is not None and not getattr(r, flag)}
        if ticked and unticked:
            return ticked
        return None
    return {r.sub_module for r in rows if r.sub_module is not None}


def can_act_on(db: Session, user: User, module: str, flag: Flag, sub_module: str | None) -> bool:
    """Check whether the user can perform ``flag`` on a record with the given sub_module value.

    A record with ``sub_module=None`` (e.g. a complaint with no query_type) is only
    accessible to users with an unrestricted permission.
    """
    scope = sub_module_scope(db, user, module, flag)
    if scope is None:
        return True
    if sub_module is None:
        return False
    return sub_module in scope
