from pathlib import Path
import platform
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".." / ".env",
        extra="ignore",
    )

    database_backend: str = "mysql"
    sqlserver_database_url: str = "Server=DESKTOP-N7O68K8\\MYSQL,1433;Database=indcool;User Id=api_user;Password=test123;Encrypt=no;TrustServerCertificate=yes;Driver=ODBC Driver 17 for SQL Server;"
    mysql_database_url: str = "mysql+mysqlconnector://root:Sandhya%231981@host.docker.internal:3306/indcool"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    upload_dir: str = "/app/uploads"
    cors_origins: str = "http://localhost:5173"
    app_public_url: str = ""
    partner_agreement_otp_channel: str = "email"

    email_enabled: bool = False
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_from_name: str = "Indcool"
    smtp_use_tls: bool = True
    smtp_use_auth: bool = True

    whatsapp_enabled: bool = False
    wa_phone_number_id: str = ""
    wa_access_token: str = ""
    wa_verify_token: str = ""
    wa_template_name: str = "otp_verification"
    wa_template_language: str = "en_US"

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
