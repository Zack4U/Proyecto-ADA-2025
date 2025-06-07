from src.controllers.manager import Manager
from src.controllers.strategies.q_nodes import QNodes
from src.controllers.strategies.geometric import GeometricSIA
from src.controllers.strategies.geometric_p import GeometricSIAP
from src.controllers.strategies.phi import Phi

from src.models.base.application import aplicacion

import numpy as np
import pandas as pd
import os
import time
import psutil
import gc

def iniciar():
    """Punto de entrada principal"""
                    # 123456789012345678901234567890 #
    estado_inicial = "100000000000000"
    condiciones =    "111111111111111"
    alcance =        "110110110110110"
    mecanismo =      "110110110110110"

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
    
def iniciar_lote(alcance, strategy):
    
    strategy = strategy.upper()
    
    # """Punto de entrada principal"""
                     # 12345678901234567890 #
    num_bits = len(alcance)
                     
    estado_inicio   = "1" + "0" * ( num_bits - 1)
    condiciones     = "1" * num_bits
    
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
    
                    #  12345678901234567890 #
    #alcance         = "110"
    
    
    num_nodos = len(estado_inicio)
    variables = range(num_nodos)

    nombre_sistema = f"N{num_nodos}{aplicacion.pagina_sample_network}"
    archivo_excel = f"results/{strategy}/{nombre_sistema}.xlsx"
    
    #Crear directorio si no existe
    directorio = os.path.dirname(archivo_excel)
    if not os.path.exists(directorio):
        os.makedirs(directorio)
    
    col_particion = "Partición"
    col_perdida = "Pérdida"
    col_tiempo = "Tiempo ejecución"

    # Si el archivo abrirlo
    if os.path.exists(archivo_excel):
        # Cargar el DataFrame existente
        df_existente = pd.read_excel(archivo_excel, engine="openpyxl")
    else: 
        df_existente = pd.DataFrame(columns=[col_particion, col_perdida, col_tiempo])

    pruebas = []
    i = 0

    for presente in generar_subarreglos(variables):
        # Para vista binaria
        presente = set(presente)
        bits_mecanismo = "".join(["1" if i in presente else "0" for i in variables])
        pruebas.append(bits_mecanismo)

    filas_nuevas = []
    
    
    for mecanismo in pruebas:
        i += 1
        print(i)
        print(f"{alcance=} {mecanismo=}")
        
        config_sistema = Manager(estado_inicial=estado_inicio)
        
        if strategy == "PHI":
            analizador = Phi(config_sistema)
        elif strategy == "QNO":
            analizador = QNodes(config_sistema)
        elif strategy == "GEO":
            analizador = GeometricSIA(config_sistema)
        elif strategy == "GEOP":
            analizador = GeometricSIAP(config_sistema)
        else:
            raise ValueError(f"Estrategia desconocida: {strategy}")
        
        sia_dos = analizador.aplicar_estrategia(condiciones, alcance, mecanismo)

        lineas = sia_dos.particion.split("\n")
        particion_str = "\n".join(lineas)

        fila = [particion_str, round(sia_dos.perdida, 4), sia_dos.tiempo_ejecucion]
        filas_nuevas.append(fila)

    # Al final, concatena todas las filas nuevas y guarda el Excel una sola vez
    df_nuevas = pd.DataFrame(filas_nuevas, columns=[col_particion, col_perdida, col_tiempo])
    df_existente = pd.concat([df_existente, df_nuevas], ignore_index=True)
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