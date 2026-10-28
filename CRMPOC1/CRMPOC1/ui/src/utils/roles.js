export function roleKey(role) {
  const key = (role || "").trim().toLowerCase();
  return ["engineer", "engineer non gst", "engineer_non_gst", "engineer non-gst", "engineer nongst"].includes(key) ? "engineer" : key;
}

export function isIndcoolServiceRole(role) {
  const key = roleKey(role);
  return key === "indcool" || key === "indcool service" || key === "indcool_service" || key === "service";
}

export function isServiceDeskRole(role) {
  const key = roleKey(role);
  return key === "service" || key === "indcool_service";
}

// Admin and Sub Admin answer the Queries that everyone else raises
export function isQueryStaffRole(role) {
  const key = roleKey(role);
  return key === "admin" || key === "incool" || key === "sub_admin";
}

export function isSubAdminRole(role) {
  return roleKey(role) === "sub_admin";
}

export function isServiceManagerRole(role) {
  const key = roleKey(role);
  return key === "service_manager" || key === "admin" || key === "sub_admin";
}

export function isSystemAdminRole(role) {
  const key = roleKey(role);
  return key === "admin" || key === "incool";
}

export function isPartnerAdminRole(role) {
  const key = roleKey(role);
  return key === "admin" || key === "incool" || key === "indcool" || key === "sub_admin";
}

export function canViewAllServiceRequests(role) {
  const key = roleKey(role);
  return (
    key === "admin"
    || key === "incool"
    || key === "indcool"
    || key === "indcool service"
    || key === "service_manager"
    || key === "sub_admin"
  );
}

export function canAssignServiceDeskUser(role) {
  return isServiceManagerRole(role);
}

export function isOperationsAdminRole(role) {
  return isSystemAdminRole(role) || isIndcoolServiceRole(role) || isServiceManagerRole(role);
}

export function isServiceTeamRole(role) {
  return isOperationsAdminRole(role) || isServiceDeskRole(role);
}

// The bare "service" role only, narrowed to the installation/request actually assigned to them --
// "indcool_service" is full-ops (see isOperationsAdminRole) despite also matching isServiceDeskRole,
// mirroring the backend's is_service_desk_user(), which excludes it the same way.
export function isNarrowServiceDeskRole(role) {
  return roleKey(role) === "service";
}

// Who may actually decide a per-serial service approval: Service Manager (capped at the backend's
// ₹2500 limit) and Admin/Sub Admin/Incool (unlimited, can override). Service-desk roles and the
// engineer can verify, observe, and recommend, but this is the one thing they can't do.
export function canApproveServiceUnits(role) {
  return isServiceManagerRole(role) || isSystemAdminRole(role);
}

// Who forwards the engineer's recommendation on to the Service Manager: Service Team (service desk
// roles) and Admin/Sub Admin/Incool (who can skip ahead at any stage). Service Manager itself doesn't
// forward -- it's the one receiving the forward, same chain as the backend's UNIT_FORWARD_ROLES.
export function canForwardServiceUnits(role) {
  return isIndcoolServiceRole(role) || isSystemAdminRole(role) || isSubAdminRole(role);
}
