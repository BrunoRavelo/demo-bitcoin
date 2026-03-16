"""
Transacción con firma digital EdDSA (Ed25519)
Representa transferencia de fondos entre direcciones

Diferencias con Bitcoin real:
- Bitcoin usa ECDSA secp256k1; nosotros usamos Ed25519 (más rápido, más moderno)
- Bitcoin usa UTXO model; nosotros usamos from/to/amount (account model simplificado)
- Bitcoin usa double SHA256 para el txid; nosotros también (corregido en v0.3.0)
- Bitcoin no tiene fees en esta implementación demo
"""

import hashlib
import json
import time
from typing import Optional


class Transaction:
    """
    Transacción de criptomoneda

    Tipos:
    - Normal:   from_address → to_address  (requiere firma Ed25519)
    - Coinbase: "COINBASE"  → miner_address (sin firma, recompensa de bloque)

    El txid (hash) se calcula con double SHA256 sobre los campos
    inmutables (from, to, amount, timestamp), igual que en Bitcoin.
    La firma NO se incluye en el hash para que el txid sea estable
    antes y después de firmar.
    """

    def __init__(self, from_address: str, to_address: str, amount: float):
        """
        Crea una transacción sin firmar.

        Args:
            from_address: Dirección del remitente (o "COINBASE")
            to_address:   Dirección del destinatario
            amount:       Cantidad a transferir (> 0)
        """
        self.from_address = from_address
        self.to_address   = to_address
        self.amount       = amount
        self.timestamp    = time.time()

        # Se llenan al llamar sign()
        self.public_key: Optional[str] = None
        self.signature:  Optional[str] = None

    # ──────────────────────────────────────────────
    # Serialización
    # ──────────────────────────────────────────────

    def to_dict(self, include_signature: bool = True) -> dict:
        """
        Serializa la transacción a diccionario.

        Args:
            include_signature: Si False, omite signature y public_key.
                               Usar False al calcular el hash y al firmar.

        Returns:
            Diccionario con los campos de la transacción.
        """
        data = {
            'from':      self.from_address,
            'to':        self.to_address,
            'amount':    self.amount,
            'timestamp': self.timestamp,
            'public_key': self.public_key,
        }

        if include_signature and self.signature:
            data['signature'] = self.signature

        return data

    @staticmethod
    def from_dict(data: dict) -> 'Transaction':
        """
        Deserializa una transacción desde diccionario (red o bloque).

        Args:
            data: Diccionario con campos de la transacción.

        Returns:
            Instancia de Transaction.
        """
        tx = Transaction(
            from_address=data['from'],
            to_address=data['to'],
            amount=data['amount'],
        )
        tx.timestamp   = data.get('timestamp', time.time())
        tx.public_key  = data.get('public_key')
        tx.signature   = data.get('signature')
        return tx

    # ──────────────────────────────────────────────
    # Hash (txid)
    # ──────────────────────────────────────────────

    def hash(self) -> str:
        """
        Calcula el txid de la transacción usando double SHA256.

        Proceso (igual que Bitcoin):
            1. Serializar campos inmutables a JSON determinístico
            2. SHA256(data)          → digest intermedio (bytes)
            3. SHA256(digest)        → txid final (hexadecimal)

        Solo incluye los campos que NO cambian después de firmar
        (from, to, amount, timestamp), por lo que el txid es
        idéntico antes y después de agregar la firma.

        Returns:
            txid en hexadecimal (64 caracteres).
        """
        data = {
            'from':      self.from_address,
            'to':        self.to_address,
            'amount':    self.amount,
            'timestamp': self.timestamp,
        }
        tx_string = json.dumps(data, sort_keys=True)

        # Double SHA256 — igual que Bitcoin
        digest1 = hashlib.sha256(tx_string.encode()).digest()
        txid    = hashlib.sha256(digest1).hexdigest()
        return txid

    # ──────────────────────────────────────────────
    # Firma
    # ──────────────────────────────────────────────

    def sign(self, wallet) -> None:
        """
        Firma la transacción con la wallet del remitente.

        Guarda public_key y signature en la transacción.
        Solo se puede firmar si wallet.address == from_address.

        Args:
            wallet: Instancia de Wallet con la clave privada del remitente.

        Raises:
            AssertionError: Si la wallet no corresponde al remitente.
            ValueError:     Si se intenta firmar una TX coinbase.
        """
        if self.from_address == "COINBASE":
            raise ValueError("Las transacciones coinbase no se firman.")

        assert wallet.address == self.from_address, (
            f"La wallet ({wallet.address[:12]}...) no corresponde "
            f"al remitente ({self.from_address[:12]}...)"
        )

        self.public_key = wallet.get_public_key_hex()
        tx_data         = self.to_dict(include_signature=False)
        self.signature  = wallet.sign_transaction(tx_data)

    # ──────────────────────────────────────────────
    # Validación
    # ──────────────────────────────────────────────

    def is_valid(self) -> bool:
        """
        Valida la transacción.

        Reglas:
        1. Coinbase siempre válida (sin firma requerida).
        2. Campos obligatorios presentes y amount > 0.
        3. Firma Ed25519 correcta sobre los datos sin signature.

        Returns:
            True si la transacción es válida.
        """
        # Regla 1 — coinbase no requiere firma
        if self.from_address == "COINBASE":
            return True

        # Regla 2 — campos básicos
        if not all([
            self.from_address,
            self.to_address,
            self.amount > 0,
            self.public_key,
            self.signature,
        ]):
            return False

        # Regla 3 — verificar firma Ed25519
        from core.wallet import Wallet
        tx_data = self.to_dict(include_signature=False)
        return Wallet.verify_signature(tx_data, self.public_key, self.signature)

    # ──────────────────────────────────────────────
    # Utilidades
    # ──────────────────────────────────────────────

    def is_coinbase(self) -> bool:
        """Retorna True si es una transacción coinbase."""
        return self.from_address == "COINBASE"

    def short_hash(self, n: int = 16) -> str:
        """Retorna los primeros n caracteres del txid (para logs)."""
        return self.hash()[:n] + "..."

    def __repr__(self):
        src = self.from_address[:10] if len(self.from_address) > 10 else self.from_address
        dst = self.to_address[:10]   if len(self.to_address)   > 10 else self.to_address
        return f"Transaction({src}...→{dst}..., amount={self.amount})"
