from src.models.base.application import aplicacion

from src.main import iniciar
from src.main import matriz_generator
from src.main import iniciar_lote


def main():
    """Inicializar el aplicativo."""

    aplicacion.profiler_habilitado = True
    aplicacion.pagina_sample_network = "A"

    iniciar()
    #iniciar_lote()
    #matriz_generator()


if __name__ == "__main__":
    main()
