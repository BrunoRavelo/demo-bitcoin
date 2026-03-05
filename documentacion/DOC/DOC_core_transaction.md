# Documentación Técnica: `core/transaction.py`

---

## Propósito del Archivo

`transaction.py` representa una transacción de criptomoneda: la transferencia de valor de una dirección a otra. Cada transacción debe estar firmada digitalmente por el remitente para probar propiedad de los fondos.

**Analogía:** Una transacción es como un cheque bancario donde:
- **from_address** = cuenta de origen (quien paga)
- **to_address** = cuenta destino (quien recibe)
- **amount** = cantidad a transferir
- **signature** = firma del titular (prueba de autorización)

---

## Tipos de Transacciones

### 1. Transacción Normal
```python
tx = Transaction("1AliceAddress...", "1BobAddress...", 10)
tx.sign(alice_wallet)
```
- Requiere firma digital del remitente
- Transfiere fondos existentes
- Valida que el remitente tenga saldo suficiente

### 2. Transacción Coinbase
```python
tx = Transaction("COINBASE", "1MinerAddress...", 50)
```
- **Sin firma** (no hay remitente real)
- Crea nuevas monedas (recompensa de bloque)
- Solo válida como primera TX de un bloque minado
- En Bitcoin: única forma de crear nuevos BTC

---

## Dependencias

```python
import hashlib
import json
import time
from typing import Optional
```

| Import | Propósito |
|--------|-----------|
| `hashlib` | SHA256 para calcular TXID |
| `json` | Serializar datos antes de firmar |
| `time` | Timestamp de creación |
| `Optional` | Type hint para campos opcionales |

---

## Clase `Transaction`

```python
class Transaction:
```

Representa una transferencia de fondos entre dos direcciones.

**Atributos de instancia:**

| Atributo | Tipo | Descripción | Cuándo se llena |
|----------|------|-------------|-----------------|
| `from_address` | `str` | Dirección del remitente (o "COINBASE") | `__init__` |
| `to_address` | `str` | Dirección del destinatario | `__init__` |
| `amount` | `float` | Cantidad a transferir | `__init__` |
| `timestamp` | `float` | Unix timestamp de creación | `__init__` |
| `public_key` | `Optional[str]` | Public key del remitente (hex) | `.sign()` |
| `signature` | `Optional[str]` | Firma digital (hex) | `.sign()` |

---

## Función `__init__`

```python
def __init__(self, from_address: str, to_address: str, amount: float):
    self.from_address = from_address
    self.to_address = to_address
    self.amount = amount
    self.timestamp = time.time()
    self.public_key: Optional[str] = None
    self.signature: Optional[str] = None
```

**¿Qué hace?**

Crea una transacción sin firmar. Los campos `public_key` y `signature` se inicializan como `None` y se llenan posteriormente con el método `.sign()`.

**¿Por qué `timestamp = time.time()`?**

El timestamp sirve para:
1. **Ordenar transacciones** cronológicamente
2. **Prevenir replay attacks** (la misma TX no puede usarse en otro momento)
3. **Calcular el TXID único** (diferentes timestamps → diferentes TXID)

**Ejemplo:**
```python
# Crear TX sin firmar
tx = Transaction("1Alice...", "1Bob...", 10)

# Estado actual:
# tx.from_address = "1Alice..."
# tx.to_address = "1Bob..."
# tx.amount = 10
# tx.timestamp = 1707234567.123
# tx.public_key = None  ← todavía no firmada
# tx.signature = None   ← todavía no firmada
```

---

## Función `to_dict`

```python
def to_dict(self, include_signature: bool = True) -> dict:
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
```

**¿Qué hace?**

Serializa la transacción a un diccionario Python. El parámetro `include_signature` controla si se incluye la firma.

**¿Por qué `include_signature` es opcional?**

Porque se usa en dos contextos diferentes:

**Contexto 1: Firmar la TX**
```python
# Para firmar, NO incluimos la signature (porque aún no existe)
tx_data = tx.to_dict(include_signature=False)
signature = wallet.sign_transaction(tx_data)
```

**Contexto 2: Transmitir la TX**
```python
# Para enviar por la red, SÍ incluimos la signature
tx_data = tx.to_dict(include_signature=True)
send_to_network(tx_data)
```

