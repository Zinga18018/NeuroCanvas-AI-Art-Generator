#!/usr/bin/env python3
"""
NeuroCanvas Configuration Module

Centralized configuration management for the NeuroCanvas application.
Handles environment variables, default settings, and configuration validation.
"""

import os
from typing import List, Dict, Any
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DatabaseConfig:
    """Database configuration settings"""
    host: str
    port: int
    name: str
    user: str
    password: str
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    echo: bool = False

    @property
    def url(self) -> str:
        """Generate database URL"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


@dataclass
class RedisConfig:
    """Redis configuration settings"""
    host: str
    port: int
    db: int
    password: str = None
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    max_connections: int = 50


@dataclass
class AIConfig:
    """AI/ML configuration settings"""
    openai_api_key: str
    openai_model: str = "gpt-4"
    openai_max_tokens: int = 2000
    openai_temperature: float = 0.7
    
    # Emotion analysis settings
    emotion_model_path: str = "cardiffnlp/twitter-roberta-base-emotion"
    emotion_confidence_threshold: float = 0.6
    
    # Art generation settings
    art_model_path: str = "runwayml/stable-diffusion-v1-5"
    art_image_size: tuple = (512, 512)
    art_num_inference_steps: int = 50
    art_guidance_scale: float = 7.5
    
    # Memory system settings
    memory_vector_dim: int = 768
    memory_similarity_threshold: float = 0.8
    memory_max_entries: int = 10000


@dataclass
class SecurityConfig:
    """Security configuration settings"""
    secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 168  # 7 days
    password_min_length: int = 8
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 30
    
    # CORS settings
    cors_origins: List[str] = None
    cors_methods: List[str] = None
    cors_headers: List[str] = None


@dataclass
class FileUploadConfig:
    """File upload configuration settings"""
    upload_folder: str
    max_file_size: int = 16 * 1024 * 1024  # 16MB
    allowed_image_extensions: set = None
    allowed_audio_extensions: set = None
    allowed_video_extensions: set = None
    
    def __post_init__(self):
        if self.allowed_image_extensions is None:
            self.allowed_image_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        if self.allowed_audio_extensions is None:
            self.allowed_audio_extensions = {'wav', 'mp3', 'ogg', 'm4a'}
        if self.allowed_video_extensions is None:
            self.allowed_video_extensions = {'mp4', 'webm', 'avi', 'mov'}


class Config:
    """Main configuration class"""
    
    # Environment
    ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    TESTING = os.getenv('TESTING', 'False').lower() == 'true'
    
    # Server settings
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))
    
    # Application settings
    APP_NAME = os.getenv('APP_NAME', 'NeuroCanvas')
    APP_VERSION = os.getenv('APP_VERSION', '1.0.0')
    
    # Database configuration
    DATABASE = DatabaseConfig(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', 5432)),
        name=os.getenv('DB_NAME', 'neurocanvas'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'password'),
        pool_size=int(os.getenv('DB_POOL_SIZE', 10)),
        max_overflow=int(os.getenv('DB_MAX_OVERFLOW', 20)),
        echo=os.getenv('DB_ECHO', 'False').lower() == 'true'
    )
    
    # Redis configuration
    REDIS = RedisConfig(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        db=int(os.getenv('REDIS_DB', 0)),
        password=os.getenv('REDIS_PASSWORD')
    )
    
    # Legacy Redis settings for backward compatibility
    REDIS_HOST = REDIS.host
    REDIS_PORT = REDIS.port
    REDIS_DB = REDIS.db
    
    # AI/ML configuration
    AI = AIConfig(
        openai_api_key=os.getenv('OPENAI_API_KEY', ''),
        openai_model=os.getenv('OPENAI_MODEL', 'gpt-4'),
        openai_max_tokens=int(os.getenv('OPENAI_MAX_TOKENS', 2000)),
        openai_temperature=float(os.getenv('OPENAI_TEMPERATURE', 0.7)),
        emotion_model_path=os.getenv('EMOTION_MODEL_PATH', 'cardiffnlp/twitter-roberta-base-emotion'),
        emotion_confidence_threshold=float(os.getenv('EMOTION_CONFIDENCE_THRESHOLD', 0.6)),
        art_model_path=os.getenv('ART_MODEL_PATH', 'runwayml/stable-diffusion-v1-5'),
        art_image_size=tuple(map(int, os.getenv('ART_IMAGE_SIZE', '512,512').split(','))),
        art_num_inference_steps=int(os.getenv('ART_NUM_INFERENCE_STEPS', 50)),
        art_guidance_scale=float(os.getenv('ART_GUIDANCE_SCALE', 7.5)),
        memory_vector_dim=int(os.getenv('MEMORY_VECTOR_DIM', 768)),
        memory_similarity_threshold=float(os.getenv('MEMORY_SIMILARITY_THRESHOLD', 0.8)),
        memory_max_entries=int(os.getenv('MEMORY_MAX_ENTRIES', 10000))
    )
    
    # Security configuration
    SECURITY = SecurityConfig(
        secret_key=os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production'),
        jwt_algorithm=os.getenv('JWT_ALGORITHM', 'HS256'),
        jwt_expiration_hours=int(os.getenv('JWT_EXPIRATION_HOURS', 168)),
        password_min_length=int(os.getenv('PASSWORD_MIN_LENGTH', 8)),
        max_login_attempts=int(os.getenv('MAX_LOGIN_ATTEMPTS', 5)),
        lockout_duration_minutes=int(os.getenv('LOCKOUT_DURATION_MINUTES', 30)),
        cors_origins=os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000').split(','),
        cors_methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
        cors_headers=['Content-Type', 'Authorization']
    )
    
    # Legacy security settings for backward compatibility
    SECRET_KEY = SECURITY.secret_key
    CORS_ORIGINS = SECURITY.cors_origins
    
    # File upload configuration
    FILE_UPLOAD = FileUploadConfig(
        upload_folder=os.getenv('UPLOAD_FOLDER', 'uploads'),
        max_file_size=int(os.getenv('MAX_FILE_SIZE', 16 * 1024 * 1024))
    )
    
    # Legacy file upload settings
    UPLOAD_FOLDER = FILE_UPLOAD.upload_folder
    MAX_CONTENT_LENGTH = FILE_UPLOAD.max_file_size
    
    # Logging configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'neurocanvas.log')
    LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', 10 * 1024 * 1024))  # 10MB
    LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', 5))
    
    # Performance settings
    RATE_LIMIT_STORAGE_URL = os.getenv('RATE_LIMIT_STORAGE_URL', f'redis://{REDIS.host}:{REDIS.port}/{REDIS.db}')
    CACHE_TYPE = os.getenv('CACHE_TYPE', 'redis')
    CACHE_REDIS_URL = os.getenv('CACHE_REDIS_URL', f'redis://{REDIS.host}:{REDIS.port}/{REDIS.db}')
    
    # WebSocket settings
    WEBSOCKET_PING_TIMEOUT = int(os.getenv('WEBSOCKET_PING_TIMEOUT', 60))
    WEBSOCKET_PING_INTERVAL = int(os.getenv('WEBSOCKET_PING_INTERVAL', 25))
    
    # Feature flags
    ENABLE_EMOTION_ANALYSIS = os.getenv('ENABLE_EMOTION_ANALYSIS', 'True').lower() == 'true'
    ENABLE_ART_GENERATION = os.getenv('ENABLE_ART_GENERATION', 'True').lower() == 'true'
    ENABLE_NARRATIVE_GENERATION = os.getenv('ENABLE_NARRATIVE_GENERATION', 'True').lower() == 'true'
    ENABLE_MEMORY_SYSTEM = os.getenv('ENABLE_MEMORY_SYSTEM', 'True').lower() == 'true'
    ENABLE_WEBSOCKETS = os.getenv('ENABLE_WEBSOCKETS', 'True').lower() == 'true'
    
    # External services
    SENTRY_DSN = os.getenv('SENTRY_DSN')
    PROMETHEUS_METRICS = os.getenv('PROMETHEUS_METRICS', 'False').lower() == 'true'
    
    @classmethod
    def validate(cls) -> Dict[str, Any]:
        """Validate configuration and return validation results"""
        errors = []
        warnings = []
        
        # Check required environment variables
        if not cls.AI.openai_api_key:
            errors.append("OPENAI_API_KEY is required")
        
        if cls.SECURITY.secret_key == 'dev-secret-key-change-in-production' and cls.ENV == 'production':
            errors.append("SECRET_KEY must be changed in production")
        
        # Check database connection parameters
        if not all([cls.DATABASE.host, cls.DATABASE.name, cls.DATABASE.user]):
            errors.append("Database configuration is incomplete")
        
        # Check file upload directory
        upload_path = Path(cls.FILE_UPLOAD.upload_folder)
        if not upload_path.exists():
            warnings.append(f"Upload directory {upload_path} does not exist and will be created")
        
        # Check Redis connection (optional)
        if not cls.REDIS.host:
            warnings.append("Redis host not configured, caching will be disabled")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    @classmethod
    def get_database_url(cls) -> str:
        """Get database URL for SQLAlchemy"""
        return cls.DATABASE.url
    
    @classmethod
    def get_redis_url(cls) -> str:
        """Get Redis URL"""
        if cls.REDIS.password:
            return f"redis://:{cls.REDIS.password}@{cls.REDIS.host}:{cls.REDIS.port}/{cls.REDIS.db}"
        return f"redis://{cls.REDIS.host}:{cls.REDIS.port}/{cls.REDIS.db}"
    
    @classmethod
    def is_development(cls) -> bool:
        """Check if running in development mode"""
        return cls.ENV == 'development'
    
    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production mode"""
        return cls.ENV == 'production'
    
    @classmethod
    def is_testing(cls) -> bool:
        """Check if running in testing mode"""
        return cls.TESTING


# Configuration validation on import
if __name__ == '__main__':
    validation_result = Config.validate()
    if not validation_result['valid']:
        print("Configuration validation failed:")
        for error in validation_result['errors']:
            print(f"  ERROR: {error}")
    
    if validation_result['warnings']:
        print("Configuration warnings:")
        for warning in validation_result['warnings']:
            print(f"  WARNING: {warning}")
    
    if validation_result['valid']:
        print("Configuration validation passed!")
