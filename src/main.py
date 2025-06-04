from src.controllers.manager import Manager
from src.controllers.strategies.q_nodes import QNodes
from src.controllers.strategies.geometric import GeometricSIA
from src.controllers.strategies.geometric_p import GeometricSIAP
from src.controllers.strategies.phi import Phi

def iniciar():
    """Punto de entrada principal"""
                    # 123456789012345678901234567890 #
    estado_inicial = "00000"
    condiciones =    "11111"
    alcance =        "11111"
    mecanismo =      "11111"

    gestor_sistema = Manager(estado_inicial)

    ### Ejemplo de solución mediante módulo de fuerza bruta ###
    analizador_fb = GeometricSIA(gestor_sistema)
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
    gestor_sistema.generar_red(24)
    
def iniciar_lote():
    
    # """Punto de entrada principal"""
                     # ABCDEFGHIJKLMNOPQRST #
    estado_inicio   = "100000000000000" # Estado inicial del sistema
    condiciones     = "111111111111111"  # Sistema candidato
    
    # Para la red de 21 Nodos:
    # ABCDEFGHIJKLMNOPQRST #
    # 100000000000000000000  Estado inicial
    # 111111111111111111111  Sistema candidato

    # 111111111111111111111  Primera secuencia
    # 111111111111111111110  Segunda secuencia
    # 011111111111111111111  Tercera secuencia
    # 011111111111111111110  Cuarta secuencia
    # 101010101010101010101  Quinta secuencia
    # 010101010101010101010  Sexta secuencia
    # 110110110110110110110  Séptima secuencia


    # último subconjunto
    # 011111100111111  Futuro
    # 011111111111111  Presente
    
                    #  ABCDEFGHIJKLMNOPQRSTU #
    alcance         = "110110110110110" # Futuro
    
    
    num_nodos = len(estado_inicio)
    variables = range(num_nodos)

    config_sistema = Manager(estado_inicial=estado_inicio)

    archivo_excel = "Datos_N15A.xlsx"
    col_particion = "Partición"
    col_perdida = "Pérdida"
    col_tiempo = "Tiempo ejecución"

    try:
        df_existente = pd.read_excel(archivo_excel)
    except FileNotFoundError:
        df_existente = pd.DataFrame(columns=[col_particion, col_perdida, col_tiempo])

    pruebas = []
    i = 42

    for presente in generar_subarreglos(variables):
        # Para vista binaria
        presente = set(presente)
        bits_mecanismo = "".join(["1" if i in presente else "0" for i in variables])
        pruebas.append(bits_mecanismo)

    for mecanismo in pruebas:
        i += 1
        print(i)
        print(f"{alcance=} {mecanismo=}")
        analizador_Q = QNodes(config_sistema)
        sia_dos = analizador_Q.aplicar_estrategia(condiciones, alcance, mecanismo)
        print("Partición")
        print(sia_dos.particion)
        print("Perdida: ")
        print(sia_dos.perdida)
        print("Tiempo de ejecución: ")
        print(sia_dos.tiempo_ejecucion)

        lineas = sia_dos.particion.split("\n")

        fila1 = pd.DataFrame(
            [[lineas[0], sia_dos.perdida, sia_dos.tiempo_ejecucion]],
            columns=[col_particion, col_perdida, col_tiempo],
        )
        fila2 = pd.DataFrame(
            [[lineas[1], "", ""]],
            columns=[col_particion, col_perdida, col_tiempo],
        )

        # Concatenar los nuevos datos con los existentes
        df_existente = pd.concat([df_existente, fila1, fila2], ignore_index=True)

        # Guardar el DataFrame actualizado en el archivo Excel
        df_existente.to_excel(archivo_excel, index=False, engine="openpyxl")

    print(f"Datos guardados en {archivo_excel}")

def generar_subarreglos(arr):
    return [
        arr,  # 1. Todo el arreglo original
        arr[:-1],  # 2. Excluir el último elemento
        arr[1:],  # 3. Excluir el primer elemento
        arr[1:-1],  # 4. Excluir los extremos
        arr[::2],  # 5. Tomar los elementos en posiciones pares
        arr[1::2],  # 6. Tomar los elementos en posiciones impares
        np.delete(
            arr, np.arange(2, len(arr), 3)
        ),  # 7. Omitir los múltiplos de 3 (índices)
    ]