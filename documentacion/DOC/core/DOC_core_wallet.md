# Documentación Técnica: `core/wallet.py`

---

## Propósito del Archivo

`wallet.py` implementa la identidad criptográfica de un usuario en la red. Una wallet contiene un par de llaves (privada y pública) y permite firmar transacciones, probar propiedad de fondos y derivar una dirección pública.

**Analogía:** Una wallet es equivalente a una cuenta bancaria donde:
- La **private key** es tu contraseña secreta (nunca se comparte)
- La **public key** es tu número de cuenta (se puede compartir)
- La **address** es tu IBAN/CLABE (versión corta del número de cuenta)

---

## Algoritmo Criptográfico: EdDSA Ed25519

Este archivo usa **EdDSA (Edwards-curve Digital Signature Algorithm)** con la curva **Ed25519**.

**¿Por qué Ed25519 y no ECDSA secp256k1 (Bitcoin)?**

Bitcoin usa ECDSA secp256k1 porque fue el estándar disponible en 2009. Ed25519 se publicó en 2011 y es superior en casi todos los aspectos:

| Aspecto | ECDSA secp256k1 (Bitcoin) | EdDSA Ed25519 (Este Demo) |
|---------|---------------------------|---------------------------|
| Velocidad de firma | Baseline | ~5x más rápido |
| Velocidad de verificación | Baseline | ~2x más rápido |
| Tamaño de public key | 65 bytes | 32 bytes |
| Tamaño de firma | ~70 bytes (variable) | 64 bytes (fija) |
| Nonce de firma | Aleatorio (riesgo reuso) | Determinístico (seguro) |
| Resistencia a timing attacks | Requiere mitigación extra | Resistente por diseño |
| Constantes de curva | Arbitrarias (sospecha NSA) | Derivadas matemáticamente |

Los conceptos que este demo enseña (firmas digitales, validación, propiedad de fondos) son **idénticos** independientemente del algoritmo usado.

---

## Dependencias
```python
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from Crypto.Hash import RIPEMD160
import hashlib
```

| Import | Propósito |
|--------|-----------|
| `ed25519` | Generar llaves, firmar y verificar con Ed25519 |
| `serialization` | Exportar public key a bytes (para transmitir) |
| `RIPEMD160` | Hash de 20 bytes usado en Bitcoin addresses |
| `hashlib` | SHA256 para hash y checksum |


## Clase `Wallet`

```python
class Wallet:
```

Representa la identidad criptográfica de un usuario. Contiene la llave privada, la llave pública derivada y la dirección pública.

**Atributos de instancia:**

| Atributo | Tipo | Descripción |
|----------|------|-------------|
| `private_key` | `Ed25519PrivateKey` | Llave privada (secreta, nunca se comparte) |
| `public_key` | `Ed25519PublicKey` | Llave pública (derivada de private_key) |
| `address` | `str` | Dirección Base58Check ~34 caracteres (pública) |
---

## Función `__init__`

```python
def __init__(self):
    self.private_key = ed25519.Ed25519PrivateKey.generate()
    self.public_key = self.private_key.public_key()
    self.address = self._generate_address()
```

**¿Qué hace?**

Genera un nuevo par de llaves desde cero al crear la wallet. Cada llamada produce llaves únicas e irrepetibles.

**Proceso:**

```
Ed25519PrivateKey.generate()
        │
        │  (derivación matemática determinística)
        ▼
Ed25519PublicKey   ←── siempre la misma public key para la misma private key
        │
        │  (hashing)
        ▼
    Address (40 hex chars)
```

**¿Por qué la public key se deriva de la private key?**

En criptografía de curva elíptica, la public key es `private_key × G` donde `G` es un punto fijo de la curva. Esta operación es fácil de calcular en una dirección pero computacionalmente imposible de revertir (conocer `private_key` a partir de `public_key`).

**En Bitcoin:** El proceso es idéntico. Cada wallet genera un par de llaves nuevo. No hay "registro" de wallets: cualquiera puede generar una y empezar a recibir fondos.

