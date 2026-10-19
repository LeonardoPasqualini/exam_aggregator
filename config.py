from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", # relative from your app is runnig
        env_file_encoding="utf-8",
    )
    # set in the .env
    database_url: str
    
    secret_key: SecretStr
    algorithm: str = "HS256" # standard for JWT
    access_token_expire_minutes: int = 30
    reset_token_expire_minutes: int = 60

    max_upload_size_bytes: int = 5 * 1024 * 1024 # 5MB
    
    # S3 config
    s3_bucket_name: str
    s3_region: str = "us-east-1"
    s3_access_key_id: SecretStr | None = None
    s3_secret_access_key: SecretStr | None = None
    s3_endpoint_url: str | None = None
    
    # Pagination
    exams_per_page: int = 10
    
    # Mailer config
    mail_server: str = "localhost"
    # smtp defaut port for tls
    mail_port: int = 587 
    # authentication with smtp server
    mail_username: str = ""
    mail_password: SecretStr = SecretStr("")
    # sender addrs
    mail_form: str = "noreply@exemple.com"
    #tells aiostmplib it's encripted
    mail_use_tls: bool = True
    
    frontend_url: str = "http://localhost:8000"
    
settings = Settings() # Loadade from .env file