**Ejemplo:**
```python
tx = Transaction("1Alice...", "1Bob...", 10)
tx.sign(alice_wallet)

# Sin firma:
tx.to_dict(include_signature=False)
# → {'from': '1Alice...', 'to': '1Bob...', 'amount': 10, 
#    'timestamp': 1707234567, 'public_key': 'abc123...'}

# Con firma:
tx.to_dict(include_signature=True)
# → {'from': '1Alice...', 'to': '1Bob...', 'amount': 10,
#    'timestamp': 1707234567, 'public_key': 'abc123...', 
#    'signature': 'def456...'}
```

---

## Función `hash` (TXID)

```python
def hash(self) -> str:
    data = {
        'from': self.from_address,
        'to': self.to_address,
        'amount': self.amount,
        'timestamp': self.timestamp
    }
    
    tx_string = json.dumps(data, sort_keys=True)
    return hashlib.sha256(tx_string.encode()).hexdigest()
```

**¿Qué hace?**

Calcula el **TXID** (Transaction ID), el identificador único de la transacción.

**Campos incluidos en el hash:**
- ✅ `from_address`
- ✅ `to_address`
- ✅ `amount`
- ✅ `timestamp`

**Campos EXCLUIDOS del hash:**
- ❌ `public_key` (metadato de firma)
- ❌ `signature` (metadato de firma)

**¿Por qué excluir `public_key` y `signature`?**

Para que el TXID sea **inmutable** y **predecible antes de firmar**:

```python
tx = Transaction("1Alice...", "1Bob...", 10)

# TXID antes de firmar
txid_before = tx.hash()  # → "abc123..."

# Firmar
tx.sign(alice_wallet)
# Ahora tx.public_key = "def456..."
# Ahora tx.signature = "789xyz..."

# TXID después de firmar
txid_after = tx.hash()  # → "abc123..." ← ¡MISMO TXID!
```

**Si incluyéramos la firma en el hash:**

```
Problema: Transaction Malleability
1. Atacante modifica la firma ligeramente (sigue siendo válida)
2. TXID cambia
3. Misma transacción, múltiples TXID
4. Caos en la blockchain
```

Bitcoin sufrió este problema hasta **SegWit (2017)** que lo resolvió de manera similar: separando la firma del TXID.

**Ejemplo:**
```python
tx = Transaction("1Alice...", "1Bob...", 10)
tx.timestamp = 1707234567  # Fijo para el ejemplo

txid = tx.hash()
# → "a3f2c1d8e9b4a7c6d5e4f3c2b1a0987654321fedcba0123456789abcdef0123"
```

---

## Función `sign`

```python
def sign(self, wallet):
    if self.from_address != "COINBASE":
        assert wallet.address == self.from_address, \
            "No puedes firmar una transacción con una wallet que no es tuya"
    
    self.public_key = wallet.get_public_key_hex()
    
    tx_data = self.to_dict(include_signature=False)
    self.signature = wallet.sign_transaction(tx_data)
```

**¿Qué hace?**

Firma la transacción con una wallet, agregando `public_key` y `signature`.

**Proceso paso a paso:**

```
1. Validar wallet
   ├─ Si from_address == "COINBASE" → skip (coinbase no se firma)
   └─ Si wallet.address ≠ from_address → Error

2. Agregar public_key
   self.public_key = wallet.get_public_key_hex()

3. Serializar datos SIN signature
   tx_data = to_dict(include_signature=False)

4. Firmar con wallet
   self.signature = wallet.sign_transaction(tx_data)

5. TX ahora está firmada y lista para propagarse
```

**¿Por qué validar que `wallet.address == from_address`?**

Prevenir errores del programador:

```python
alice = Wallet()
bob = Wallet()

# Crear TX desde Alice
tx = Transaction(alice.address, bob.address, 10)

# ERROR: Intentar firmar con wallet de Bob
tx.sign(bob)  # ❌ AssertionError: "No puedes firmar una TX que no es tuya"

# CORRECTO: Firmar con wallet de Alice
tx.sign(alice)  # ✅ Funciona
```

