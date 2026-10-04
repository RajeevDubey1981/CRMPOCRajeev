from types import SimpleNamespace

from app.config import settings
from app.services import sms_service, workflow_notifications


class _Resp:
    def __init__(self, data=None, ok=True, status_code=200):
        self._data, self.ok, self.status_code = data if data is not None else {"ErrorCode": "000", "ErrorMessage": "Done", "JobId": "1"}, ok, status_code

    def json(self):
        return self._data


def _configure(monkeypatch):
    for k, v in {
        "sms_enabled": True, "sms_user": "u", "sms_password": "p", "sms_sender_id": "INDCOL",
        "sms_pe_id": "1101", "sms_happy_code_template_id": "1107", "sms_channel": "Trans", "sms_route": "",
    }.items():
        monkeypatch.setattr(settings, k, v)


def test_sends_the_hub_request_with_dlt_fields(monkeypatch):
    _configure(monkeypatch)
    seen = {}
    monkeypatch.setattr(sms_service.requests, "get", lambda url, params=None, timeout=None: seen.update(url=url, params=params) or _Resp())
    ok = sms_service.send_service_happy_code_sms("98765 43210", customer_name=" Amit  Sharma ", service_code="1407", completion_code="482913")
    assert ok is True
    p = seen["params"]
    assert seen["url"].endswith("/api/mt/SendSMS")
    assert p["number"] == "919876543210" and p["senderid"] == "INDCOL" and p["channel"] == "Trans"
    assert p["DLTTemplateId"] == "1107" and p["PEId"] == "1101" and p["DCS"] == "0" and p["flashsms"] == "0"
    assert "route" not in p
    assert "Amit Sharma" in p["text"] and "1407" in p["text"] and "Happy Code is 482913" in p["text"]


def test_route_is_sent_only_when_set(monkeypatch):
    _configure(monkeypatch)
    monkeypatch.setattr(settings, "sms_route", "5")
    seen = {}
    monkeypatch.setattr(sms_service.requests, "get", lambda url, params=None, timeout=None: seen.update(params=params) or _Resp())
    sms_service.send_service_happy_code_sms("9876543210", customer_name=None, service_code="9", completion_code="1")
    assert seen["params"]["route"] == "5"
    assert seen["params"]["text"].startswith("Dear Customer,")


def test_off_by_default_and_when_incomplete(monkeypatch):
    calls = []
    monkeypatch.setattr(sms_service.requests, "get", lambda *a, **k: calls.append(1) or _Resp())
    assert sms_service.send_service_happy_code_sms("9876543210", customer_name="A", service_code="9", completion_code="1") is False
    _configure(monkeypatch)
    monkeypatch.setattr(settings, "sms_happy_code_template_id", "")
    assert sms_service.send_service_happy_code_sms("9876543210", customer_name="A", service_code="9", completion_code="1") is False
    monkeypatch.setattr(settings, "sms_happy_code_template_id", "1107")
    assert sms_service.send_service_happy_code_sms("", customer_name="A", service_code="9", completion_code="1") is False
    assert calls == []


def test_hub_error_returns_false_and_does_not_log_the_password(monkeypatch, caplog):
    _configure(monkeypatch)
    monkeypatch.setattr(sms_service.requests, "get", lambda *a, **k: _Resp({"ErrorCode": "006", "ErrorMessage": "Invalid DLT template"}))
    with caplog.at_level("ERROR"):
        assert sms_service.send_service_happy_code_sms("9876543210", customer_name="A", service_code="9", completion_code="1") is False
    assert "Invalid DLT template" in caplog.text and "password" not in caplog.text.lower() and "p=" not in caplog.text


def test_bad_text_placeholder_is_handled(monkeypatch):
    _configure(monkeypatch)
    monkeypatch.setattr(settings, "sms_happy_code_text", "Hello {nme} {code}")
    assert sms_service.send_service_happy_code_sms("9876543210", customer_name="A", service_code="9", completion_code="1") is False


def test_assignment_triggers_sms_too(monkeypatch):
    got = []
    monkeypatch.setattr(workflow_notifications, "send_service_happy_code_email", lambda *a, **k: None)
    monkeypatch.setattr(workflow_notifications, "send_service_happy_code_whatsapp", lambda *a, **k: None)
    monkeypatch.setattr(workflow_notifications, "send_service_happy_code_sms", lambda mobile, **k: got.append((mobile, k)))
    svc = SimpleNamespace(id=1407, customer_email=None, customer_mobile="9876543210", customer_name="Amit")
    workflow_notifications.notify_customer_happy_code(None, svc, completion_code="482913")
    assert got == [("9876543210", {"customer_name": "Amit", "service_code": "1407", "completion_code": "482913"})]
