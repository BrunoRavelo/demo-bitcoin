"""
Transacción con firma digital ECDSA
Representa transferencia de fondos entre direcciones
"""

import hashlib
import json
import time
from typing import Optional


class Transaction:
    """
    Transacción de criptomoneda
    
    Tipos:
    - Normal: from_address → to_address (requiere firma)
    - Coinbase: COINBASE → miner_address (sin firma, reward de bloque)
    """
    
    def __init__(self, from_address: str, to_address: str, amount: float):
        """
        Crea una transacción
        
        Args:
            from_address: Dirección del remitente (o "COINBASE")
            to_address: Dirección del destinatario
            amount: Cantidad a transferir
        """
        self.from_address = from_address
        self.to_address = to_address
        self.amount = amount
        self.timestamp = time.time()
        
        # Campos de firma (se llenan con sign())
        self.public_key: Optional[str] = None
        self.signature: Optional[str] = None
    
    def to_dict(self, include_signature: bool = True) -> dict:
        """
        Serializa transacción a diccionario
        
        Args:
            include_signature: Si False, excluye signature (para firmar)
        
        Returns:
            Diccionario con los datos de la transacción
        """
        data = {
            'from': self.from_address,
            'to': self.to_address,
            'amount': self.amount,
            'timestamp': self.timestamp,
            'public_key': self.public_key
        }
        
        if include_signature and self.signature:
            data['signature'] = self.signature
        
        return data
    
    def hash(self) -> str:
        """
        Calcula hash único de la transacción (sin signature ni public_key)
        Sirve como identificador (txid)
        
        Returns:
            Hash SHA256 en hexadecimal
        """
        # Hash solo de campos inmutables
        data = {
            'from': self.from_address,
            'to': self.to_address,
            'amount': self.amount,
            'timestamp': self.timestamp
        }
        
        tx_string = json.dumps(data, sort_keys=True)
        return hashlib.sha256(tx_string.encode()).hexdigest()
    
    def sign(self, wallet):
        """
        Firma la transacción con una wallet
        
        Args:
            wallet: Instancia de Wallet con private key
        
        Raises:
            AssertionError: Si la wallet no coincide con from_address
        """
        # Verificar que la wallet sea del remitente
        if self.from_address != "COINBASE":
            assert wallet.address == self.from_address, \
                "No puedes firmar una transacción con una wallet que no es tuya"
        
        # Agregar public key
        self.public_key = wallet.get_public_key_hex()
        
        # Firmar los datos (sin signature)
        tx_data = self.to_dict(include_signature=False)
        self.signature = wallet.sign_transaction(tx_data)
    
    def is_valid(self) -> bool:
        """
        Valida la transacción
        
        Validaciones:
        1. Coinbase no requiere firma
        2. Campos básicos completos
        3. Amount > 0
        4. Firma ECDSA válida
        
        Returns:
            True si la transacción es válida
        """
        # 1. Transacciones coinbase no requieren firma
        if self.from_address == "COINBASE":
            return True
        
        # 2. Verificar campos básicos
        if not all([
            self.from_address,
            self.to_address,
            self.amount > 0,
            self.public_key,
            self.signature
        ]):
            return False
        
        # 3. Verificar firma ECDSA
        from core.wallet import Wallet
        
        tx_data = self.to_dict(include_signature=False)
        
        return Wallet.verify_signature(
            tx_data,
            self.public_key,
            self.signature
        )
    
    @staticmethod
    def from_dict(data: dict) -> 'Transaction':
        """
        Deserializa transacción desde diccionario
        
        Args:
            data: Diccionario con datos de transacción
        
        Returns:
            Instancia de Transaction
        """
        tx = Transaction(
            from_address=data['from'],
            to_address=data['to'],
            amount=data['amount']
        )
        
        tx.timestamp = data.get('timestamp', time.time())
        tx.public_key = data.get('public_key')
        tx.signature = data.get('signature')
        
        return tx
    
    def __repr__(self):
        return f"Transaction(from={self.from_address[:8]}..., to={self.to_address[:8]}..., amount={self.amount})"