"""
utils/logger.py - VERSIÓN MEJORADA PARA TESTING
"""

import logging
import os


def setup_logger(node_id: str, level=logging.INFO):
    """
    Configura logger para un nodo específico
    
    Args:
        node_id: Identificador único del nodo (ej. "Node-a1b2")
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR)
    
    Returns:
        logging.Logger configurado
    """
    # Crear directorio logs si no existe
    os.makedirs('logs', exist_ok=True)
    
    # Nombre de archivo único por nodo (SIN timestamp - se sobrescribe)
    log_filename = f'logs/node_{node_id}.log'
    
    # Crear logger
    logger = logging.getLogger(f'Node-{node_id}')
    logger.setLevel(level)
    
    # Evitar duplicar handlers si ya existe
    if logger.handlers:
        return logger
    
    # Formato de mensajes
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Handler para archivo (mode='w' sobrescribe en vez de append)
    file_handler = logging.FileHandler(log_filename, mode='w')
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    
    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    
    # Agregar handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger