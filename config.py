from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", # relative from your app is runnig
        env_file_encoding="utf-8",
    )
    
    secret_key: SecretStr
    algorithm: str = "HS256" # standard for JWT
    access_token_expire_minutes: int = 30
    reset_token_expire_minutes: int = 60

    max_upload_size_bytes: int = 5 * 1024 * 1024 # 5MB
    
    exams_per_page: int = 10
    
    mail_server: str = "localhost"
    mail_port: int = 587 # smtp defaut port for tls
    mail_username: str = "" # authentication with smtp server
    mail_password: SecretStr = SecretStr("") # authentication with smtp server
    mail_form: str = "noreply@exemple.com" # sender addrs
    mail_use_tls: bool = True #tells aiostmplib it's encripted
    
    frontend_url: str = "http://localhost:8000"
    
settings = Settings() # Loadade from .env file