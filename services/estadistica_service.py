"""
Servicio para calcular estadísticas del dashboard.

Proporciona estadísticas personalizadas según el rol del usuario.
"""
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, Date

from database.models import UsuarioORM, MascotaORM, CitaORM, VacunaORM, FacturaORM
from models.estadisticas import (
    EstadisticasCliente,
    EstadisticasVeterinario,
    EstadisticasAdmin
)
import logging

logger = logging.getLogger(__name__)


class EstadisticaService:
    """Servicio para calcular estadísticas del dashboard."""
    
    def __init__(self, db: Session):
        """
        Initialize estadistica service.
        
        Args:
            db: SQLAlchemy session
        """
        self.db = db
    
    def get_estadisticas_cliente(self, username: str) -> EstadisticasCliente:
        """
        Obtener estadísticas para un cliente.
        
        Args:
            username: Username del cliente
            
        Returns:
            EstadisticasCliente con conteos personalizados
        """
        # Mascotas propias
        mis_mascotas = self.db.query(MascotaORM).filter(
            MascotaORM.propietario == username,
            MascotaORM.is_deleted == False
        ).count()
        
        # IDs de mascotas propias
        mascota_ids = self.db.query(MascotaORM.id).filter(
            MascotaORM.propietario == username,
            MascotaORM.is_deleted == False
        ).all()
        mascota_ids = [m[0] for m in mascota_ids]
        
        # Citas pendientes
        citas_pendientes = self.db.query(CitaORM).filter(
            CitaORM.id_mascota.in_(mascota_ids),
            CitaORM.estado == "pendiente",
            CitaORM.is_deleted == False
        ).count() if mascota_ids else 0
        
        # Citas completadas
        citas_completadas = self.db.query(CitaORM).filter(
            CitaORM.id_mascota.in_(mascota_ids),
            CitaORM.estado == "completada",
            CitaORM.is_deleted == False
        ).count() if mascota_ids else 0
        
        # Vacunas aplicadas a mis mascotas
        vacunas_aplicadas = self.db.query(VacunaORM).filter(
            VacunaORM.id_mascota.in_(mascota_ids),
            VacunaORM.is_deleted == False
        ).count() if mascota_ids else 0
        
        # Facturas pendientes
        facturas_pendientes = self.db.query(FacturaORM).filter(
            FacturaORM.id_mascota.in_(mascota_ids),
            FacturaORM.estado == "pendiente",
            FacturaORM.is_deleted == False
        ).count() if mascota_ids else 0
        
        # Facturas pagadas
        facturas_pagadas = self.db.query(FacturaORM).filter(
            FacturaORM.id_mascota.in_(mascota_ids),
            FacturaORM.estado == "pagada",
            FacturaORM.is_deleted == False
        ).count() if mascota_ids else 0
        
        return EstadisticasCliente(
            mis_mascotas=mis_mascotas,
            citas_pendientes=citas_pendientes,
            citas_completadas=citas_completadas,
            vacunas_aplicadas=vacunas_aplicadas,
            facturas_pendientes=facturas_pendientes,
            facturas_pagadas=facturas_pagadas
        )
    
    def get_estadisticas_veterinario(self, username: str) -> EstadisticasVeterinario:
        """
        Obtener estadísticas para un veterinario.
        
        Args:
            username: Username del veterinario
            
        Returns:
            EstadisticasVeterinario con conteos personalizados
        """
        # Mascotas propias como propietario
        mis_mascotas = self.db.query(MascotaORM).filter(
            MascotaORM.propietario == username,
            MascotaORM.is_deleted == False
        ).count()
        
        # Citas asignadas a mí (pendientes)
        citas_asignadas = self.db.query(CitaORM).filter(
            CitaORM.veterinario == username,
            CitaORM.estado == "pendiente",
            CitaORM.is_deleted == False
        ).count()
        
        # Citas completadas por mí
        citas_completadas = self.db.query(CitaORM).filter(
            CitaORM.veterinario == username,
            CitaORM.estado == "completada",
            CitaORM.is_deleted == False
        ).count()
        
        # Vacunas aplicadas por mí
        vacunas_aplicadas = self.db.query(VacunaORM).filter(
            VacunaORM.veterinario == username,
            VacunaORM.is_deleted == False
        ).count()
        
        # Facturas emitidas por mí (pendientes)
        facturas_emitidas = self.db.query(FacturaORM).filter(
            FacturaORM.veterinario == username,
            FacturaORM.estado == "pendiente",
            FacturaORM.is_deleted == False
        ).count()
        
        # Facturas cobradas por mí
        facturas_cobradas = self.db.query(FacturaORM).filter(
            FacturaORM.veterinario == username,
            FacturaORM.estado == "pagada",
            FacturaORM.is_deleted == False
        ).count()
        
        return EstadisticasVeterinario(
            mis_mascotas=mis_mascotas,
            citas_asignadas=citas_asignadas,
            citas_completadas=citas_completadas,
            vacunas_aplicadas=vacunas_aplicadas,
            facturas_emitidas=facturas_emitidas,
            facturas_cobradas=facturas_cobradas
        )
    
    def get_estadisticas_admin(self) -> EstadisticasAdmin:
        """
        Obtener estadísticas globales para administrador.
        
        Returns:
            EstadisticasAdmin con conteos globales
        """
        # Total de mascotas
        total_mascotas = self.db.query(MascotaORM).filter(
            MascotaORM.is_deleted == False
        ).count()
        
        # Total de usuarios
        total_usuarios = self.db.query(UsuarioORM).filter(
            UsuarioORM.is_deleted == False
        ).count()
        
        # Citas pendientes
        citas_pendientes = self.db.query(CitaORM).filter(
            CitaORM.estado == "pendiente",
            CitaORM.is_deleted == False
        ).count()
        
        # Citas para hoy
        hoy = date.today()
        citas_hoy = self.db.query(CitaORM).filter(
            func.cast(CitaORM.fecha, Date) == hoy,
            CitaORM.is_deleted == False
        ).count()
        
        # Vacunas del mes actual
        inicio_mes = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        fin_mes = (inicio_mes + relativedelta(months=1))
        
        vacunas_mes = self.db.query(VacunaORM).filter(
            and_(
                VacunaORM.fecha_aplicacion >= inicio_mes.date(),
                VacunaORM.fecha_aplicacion < fin_mes.date()
            ),
            VacunaORM.is_deleted == False
        ).count()
        
        # Facturas pendientes
        facturas_pendientes = self.db.query(FacturaORM).filter(
            FacturaORM.estado == "pendiente",
            FacturaORM.is_deleted == False
        ).count()
        
        # Ingresos del mes (facturas pagadas)
        ingresos_mes_result = self.db.query(
            func.sum(FacturaORM.total)
        ).filter(
            and_(
                FacturaORM.fecha_factura >= inicio_mes,
                FacturaORM.fecha_factura < fin_mes
            ),
            FacturaORM.estado == "pagada",
            FacturaORM.is_deleted == False
        ).scalar()
        
        ingresos_mes = float(ingresos_mes_result) if ingresos_mes_result else 0.0
        
        return EstadisticasAdmin(
            total_mascotas=total_mascotas,
            total_usuarios=total_usuarios,
            citas_pendientes=citas_pendientes,
            citas_hoy=citas_hoy,
            vacunas_mes=vacunas_mes,
            facturas_pendientes=facturas_pendientes,
            ingresos_mes=ingresos_mes
        )
    
    def get_estadisticas(self, current_user: UsuarioORM):
        """
        Obtener estadísticas según el rol del usuario.
        
        Args:
            current_user: Usuario autenticado
            
        Returns:
            Estadísticas apropiadas según el rol
        """
        if current_user.role == "admin":
            return self.get_estadisticas_admin()
        elif current_user.role == "veterinario":
            return self.get_estadisticas_veterinario(current_user.username)
        else:  # cliente
            return self.get_estadisticas_cliente(current_user.username)
