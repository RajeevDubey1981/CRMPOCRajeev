from pathlib import Path
import platform
from urllib.parse import quote_plus

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".." / ".env",
        extra="ignore",
    )

    database_backend: str = "mysql"
    sqlserver_database_url: str = "Server=localhost\\MYSQL,1433;Database=indcool;User Id=api_user;Password=change-me;Encrypt=no;TrustServerCertificate=yes;Driver=ODBC Driver 17 for SQL Server;"
    mysql_database_url: str = "mysql+mysqlconnector://root:change-me@host.docker.internal:3306/indcool"
    # Sales module: its own database, linked to the CRM only by reference numbers. Empty = Sales is switched off
    # and the CRM works exactly as before.
    sales_database_url: str = ""
    marketing_database_url: str = ""
    # Spare parts, misc/on-demand/whole-unit approvals: its own database. Empty = Parts is switched off.
    parts_database_url: str = ""
    # Key that locks the platform tokens (Meta ...) kept in the Marketing database. If empty, JWT_SECRET is used.
    marketing_secret_key: str = ""
    # Meta (Facebook, Instagram, ads): the app is made at developers.facebook.com; its id and secret live only in the server .env
    meta_app_id: str = ""
    meta_app_secret: str = ""
    meta_redirect_uri: str = "https://indcoolapplainces.com/api/marketing/meta/callback"
    meta_graph_version: str = "v23.0"
    sales_sync_enabled: bool = True
    sales_sync_seconds: int = 60
    # Key that locks the keys and passwords of the Sales connections (IndiaMART, Meta ...). If empty, JWT_SECRET is used.
    sales_secret_key: str = ""
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    # /docs, /redoc and /openapi.json hand out a complete, unauthenticated map of every route, param and
    # model in the API. Handy in dev, free recon for an attacker in prod -- set API_DOCS_ENABLED=false on
    # the live server (security review, 2026-10-27).
    api_docs_enabled: bool = True
    upload_dir: str = "/app/uploads"
    cors_origins: str = "http://localhost:5173"
    app_public_url: str = ""
    partner_agreement_otp_channel: str = "email"
    payment_approval_steps: int = 3

    email_enabled: bool = False
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_from_name: str = "Indcool"
    smtp_use_tls: bool = True
    smtp_use_auth: bool = True
    # Bounce detection: reads delivery-failure reports from the sending mailbox (read only)
    bounce_check_enabled: bool = True
    imap_host: str = "imap.gmail.com"
    imap_port: int = 993
    bounce_poll_seconds: int = 120
    bounce_lookback_days: int = 3

    # Bid management
    bid_confirm_days: int = 1  # (old rule, kept for bids allocated before the hours rule) days to confirm
    bid_confirm_hours: int = 48  # a vendor must accept or reject within this many hours of allocation
    bid_submit_buffer_days: int = 1  # and submit this many days before the bid end date
    bid_reminders_enabled: bool = True
    bid_reminder_hour_ist: int = 9
    bid_team_email: str = ""  # comma separated; empty means every user ticked as bid manager

    whatsapp_enabled: bool = False
    wa_phone_number_id: str = ""
    wa_access_token: str = ""
    wa_verify_token: str = ""
    wa_template_name: str = "otp_verification"
    wa_template_language: str = "en_US"
    wa_happy_code_template: str = "service_happy_code_otp"
    wa_happy_code_language: str = "en_US"

    # SMS India Hub (SMS needs a DLT-approved template; keep off until the account and DLT ids are set in .env)
    sms_enabled: bool = False
    sms_api_url: str = "https://cloud.smsindiahub.in/api/mt/SendSMS"
    sms_user: str = ""
    sms_password: str = ""
    sms_sender_id: str = ""
    sms_channel: str = "Trans"
    sms_route: str = ""
    sms_pe_id: str = ""
    sms_happy_code_template_id: str = ""
    sms_happy_code_text: str = (
        "Dear {name}, your INDcool service request {service} has an engineer assigned. "
        "Your Happy Code is {code}. Please give it to our engineer on completion of your service request. "
        "-TEAM INDcool"
    )

    seed_admin_email: str = "admin@indcool.com"
    seed_admin_password: str = "admin123"
    seed_admin_name: str = "Administrator"

    # GST Suvidha Provider (sandbox.co.in or similar). Always on by default.
    gst_lookup_enabled: bool = True
    gst_provider_url: str = "https://api.sandbox.co.in/gst/compliance/public/gstin/search"
    gst_provider_api_key: str = ""
    gst_provider_api_secret: str = ""
    gst_provider_authorization: str = ""

    def _resolve_sqlserver_url(self) -> str:
        raw = (self.sqlserver_database_url or "").strip()
        if raw.startswith("Server=") or raw.startswith("server="):
            parts: dict[str, str] = {}
            for segment in raw.split(";"):
                if "=" in segment:
                    key, value = segment.split("=", 1)
                    parts[key.strip().lower()] = value.strip()

            server = parts.get("server", "localhost")
            database = parts.get("database", "master")
            user_id = parts.get("user id") or parts.get("uid") or ""
            password = parts.get("password") or parts.get("pwd") or ""
            driver = parts.get("driver", "ODBC Driver 17 for SQL Server")
            # The Docker image installs Microsoft's Linux ODBC 18 package.
            # If an older SQL Server connection string still asks for Driver 17,
            # normalize it so containerized deployments start successfully.
            if platform.system() != "Windows" and driver.strip().lower() == "odbc driver 17 for sql server":
                driver = "ODBC Driver 18 for SQL Server"
            encrypt = parts.get("encrypt", "no")
            trust_server_certificate = parts.get("trustservercertificate", "yes")
            if trust_server_certificate.lower() in {"true", "1", "yes", "y", "on"}:
                trust_server_certificate = "yes"
            else:
                trust_server_certificate = "no"

            odbc_connection_string = (
                f"Driver={{{driver}}};"
                f"Server={server};"
                f"Database={database};"
                f"UID={user_id};"
                f"PWD={password};"
                f"Encrypt={encrypt};"
                f"TrustServerCertificate={trust_server_certificate};"
            )

            return f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc_connection_string)}"

        return raw

    def get_database_url(self) -> str:
        backend = (self.database_backend or "mysql").strip().lower()
        if backend == "sqlserver":
            return self._resolve_sqlserver_url()
        if backend == "mysql":
            database_url = (self.mysql_database_url or "").strip()
            if platform.system() == "Windows":
                database_url = database_url.replace("@host.docker.internal:", "@127.0.0.1:")
            return database_url
        raise ValueError(f"Unsupported database_backend '{self.database_backend}'. Use 'mysql' or 'sqlserver'.")

    @field_validator("marketing_database_url")
    @classmethod
    def _marketing_driver(cls, value: str) -> str:
        """The CRM uses the mysql-connector driver. A Marketing URL written for pymysql is read as the same database."""
        return value.replace("mysql+pymysql://", "mysql+mysqlconnector://", 1) if isinstance(value, str) else value

    @field_validator("parts_database_url")
    @classmethod
    def _parts_driver(cls, value: str) -> str:
        """The CRM uses the mysql-connector driver. A Parts URL written for pymysql is read as the same database."""
        return value.replace("mysql+pymysql://", "mysql+mysqlconnector://", 1) if isinstance(value, str) else value

    @property
    def resolved_upload_dir(self) -> Path:
        raw = (self.upload_dir or "").strip()
        if raw:
            if platform.system() == "Windows" and raw.startswith("/app/"):
                return (Path(__file__).resolve().parents[1] / raw.removeprefix("/app/")).resolve()
            candidate = Path(raw)
            if candidate.is_absolute():
                return candidate
            return (Path(__file__).resolve().parents[1] / candidate).resolve()
        return Path(__file__).resolve().parents[1] / "uploads"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def normalized_partner_agreement_otp_channel(self) -> str:
        channel = (self.partner_agreement_otp_channel or "email").strip().lower()
        return channel if channel in {"email", "whatsapp"} else "email"


settings = Settings()
