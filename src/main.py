from src.controllers.manager import Manager

from src.controllers.strategies.q_nodes import QNodes


def iniciar():
    """Punto de entrada principal"""
                    # ABCDEFGHIJKLMNOPQRST #
    estado_inicial = "10000000000000000000"
    condiciones =    "11111111111111111111"
    alcance =        "01111111111111111111"
    mecanismo =      "11111111111111111111"

    gestor_sistema = Manager(estado_inicial)

    ### Ejemplo de solución mediante módulo de fuerza bruta ###
    analizador_fb = QNodes(gestor_sistema)
    sia_uno = analizador_fb.aplicar_estrategia(
        condiciones,
        alcance,
        mecanismo,
    )
    print(sia_uno)

def matriz_generator():
                    # ABCDEFGHIJKLMNOPQRST #
    estado_inicial = "10000000000000000000"
    gestor_sistema = Manager(estado_inicial)
    gestor_sistema.generar_red(25)