---

## Función `_generate_address` y auxiliares

### Funciones auxiliares

#### `_hash160`
```python
def _hash160(self, pub_bytes: bytes) -> bytes:
    sha256 = hashlib.sha256(pub_bytes).digest()
    h = RIPEMD160.new(sha256)
    return h.digest()
```

**¿Qué hace?**

Aplica SHA256 seguido de RIPEMD160, proceso llamado "Hash160" en Bitcoin. Reduce la public key de 32 bytes a 20 bytes.
```
Public Key (32 bytes)
      │
      ▼
SHA256  →  32 bytes
      │
      ▼
RIPEMD160  →  20 bytes (Hash160)
```

---

#### `_checksum`
```python
def _checksum(self, payload: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
```

**¿Qué hace?**

Calcula doble SHA256 y toma los primeros 4 bytes. Detecta errores tipográficos en la address.
```
Payload (21 bytes)
      │
      ▼
SHA256  →  32 bytes
      │
      ▼
SHA256  →  32 bytes
      │
      ▼
[:4]  →  4 bytes (checksum)
```

Si alguien escribe mal un carácter de la address, el checksum no coincide y la wallet lo rechaza.

---

#### `_base58check_encode`
```python
def _base58check_encode(self, payload: bytes) -> str:
    alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    
    # Contar ceros iniciales
    count = 0
    for byte in payload:
        if byte == 0:
            count += 1
        else:
            break
    
    # Convertir a número entero
    num = int.from_bytes(payload, 'big')
    
    # Convertir a Base58
    result = ''
    while num > 0:
        num, remainder = divmod(num, 58)
        result = alphabet[remainder] + result
    
    return '1' * count + result
```

**¿Qué hace?**

Codifica bytes en Base58Check, el formato legible de Bitcoin.

**¿Por qué Base58 y no Base64?**

Base58 elimina caracteres confusos que se ven similares:
- `0` (cero) y `O` (o mayúscula)
- `I` (i mayúscula) y `l` (L minúscula)

**Alphabet Base58:**
```
123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz
```

**Proceso:**
```
Payload bytes → número entero → división base 58 → string legible
```

Los ceros iniciales se convierten en caracteres `'1'` para preservar información.

---

### `_generate_address` (función principal)
```python
def _generate_address(self) -> str:
    pub_bytes = self.public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    
    hash160 = self._hash160(pub_bytes)
    versioned = b'\x00' + hash160
    checksum = self._checksum(versioned)
    payload = versioned + checksum
    
    return self._base58check_encode(payload)
```

**¿Qué hace?**

Deriva una address idéntica a Bitcoin mediante un proceso de 5 pasos.

**Proceso completo (idéntico a Bitcoin):**
```
Public Key (32 bytes Ed25519)
          │
          ▼
    SHA256  →  32 bytes
          │
          ▼
    RIPEMD160  →  20 bytes (Hash160)
          │
          ▼
    Agregar version byte (0x00)  →  21 bytes
          │
          ▼
    SHA256(SHA256(21 bytes))[:4]  →  4 bytes (checksum)
          │
          ▼
    Concatenar: version + hash160 + checksum  →  25 bytes
          │
          ▼
    Base58Check encode  →  string ~34 caracteres
          │
          ▼
    Address: "1A2B3CXyz4D5E6F..."
```

**Ejemplo:**
```
Public Key:   a3f2c1d8e9b4... (32 bytes)
SHA256:       7e6d5c4b3a2f... (32 bytes)
RIPEMD160:    9b8a7c6d5e4f... (20 bytes)
Version:      00 9b8a7c6d... (21 bytes, 0x00 = mainnet)
Checksum:     a1b2c3d4       (4 bytes)
Payload:      00 9b8a... a1b2c3d4 (25 bytes)
Address:      1A2B3CXyz4D5E6F... (~34 chars Base58Check)
```

**¿Por qué este proceso?**