**Ejemplo completo:**
```python
alice = Wallet()
bob = Wallet()

# 1. Crear TX
tx = Transaction(alice.address, bob.address, 10)
print(tx.signature)  # → None (sin firmar)

# 2. Firmar
tx.sign(alice)
print(tx.signature)  # → "abc123def456..." (firmada)
print(tx.public_key)  # → "789xyz..." (agregada)
```

---

## Función `is_valid`

```python
def is_valid(self) -> bool:
    # 1. Coinbase no requiere firma
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
    
    # 3. Verificar firma digital
    from core.wallet import Wallet
    tx_data = self.to_dict(include_signature=False)
    
    return Wallet.verify_signature(
        tx_data,
        self.public_key,
        self.signature
    )
```

**¿Qué hace?**

Valida que la transacción sea legítima mediante 3 capas de validación.

**Capa 1: Coinbase Exception**
```python
if self.from_address == "COINBASE":
    return True
```

Las transacciones coinbase son especiales:
- No tienen remitente real (crean monedas nuevas)
- No requieren firma
- Solo válidas como primera TX de un bloque minado

**Capa 2: Validación de Campos**
```python
if not all([
    self.from_address,      # No vacío
    self.to_address,        # No vacío
    self.amount > 0,        # Mayor que cero
    self.public_key,        # Presente
    self.signature          # Presente
]):
    return False
```

Verifica que todos los campos necesarios existan y sean válidos.

**Capa 3: Validación Criptográfica**
```python
tx_data = self.to_dict(include_signature=False)
return Wallet.verify_signature(tx_data, self.public_key, self.signature)
```

Verifica la firma digital Ed25519. Si la firma no coincide con los datos y la public key, la TX es inválida.

**Flujo de validación:**

```
                is_valid()
                    │
                    ▼
            ¿from_address == "COINBASE"?
                    │
        ┌───────────┴───────────┐
       Sí                       No
        │                        │
        ▼                        ▼
    return True       ¿Todos los campos presentes?
                                 │
                     ┌───────────┴───────────┐
                    Sí                       No
                     │                        │
                     ▼                        ▼
          ¿Firma Ed25519 válida?        return False
                     │
         ┌───────────┴───────────┐
        Sí                       No
         │                        │
         ▼                        ▼
    return True            return False
```

**Casos que devuelven `False`:**

| Caso | Por qué |
|------|---------|
| `from_address` vacío | TX debe tener origen |
| `to_address` vacío | TX debe tener destino |
| `amount <= 0` | No se pueden enviar 0 monedas |
| `public_key` faltante | No se puede verificar sin public key |
| `signature` faltante | TX sin firmar es inválida |
| Firma no coincide | Datos fueron modificados o firma falsa |

**Ejemplo:**
```python
alice = Wallet()
bob = Wallet()

# TX válida
tx = Transaction(alice.address, bob.address, 10)
tx.sign(alice)
print(tx.is_valid())  # → True

# TX modificada después de firmar (ataque)
tx.amount = 99999
print(tx.is_valid())  # → False (firma ya no coincide)

# TX coinbase (sin firma)
coinbase = Transaction("COINBASE", alice.address, 50)
print(coinbase.is_valid())  # → True (coinbase no requiere firma)
```

---

## Función estática `from_dict`

```python
@staticmethod
def from_dict(data: dict) -> 'Transaction':
    tx = Transaction(
        from_address=data['from'],
        to_address=data['to'],
        amount=data['amount']
    )
    
    tx.timestamp = data.get('timestamp', time.time())
    tx.public_key = data.get('public_key')
    tx.signature = data.get('signature')
    
    return tx
```

**¿Qué hace?**

Deserializa una transacción desde un diccionario (inverso de `to_dict`).

**¿Por qué es `@staticmethod`?**

Porque crea una **nueva instancia** de Transaction. No opera sobre una instancia existente.

**Proceso:**

```
Diccionario (de red o archivo)
        │
        ▼
Transaction.__init__()  ← Crea objeto base
        │
        ▼
Rellenar campos opcionales (timestamp, public_key, signature)
        │
        ▼
Retornar instancia completa
```

**Uso típico:**

