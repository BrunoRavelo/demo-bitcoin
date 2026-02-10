"""
Wallet con criptografía EdDSA (Ed25519)
Genera par de llaves, firma transacciones, deriva direcciones

Nota: Bitcoin usa ECDSA secp256k1, pero este demo usa Ed25519
por ser más seguro, rápido y moderno. Los conceptos fundamentales
(firmas digitales, validación) son idénticos.
"""

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
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
    
    def _generate_address(self) -> str:
        """
        Genera dirección desde public key
        Proceso: SHA256(SHA256(public_key))[:20] en hex
        
        Nota: Bitcoin usa SHA256 -> RIPEMD160 -> Base58Check
        Aquí simplificamos a double SHA256 para el demo
        
        Returns:
            Dirección de 40 caracteres (20 bytes en hex)
        """
        # Serializar public key (32 bytes en Ed25519)
        pub_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        # Double SHA256 (como Bitcoin)
        hash1 = hashlib.sha256(pub_bytes).digest()
        hash2 = hashlib.sha256(hash1).digest()
        
        # Tomar primeros 20 bytes y convertir a hex
        address = hash2[:20].hex()
        
        return address
    
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