1. **SHA256:** Primera capa de hash
2. **RIPEMD160:** Reduce tamaño (20 bytes más compacto que 32)
3. **Version byte:** Indica red (0x00 = Bitcoin mainnet)
4. **Checksum:** Detecta typos al escribir la address
5. **Base58Check:** Formato legible sin caracteres confusos

**Diferencia con la versión anterior:**

| Aspecto | Versión Anterior | Versión Actual (Bitcoin) |
|---------|------------------|--------------------------|
| Hash | SHA256 → SHA256 | SHA256 → RIPEMD160 |
| Checksum | No | Sí (4 bytes) |
| Codificación | hex | Base58Check |
| Longitud | 40 chars | ~34 chars |
| Formato | `9b8a7c...` | `1A2B3C...` |
| Detección errores | No | Sí |

**¿Por qué no usar directamente la public key como address?**

1. **Privacidad:** La address no revela tu public key hasta que firmas (gastas fondos)
2. **Seguridad extra:** Si Ed25519 fuera rota en el futuro, la public key aún está oculta detrás de dos capas de hash
3. **Tamaño:** ~34 chars es más compacto y legible
4. **Checksum:** Previene enviar fondos a addresses con typos

**Nota:** El método es `_generate_address` (prefijo `_`) porque es de uso interno. Se llama desde `__init__` pero no debe llamarse externamente.

## Función `sign_transaction`

```python
def sign_transaction(self, tx_data: dict) -> str:
    import json
    tx_string = json.dumps(tx_data, sort_keys=True)
    signature = self.private_key.sign(tx_string.encode('utf-8'))
    return signature.hex()
```

**¿Qué hace?**

Firma los datos de una transacción con la private key, produciendo una firma de 64 bytes (128 caracteres hex).

**Proceso paso a paso:**

```
tx_data (dict)
        │
        ▼
json.dumps(sort_keys=True)  →  string determinístico
        │
        ▼
.encode('utf-8')  →  bytes
        │
        ▼
Ed25519PrivateKey.sign(bytes)  →  firma (64 bytes)
        │
        ▼
.hex()  →  string de 128 caracteres hex
```

**¿Por qué `sort_keys=True`?**

Los diccionarios en Python no garantizan orden. Sin `sort_keys=True`:
```python
# Podría producir strings diferentes para el mismo dict
json.dumps({"b": 2, "a": 1})  # → '{"b": 2, "a": 1}'
json.dumps({"a": 1, "b": 2})  # → '{"a": 1, "b": 2}'
```

Con `sort_keys=True`, el mismo diccionario siempre produce el mismo string, lo que garantiza que la firma sea reproducible y verificable.

Bitcoin define un formato binario estricto donde cada campo ocupa una posición fija:
Posición 0-3:    version     (4 bytes, siempre)
Posición 4-X:    inputs      (variable)
Posición X-Y:    outputs     (variable)
Posición Y-Y+4:  locktime    (4 bytes, siempre)
[00 00 00 01][01][abc123...][00 00 00 00]
 ↑ version    ↑   ↑ input    ↑ locktime
              nro

| Aspecto | Bitcoin (binario) | Este Demo (JSON) |
|---------|-------------------|------------------|
| **Formato** | Bytes crudos posición fija | String JSON legible |
| **Determinismo** | Por diseño (posición fija) | `sort_keys=True` |
| **Legibilidad** | Nula (bytes) | Alta (texto) |
| **Tamaño** | ~200-500 bytes | ~100-300 chars |
| **Implementación** | Compleja (parser binario) | Simple (json.dumps) |
| **Concepto** | ✅ Igual | ✅ Igual |

---

### ¿Por qué el resultado es prácticamente idéntico?

Porque en ambos casos se logra lo mismo:
```
Transacción (objeto)
      │
      ▼
Serialización determinística  ←── aquí es donde difieren técnicamente
      │
      ▼
Bytes únicos y reproducibles
      │
      ▼
Ed25519/ECDSA.sign(bytes)
      │
      ▼
Firma digital

```




**¿Por qué Ed25519 es determinístico?**

