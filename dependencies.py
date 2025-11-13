"""
Dependency injection for services and repositories.

This module provides FastAPI dependencies for injecting services
and repositories into route handlers.
"""

from typing import Generator, Optional
from sqlalchemy.orm import Session
from fastapi import Depends

from database.db import get_db
from repositories.mascota_repository import MascotaRepository
from repositories.usuario_repository import UsuarioRepository
from repositories.cita_repository import CitaRepository
from repositories.vacuna_repository import VacunaRepository
from repositories.factura_repository import FacturaRepository
from repositories.receta_repository import RecetaRepository
from services.mascota_service import MascotaService
from services.usuario_service import UsuarioService
from services.cita_service import CitaService
from services.vacuna_service import VacunaService
from services.factura_service import FacturaService
from services.receta_service import RecetaService
from services.estadistica_service import EstadisticaService


# ==================== Repository Dependencies ====================

def get_mascota_repository(db: Session = None) -> MascotaRepository:
    """
    Get MascotaRepository instance.
    
    Args:
        db: Database session (injected by FastAPI)
        
    Returns:
        MascotaRepository instance
    """
    if db is None:
        from database.db import SessionLocal
        db = SessionLocal()
    return MascotaRepository(db)


def get_usuario_repository(db: Session = None) -> UsuarioRepository:
    """
    Get UsuarioRepository instance.
    
    Args:
        db: Database session (injected by FastAPI)
        
    Returns:
        UsuarioRepository instance
    """
    if db is None:
        from database.db import SessionLocal
        db = SessionLocal()
    return UsuarioRepository(db)


def get_cita_repository(db: Session = None) -> CitaRepository:
    """
    Get CitaRepository instance.
    
    Args:
        db: Database session (injected by FastAPI)
        
    Returns:
        CitaRepository instance
    """
    if db is None:
        from database.db import SessionLocal
        db = SessionLocal()
    return CitaRepository(db)


def get_vacuna_repository(db: Session = None) -> VacunaRepository:
    """
    Get VacunaRepository instance.
    
    Args:
        db: Database session (injected by FastAPI)
        
    Returns:
        VacunaRepository instance
    """
    if db is None:
        from database.db import SessionLocal
        db = SessionLocal()
    return VacunaRepository(db)


def get_factura_repository(db: Session = None) -> FacturaRepository:
    """
    Get FacturaRepository instance.
    
    Args:
        db: Database session (injected by FastAPI)
        
    Returns:
        FacturaRepository instance
    """
    if db is None:
        from database.db import SessionLocal
        db = SessionLocal()
    return FacturaRepository(db)


def get_receta_repository(db: Session = None) -> RecetaRepository:
    """
    Get RecetaRepository instance.
    
    Args:
        db: Database session (injected by FastAPI)
        
    Returns:
        RecetaRepository instance
    """
    if db is None:
        from database.db import SessionLocal
        db = SessionLocal()
    return RecetaRepository(db)


# ==================== Service Dependencies ====================

def get_mascota_service(db: Session = None) -> MascotaService:
    """
    Get MascotaService instance.
    
    This is the main dependency to use in route handlers for mascota operations.
    
    Args:
        db: Database session (injected by FastAPI)
        
    Returns:
        MascotaService instance with injected repository
        
    Example:
        ```python
        @router.get("/mascotas")
        def get_mascotas(
            service: MascotaService = Depends(get_mascota_service)
        ):
            return service.get_mascotas(...)
        ```
    """
    repository = get_mascota_repository(db)
    return MascotaService(repository)


def get_usuario_service(db: Session = None) -> UsuarioService:
    """
    Get UsuarioService instance.
    
    This is the main dependency to use in route handlers for usuario operations.
    
    Args:
        db: Database session (injected by FastAPI)
        
    Returns:
        UsuarioService instance with injected repository
        
    Example:
        ```python
        @router.get("/usuarios")
        def get_usuarios(
            service: UsuarioService = Depends(get_usuario_service)
        ):
            return service.get_usuarios(...)
        ```
    """
    repository = get_usuario_repository(db)
    return UsuarioService(repository)


def get_cita_service(db: Session = None) -> CitaService:
    """
    Get CitaService instance.
    
    This is the main dependency to use in route handlers for cita operations.
    
    Args:
        db: Database session (injected by FastAPI)
        
    Returns:
        CitaService instance with injected repositories
    """
    cita_repo = get_cita_repository(db)
    mascota_repo = get_mascota_repository(db)
    usuario_repo = get_usuario_repository(db)
    return CitaService(cita_repo, mascota_repo, usuario_repo)


def get_vacuna_service(db: Session = None) -> VacunaService:
    """
    Get VacunaService instance.
    
    This is the main dependency to use in route handlers for vacuna operations.
    
    Args:
        db: Database session (injected by FastAPI)
        
    Returns:
        VacunaService instance with injected repositories
    """
    vacuna_repo = get_vacuna_repository(db)
    mascota_repo = get_mascota_repository(db)
    usuario_repo = get_usuario_repository(db)
    return VacunaService(vacuna_repo, mascota_repo, usuario_repo)


def get_factura_service(db: Session = None) -> FacturaService:
    """
    Get FacturaService instance.
    
    This is the main dependency to use in route handlers for factura operations.
    
    Args:
        db: Database session (injected by FastAPI)
        
    Returns:
        FacturaService instance with injected repositories
    """
    factura_repo = get_factura_repository(db)
    cita_repo = get_cita_repository(db)
    mascota_repo = get_mascota_repository(db)
    usuario_repo = get_usuario_repository(db)
    return FacturaService(factura_repo, cita_repo, mascota_repo, usuario_repo)


