"""
Wallet con criptografía EdDSA (Ed25519)
Genera par de llaves, firma transacciones, deriva direcciones

Nota: Bitcoin usa ECDSA secp256k1, pero este demo usa Ed25519
por ser más seguro, rápido y moderno. Los conceptos fundamentales
(firmas digitales, validación) son idénticos.
"""

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from Crypto.Hash import RIPEMD160
import hashlib


class Wallet:
    """
    Wallet de criptomoneda con:
    - Par de llaves EdDSA (Ed25519)
    - Dirección pública derivada
    - Capacidad de firmar transacciones
    
    Ed25519 vs ECDSA secp256k1 (Bitcoin):
    - 5-10x más rápido
    - Firmas más pequeñas (64 bytes vs ~70 bytes)
    - Nonce determinístico (sin riesgo de reuso)
    - Resistente a timing attacks
    """
    
    def __init__(self):
        """Genera un nuevo par de llaves Ed25519"""
        # Generar private key (32 bytes)
        self.private_key = ed25519.Ed25519PrivateKey.generate()
        
        # Derivar public key desde private key (32 bytes)
        self.public_key = self.private_key.public_key()
        
        # Generar dirección desde public key
        self.address = self._generate_address()
    
    def _hash160(self, pub_bytes: bytes) -> bytes:
        """SHA256 → RIPEMD160 (Hash160, igual que Bitcoin)"""
        sha256 = hashlib.sha256(pub_bytes).digest()
        h = RIPEMD160.new(sha256)
        return h.digest()

    def _checksum(self, payload: bytes) -> bytes:
        """SHA256(SHA256(payload))[:4] - detecta errores tipográficos"""
        return hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]

    def _base58check_encode(self, payload: bytes) -> str:
        """Convierte bytes a string Base58Check (como Bitcoin)"""
        alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
        
        # Contar ceros iniciales (se convierten en '1')
        count = 0
        for byte in payload:
            if byte == 0:
                count += 1
            else:
                break
        
        # Convertir bytes a número entero
        num = int.from_bytes(payload, 'big')
        
        # Convertir a Base58
        result = ''
        while num > 0:
            num, remainder = divmod(num, 58)
            result = alphabet[remainder] + result
        
        return '1' * count + result

    def _generate_address(self) -> str:
        """
        Genera address idéntica a Bitcoin:
        SHA256 → RIPEMD160 → version byte → checksum → Base58Check
        
        Returns:
            Address ~34 caracteres, empieza con '1'
        """
        # Serializar public key (32 bytes)
        pub_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        # Hash160: SHA256 → RIPEMD160
        hash160 = self._hash160(pub_bytes)
        
        # Version byte 0x00 = mainnet (como Bitcoin)
        versioned = b'\x00' + hash160
        
        # Checksum: SHA256(SHA256(versioned))[:4]
        checksum = self._checksum(versioned)
        
        # Payload final: version + hash160 + checksum
        payload = versioned + checksum
        
        # Codificar en Base58Check
        return self._base58check_encode(payload)
    
    def sign_transaction(self, tx_data: dict) -> str:
        """
        Firma datos de transacción con private key
        
        Ed25519 características:
        - Firma determinística (sin RNG)
        - Hash SHA-512 integrado
        - Firma de 64 bytes (fija)
        
        Args:
            tx_data: Diccionario con datos de la transacción
        
        Returns:
            Firma en formato hexadecimal (128 caracteres)
        """
        import json
        
        # Serializar tx_data de forma determinística
        tx_string = json.dumps(tx_data, sort_keys=True)
        
        # Firmar con Ed25519
        # (internamente usa SHA-512, nonce determinístico)
        signature = self.private_key.sign(tx_string.encode('utf-8'))
        
        # Retornar en hex para facilitar serialización JSON
        # Ed25519 firma = 64 bytes = 128 caracteres hex
        return signature.hex()
    
    def get_public_key_hex(self) -> str:
        """
        Retorna public key en formato hexadecimal
        
        Ed25519 public key = 32 bytes = 64 caracteres hex
        (vs ECDSA uncompressed = 65 bytes = 130 caracteres hex)
        
        Returns:
            Public key en hex (para incluir en transacciones)
        """
        pub_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        return pub_bytes.hex()
    
    @staticmethod
    def verify_signature(tx_data: dict, public_key_hex: str, signature_hex: str) -> bool:
        """
        Verifica firma de una transacción
        
        Ed25519 ventajas en verificación:
        - ~2x más rápido que ECDSA
        - Resistente a timing attacks
        
        Args:
            tx_data: Datos de la transacción (sin signature)
            public_key_hex: Public key en formato hex (64 caracteres)
            signature_hex: Firma en formato hex (128 caracteres)
        
        Returns:
            True si la firma es válida
        """
        import json
        
        try:
            # Reconstruir public key desde hex (32 bytes)
            pub_bytes = bytes.fromhex(public_key_hex)
            public_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
            
            # Serializar tx_data (debe ser idéntico a cuando se firmó)
            tx_string = json.dumps(tx_data, sort_keys=True)
            
            # Convertir signature de hex a bytes (64 bytes)
            signature = bytes.fromhex(signature_hex)
            
            # Verificar firma
            # (lanza InvalidSignature exception si es inválida)
            public_key.verify(signature, tx_string.encode('utf-8'))
            
            # Si no lanzó excepción, la firma es válida
            return True
            
        except Exception as e:
            # Cualquier error = firma inválida
            return False
    
    def __repr__(self):
        return f"Wallet(address={self.address[:16]}...)"