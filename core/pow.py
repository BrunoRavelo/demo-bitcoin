"""
Proof of Work (PoW) - Minado
Encuentra un nonce que haga que el hash del bloque cumpla con la difficulty

En Bitcoin:
- Difficulty ajustable (cada 2016 bloques ~2 semanas)
- Objetivo: 1 bloque cada ~10 minutos
- Actualmente: ~19 ceros al inicio del hash
"""

import hashlib
import json
import time


class ProofOfWork:
    """
    Sistema de Proof of Work
    
    Objetivo: Encontrar un nonce tal que:
    SHA256(SHA256(block_header)) empiece con X ceros
    
    Difficulty 3 = "000..." (~4,000 intentos, ~0.5s)
    Difficulty 4 = "0000..." (~65,000 intentos, ~5s)
    Difficulty 5 = "00000..." (~1,000,000 intentos, ~60s)
    """
    
    def __init__(self, block_header, difficulty: int = 4):
        """
        Inicializa PoW solver
        
        Args:
            block_header: Objeto BlockHeader a minar
            difficulty: Número de ceros requeridos al inicio del hash
        """
        self.header = block_header
        self.difficulty = difficulty
        self.target = '0' * difficulty  # Ejemplo: "0000" para difficulty 4
    
    def mine(self) -> int:
        """
        Encuentra nonce que satisface la difficulty
        
        Proceso:
        1. Probar nonce = 0, 1, 2, 3, ...
        2. Para cada nonce: calcular hash del header
        3. Si hash empieza con 'target' ceros → ¡encontrado!
        4. Si no → incrementar nonce y repetir
        
        Returns:
            Nonce que hace válido el bloque
        """
        nonce = 0
        start_time = time.time()
        
        print(f"[MINING] Iniciando minado (difficulty={self.difficulty})...")
        
        while True:
            # Actualizar nonce en el header
            self.header.nonce = nonce
            
            # Calcular hash del header
            block_hash = self.header.hash()
            
            # Verificar si cumple difficulty
            if block_hash.startswith(self.target):
                elapsed = time.time() - start_time
                print(f"[MINED] ¡Bloque minado!")
                print(f"        Nonce: {nonce}")
                print(f"        Hash: {block_hash}")
                print(f"        Tiempo: {elapsed:.2f}s")
                print(f"        Intentos: {nonce + 1:,}")
                return nonce
            
            nonce += 1
            
            # Logging cada 10,000 intentos (feedback visual)
            if nonce > 0 and nonce % 10000 == 0:
                elapsed = time.time() - start_time
                rate = nonce / elapsed if elapsed > 0 else 0
                print(f"[MINING] Intentos: {nonce:,} ({rate:,.0f} hashes/s)")
    
    def validate(self, nonce: int) -> bool:
        """
        Valida que un nonce es correcto
        
        Usado para verificar bloques recibidos de otros nodos
        
        Args:
            nonce: Nonce a validar
        
        Returns:
            True si el nonce hace que el hash cumpla difficulty
        """
        self.header.nonce = nonce
        block_hash = self.header.hash()
        
        return block_hash.startswith(self.target)
    
    def __repr__(self):
        return f"ProofOfWork(difficulty={self.difficulty}, target={self.target})"