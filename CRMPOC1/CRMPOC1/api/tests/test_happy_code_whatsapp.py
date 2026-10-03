from types import SimpleNamespace

from app.config import settings
from app.services import service_whatsapp, workflow_notifications


class _Resp:
    def __init__(self, ok=True, status_code=200, text="{}"):
        self.ok, self.status_code, self.text = ok, status_code, text


def _enable(monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_enabled", True)
    monkeypatch.setattr(settings, "wa_phone_number_id", "12345")
    monkeypatch.setattr(settings, "wa_access_token", "Bearer TESTTOKEN")


def test_payload_is_authentication_template_with_code_in_body_and_button(monkeypatch):
    _enable(monkeypatch)
    seen = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        seen.update(url=url, json=json, headers=headers)
        return _Resp()

    monkeypatch.setattr(service_whatsapp.requests, "post", fake_post)
    ok = service_whatsapp.send_service_happy_code_whatsapp(
        "98765 43210", customer_name="  Amit   Sharma ", service_code="1407", completion_code="482913"
    )
    assert ok is True
    assert seen["url"].endswith("/12345/messages")
    assert seen["headers"]["Authorization"] == "Bearer TESTTOKEN"
    body = seen["json"]
    assert body["to"] == "919876543210"
    assert body["template"]["name"] == "service_happy_code_otp"
    assert body["template"]["language"]["code"] == "en_US"
    comps = body["template"]["components"]
    assert comps[0] == {"type": "body", "parameters": [{"type": "text", "text": "482913"}]}
    assert comps[1] == {"type": "button", "sub_type": "url", "index": "0", "parameters": [{"type": "text", "text": "482913"}]}


def test_missing_name_is_fine_and_disabled_or_no_mobile_skips(monkeypatch):
    _enable(monkeypatch)
    calls = []
    monkeypatch.setattr(service_whatsapp.requests, "post", lambda *a, **k: calls.append(k["json"]) or _Resp())
    assert service_whatsapp.send_service_happy_code_whatsapp("9876543210", customer_name=None, service_code="9", completion_code="123456")
    assert calls[-1]["template"]["components"][0]["parameters"][0]["text"] == "123456"

    assert service_whatsapp.send_service_happy_code_whatsapp("", customer_name="A", service_code="9", completion_code="1") is False
    monkeypatch.setattr(settings, "whatsapp_enabled", False)
    n = len(calls)
    assert service_whatsapp.send_service_happy_code_whatsapp("9876543210", customer_name="A", service_code="9", completion_code="1") is False
    assert len(calls) == n


def test_rejection_does_not_raise(monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(service_whatsapp.requests, "post", lambda *a, **k: _Resp(ok=False, status_code=400, text="template not approved"))
    assert service_whatsapp.send_service_happy_code_whatsapp("9876543210", customer_name="A", service_code="9", completion_code="1") is False


def test_assignment_sends_both_email_and_whatsapp(monkeypatch):
    emails, whats = [], []
    monkeypatch.setattr(workflow_notifications, "send_service_happy_code_email", lambda to, **k: emails.append((to, k)))
    monkeypatch.setattr(workflow_notifications, "send_service_happy_code_messages", lambda mobile, **k: whats.append((mobile, k)))
    svc = SimpleNamespace(id=1407, customer_email="c@example.com", customer_mobile="9876543210", customer_name="Amit")
    workflow_notifications.notify_customer_happy_code(None, svc, completion_code="482913")
    assert emails == [("c@example.com", {"service_id": 1407, "completion_code": "482913"})]
    assert whats == [("9876543210", {"customer_name": "Amit", "service_code": "1407", "completion_code": "482913"})]

    # email only / mobile only
    emails.clear(); whats.clear()
    workflow_notifications.notify_customer_happy_code(None, SimpleNamespace(id=2, customer_email=None, customer_mobile="9876543210", customer_name=""), completion_code="111111")
    assert not emails and whats[0][1]["customer_name"] is None
    emails.clear(); whats.clear()
    workflow_notifications.notify_customer_happy_code(None, SimpleNamespace(id=3, customer_email="x@y.com", customer_mobile=None, customer_name="B"), completion_code="222222")
    assert emails and not whats


def test_visit_confirmation_then_code_are_sent_in_order(monkeypatch):
    _enable(monkeypatch)
    sent = []
    monkeypatch.setattr(service_whatsapp.requests, "post", lambda url, json=None, **k: sent.append(json) or _Resp())
    service_whatsapp.send_service_happy_code_messages(
        "9876543210", customer_name="Amit Sharma", service_code="1407", completion_code="482913"
    )
    assert [m["template"]["name"] for m in sent] == ["service_visit_confirmed", "service_happy_code_otp"]
    assert [p["text"] for p in sent[0]["template"]["components"][0]["parameters"]] == ["Amit Sharma", "1407"]
    assert sent[1]["template"]["components"][0]["parameters"][0]["text"] == "482913"


def test_code_still_sent_when_confirmation_template_is_rejected(monkeypatch):
    _enable(monkeypatch)
    sent = []

    def fake_post(url, json=None, **k):
        sent.append(json["template"]["name"])
        return _Resp(ok=json["template"]["name"] != "service_visit_confirmed", status_code=400, text="template not approved")

    monkeypatch.setattr(service_whatsapp.requests, "post", fake_post)
    service_whatsapp.send_service_happy_code_messages("9876543210", customer_name="A", service_code="9", completion_code="123456")
    assert sent == ["service_visit_confirmed", "service_happy_code_otp"]
