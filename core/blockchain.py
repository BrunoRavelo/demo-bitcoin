"""
Blockchain - Cadena de bloques enlazados
Incluye genesis, mempool, minado, validación y longest chain rule

Sprint 4.1/4.2:
- replace_chain(): longest chain rule
- get_chain_as_dicts(): serialización para enviar por red
- add_block(): limpia mempool de TXs confirmadas
- Constantes importadas desde config.py
"""

import time
from typing import List, Optional
from core.block import Block, BlockHeader
from core.transaction import Transaction
from core.merkle import MerkleTree
from core.pow import ProofOfWork
from config import BLOCK_REWARD, DIFFICULTY, MAX_MEMPOOL_SIZE, MAX_TXS_PER_BLOCK


class Blockchain:
    """
    Cadena de bloques completa.

    Responsabilidades:
    - Mantener cadena de bloques
    - Gestionar mempool (TXs pendientes)
    - Minar nuevos bloques
    - Validar bloques y cadenas
    - Calcular balances
    - Resolver forks (longest chain rule)
    """

    def __init__(self):
        """Inicializa blockchain con genesis block."""
        self.chain:   List[Block]       = []
        self.mempool: List[Transaction] = []

        # Constantes desde config.py
        self.BLOCK_REWARD      = BLOCK_REWARD
        self.DIFFICULTY        = DIFFICULTY
        self.MAX_MEMPOOL_SIZE  = MAX_MEMPOOL_SIZE
        self.MAX_TXS_PER_BLOCK = MAX_TXS_PER_BLOCK

        self.create_genesis_block()

    # ──────────────────────────────────────────────────────────
    # Genesis
    # ──────────────────────────────────────────────────────────

    def create_genesis_block(self):
        """
        Crea el bloque génesis (primer bloque, hardcodeado).

        Todos los nodos deben generar el MISMO genesis para
        que sus cadenas sean compatibles. Por eso:
        - timestamp = 0 (no usa time.time())
        - nonce = 0 (sin PoW)
        - difficulty = 1 (no requiere minado)
        """
        genesis_tx           = Transaction("COINBASE", "genesis_address", 0)
        genesis_tx.timestamp = 0

        merkle = MerkleTree([genesis_tx])

        header = BlockHeader(
            prev_hash='0' * 64,
            merkle_root=merkle.get_root(),
            timestamp=0,
            difficulty=1,
            nonce=0,
        )

        genesis = Block(header, [genesis_tx])
        self.chain.append(genesis)

        print(f"[GENESIS] Bloque génesis: {genesis.hash[:16]}...")

    # ──────────────────────────────────────────────────────────
    # Consultas
    # ──────────────────────────────────────────────────────────

    def get_latest_block(self) -> Block:
        """Retorna el último bloque de la cadena."""
        return self.chain[-1]

    def get_height(self) -> int:
        """Retorna la altura actual de la cadena (número de bloques)."""
        return len(self.chain)

    def get_block_by_hash(self, block_hash: str) -> Optional[Block]:
        """
        Busca un bloque por su hash.

        Args:
            block_hash: Hash del bloque a buscar.

        Returns:
            Bloque si se encuentra, None si no existe.
        """
        for block in self.chain:
            if block.hash == block_hash:
                return block
        return None

    def get_balance(self, address: str) -> float:
        """
        Calcula el balance de una dirección recorriendo toda la cadena.

        Modelo account (simplificado vs UTXO de Bitcoin):
        - Suma todas las TXs donde to_address == address
        - Resta todas las TXs donde from_address == address

        Args:
            address: Dirección a consultar.

        Returns:
            Balance confirmado (solo bloques minados, no mempool).
        """
        balance = 0.0
        for block in self.chain:
            for tx in block.transactions:
                if tx.to_address == address:
                    balance += tx.amount
                if tx.from_address == address and tx.from_address != "COINBASE":
                    balance -= tx.amount
        return balance

    def has_sufficient_balance(self, address: str, amount: float) -> bool:
        """Verifica si una dirección tiene fondos suficientes."""
        return self.get_balance(address) >= amount

    # ──────────────────────────────────────────────────────────
    # Mempool
    # ──────────────────────────────────────────────────────────

    def add_transaction_to_mempool(self, tx: Transaction) -> bool:
        """
        Agrega una transacción al mempool después de validar.

        Validaciones:
        1. Límite de mempool no excedido
        2. Firma válida
        3. No duplicada (mismo txid)
        4. Balance suficiente (TXs normales)

        Args:
            tx: Transacción a agregar.

        Returns:
            True si se agregó exitosamente.
        """
        if len(self.mempool) >= self.MAX_MEMPOOL_SIZE:
            print("[MEMPOOL] Rechazada: mempool lleno")
            return False

        if not tx.is_valid():
            print("[MEMPOOL] Rechazada: firma inválida")
            return False

        tx_hash = tx.hash()
        if any(t.hash() == tx_hash for t in self.mempool):
            print("[MEMPOOL] Rechazada: duplicada")
            return False

        if tx.from_address != "COINBASE":
            if not self.has_sufficient_balance(tx.from_address, tx.amount):
                print("[MEMPOOL] Rechazada: fondos insuficientes")
                return False

        self.mempool.append(tx)
        print(
            f"[MEMPOOL] TX agregada: {tx_hash[:16]}... "
            f"({tx.from_address[:8]}→{tx.to_address[:8]}, {tx.amount})"
        )
        return True

    def get_transactions_for_mining(self, max_count: int = None) -> List[Transaction]:
        """
        Selecciona TXs del mempool para incluir en el próximo bloque.
        Estrategia: FIFO (primero en llegar, primero en minarse).
        Bitcoin real: ordena por fee/byte.
        """
        if max_count is None:
            max_count = self.MAX_TXS_PER_BLOCK
        return self.mempool[:max_count]

    def remove_transactions(self, tx_hashes: List[str]):
        """
        Elimina TXs del mempool por sus hashes.
        Llamado después de minar o recibir un bloque externo.
        """
        self.mempool = [
            tx for tx in self.mempool
            if tx.hash() not in tx_hashes
        ]

    # ──────────────────────────────────────────────────────────
    # Minado
    # ──────────────────────────────────────────────────────────

    def mine_block(self, miner_address: str) -> Optional[Block]:
        """
        Mina un nuevo bloque (proceso completo).

        Proceso:
        1. Coinbase TX (recompensa para el minero)
        2. Seleccionar TXs del mempool
        3. Calcular Merkle root
        4. Crear header
        5. PoW — encontrar nonce  ← aquí se gasta el tiempo
        6. Crear bloque
        7. Validar y agregar a la cadena
        8. Limpiar mempool

        Args:
            miner_address: Dirección que recibe la recompensa.

        Returns:
            Bloque minado si exitoso, None si falla.
        """
        print(f"\n[MINING] Iniciando bloque #{len(self.chain)}...")

        coinbase           = Transaction("COINBASE", miner_address, self.BLOCK_REWARD)
        coinbase.timestamp = time.time()

        pending_txs = self.get_transactions_for_mining()
        block_txs   = [coinbase] + pending_txs

        print(
            f"[MINING] TXs: {len(block_txs)} "
            f"(1 coinbase + {len(pending_txs)} del mempool)"
        )

        merkle      = MerkleTree(block_txs)
        merkle_root = merkle.get_root()

        header = BlockHeader(
            prev_hash=self.get_latest_block().hash,
            merkle_root=merkle_root,
            timestamp=time.time(),
            difficulty=self.DIFFICULTY,
            nonce=0,
        )

        print(f"[MINING] Buscando nonce (difficulty={self.DIFFICULTY})...")
        pow_solver   = ProofOfWork(header, self.DIFFICULTY)
        header.nonce = pow_solver.mine()

        new_block = Block(header, block_txs)
        print(f"[MINING] Bloque encontrado: {new_block.hash[:16]}...")

        if self.add_block(new_block):
            tx_hashes = [tx.hash() for tx in pending_txs]
            self.remove_transactions(tx_hashes)
            print(
                f"[MINING] Agregado. Altura: {len(self.chain)}, "
                f"Mempool: {len(self.mempool)} TXs\n"
            )
            return new_block
        else:
            print("[MINING] ERROR: bloque inválido, no se agregó\n")
            return None

    # ──────────────────────────────────────────────────────────
    # Validación y adición de bloques
    # ──────────────────────────────────────────────────────────

    def add_block(self, block: Block) -> bool:
        """
        Agrega un bloque a la cadena después de validarlo.
        Si es válido, limpia del mempool las TXs que confirma.

        Args:
            block: Bloque a agregar.

        Returns:
            True si se agregó exitosamente.
        """
        if not self.validate_block(block):
            return False

        self.chain.append(block)

        # Limpiar del mempool las TXs que este bloque confirma
        confirmed_hashes = [tx.hash() for tx in block.transactions]
        self.remove_transactions(confirmed_hashes)

        return True

    def validate_block(self, block: Block) -> bool:
        """
        Valida un bloque individual contra el estado actual de la cadena.

        Validaciones:
        1. PoW válido (hash cumple difficulty)
        2. Merkle root correcto
        3. prev_hash conecta con el último bloque
        4. Timestamp razonable (no más de 2h en el futuro)
        5. Primera TX es coinbase
        6. Todas las TXs son válidas
        """
        if not block.validate_pow():
            print("[VALIDATION] Bloque inválido: PoW incorrecto")
            return False

        if not block.validate_merkle_root():
            print("[VALIDATION] Bloque inválido: Merkle root incorrecto")
            return False

        if block.header.prev_hash != self.get_latest_block().hash:
            print("[VALIDATION] Bloque inválido: prev_hash no conecta")
            return False

        if block.header.timestamp > time.time() + 7200:
            print("[VALIDATION] Bloque inválido: timestamp futuro")
            return False

        if block.transactions and block.transactions[0].from_address != "COINBASE":
            print("[VALIDATION] Bloque inválido: primera TX no es coinbase")
            return False

        if not block.validate_transactions():
            print("[VALIDATION] Bloque inválido: TX inválida")
            return False

        return True

    def validate_chain(self, chain: List[Block]) -> bool:
        """
        Valida una cadena completa.

        Verifica:
        1. Genesis coincide con el nuestro
        2. Todos los bloques están correctamente enlazados
        3. Cada bloque tiene PoW, Merkle root y TXs válidos

        Args:
            chain: Cadena a validar.

        Returns:
            True si la cadena es válida.
        """
        if not chain:
            return False

        if chain[0].hash != self.chain[0].hash:
            print("[VALIDATION] Cadena inválida: genesis diferente")
            return False

        for i in range(1, len(chain)):
            current  = chain[i]
            previous = chain[i - 1]

            if current.header.prev_hash != previous.hash:
                print(f"[VALIDATION] Bloque {i}: prev_hash no enlaza")
                return False

            if not current.validate_pow():
                print(f"[VALIDATION] Bloque {i}: PoW inválido")
                return False

            if not current.validate_merkle_root():
                print(f"[VALIDATION] Bloque {i}: Merkle inválido")
                return False

            if not current.validate_transactions():
                print(f"[VALIDATION] Bloque {i}: TXs inválidas")
                return False

        return True

    # ──────────────────────────────────────────────────────────
    # Longest chain rule (Sprint 4.2)
    # ──────────────────────────────────────────────────────────

    def replace_chain(self, new_chain: List[Block]) -> bool:
        """
        Implementa la longest chain rule (regla de la cadena más larga).

        Reemplaza la cadena actual si la nueva es:
        1. Más larga (más bloques)
        2. Válida (genesis, enlaces, PoW, Merkle, TXs)

        Cuando se reemplaza la cadena:
        - Las TXs de los bloques huérfanos vuelven al mempool
          (excepto coinbase) para ser reconfirmadas
        - Las TXs ya confirmadas en la nueva cadena se eliminan
          del mempool

        En Bitcoin real: se usa trabajo acumulado (suma de difficulty),
        no número de bloques. Como nuestra difficulty es fija, ambas
        métricas son equivalentes.

        Args:
            new_chain: Cadena candidata a reemplazar la actual.

        Returns:
            True si la cadena fue reemplazada.
        """
        # La nueva cadena debe ser más larga
        if len(new_chain) <= len(self.chain):
            print(
                f"[CHAIN] Cadena rechazada: "
                f"nueva ({len(new_chain)}) <= actual ({len(self.chain)})"
            )
            return False

        # La nueva cadena debe ser válida
        if not self.validate_chain(new_chain):
            print("[CHAIN] Cadena rechazada: inválida")
            return False

        # ── Resolver fork: recuperar TXs huérfanas ────────────
        # Encontrar desde qué bloque divergen las cadenas
        fork_point = self._find_fork_point(new_chain)

        # TXs en bloques huérfanos (los que perdemos al reemplazar)
        orphaned_txs = []
        for block in self.chain[fork_point:]:
            for tx in block.transactions:
                if not tx.is_coinbase():
                    orphaned_txs.append(tx)

        # TXs ya confirmadas en la nueva cadena
        confirmed_in_new = set()
        for block in new_chain[fork_point:]:
            for tx in block.transactions:
                confirmed_in_new.add(tx.hash())

        # Reemplazar cadena
        old_height = len(self.chain)
        self.chain = new_chain

        # Devolver TXs huérfanas al mempool (si no están ya confirmadas)
        recovered = 0
        for tx in orphaned_txs:
            if tx.hash() not in confirmed_in_new:
                if self.add_transaction_to_mempool(tx):
                    recovered += 1

        # Limpiar del mempool las TXs ya confirmadas en la nueva cadena
        self.remove_transactions(list(confirmed_in_new))

        print(
            f"[CHAIN] Cadena reemplazada: "
            f"{old_height} → {len(self.chain)} bloques "
            f"(fork en bloque {fork_point}, "
            f"{len(orphaned_txs)} TXs huérfanas, "
            f"{recovered} devueltas al mempool)"
        )
        return True

    def _find_fork_point(self, other_chain: List[Block]) -> int:
        """
        Encuentra el índice donde dos cadenas divergen.

        Compara bloque por bloque hasta encontrar el primero diferente.
        El fork point es el primer índice donde los hashes no coinciden.

        Args:
            other_chain: Cadena con la que comparar.

        Returns:
            Índice del primer bloque divergente.
        """
        min_len = min(len(self.chain), len(other_chain))
        for i in range(min_len):
            if self.chain[i].hash != other_chain[i].hash:
                return i
        return min_len

    # ──────────────────────────────────────────────────────────
    # Serialización (para enviar por red)
    # ──────────────────────────────────────────────────────────

    def get_chain_as_dicts(self) -> List[dict]:
        """
        Serializa la cadena completa a lista de diccionarios.
        Usada por el mensaje 'getblocks' para enviar la cadena por red.

        Returns:
            Lista de dicts, uno por bloque.
        """
        return [block.to_dict() for block in self.chain]

    @staticmethod
    def chain_from_dicts(data: List[dict]) -> List[Block]:
        """
        Deserializa una cadena desde lista de diccionarios.
        Usada al recibir una cadena de otro nodo.

        Args:
            data: Lista de dicts (de get_chain_as_dicts).

        Returns:
            Lista de bloques.
        """
        return [Block.from_dict(block_data) for block_data in data]

    # ──────────────────────────────────────────────────────────
    # Utilidades
    # ──────────────────────────────────────────────────────────

    def __repr__(self):
        return (
            f"Blockchain("
            f"height={len(self.chain)}, "
            f"mempool={len(self.mempool)})"
        )
