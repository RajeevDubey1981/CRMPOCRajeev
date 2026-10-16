import assert from "node:assert/strict";
import test from "node:test";
import * as roles from "./roles.js";

test("Non GST engineers have the same role checks as engineers", () => {
  for (const alias of ["Engineer", "Engineer Non GST", "engineer_non_gst", " ENGINEER NON-GST ", "engineer nongst"]) {
    assert.equal(roles.roleKey(alias), "engineer");
    for (const [name, check] of Object.entries(roles)) {
      if (name !== "roleKey") assert.equal(check(alias), check("engineer"), name);
    }
  }
  assert.equal(roles.roleKey("admin"), "admin");
  assert.equal(roles.roleKey("vendor"), "vendor");
});
