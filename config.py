"""
Configuración centralizada de la aplicación usando pydantic-settings.

Este módulo maneja todas las variables de entorno y configuraciones
de la aplicación de manera tipada y validada.
"""
import secrets
import logging
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Configuración de la aplicación cargada desde variables de entorno."""
    
    # Database
    database_url: str = Field(
        default="mssql+pyodbc:///?odbc_connect=DRIVER%3D%7BODBC+Driver+17+for+SQL+Server%7D%3BSERVER%3DSANTIAGO%5CSQLEXPRESS%3BDATABASE%3DAPIVeterinaria%3BTrusted_Connection%3Dyes%3B",
        description="URL de conexión a la base de datos"
    )
    
    # JWT Configuration
    jwt_secret_key: str = Field(
        default="",
        description="Clave secreta para firmar tokens JWT (OBLIGATORIO en producción)"
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="Algoritmo para firmar JWT"
    )
    jwt_access_minutes: int = Field(
        default=30,
        ge=1,
        le=1440,
        description="Tiempo de expiración del token en minutos"
    )
    jwt_issuer: str = Field(
        default="APIVeterinaria",
        description="Emisor del token JWT"
    )
    jwt_audience: str = Field(
        default="APIVeterinariaClient",
        description="Audiencia del token JWT"
    )
    
    # CORS Configuration
    cors_allowed_origins: str = Field(
        default="http://localhost,http://localhost:3000,http://localhost:5000,http://localhost:5059,http://localhost:8000",
        description="Orígenes permitidos para CORS, separados por coma"
    )
    
    # Application
    app_name: str = Field(
        default="API Veterinaria",
        description="Nombre de la aplicación"
    )
    app_version: str = Field(
        default="1.0.0",
        description="Versión de la aplicación"
    )
    debug_mode: bool = Field(
        default=False,
        description="Modo debug (solo para desarrollo)"
    )
    
    # Paginación
    default_page_size: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Tamaño de página por defecto para listados"
    )
    max_page_size: int = Field(
        default=500,
        ge=1,
        le=500,
        description="Tamaño máximo de página permitido"
    )
    
    # Logging
    log_level: str = Field(
        default="INFO",
        description="Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    
    # Timezone
    timezone: str = Field(
        default="America/Bogota",
        description="Zona horaria de la aplicación (formato IANA)"
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret_key(cls, v: str) -> str:
        """Valida y genera JWT_SECRET_KEY si no existe."""
        if not v or len(v) < 32:
            # Generar una clave automáticamente para desarrollo
            generated_key = secrets.token_urlsafe(48)
            logger.warning(
                "⚠️  JWT_SECRET_KEY no configurado o muy corto. "
                "Se generó una clave temporal para desarrollo.\n"
                "⚠️  IMPORTANTE: En producción, configura JWT_SECRET_KEY en .env\n"
                f"   Puedes usar esta: {generated_key}"
            )
            return generated_key
        return v
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Valida que el nivel de logging sea válido."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            logger.warning(
                f"Nivel de log '{v}' no válido. Usando 'INFO'. "
                f"Niveles válidos: {valid_levels}"
            )
            return "INFO"
        return v_upper
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Devuelve la lista de orígenes CORS permitidos."""
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]
    
    @property
    def is_production(self) -> bool:
        """Determina si la app está en modo producción."""
        return not self.debug_mode


# Instancia global de configuración
settings = Settings()


def configure_logging():
    """Configura el sistema de logging de la aplicación."""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format=log_format,
        handlers=[
            logging.StreamHandler(),
        ]
    )
    
    # Reducir verbosidad de librerías externas
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    logger.info(f"🚀 Logging configurado en nivel {settings.log_level}")
    logger.info(f"📦 Aplicación: {settings.app_name} v{settings.app_version}")
    logger.info(f"🔧 Modo: {'Desarrollo' if settings.debug_mode else 'Producción'}")


def get_settings() -> Settings:
    """Retorna la instancia de configuración (útil para dependency injection)."""
    return settings