ECDSA (Bitcoin) requiere un nonce aleatorio en cada firma. Si el nonce se repite o es predecible, la private key queda expuesta (caso PlayStation 3, 2010). Ed25519 calcula el nonce internamente como:

```
nonce = SHA512(private_key || mensaje)
```

Esto garantiza que el mismo mensaje firmado con la misma llave siempre produce la **misma firma**, sin depender de un generador de números aleatorios.

**Implicación para el demo:**
```python
firma1 = wallet.sign_transaction({"amount": 10})  # → "abc123..."
firma2 = wallet.sign_transaction({"amount": 10})  # → "abc123..." (idéntica)
firma3 = wallet.sign_transaction({"amount": 99})  # → "xyz789..." (diferente)
```

---

## Función `get_public_key_hex`

```python
def get_public_key_hex(self) -> str:
    pub_bytes = self.public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    return pub_bytes.hex()
```

**¿Qué hace?**

Exporta la public key a formato hexadecimal para que pueda incluirse en transacciones y transmitirse por la red.

**¿Por qué es necesario exportar?**

El objeto `Ed25519PublicKey` de Python no es serializable directamente a JSON. Necesitamos convertirlo a bytes y luego a hex para:
- Incluirlo en el diccionario de la transacción
- Transmitirlo por WebSocket como parte del mensaje P2P
- Reconstruirlo en el nodo receptor para verificar la firma

**Formato:**
```
Ed25519PublicKey (objeto Python)
        │
        ▼
.public_bytes(Raw, Raw)  →  32 bytes
        │
        ▼
.hex()  →  64 caracteres hex
```

**Ejemplo:**
```
pub_hex = "a3f2c1d8e9b47c6d5e4f3c2b1a0987654321..."
          ← 64 caracteres exactos (32 bytes) →
```

---

## Función estática `verify_signature`

```python
@staticmethod
def verify_signature(tx_data: dict, public_key_hex: str, signature_hex: str) -> bool:
    import json
    try:
        pub_bytes = bytes.fromhex(public_key_hex)
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
        tx_string = json.dumps(tx_data, sort_keys=True)
        signature = bytes.fromhex(signature_hex)
        public_key.verify(signature, tx_string.encode('utf-8'))
        return True
    except Exception:
        return False
```

**¿Qué hace?**

Verifica que una firma corresponde a los datos dados y fue producida por el dueño de la public key. Es el mecanismo que permite a cualquier nodo verificar transacciones sin conocer la private key.

**¿Por qué es `@staticmethod`?**

No necesita acceso a `self` (no usa private key ni address de ninguna wallet). Cualquier nodo puede verificar firmas ajenas sin tener ninguna wallet. Es una operación de validación, no de firma.

**Proceso paso a paso:**

```
public_key_hex (str 64 chars)
        │
        ▼
bytes.fromhex()  →  32 bytes
        │
        ▼
Ed25519PublicKey.from_public_bytes()  →  objeto PublicKey reconstruido
        
tx_data (dict)
        │
        ▼
json.dumps(sort_keys=True).encode()  →  bytes (debe ser IDÉNTICO a cuando se firmó)

signature_hex (str 128 chars)
        │
        ▼
bytes.fromhex()  →  64 bytes

        ▼
public_key.verify(signature, message)
        │
        ├── Sin excepción  →  return True  ✅
        └── InvalidSignature  →  return False  ❌
```

**¿Por qué `try/except` en lugar de retornar el resultado directamente?**

La librería `cryptography` lanza una excepción `InvalidSignature` cuando la firma no es válida, en lugar de retornar `False`. El `try/except` convierte este comportamiento a un booleano limpio, más fácil de usar:

```python
# Sin try/except (incómodo):
try:
    public_key.verify(sig, msg)
    # válida
except InvalidSignature:
    # inválida

# Con try/except encapsulado (limpio):
if Wallet.verify_signature(data, pubkey, sig):
    # válida
else:
    # inválida
```

**¿Qué hace `verify` internamente?**

