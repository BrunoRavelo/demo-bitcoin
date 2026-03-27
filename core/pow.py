"""
Proof of Work — Sprint 9.2

Usa comparación numérica de 256 bits (idéntico a Bitcoin):
    int(hash, 16) < target

En lugar del sistema anterior de contar ceros:
    hash.startswith('0' * difficulty)

Ventaja del target numérico:
    - Ajuste continuo y granular (no en saltos discretos)
    - Permite acercarse exactamente al tiempo objetivo
    - Comportamiento idéntico al protocolo real de Bitcoin
"""

import time
import threading
from typing import Optional


class ProofOfWork:
    """
    Encuentra el nonce que hace que int(header.hash(), 16) < target.

    El proceso es idéntico a Bitcoin:
    1. Incrementar nonce desde 0
    2. Calcular hash del header
    3. Interpretar hash como número de 256 bits
    4. Si es menor que target → nonce válido encontrado
    5. Si no → incrementar nonce y repetir

    El target determina la dificultad:
        target alto → muchos hashes válidos → fácil
        target bajo → pocos hashes válidos  → difícil
    """

    def __init__(self, header, target: int):
        """
        Args:
            header: BlockHeader con método hash()
            target: Número de 256 bits. Hash válido si int(hash,16) < target
        """
        self.header = header
        self.target = target

    def mine(
        self,
        stop_event        = None,
        progress_callback = None,
    ) -> Optional[int]:
        """
        Busca el nonce válido incrementando desde 0.

        Args:
            stop_event:        threading.Event para cancelar el minado.
                               Si se activa, retorna None limpiamente.
            progress_callback: Callable(attempts: int, hashrate: float).
                               Se invoca cada 10,000 intentos para que
                               el dashboard muestre progreso real.

        Returns:
            Nonce válido, o None si fue cancelado.
        """
        if stop_event is not None and stop_event.is_set():
            return None

        nonce      = 0
        start_time = time.time()
        log_every  = 10_000

        while True:
            if stop_event is not None and nonce % 1000 == 0:
                if stop_event.is_set():
                    elapsed = time.time() - start_time
                    print(
                        f"[POW] Cancelado tras {nonce:,} intentos "
                        f"({elapsed:.2f}s)\n"
                    )
                    return None

            self.header.nonce = nonce
            hash_int = int(self.header.hash(), 16)

            if hash_int < self.target:
                elapsed   = time.time() - start_time
                hashrate  = nonce / elapsed if elapsed > 0 else 0
                print(
                    f"[POW] ¡Bloque minado!\n"
                    f"      Nonce:    {nonce:,}\n"
                    f"      Hash:     {self.header.hash()}\n"
                    f"      Tiempo:   {elapsed:.2f}s\n"
                    f"      Intentos: {nonce:,} ({hashrate:,.0f} h/s)\n"
                )
                return nonce

            # Reporte de progreso cada 10,000 intentos
            if nonce > 0 and nonce % log_every == 0:
                elapsed  = time.time() - start_time
                hashrate = nonce / elapsed if elapsed > 0 else 0
                print(f"[POW] {nonce:,} intentos ({hashrate:,.0f} h/s)...")
                if progress_callback is not None:
                    progress_callback(nonce, hashrate)

            nonce += 1

    def validate(self, nonce: int) -> bool:
        """
        Verifica que un nonce produce un hash válido.

        Args:
            nonce: Nonce a verificar

        Returns:
            True si int(hash, 16) < target
        """
        self.header.nonce = nonce
        return int(self.header.hash(), 16) < self.target
