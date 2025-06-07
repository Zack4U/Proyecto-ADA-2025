from src.models.base.application import aplicacion

from src.main import iniciar
from src.main import matriz_generator
from src.main import iniciar_lote
    
def main():
    """Inicializar el aplicativo."""

    aplicacion.profiler_habilitado = True
    aplicacion.pagina_sample_network = "A"

    #iniciar()
    #matriz_generator()
    
    # ESTRATEGIA = PHI, GEO, GEOP
    # ALCANCE =  "12345678901234567890"
    iniciar_lote("11111111111111111110", "GEO")

if __name__ == "__main__":
    main()

    # 111111111111111111111  Primera secuencia
    # 111111111111111111110  Segunda secuencia
    # 011111111111111111111  Tercera secuencia
    # 011111111111111111110  Cuarta secuencia
    # 101010101010101010101  Quinta secuencia
    # 010101010101010101010  Sexta secuencia
    # 110110110110110110110  Séptima secuencia
