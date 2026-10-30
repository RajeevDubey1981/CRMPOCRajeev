"""Isolated email tests; no database or SMTP connection is required."""
import ast
from datetime import date
from html import escape
from pathlib import Path
import unittest
from unittest.mock import Mock


class PooledPaymentEmailTests(unittest.TestCase):
    def setUp(self):
        source = Path(__file__).resolve().parents[1] / "app/services/workflow_notifications.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in {
            "_queue", "_details_html", "_send_payment_credited_email", "notify_pooled_payment_credited"
        }]
        self.send = Mock(return_value=True)
        self.scope = dict(escape=escape, send_template_email=self.send,
                          HELPDESK_EMAIL="support@indcool.in", TOLL_FREE_NUMBER="1800-11-9515",
                          _from_name=lambda: "INDcool Service Team")
        module = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)] + functions, type_ignores=[])
        exec(compile(ast.fix_missing_locations(module), str(source), "exec"), self.scope)

    def notify(self, **overrides):
        args = dict(payee_email="engineer@example.com", payee_name="Rajesh",
                    items=[("Installation #101", 1200), ("Service SR-202 / Payment #7", 800)],
                    total_amount=2000, payment_type="UPI", payment_reference="UTR123",
                    payment_paid_on=date(2026, 10, 30))
        args.update(overrides)
        self.scope["notify_pooled_payment_credited"](None, **args)

    def test_mixed_pool_sends_one_email_with_total_and_each_item(self):
        self.notify()
        self.send.assert_called_once()
        mail = self.send.call_args.kwargs
        self.assertEqual(mail["template"], "payment_credited")
        self.assertEqual(mail["subject"], "Payment credited — ₹2,000.00")
        for text in ("Installation #101", "₹1,200.00", "Service SR-202 / Payment #7", "₹800.00", "UTR123", "30 Oct 2026", "2 request(s)"):
            self.assertIn(text, mail["context"]["details_html"])

    def test_vendor_pool_uses_vendor_recipient(self):
        self.notify(payee_email="vendor@example.com", payee_name="Vendor Ltd")
        self.assertEqual(self.send.call_args.kwargs["to"], "vendor@example.com")
        self.assertEqual(self.send.call_args.kwargs["context"]["recipient_name"], "Vendor Ltd")

    def test_missing_recipient_or_empty_pool_sends_nothing(self):
        self.notify(payee_email=None)
        self.notify(items=[])
        self.send.assert_not_called()

    def test_reference_and_labels_are_html_escaped(self):
        self.notify(payment_reference="<ref>", items=[("<request>", 2000)])
        html = self.send.call_args.kwargs["context"]["details_html"]
        self.assertIn("&lt;ref&gt;", html)
        self.assertIn("&lt;request&gt;", html)


if __name__ == "__main__":
    unittest.main()