def get_receta_service(db: Session = None) -> RecetaService:
    """
    Get RecetaService instance.
    
    This is the main dependency to use in route handlers for receta operations.
    
    Args:
        db: Database session (injected by FastAPI)
        
    Returns:
        RecetaService instance with injected repositories
    """
    receta_repo = get_receta_repository(db)
    cita_repo = get_cita_repository(db)
    mascota_repo = get_mascota_repository(db)
    usuario_repo = get_usuario_repository(db)
    return RecetaService(receta_repo, cita_repo, mascota_repo, usuario_repo)


def get_estadistica_service(db: Session = Depends(get_db)) -> EstadisticaService:
    """
    Get EstadisticaService instance.
    
    This is the main dependency to use in route handlers for estadistica operations.
    
    Args:
        db: Database session (injected by FastAPI)
        
    Returns:
        EstadisticaService instance with database session
    """
    return EstadisticaService(db)


# ==================== Context Manager for Services ====================

class ServiceContext:
    """
    Context manager for service layer with automatic transaction management.
    
    Usage:
        ```python
        with ServiceContext() as ctx:
            mascota = ctx.mascota_service.create_mascota(...)
            # Automatically commits on success
        # Automatically rollbacks on exception
        ```
    """
    
    def __init__(self):
        """Initialize the service context."""
        from database.db import SessionLocal
        self.db: Session = SessionLocal()
        
        # Initialize repositories
        self._mascota_repo: Optional[MascotaRepository] = None
        self._usuario_repo: Optional[UsuarioRepository] = None
        self._cita_repo: Optional[CitaRepository] = None
        self._vacuna_repo: Optional[VacunaRepository] = None
        self._factura_repo: Optional[FacturaRepository] = None
        self._receta_repo: Optional[RecetaRepository] = None
        
        # Initialize services
        self._mascota_service: Optional[MascotaService] = None
        self._usuario_service: Optional[UsuarioService] = None
        self._cita_service: Optional[CitaService] = None
        self._vacuna_service: Optional[VacunaService] = None
        self._factura_service: Optional[FacturaService] = None
        self._receta_service: Optional[RecetaService] = None
    
    def __enter__(self):
        """Enter the context."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context and cleanup."""
        if exc_type is not None:
            # Exception occurred, rollback
            self.db.rollback()
        else:
            # Success, commit
            self.db.commit()
        
        # Always close the session
        self.db.close()
    
    @property
    def mascota_service(self) -> MascotaService:
        """Get or create MascotaService instance."""
        if self._mascota_service is None:
            if self._mascota_repo is None:
                self._mascota_repo = MascotaRepository(self.db)
            self._mascota_service = MascotaService(self._mascota_repo)
        return self._mascota_service
    
    @property
    def usuario_service(self) -> UsuarioService:
        """Get or create UsuarioService instance."""
        if self._usuario_service is None:
            if self._usuario_repo is None:
                self._usuario_repo = UsuarioRepository(self.db)
            self._usuario_service = UsuarioService(self._usuario_repo)
        return self._usuario_service
    
    @property
    def cita_service(self) -> CitaService:
        """Get or create CitaService instance."""
        if self._cita_service is None:
            if self._cita_repo is None:
                self._cita_repo = CitaRepository(self.db)
            if self._mascota_repo is None:
                self._mascota_repo = MascotaRepository(self.db)
            if self._usuario_repo is None:
                self._usuario_repo = UsuarioRepository(self.db)
            self._cita_service = CitaService(self._cita_repo, self._mascota_repo, self._usuario_repo)
        return self._cita_service
    
    @property
    def vacuna_service(self) -> VacunaService:
        """Get or create VacunaService instance."""
        if self._vacuna_service is None:
            if self._vacuna_repo is None:
                self._vacuna_repo = VacunaRepository(self.db)
            if self._mascota_repo is None:
                self._mascota_repo = MascotaRepository(self.db)
            if self._usuario_repo is None:
                self._usuario_repo = UsuarioRepository(self.db)
            self._vacuna_service = VacunaService(self._vacuna_repo, self._mascota_repo, self._usuario_repo)
        return self._vacuna_service
    
    @property
    def factura_service(self) -> FacturaService:
        """Get or create FacturaService instance."""
        if self._factura_service is None:
            if self._factura_repo is None:
                self._factura_repo = FacturaRepository(self.db)
            if self._cita_repo is None:
                self._cita_repo = CitaRepository(self.db)
            if self._mascota_repo is None:
                self._mascota_repo = MascotaRepository(self.db)
            if self._usuario_repo is None:
                self._usuario_repo = UsuarioRepository(self.db)
            self._factura_service = FacturaService(self._factura_repo, self._cita_repo, self._mascota_repo, self._usuario_repo)
        return self._factura_service
    
    @property
    def receta_service(self) -> RecetaService:
        """Get or create RecetaService instance."""
        if self._receta_service is None:
            if self._receta_repo is None:
                self._receta_repo = RecetaRepository(self.db)
            if self._cita_repo is None:
                self._cita_repo = CitaRepository(self.db)
            if self._mascota_repo is None:
                self._mascota_repo = MascotaRepository(self.db)
            if self._usuario_repo is None:
                self._usuario_repo = UsuarioRepository(self.db)
            self._receta_service = RecetaService(self._receta_repo, self._cita_repo, self._mascota_repo, self._usuario_repo)
        return self._receta_service
    
    def commit(self):
        """Manually commit the transaction."""
        self.db.commit()
    
    def rollback(self):
        """Manually rollback the transaction."""
        self.db.rollback()
