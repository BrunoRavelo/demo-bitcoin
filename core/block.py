"""
Bloque de la blockchain
Contiene header (metadatos) y transacciones
"""

import hashlib
import json
import time
from typing import List, Optional
from core.merkle import MerkleTree


class BlockHeader:
    """
    Header del bloque (metadatos)
    
    En Bitcoin:
    - Header = 80 bytes fijos
    - Se usa para PoW (minar)
    - Hash del header = identificador del bloque
    
    Campos:
    - prev_hash: Hash del bloque anterior (enlace)
    - merkle_root: Raíz del árbol Merkle de transacciones
    - timestamp: Cuándo se creó el bloque
    - nonce: Número encontrado por PoW
    - difficulty: Cuántos ceros requiere el hash
    """
    
    def __init__(self, prev_hash: str, merkle_root: str, 
                 timestamp: float, difficulty: int = 4, nonce: int = 0):
        """
        Crea un header de bloque
        
        Args:
            prev_hash: Hash del bloque anterior (64 caracteres hex)
            merkle_root: Raíz del Merkle tree (64 caracteres hex)
            timestamp: Unix timestamp
            difficulty: Número de ceros requeridos en hash
            nonce: Número para PoW (se encuentra al minar)
        """
        self.prev_hash = prev_hash
        self.merkle_root = merkle_root
        self.timestamp = timestamp
        self.difficulty = difficulty
        self.nonce = nonce
    
    def to_dict(self) -> dict:
        """
        Serializa header a diccionario
        
        Returns:
            Diccionario con todos los campos
        """
        return {
            'prev_hash': self.prev_hash,
            'merkle_root': self.merkle_root,
            'timestamp': self.timestamp,
            'difficulty': self.difficulty,
            'nonce': self.nonce
        }
    
    def hash(self) -> str:
        """
        Calcula hash del header (identifica el bloque)
        
        Proceso (como Bitcoin):
        1. Serializar header a JSON
        2. SHA256(data)
        3. SHA256(resultado) → double SHA256
        
        Returns:
            Hash SHA256 en hexadecimal (64 caracteres)
        """
        # Serializar de forma determinística
        header_str = json.dumps(self.to_dict(), sort_keys=True)
        
        # Double SHA256 (como Bitcoin)
        hash1 = hashlib.sha256(header_str.encode()).digest()
        hash2 = hashlib.sha256(hash1).hexdigest()
        
        return hash2
    
    @staticmethod
    def from_dict(data: dict) -> 'BlockHeader':
        """
        Deserializa header desde diccionario
        
        Args:
            data: Diccionario con campos del header
        
        Returns:
            Instancia de BlockHeader
        """
        return BlockHeader(
            prev_hash=data['prev_hash'],
            merkle_root=data['merkle_root'],
            timestamp=data['timestamp'],
            difficulty=data['difficulty'],
            nonce=data['nonce']
        )
    
    def __repr__(self):
        return f"BlockHeader(hash={self.hash()[:16]}..., nonce={self.nonce})"


class Block:
    """
    Bloque completo: header + transacciones
    
    Un bloque es válido si:
    1. PoW válido (hash cumple difficulty)
    2. Merkle root correcto
    3. Todas las transacciones válidas
    4. prev_hash conecta con bloque anterior
    """
    
    def __init__(self, header: BlockHeader, transactions: List):
        """
        Crea un bloque
        
        Args:
            header: BlockHeader con metadatos
            transactions: Lista de objetos Transaction
        """
        self.header = header
        self.transactions = transactions
    
    @property
    def hash(self) -> str:
        """
        Hash único del bloque (hash del header)
        
        Returns:
            Hash SHA256 en hexadecimal
        """
        return self.header.hash()
    
    def validate_merkle_root(self) -> bool:
        """
        Verifica que merkle_root coincida con las transacciones
        
        Recalcula Merkle tree y compara root
        
        Returns:
            True si el Merkle root es correcto
        """
        # Recalcular Merkle root
        merkle = MerkleTree(self.transactions)
        calculated_root = merkle.get_root()
        
        # Comparar con el que está en el header
        return calculated_root == self.header.merkle_root
    
    def validate_pow(self) -> bool:
        """
        Verifica que el hash del bloque cumpla difficulty
        
        Returns:
            True si el hash tiene suficientes ceros al inicio
        """
        target = '0' * self.header.difficulty
        return self.hash.startswith(target)
    
    def validate_transactions(self) -> bool:
        """
        Verifica que todas las transacciones sean válidas
        
        Valida firmas digitales de cada TX
        
        Returns:
            True si todas las TXs son válidas
        """
        for tx in self.transactions:
            if not tx.is_valid():
                return False
        return True
    
    def to_dict(self) -> dict:
        """
        Serializa bloque completo a diccionario
        
        Returns:
            Diccionario con header y transacciones
        """
        return {
            'header': self.header.to_dict(),
            'transactions': [tx.to_dict() for tx in self.transactions]
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'Block':
        """
        Deserializa bloque desde diccionario
        
        Args:
            data: Diccionario con header y transacciones
        
        Returns:
            Instancia de Block
        """
        from core.transaction import Transaction
        
        # Reconstruir header
        header = BlockHeader.from_dict(data['header'])
        
        # Reconstruir transacciones
        transactions = [
            Transaction.from_dict(tx_data) 
            for tx_data in data['transactions']
        ]
        
        return Block(header, transactions)
    
    def __repr__(self):
        return f"Block(hash={self.hash[:16]}..., txs={len(self.transactions)})"