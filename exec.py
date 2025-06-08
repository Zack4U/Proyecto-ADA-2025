from src.models.base.application import aplicacion

from src.main import iniciar
from src.main import matriz_generator
from src.main import iniciar_lote
from src.main import iniciar_uno

import signal
import sys
        
# Manejo de señales para abortar correctamente en caso de interrupción
def handler(signum, frame):
    print(f"Rank {MPI.COMM_WORLD.Get_rank()} received signal {signum}, aborting MPI.")
    MPI.COMM_WORLD.Abort()
    sys.exit(1)

signal.signal(signal.SIGINT, handler)    


def main():    
    aplicacion.profiler_habilitado = True
    aplicacion.pagina_sample_network = "A"
    
    
    # iniciar()
    # matriz_generator()

    # ESTRATEGIA = PHI, QNO, GEO, GEOMP, GEOCUDA
    # ALCANCE =  "12345678901234567890"
    # iniciar_lote("111111111111111111111", "GEOCUDA")
    # ALCANCE = "123456789012345678901"  "123456789012345678901"
    iniciar_uno("111111111111111111111", "110110110110110110110", "GEOCUDA")

if __name__ == "__main__":
    main()

    # 111111111111111111111  Primera secuencia
    # 111111111111111111110  Segunda secuencia
    # 011111111111111111111  Tercera secuencia
    # 011111111111111111110  Cuarta secuencia
    # 101010101010101010101  Quinta secuencia
    # 010101010101010101010  Sexta secuencia
    # 110110110110110110110  Séptima secuencia
