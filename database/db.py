from typing import List, Optional
from datetime import datetime
from models import (
    Mascota, Cita, Vacuna, Factura,
    EstadoCita, EstadoFactura
)

# Base de datos simulada
mascotas_db: List[Mascota] = []
citas_db: List[Cita] = []
vacunas_db: List[Vacuna] = []
facturas_db: List[Factura] = []

# Contadores para IDs
mascota_id_counter = 1
cita_id_counter = 1
vacuna_id_counter = 1
factura_id_counter = 1

# Funciones auxiliares para encontrar registros
def encontrar_mascota(mascota_id: int) -> Optional[Mascota]:
    """Encuentra una mascota por su ID"""
    for mascota in mascotas_db:
        if mascota.id == mascota_id:
            return mascota
    return None

def encontrar_cita(cita_id: int) -> Optional[Cita]:
    """Encuentra una cita por su ID"""
    for cita in citas_db:
        if cita.id == cita_id:
            return cita
    return None

def encontrar_vacuna(vacuna_id: int) -> Optional[Vacuna]:
    """Encuentra una vacuna por su ID"""
    for vacuna in vacunas_db:
        if vacuna.id == vacuna_id:
            return vacuna
    return None

def encontrar_factura(factura_id: int) -> Optional[Factura]:
    """Encuentra una factura por su ID"""
    for factura in facturas_db:
        if factura.id == factura_id:
            return factura
    return None

def generar_numero_factura(factura_id: int) -> str:
    """Genera un número de factura con formato FAC-YYYY-NNNN"""
    año_actual = datetime.now().year
    return f"FAC-{año_actual}-{factura_id:04d}"

def calcular_total_factura(valor_servicio: float, iva: float, descuento: float) -> float:
    """Calcula el total de la factura aplicando IVA y descuento"""
    subtotal = valor_servicio - descuento
    total = subtotal + (subtotal * iva / 100)
    return round(total, 2)

def obtener_proximo_id_mascota() -> int:
    """Obtiene el próximo ID disponible para mascotas"""
    global mascota_id_counter
    current_id = mascota_id_counter
    mascota_id_counter += 1
    return current_id

def obtener_proximo_id_cita() -> int:
    """Obtiene el próximo ID disponible para citas"""
    global cita_id_counter
    current_id = cita_id_counter
    cita_id_counter += 1
    return current_id

def obtener_proximo_id_vacuna() -> int:
    """Obtiene el próximo ID disponible para vacunas"""
    global vacuna_id_counter
    current_id = vacuna_id_counter
    vacuna_id_counter += 1
    return current_id

def obtener_proximo_id_factura() -> int:
    """Obtiene el próximo ID disponible para facturas"""
    global factura_id_counter
    current_id = factura_id_counter
    factura_id_counter += 1
    return current_id