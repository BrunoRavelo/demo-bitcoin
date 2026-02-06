"""
Protocolo de mensajes P2P - VERSIÓN MÍNIMA FASE 1
Define formato básico de mensajes
"""

import json
import hashlib
import uuid
from datetime import datetime


def create_message(msg_type: str, payload: dict) -> dict:
    """
    Crea un mensaje P2P con formato estándar
    
    Args:
        msg_type: Tipo de mensaje (ej. "version", "ping", "hello")
        payload: Datos del mensaje
    
    Returns:
        Diccionario con formato estándar
    """
    # Calcular checksum del payload
    payload_str = json.dumps(payload, sort_keys=True)
    checksum = hashlib.sha256(payload_str.encode()).hexdigest()
    
    return {
        'type': msg_type,
        'id': str(uuid.uuid4()),
        'timestamp': datetime.now().timestamp(),
        'payload': payload,
        'checksum': checksum
    }


def validate_message(msg: dict) -> bool:
    """
    Valida que un mensaje tenga formato correcto y checksum válido
    
    Args:
        msg: Diccionario con el mensaje recibido
    
    Returns:
        True si el mensaje es válido
    """
    # Verificar campos requeridos
    required = ['type', 'id', 'timestamp', 'payload', 'checksum']
    if not all(field in msg for field in required):
        return False
    
    # Verificar checksum
    payload_str = json.dumps(msg['payload'], sort_keys=True)
    calculated_checksum = hashlib.sha256(payload_str.encode()).hexdigest()
    
    return calculated_checksum == msg['checksum']