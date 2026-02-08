"""
Wallet con criptografía ECDSA (secp256k1)
Genera par de llaves, firma transacciones, deriva direcciones
"""

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
import hashlib


class Wallet:
    """
    Wallet de criptomoneda con:
    - Par de llaves ECDSA (secp256k1)
    - Dirección pública derivada
    - Capacidad de firmar transacciones
    """
    
    def __init__(self):
        """Genera un nuevo par de llaves"""
        # Generar private key (curva secp256k1 - misma que Bitcoin)
        self.private_key = ec.generate_private_key(
            ec.SECP256K1(),
            default_backend()
        )
        
        # Derivar public key desde private key
        self.public_key = self.private_key.public_key()
        
        # Generar dirección desde public key
        self.address = self._generate_address()
    
    def _generate_address(self) -> str:
        """
        Genera dirección desde public key
        Simplificado: SHA256(public_key)[:20] en hex
        Bitcoin real: SHA256 -> RIPEMD160 -> Base58Check
        
        Returns:
            Dirección de 40 caracteres (20 bytes en hex)
        """
        # Serializar public key en formato comprimido
        pub_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        )
        
        # Hash SHA256
        hash1 = hashlib.sha256(pub_bytes).digest()
        
        # Segundo SHA256 (como Bitcoin)
        hash2 = hashlib.sha256(hash1).digest()
        
        # Tomar primeros 20 bytes y convertir a hex
        address = hash2[:20].hex()
        
        return address
    
    def sign_transaction(self, tx_data: dict) -> str:
        """
        Firma datos de transacción con private key
        
        Args:
            tx_data: Diccionario con datos de la transacción
        
        Returns:
            Firma en formato hexadecimal
        """
        import json
        
        # Serializar tx_data de forma determinística
        tx_string = json.dumps(tx_data, sort_keys=True)
        
        # Firmar con ECDSA
        signature = self.private_key.sign(
            tx_string.encode('utf-8'),
            ec.ECDSA(hashes.SHA256())
        )
        
        # Retornar en hex para facilitar serialización JSON
        return signature.hex()
    
    def get_public_key_hex(self) -> str:
        """
        Retorna public key en formato hexadecimal
        
        Returns:
            Public key en hex (para incluir en transacciones)
        """
        pub_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        )
        return pub_bytes.hex()
    
    @staticmethod
    def verify_signature(tx_data: dict, public_key_hex: str, signature_hex: str) -> bool:
        """
        Verifica firma de una transacción
        
        Args:
            tx_data: Datos de la transacción (sin signature)
            public_key_hex: Public key en formato hex
            signature_hex: Firma en formato hex
        
        Returns:
            True si la firma es válida
        """
        import json
        
        try:
            # Reconstruir public key desde hex
            pub_bytes = bytes.fromhex(public_key_hex)
            public_key = ec.EllipticCurvePublicKey.from_encoded_point(
                ec.SECP256K1(),
                pub_bytes
            )
            
            # Serializar tx_data (debe ser idéntico a cuando se firmó)
            tx_string = json.dumps(tx_data, sort_keys=True)
            
            # Convertir signature de hex a bytes
            signature = bytes.fromhex(signature_hex)
            
            # Verificar firma
            public_key.verify(
                signature,
                tx_string.encode('utf-8'),
                ec.ECDSA(hashes.SHA256())
            )
            
            # Si no lanzó excepción, la firma es válida
            return True
            
        except Exception as e:
            # Cualquier error = firma inválida
            return False
    
    def __repr__(self):
        return f"Wallet(address={self.address[:16]}...)"