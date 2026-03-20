"""
Proof of Work (PoW) — Minado
Encuentra un nonce que haga que el hash del bloque cumpla con la difficulty

Sprint 4.3:
- mine() acepta stop_event (threading.Event) para cancelación limpia
- Permite interrumpir el minado cuando llega un bloque externo

En Bitcoin:
- Difficulty ajustable (cada 2016 bloques ~2 semanas)
- Objetivo: 1 bloque cada ~10 minutos
- Actualmente: ~19 ceros al inicio del hash
"""

import time
import threading
from typing import Optional


class ProofOfWork:
    """
    Sistema de Proof of Work.

    Objetivo: encontrar un nonce tal que:
        SHA256d(block_header) empiece con X ceros

    Difficulty 3 → ~4,000 intentos   (~0.5s)
    Difficulty 4 → ~65,000 intentos  (~5-15s)
    Difficulty 5 → ~1,000,000 intentos (~60s)

    Cancelación:
    mine() acepta un threading.Event opcional. Si el evento se activa
    durante el minado, mine() retorna None inmediatamente.
    Esto permite que el event loop de asyncio cancele el minado
    cuando llega un bloque externo válido.
    """

    def __init__(self, block_header, difficulty: int = 5):
        """
        Args:
            block_header: Objeto BlockHeader a minar.
            difficulty:   Número de ceros requeridos al inicio del hash.
        """
        self.header     = block_header
        self.difficulty = difficulty
        self.target     = '0' * difficulty

    def mine(self, stop_event: Optional[threading.Event] = None) -> Optional[int]:
        """
        Encuentra el nonce que satisface la difficulty.

        Proceso:
        1. Probar nonce = 0, 1, 2, 3, ...
        2. Para cada nonce: calcular hash del header
        3. Si hash empieza con target ceros → retornar nonce
        4. Si stop_event está activo → retornar None (cancelado)
        5. Si no → incrementar nonce y repetir

        Args:
            stop_event: threading.Event opcional. Si se activa durante
                        el minado, la función retorna None limpiamente.
                        Si es None, mina sin posibilidad de cancelación.

        Returns:
            Nonce válido si tuvo éxito.
            None si fue cancelado via stop_event.
        """
        nonce      = 0
        start_time = time.time()

        print(f"[POW] Iniciando (difficulty={self.difficulty}, target='{self.target}')...")

        while True:
            # Verificar cancelación cada iteración
            if stop_event is not None and stop_event.is_set():
                elapsed = time.time() - start_time
                print(
                    f"[POW] Cancelado tras {nonce:,} intentos "
                    f"({elapsed:.2f}s)"
                )
                return None

            self.header.nonce = nonce
            block_hash        = self.header.hash()

            if block_hash.startswith(self.target):
                elapsed = time.time() - start_time
                rate    = nonce / elapsed if elapsed > 0 else 0
                print(
                    f"[POW] ¡Bloque minado!\n"
                    f"      Nonce:    {nonce:,}\n"
                    f"      Hash:     {block_hash}\n"
                    f"      Tiempo:   {elapsed:.2f}s\n"
                    f"      Intentos: {nonce + 1:,} ({rate:,.0f} h/s)"
                )
                return nonce

            nonce += 1

            # Log de progreso cada 10,000 intentos
            if nonce % 10000 == 0:
                elapsed = time.time() - start_time
                rate    = nonce / elapsed if elapsed > 0 else 0
                print(f"[POW] {nonce:,} intentos ({rate:,.0f} h/s)...")

    def validate(self, nonce: int) -> bool:
        """
        Valida que un nonce produce un hash válido.
        Usado para verificar bloques recibidos de otros nodos.

        Args:
            nonce: Nonce a validar.

        Returns:
            True si el hash cumple la difficulty.
        """
        self.header.nonce = nonce
        return self.header.hash().startswith(self.target)

    def __repr__(self):
        return f"ProofOfWork(difficulty={self.difficulty}, target='{self.target}')"
