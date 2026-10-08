export function roleKey(role) {
  return (role || "").trim().toLowerCase();
}

export function isIndcoolServiceRole(role) {
  const key = roleKey(role);
  return key === "indcool" || key === "indcool service" || key === "indcool_service" || key === "service";
}

export function isServiceDeskRole(role) {
  const key = roleKey(role);
  return key === "service" || key === "indcool_service";
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