```python
# Nodo A crea TX
tx1 = Transaction("1Alice...", "1Bob...", 10)
tx1.sign(alice_wallet)

# Serializar para red
tx_data = tx1.to_dict()

# ─────────────────────────────────
# Transmisión por WebSocket
# ─────────────────────────────────

# Nodo B recibe datos
received_data = {
    'from': '1Alice...',
    'to': '1Bob...',
    'amount': 10,
    'timestamp': 1707234567,
    'public_key': 'abc123...',
    'signature': 'def456...'
}

# Reconstruir TX en Nodo B
tx2 = Transaction.from_dict(received_data)

# tx2 es idéntica a tx1
print(tx2.is_valid())  # → True
```

**¿Por qué `data.get()` en lugar de `data[]`?**

`get()` retorna `None` si la llave no existe, evitando `KeyError`:

```python
# Con data[]
tx.timestamp = data['timestamp']  # ← KeyError si no existe

# Con data.get()
tx.timestamp = data.get('timestamp', time.time())  # ← usa default si no existe
```

Esto permite deserializar TXs antiguas que no tenían ciertos campos.

---

## Función `__repr__`

```python
def __repr__(self):
    return f"Transaction(from={self.from_address[:8]}..., to={self.to_address[:8]}..., amount={self.amount})"
```

**¿Qué hace?**

Define cómo se muestra la transacción al imprimirla. Muestra solo los primeros 8 caracteres de las addresses para brevedad.

**Ejemplo:**
```python
tx = Transaction("1AliceXyz123...", "1BobAbc456...", 10)
print(tx)
# → Transaction(from=1AliceXy..., to=1BobAbc4..., amount=10)
```

---

## Ciclo de Vida de una Transacción

```
1. CREACIÓN
   tx = Transaction(from, to, amount)
   Estado: sin firmar
   
2. FIRMA
   tx.sign(wallet)
   Estado: firmada, lista para propagarse
   
3. PROPAGACIÓN P2P
   send_to_network(tx.to_dict())
   Estado: en mempool de otros nodos
   
4. VALIDACIÓN
   if tx.is_valid():
       add_to_mempool(tx)
   Estado: en mempool local
   
5. MINADO
   block = mine_block([tx, ...])
   Estado: en blockchain (confirmada)
   
6. INMUTABILIDAD
   Modificar tx → firma inválida → rechazada
   Estado: permanente en la cadena
```

---

## Diferencias con Bitcoin

| Aspecto | Bitcoin | Este Demo |
|---------|---------|-----------|
| **Modelo** | UTXO (inputs/outputs) | Balance simple (from/to) |
| **Inputs** | Referencias a UTXOs previos | Solo `from_address` |
| **Outputs** | Múltiples outputs + cambio | Solo `to_address` |
| **Fees** | Diferencia inputs-outputs | Sin fees |
| **Script** | Bitcoin Script (Turing-incompleto) | Validación simple |
| **Serialización** | Formato binario | JSON |
| **TXID** | Double SHA256 del binario | SHA256 del JSON |

**Concepto idéntico:** Ambos prueban propiedad mediante firma digital y previenen modificación.

---

## Tests Asociados: `tests/test_transaction.py`

| Test | Función que prueba | Qué verifica |
|------|-------------------|--------------|
| `test_create_transaction` | `__init__` | TX se crea sin firma |
| `test_transaction_hash` | `hash` | TXID es consistente |
| `test_different_transactions_different_hashes` | `hash` | TXs diferentes → TXIDs diferentes |
| `test_sign_transaction` | `sign` | Agrega signature y public_key |
| `test_cannot_sign_with_wrong_wallet` | `sign` | Error si wallet incorrecta |
| `test_valid_signed_transaction` | `is_valid` | TX firmada es válida |
| `test_invalid_transaction_no_signature` | `is_valid` | TX sin firma es inválida |
| `test_invalid_transaction_tampered_amount` | `is_valid` | TX modificada es inválida |
| `test_invalid_transaction_zero_amount` | `is_valid` | amount <= 0 es inválido |
| `test_coinbase_transaction_valid` | `is_valid` | Coinbase sin firma es válida |
| `test_transaction_to_dict` | `to_dict` | Serialización correcta |
| `test_transaction_from_dict` | `from_dict` | Deserialización correcta |
| `test_transaction_hash_excludes_signature` | `hash` | TXID no cambia al firmar |

---

*Documento: `DOC_core_transaction.md` — Demo Blockchain Fase 2.1*
