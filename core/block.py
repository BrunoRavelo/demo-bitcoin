"""
Bloque de la blockchain.
Contiene header (metadatos) y transacciones.

Sprint 9.2: difficulty ajustable.
    - BlockHeader usa `target` (int de 256 bits) en lugar de `difficulty` (int de ceros)
    - validate_pow() compara int(hash, 16) < target (idéntico a Bitcoin)
"""

import hashlib
import json
import time
from typing import List, Optional
from core.merkle import MerkleTree


class BlockHeader:
    """
    Header del bloque (metadatos).

    El campo `target` es un entero de 256 bits.
    Un bloque es válido si int(hash, 16) < target.
    A menor target → más difícil encontrar un hash válido.
    """

    def __init__(
        self,
        prev_hash:   str,
        merkle_root: str,
        timestamp:   float,
        target:      int,
        nonce:       int = 0,
    ):
        self.prev_hash   = prev_hash
        self.merkle_root = merkle_root
        self.timestamp   = timestamp
        self.target      = target
        self.nonce       = nonce

    def to_dict(self) -> dict:
        return {
            'prev_hash':   self.prev_hash,
            'merkle_root': self.merkle_root,
            'timestamp':   self.timestamp,
            'target':      self.target,
            'nonce':       self.nonce,
        }

    def hash(self) -> str:
        """
        Double SHA256 del header serializado (idéntico a Bitcoin).
        El campo `target` no afecta la búsqueda del nonce —
        solo define cuándo un hash es válido.
        """
        header_str = json.dumps(self.to_dict(), sort_keys=True)
        hash1      = hashlib.sha256(header_str.encode()).digest()
        return hashlib.sha256(hash1).hexdigest()

    @staticmethod
    def from_dict(data: dict) -> 'BlockHeader':
        return BlockHeader(
            prev_hash=data['prev_hash'],
            merkle_root=data['merkle_root'],
            timestamp=data['timestamp'],
            target=data['target'],
            nonce=data['nonce'],
        )

    @property
    def difficulty_display(self) -> str:
        """
        Representación legible del target para el dashboard.
        Muestra los primeros 16 caracteres hex del target.
        """
        return hex(self.target)[2:18] + '...'

    def __repr__(self):
        return f"BlockHeader(hash={self.hash()[:16]}..., nonce={self.nonce})"


class Block:
    """
    Bloque completo: header + transacciones.

    Un bloque es válido si:
    1. PoW válido: int(hash, 16) < header.target
    2. Merkle root correcto
    3. Todas las transacciones válidas
    4. prev_hash conecta con bloque anterior
    """

    def __init__(self, header: BlockHeader, transactions: List):
        self.header       = header
        self.transactions = transactions

    @property
    def hash(self) -> str:
        return self.header.hash()

    def validate_merkle_root(self) -> bool:
        merkle           = MerkleTree(self.transactions)
        calculated_root  = merkle.get_root()
        return calculated_root == self.header.merkle_root

    def validate_pow(self) -> bool:
        """
        Verifica PoW estilo Bitcoin:
        int(hash, 16) < target
        """
        return int(self.hash, 16) < self.header.target

    def validate_transactions(self) -> bool:
        for tx in self.transactions:
            if not tx.is_valid():
                return False
        return True

    def to_dict(self) -> dict:
        return {
            'header':       self.header.to_dict(),
            'transactions': [tx.to_dict() for tx in self.transactions],
        }

    @staticmethod
    def from_dict(data: dict) -> 'Block':
        from core.transaction import Transaction
        header       = BlockHeader.from_dict(data['header'])
        transactions = [
            Transaction.from_dict(tx_data)
            for tx_data in data['transactions']
        ]
        return Block(header, transactions)

    def __repr__(self):
        return f"Block(hash={self.hash[:16]}..., txs={len(self.transactions)})"
