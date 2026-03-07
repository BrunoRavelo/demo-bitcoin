"""
Blockchain - Cadena de bloques enlazados
Incluye genesis, mempool, minado y validación
"""

import time
from typing import List, Optional
from core.block import Block, BlockHeader
from core.transaction import Transaction
from core.merkle import MerkleTree
from core.pow import ProofOfWork


class Blockchain:
    """
    Cadena de bloques completa
    
    Responsabilidades:
    - Mantener cadena de bloques
    - Gestionar mempool (TXs pendientes)
    - Minar nuevos bloques
    - Validar bloques y cadenas
    - Calcular balances
    
    Características:
    - Genesis block automático
    - Difficulty fija (4 ceros)
    - Block reward fijo (50 coins)
    - Máximo 10 TXs por bloque
    """
    
    def __init__(self):
        """Inicializa blockchain con genesis block"""
        self.chain: List[Block] = []
        self.mempool: List[Transaction] = []
        
        # Constantes (como Bitcoin pero simplificadas)
        self.BLOCK_REWARD = 50      # Recompensa por minar
        self.DIFFICULTY = 4         # Número de ceros en hash
        self.MAX_MEMPOOL_SIZE = 1000
        self.MAX_TXS_PER_BLOCK = 10
        
        # Crear genesis block
        self.create_genesis_block()
    
    def create_genesis_block(self):
        """
        Crea el bloque génesis (primer bloque)
        
        Características:
        - prev_hash: ceros (no hay bloque anterior)
        - timestamp: 0 (época Unix)
        - nonce: 0 (sin minado)
        - difficulty: 1 (fácil)
        - Solo contiene coinbase TX de valor 0
        
        Nota: Hardcodeado para que todos los nodos 
        tengan el MISMO genesis
        """
        # Coinbase TX del genesis
        genesis_tx = Transaction("COINBASE", "genesis_address", 0)
        genesis_tx.timestamp = 0
        
        # Calcular Merkle root
        merkle = MerkleTree([genesis_tx])
        
        # Crear header (sin minado)
        header = BlockHeader(
            prev_hash='0' * 64,
            merkle_root=merkle.get_root(),
            timestamp=0,
            difficulty=1,  # Baja difficulty (no requiere minado)
            nonce=0
        )
        
        # Crear bloque genesis
        genesis = Block(header, [genesis_tx])
        
        # Agregar a la cadena
        self.chain.append(genesis)
        
        print(f"[GENESIS] Bloque génesis creado: {genesis.hash[:16]}...")
    
    def get_latest_block(self) -> Block:
        """
        Retorna el último bloque de la cadena
        
        Returns:
            Último bloque
        """
        return self.chain[-1]
    
    def add_transaction_to_mempool(self, tx: Transaction) -> bool:
        """
        Agrega transacción al mempool después de validar
        
        Validaciones:
        1. Límite de mempool no excedido
        2. Firma válida
        3. No duplicada (mismo hash)
        4. Balance suficiente (para TXs normales)
        
        Args:
            tx: Transacción a agregar
        
        Returns:
            True si se agregó exitosamente
        """
        # 1. Verificar límite
        if len(self.mempool) >= self.MAX_MEMPOOL_SIZE:
            print(f"[MEMPOOL] Rechazada: mempool lleno")
            return False
        
        # 2. Validar firma
        if not tx.is_valid():
            print(f"[MEMPOOL] Rechazada: firma inválida")
            return False
        
        # 3. Verificar duplicados
        tx_hash = tx.hash()
        if any(t.hash() == tx_hash for t in self.mempool):
            print(f"[MEMPOOL] Rechazada: duplicada")
            return False
        
        # 4. Verificar balance (solo para TXs normales)
        if tx.from_address != "COINBASE":
            if not self.has_sufficient_balance(tx.from_address, tx.amount):
                print(f"[MEMPOOL] Rechazada: fondos insuficientes")
                return False
        
        # Agregar a mempool
        self.mempool.append(tx)
        print(f"[MEMPOOL] TX agregada: {tx_hash[:16]}... ({tx.from_address[:8]}→{tx.to_address[:8]}, {tx.amount})")
        
        return True
    
    def get_transactions_for_mining(self, max_count: int = None) -> List[Transaction]:
        """
        Selecciona transacciones del mempool para minar
        
        Bitcoin: ordena por fee/byte (más rentables primero)
        Nuestro demo: FIFO (primeras en llegar)
        
        Args:
            max_count: Máximo de TXs a retornar (default: MAX_TXS_PER_BLOCK)
        
        Returns:
            Lista de transacciones para incluir en bloque
        """
        if max_count is None:
            max_count = self.MAX_TXS_PER_BLOCK
        
        return self.mempool[:max_count]
    
    def remove_transactions(self, tx_hashes: List[str]):
        """
        Elimina transacciones del mempool
        
        Usado después de minar para limpiar TXs ya confirmadas
        
        Args:
            tx_hashes: Lista de hashes de TXs a eliminar
        """
        self.mempool = [
            tx for tx in self.mempool 
            if tx.hash() not in tx_hashes
        ]
    
    def mine_block(self, miner_address: str) -> Optional[Block]:
        """
        Mina un nuevo bloque (proceso completo)
        
        Proceso:
        1. Crear coinbase TX (recompensa para minero)
        2. Seleccionar TXs del mempool
        3. Calcular Merkle root
        4. Crear header
        5. Encontrar nonce (PoW) ← AQUÍ SE GASTA TIEMPO
        6. Crear bloque
        7. Validar y agregar a cadena
        8. Limpiar mempool
        
        Args:
            miner_address: Dirección que recibirá la recompensa
        
        Returns:
            Bloque minado si exitoso, None si falla
        """
        print(f"\n[MINING] Iniciando minado de bloque #{len(self.chain)}...")
        
        # 1. Crear coinbase transaction
        coinbase = Transaction(
            from_address="COINBASE",
            to_address=miner_address,
            amount=self.BLOCK_REWARD
        )
        coinbase.timestamp = time.time()
        
        # 2. Seleccionar TXs del mempool
        pending_txs = self.get_transactions_for_mining()
        
        # Combinar: coinbase + TXs pendientes
        block_txs = [coinbase] + pending_txs
        
        print(f"[MINING] Transacciones en bloque: {len(block_txs)} (1 coinbase + {len(pending_txs)} del mempool)")
        
        # 3. Calcular Merkle root
        merkle = MerkleTree(block_txs)
        merkle_root = merkle.get_root()
        
        # 4. Crear header
        header = BlockHeader(
            prev_hash=self.get_latest_block().hash,
            merkle_root=merkle_root,
            timestamp=time.time(),
            difficulty=self.DIFFICULTY,
            nonce=0  # Se encontrará con PoW
        )
        
        # 5. Proof of Work (encontrar nonce)
        print(f"[MINING] Buscando nonce (difficulty={self.DIFFICULTY})...")
        pow_solver = ProofOfWork(header, self.DIFFICULTY)
        nonce = pow_solver.mine()
        header.nonce = nonce
        
        # 6. Crear bloque
        new_block = Block(header, block_txs)
        
        print(f"[MINING] Bloque minado: {new_block.hash[:16]}...")
        
        # 7. Validar y agregar
        if self.add_block(new_block):
            # 8. Limpiar mempool
            tx_hashes = [tx.hash() for tx in pending_txs]
            self.remove_transactions(tx_hashes)
            
            print(f"[MINING] Bloque agregado a la cadena. Altura: {len(self.chain)}")
            print(f"[MINING] Mempool limpiado: {len(tx_hashes)} TXs removidas\n")
            
            return new_block
        else:
            print(f"[MINING] ERROR: Bloque inválido, no se agregó\n")
            return None
    
    def add_block(self, block: Block) -> bool:
        """
        Agrega bloque a la cadena después de validar
        
        Args:
            block: Bloque a agregar
        
        Returns:
            True si se agregó exitosamente
        """
        if not self.validate_block(block):
            return False
        
        self.chain.append(block)
        return True
    
    def validate_block(self, block: Block) -> bool:
        """
        Valida un bloque individual
        
        Validaciones:
        1. PoW válido
        2. Merkle root correcto
        3. prev_hash conecta con último bloque
        4. Timestamp razonable
        5. Primera TX es coinbase
        6. Todas las TXs válidas
        
        Args:
            block: Bloque a validar
        
        Returns:
            True si el bloque es válido
        """
        # 1. PoW válido
        if not block.validate_pow():
            print(f"[VALIDATION] Bloque inválido: PoW incorrecto")
            return False
        
        # 2. Merkle root correcto
        if not block.validate_merkle_root():
            print(f"[VALIDATION] Bloque inválido: Merkle root incorrecto")
            return False
        
        # 3. prev_hash conecta con cadena
        if block.header.prev_hash != self.get_latest_block().hash:
            print(f"[VALIDATION] Bloque inválido: prev_hash no conecta")
            return False
        
        # 4. Timestamp razonable (no más de 2 horas en el futuro)
        if block.header.timestamp > time.time() + 7200:
            print(f"[VALIDATION] Bloque inválido: timestamp futuro")
            return False
        
        # 5. Primera TX debe ser coinbase
        if len(block.transactions) > 0:
            if block.transactions[0].from_address != "COINBASE":
                print(f"[VALIDATION] Bloque inválido: primera TX no es coinbase")
                return False
        
        # 6. Todas las TXs válidas
        if not block.validate_transactions():
            print(f"[VALIDATION] Bloque inválido: alguna TX inválida")
            return False
        
        return True
    
    def validate_chain(self, chain: List[Block]) -> bool:
        """
        Valida cadena completa
        
        Verifica:
        1. Genesis coincide
        2. Todos los bloques están enlazados correctamente
        3. Cada bloque es válido individualmente
        
        Args:
            chain: Cadena a validar
        
        Returns:
            True si la cadena es válida
        """
        # 1. Genesis debe coincidir
        if chain[0].hash != self.chain[0].hash:
            print(f"[VALIDATION] Cadena inválida: genesis diferente")
            return False
        
        # 2. Validar enlaces y bloques
        for i in range(1, len(chain)):
            current = chain[i]
            previous = chain[i - 1]
            
            # Verificar enlace
            if current.header.prev_hash != previous.hash:
                print(f"[VALIDATION] Cadena inválida: bloque {i} no enlaza con {i-1}")
                return False
            
            # Validar bloque (PoW, Merkle, TXs)
            if not current.validate_pow():
                print(f"[VALIDATION] Cadena inválida: bloque {i} tiene PoW inválido")
                return False
            
            if not current.validate_merkle_root():
                print(f"[VALIDATION] Cadena inválida: bloque {i} tiene Merkle inválido")
                return False
            
            if not current.validate_transactions():
                print(f"[VALIDATION] Cadena inválida: bloque {i} tiene TXs inválidas")
                return False
        
        return True
    
    def get_balance(self, address: str) -> float:
        """
        Calcula balance de una dirección
        
        Recorre toda la cadena sumando/restando transacciones
        
        Args:
            address: Dirección a consultar
        
        Returns:
            Balance actual
        """
        balance = 0
        
        for block in self.chain:
            for tx in block.transactions:
                # Recibió fondos
                if tx.to_address == address:
                    balance += tx.amount
                
                # Envió fondos (no coinbase)
                if tx.from_address == address and tx.from_address != "COINBASE":
                    balance -= tx.amount
        
        return balance
    
    def has_sufficient_balance(self, address: str, amount: float) -> bool:
        """
        Verifica si una dirección tiene fondos suficientes
        
        Args:
            address: Dirección a verificar
            amount: Cantidad requerida
        
        Returns:
            True si tiene fondos suficientes
        """
        return self.get_balance(address) >= amount
    
    def __repr__(self):
        return f"Blockchain(blocks={len(self.chain)}, mempool={len(self.mempool)})"