Ed25519 recalcula la firma esperada con la public key y verifica que coincide:
```
firma_esperada = recalcular(public_key, mensaje)
firma_esperada == firma_recibida  →  ✅
firma_esperada != firma_recibida  →  ❌ InvalidSignature
```

**Casos que devuelven `False`:**

| Caso | Por qué falla |
|------|---------------|
| Datos modificados | `tx_string` diferente → firma no coincide |
| Public key incorrecta | Firma fue producida por otra private key |
| Firma corrupta | Bytes de firma inválidos |
| Firma de otro mensaje | Firma válida pero para datos diferentes |

---

En este proyecto sí se usa el algoritmo oficial de verificación de EdDSA (Ed25519).


**Diferencia con Bitcoin Real**
En Bitcoin no solo se verifica una firma.
La validación de una transacción implica ejecutar un pequeño programa llamado **Bitcoin Script**.

Validación en el Demo

En este demo la lógica es simplificada:
Se verifica únicamente que la firma corresponda al mensaje y a la public key.

En Bitcoin Real
En Bitcoin la validación funciona así:

    Ejecutar ScriptSig + ScriptPubKey
    → evaluar pila (stack)
    → si el resultado final es TRUE
    → la transacción es válida


## Función `__repr__`

```python
def __repr__(self):
    return f"Wallet(address={self.address[:16]}...)"
```

**¿Qué hace?**

Define cómo se muestra la wallet al imprimirla o en logs. Muestra solo los primeros 16 caracteres de la address para evitar exponer la dirección completa innecesariamente.

**Ejemplo:**
```python
wallet = Wallet()
print(wallet)  # → Wallet(address=9b8a7c6d5e4f3c2b...)
```

---

## Flujo Completo de Uso

```python
# 1. Crear wallet
alice = Wallet()
# → Genera private_key, deriva public_key, calcula address

# 2. Ver dirección (para recibir fondos)
print(alice.address)  # → "9b8a7c6d5e4f..."

# 3. Firmar transacción
tx_data = {
    "from": alice.address,
    "to": "destinatario",
    "amount": 10,
    "timestamp": 1707234567
}
signature = alice.sign_transaction(tx_data)
# → "abc123def456..." (128 chars hex)

# 4. Compartir public key para verificación
pub_key = alice.get_public_key_hex()
# → "a3f2c1d8..." (64 chars hex)

# 5. Cualquier nodo verifica (sin conocer private key)
is_valid = Wallet.verify_signature(tx_data, pub_key, signature)
# → True

# 6. Modificar datos → firma inválida
tx_data["amount"] = 99999
is_valid = Wallet.verify_signature(tx_data, pub_key, signature)
# → False
```

---

## Tests Asociados: `tests/test_wallet.py`

| Test | Función que prueba | Qué verifica |
|------|-------------------|--------------|
| `test_create_wallet` | `__init__` | Llaves y address se crean correctamente |
| `test_wallets_have_different_addresses` | `__init__` | Cada wallet es única |
| `test_get_public_key_hex` | `get_public_key_hex` | Retorna 64 chars hex (32 bytes Ed25519) |
| `test_sign_transaction` | `sign_transaction` | Retorna 128 chars hex (64 bytes firma) |
| `test_verify_valid_signature` | `verify_signature` | Firma válida retorna True |
| `test_verify_invalid_signature_wrong_data` | `verify_signature` | Datos modificados retornan False |
| `test_verify_invalid_signature_wrong_pubkey` | `verify_signature` | Public key incorrecta retorna False |
| `test_verify_invalid_signature_corrupted` | `verify_signature` | Firma corrupta retorna False |
| `test_deterministic_signatures` | `sign_transaction` | Mismo mensaje = misma firma |
| `test_different_messages_different_signatures` | `sign_transaction` | Mensajes distintos = firmas distintas |

---

*Documento: `DOC_core_wallet.md` — Demo Blockchain Fase 2.1*
implementar checksum y ripemd
ponerle passwords a las llaves privadas
