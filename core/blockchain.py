"""
Blockchain — Sprint 4.3
Agrega mine_block_cancellable() para minado asíncrono con cancelación
"""

import time
import threading
from typing import List, Optional
from core.block import Block, BlockHeader
from core.transaction import Transaction
from core.merkle import MerkleTree
from core.pow import ProofOfWork
from config import BLOCK_REWARD, DIFFICULTY, MAX_MEMPOOL_SIZE, MAX_TXS_PER_BLOCK


class Blockchain:
    """
    Cadena de bloques completa.

    Sprint 4.3: agrega mine_block_cancellable() que acepta un
    threading.Event para poder interrumpir el PoW cuando llega
    un bloque externo válido.
    """

    def __init__(self):
        self.chain:   List[Block]       = []
        self.mempool: List[Transaction] = []

        self.BLOCK_REWARD      = BLOCK_REWARD
        self.DIFFICULTY        = DIFFICULTY
        self.MAX_MEMPOOL_SIZE  = MAX_MEMPOOL_SIZE
        self.MAX_TXS_PER_BLOCK = MAX_TXS_PER_BLOCK

        self.create_genesis_block()

    # ──────────────────────────────────────────────────────────
    # Genesis
    # ──────────────────────────────────────────────────────────

    def create_genesis_block(self):
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
        return self.chain[-1]

    def get_height(self) -> int:
        return len(self.chain)

    def get_block_by_hash(self, block_hash: str) -> Optional[Block]:
        for block in self.chain:
            if block.hash == block_hash:
                return block
        return None

    def get_balance(self, address: str) -> float:
        balance = 0.0
        for block in self.chain:
            for tx in block.transactions:
                if tx.to_address == address:
                    balance += tx.amount
                if tx.from_address == address and tx.from_address != "COINBASE":
                    balance -= tx.amount
        return balance

    def has_sufficient_balance(self, address: str, amount: float) -> bool:
        return self.get_balance(address) >= amount

    # ──────────────────────────────────────────────────────────
    # Mempool
    # ──────────────────────────────────────────────────────────

    def add_transaction_to_mempool(self, tx: Transaction) -> bool:
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
        if max_count is None:
            max_count = self.MAX_TXS_PER_BLOCK
        return self.mempool[:max_count]

    def remove_transactions(self, tx_hashes: List[str]):
        self.mempool = [
            tx for tx in self.mempool
            if tx.hash() not in tx_hashes
        ]

    # ──────────────────────────────────────────────────────────
    # Minado
    # ──────────────────────────────────────────────────────────

    def mine_block(self, miner_address: str) -> Optional[Block]:
        """
        Mina un bloque de forma bloqueante (sin cancelación).
        Mantener para tests y uso directo.
        Para uso en red, usar mine_block_cancellable().
        """
        return self.mine_block_cancellable(miner_address, stop_event=None)

    def mine_block_cancellable(
        self,
        miner_address: str,
        stop_event: Optional[threading.Event] = None,
    ) -> Optional[Block]:
        """
        Mina un bloque con soporte de cancelación.

        Igual que mine_block() pero acepta un threading.Event.
        Si stop_event se activa durante el PoW, retorna None
        limpiamente sin agregar nada a la cadena.

        Usado por P2PNode.start_mining_loop() que corre este método
        en un thread del executor. Cuando llega un bloque externo
        válido, P2PNode activa stop_event para interrumpir el minado
        y reinicia con el nuevo prev_hash.

        Args:
            miner_address: Dirección que recibe la recompensa.
            stop_event:    threading.Event para cancelación.
                           None = minar sin posibilidad de cancelar.

        Returns:
            Bloque minado si tuvo éxito.
            None si fue cancelado o falló la validación.
        """
        print(f"\n[MINING] Iniciando bloque #{self.get_height()}...")

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

        # PoW con soporte de cancelación
        pow_solver = ProofOfWork(header, self.DIFFICULTY)
        nonce      = pow_solver.mine(stop_event=stop_event)

        # Si fue cancelado, nonce es None
        if nonce is None:
            print("[MINING] Minado cancelado — bloque externo recibido\n")
            return None

        header.nonce = nonce
        new_block    = Block(header, block_txs)

        print(f"[MINING] Bloque encontrado: {new_block.hash[:16]}...")

        if self.add_block(new_block):
            print(
                f"[MINING] Agregado. Altura: {self.get_height()}, "
                f"Mempool: {len(self.mempool)} TXs\n"
            )
            return new_block
        else:
            print("[MINING] ERROR: bloque inválido\n")
            return None

    # ──────────────────────────────────────────────────────────
    # Validación
    # ──────────────────────────────────────────────────────────

    def add_block(self, block: Block) -> bool:
        if not self.validate_block(block):
            return False
        self.chain.append(block)
        confirmed_hashes = [tx.hash() for tx in block.transactions]
        self.remove_transactions(confirmed_hashes)
        return True

    def validate_block(self, block: Block) -> bool:
        if not block.validate_pow():
            print("[VALIDATION] PoW incorrecto")
            return False
        if not block.validate_merkle_root():
            print("[VALIDATION] Merkle root incorrecto")
            return False
        if block.header.prev_hash != self.get_latest_block().hash:
            print("[VALIDATION] prev_hash no conecta")
            return False
        if block.header.timestamp > time.time() + 7200:
            print("[VALIDATION] Timestamp futuro")
            return False
        if block.transactions and block.transactions[0].from_address != "COINBASE":
            print("[VALIDATION] Primera TX no es coinbase")
            return False
        if not block.validate_transactions():
            print("[VALIDATION] TX inválida")
            return False
        return True

    def validate_chain(self, chain: List[Block]) -> bool:
        if not chain:
            return False
        if chain[0].hash != self.chain[0].hash:
            print("[VALIDATION] Genesis diferente")
            return False
        for i in range(1, len(chain)):
            current  = chain[i]
            previous = chain[i - 1]
            if current.header.prev_hash != previous.hash:
                print(f"[VALIDATION] Bloque {i}: enlace roto")
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
    # Longest chain rule
    # ──────────────────────────────────────────────────────────

    def replace_chain(self, new_chain: List[Block]) -> bool:
        if len(new_chain) <= len(self.chain):
            print(
                f"[CHAIN] Rechazada: nueva ({len(new_chain)}) "
                f"<= actual ({len(self.chain)})"
            )
            return False

        if not self.validate_chain(new_chain):
            print("[CHAIN] Rechazada: inválida")
            return False

        fork_point = self._find_fork_point(new_chain)

        orphaned_txs = []
        for block in self.chain[fork_point:]:
            for tx in block.transactions:
                if not tx.is_coinbase():
                    orphaned_txs.append(tx)

        confirmed_in_new = {
            tx.hash()
            for block in new_chain[fork_point:]
            for tx in block.transactions
        }

        old_height  = len(self.chain)
        self.chain  = new_chain

        recovered = 0
        for tx in orphaned_txs:
            if tx.hash() not in confirmed_in_new:
                if self.add_transaction_to_mempool(tx):
                    recovered += 1

        self.remove_transactions(list(confirmed_in_new))

        print(
            f"[CHAIN] Reemplazada: {old_height}→{len(self.chain)} bloques "
            f"(fork en {fork_point}, {recovered} TXs recuperadas)"
        )
        return True

    def _find_fork_point(self, other_chain: List[Block]) -> int:
        min_len = min(len(self.chain), len(other_chain))
        for i in range(min_len):
            if self.chain[i].hash != other_chain[i].hash:
                return i
        return min_len

    # ──────────────────────────────────────────────────────────
    # Serialización
    # ──────────────────────────────────────────────────────────

    def get_chain_as_dicts(self) -> List[dict]:
        return [block.to_dict() for block in self.chain]

    @staticmethod
    def chain_from_dicts(data: List[dict]) -> List[Block]:
        return [Block.from_dict(d) for d in data]

    def __repr__(self):
        return f"Blockchain(height={self.get_height()}, mempool={len(self.mempool)})"
