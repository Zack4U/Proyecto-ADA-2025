import time
import numpy as np
import pandas as pd

from src.models.base.sia import SIA
from src.models.core.solution import Solution
from src.funcs.base import emd_efecto, ABECEDARY
from src.funcs.format import fmt_biparticion

from src.middlewares.profile import profile

from src.constants.models import (GEOMETRIC_LABEL, GEOMETRIC_ANALYSIS_TAG)
from src.constants.base import (TYPE_TAG)

class GeometricSIA(SIA):
    def __init__(self, gestor):
        super().__init__(gestor)
        self.tensores = {}
        self.tabla_transiciones = {}

    @profile(context={TYPE_TAG: GEOMETRIC_ANALYSIS_TAG})
    def aplicar_estrategia(self, condicion: str, alcance: str, mecanismo: str) -> Solution:
        print("Iniciando SIA Geométrica...")
        tiempo_inicio = time.time()
        self.sia_preparar_subsistema(condicion, alcance, mecanismo)
        print(f"Tiempo de preparación del subsistema: {time.time() - tiempo_inicio:.8f} segundos")

        tiempo_inicio = time.time()
        print("Descomponiendo en tensores...")
        self.tensores = self.descomponer_en_tensores()
        print(f"Tiempo de descomposición: {time.time() - tiempo_inicio:.8f} segundos")

        tiempo_inicio = time.time()
        print("Calculando tabla de costos...")
        self.tabla_transiciones = self.calcular_tabla_costos()
        print(f"Tiempo de cálculo de tabla de costos: {time.time() - tiempo_inicio:.8f} segundos")

        # tiempo_inicio = time.time()
        # print("Guardando tablas de costos en Excel...")
        # self.guardar_tabla_costos_excel() 
        # print(f"Tiempo de guardado de tablas: {time.time() - tiempo_inicio:.8f} segundos")
        
        tiempo_inicio = time.time()
        print("Identificando biparticiones candidatas...")
        candidatos = self.identificar_biparticiones_candidatas()
        print(f"Tiempo de identificación de candidatas: {time.time() - tiempo_inicio:.8f} segundos")

        tiempo_inicio = time.time()
        print("Evaluando biparticiones...")
        mejor, mejor_dist, mejor_cost = self.evaluar_biparticiones(candidatos)
        print(f"Tiempo de evaluación de biparticiones: {time.time() - tiempo_inicio:.8f} segundos")
        
        print("Obteniendo particion final...")
        print(f"Mejor partición: {mejor} con costo {mejor_cost}")
        

        return Solution(
            estrategia=GEOMETRIC_LABEL,
            perdida=mejor_cost,
            distribucion_subsistema=self.sia_dists_marginales,
            distribucion_particion=mejor_dist,
            tiempo_total=time.time() - self.sia_tiempo_inicio,
            particion=fmt_biparticion(
                [tuple(mejor[0]), tuple(mejor[2])],
                [tuple(mejor[1]), tuple(mejor[3])],
            ),
        )

    def descomponer_en_tensores(self):
        tensores = {}
        for i, ncubo in enumerate(self.sia_subsistema.ncubos):
            # print(f"Tensor {i} (forma {ncubo.data.shape}):\n{ncubo.data}\n")
            tensores[i] = ncubo.data.flatten()
        return tensores
    
    def hamming_distance(self, s1, s2):
        """Calcula la distancia de Hamming entre dos estados enteros."""
        return bin(s1 ^ s2).count('1')

    def bits_to_int(self, bits):
        """Convierte una lista de bits (orden big endian) a entero."""
        return int(''.join(str(b) for b in bits), 2)

    def calcular_tabla_costos(self):
        if not self.tensores:
            return {}

        first_key = next(iter(self.tensores))
        num_states = len(self.tensores[first_key])
        num_bits = (num_states - 1).bit_length()
        source_state = self.bits_to_int(self.sia_subsistema.estado_inicial)
        

        tablas = {}
        for var, tensor in self.tensores.items():
            fila = np.zeros(num_states)
            for d in range(1, num_bits + 1):
                for j in range(num_states):
                    # print(f"Evaluando estado {j} con distancia {d} desde {source_state}")
                    if self.hamming_distance(source_state, j) == d:
                        gamma = 2**-d
                        delta = abs(tensor[source_state] - tensor[j])
                        suma_intermedia = sum(
                            fila[source_state ^ (1 << k)]
                            for k in range(num_bits)
                            if self.hamming_distance(source_state ^ (1 << k), j) == d - 1 and (source_state ^ (1 << k)) < num_states
                        )
                        fila[j] = gamma * (delta + suma_intermedia)
            tablas[var] = fila
        return tablas

    def guardar_tabla_costos_excel(self):
        if not self.tabla_transiciones:
            return

        output_dir = self.sia_gestor.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        file_path = output_dir / "costos_desde_estado_inicial.xlsx"

        first_key = next(iter(self.tabla_transiciones))
        num_states = len(self.tabla_transiciones[first_key])
        num_bits = (num_states - 1).bit_length()
        estado_inicial = self.bits_to_int(self.sia_subsistema.estado_inicial)

        columnas = []
        for k in self.tabla_transiciones:
            if hasattr(self, 'sia_condicion_nodos_nombres') and k < len(self.sia_condicion_nodos_nombres):
                columnas.append(self.sia_condicion_nodos_nombres[k])
            elif k < len(ABECEDARY):
                columnas.append(ABECEDARY[k])
            else:
                columnas.append(str(k))

        datos = []
        filas = []
        for j in range(num_states):
            if j == estado_inicial:
                continue
            fila = [self.tabla_transiciones[k][j] for k in self.tabla_transiciones]
            datos.append(fila)
            filas.append(f"{format(estado_inicial, f'0{num_bits}b')} > {format(j, f'0{num_bits}b')}")

        df = pd.DataFrame(datos, columns=columnas, index=filas)

        with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='CostosTransiciones')
            ws = writer.sheets['CostosTransiciones']
            ws.conditional_format(1, 1, len(df), len(df.columns), {
                'type': '2_color_scale', 'min_color': "#FFFFFF", 'max_color': "#F8696B"
            })
            
        print(f"Tabla de costos guardada en {file_path}")
    
    def identificar_biparticiones_candidatas(self):
        if not self.tabla_transiciones:
            return []

        first_key = next(iter(self.tabla_transiciones))
        num_states = len(self.tabla_transiciones[first_key])
        num_bits = (num_states - 1).bit_length()
        estado_inicial = self.bits_to_int(self.sia_subsistema.estado_inicial)
        # max_ceros = 0

        candidatas = []
        # Para cada estado destino (distinto al inicial)
        for j in range(num_states):
            if j == estado_inicial:
                continue
            # Variables con costo 0 en la transición actual
            grupo = [k for k, fila in self.tabla_transiciones.items() if fila[j] == 0]
            if not grupo or len(grupo) == num_bits:
                continue  # Ignora grupos vacíos o el grupo total
            # if len(grupo) < max_ceros:
            #     continue
            # max_ceros = len(grupo)
            #print(f"Estado {j} ({format(j, f'0{num_bits}b')}): Grupo {grupo}")
            complemento = [k for k in range(num_bits) if k not in grupo]
            # Identifica mecanismos: variables que cambian entre estado_inicial y j
            bits_ini = format(estado_inicial, f'0{num_bits}b')
            bits_j = format(j, f'0{num_bits}b')
            mecanismo_grupo = [idx for idx, (b1, b2) in enumerate(zip(bits_ini, bits_j)) if b1 != b2]
            mecanismo_complemento = [idx for idx, (b1, b2) in enumerate(zip(bits_ini, bits_j)) if b1 == b2]
            # Solo considerar biparticiones no triviales
            if grupo and complemento:
                candidatas.append((grupo, complemento, mecanismo_grupo, mecanismo_complemento))
            # print(f"Estado {j} ({format(j, f'0{num_bits}b')}): Grupo {grupo}, Complemento {complemento}")
        # Elimina duplicados
        candidatas_unicas = []
        for c in candidatas:
            if (c[1], c[0]) not in candidatas_unicas and c not in candidatas_unicas:
                candidatas_unicas.append(c)
        print(f"Se encontraron {len(candidatas_unicas)} biparticiones candidatas.")
        return candidatas_unicas
        
    def evaluar_biparticiones(self, candidatos):
        mejor = None
        mejor_costo = float('inf')
        mejor_dist = None
        memoria_particiones = {}

        for A, B, a, b in candidatos:
            # Memoización para evitar cálculos repetidos
            clave = (tuple(sorted(A)), tuple(sorted(B)))
            if clave in memoria_particiones:
                costo, dist = memoria_particiones[clave]
            else:
                costo, dist = self.evaluar_coste_biparticion(A, B, a, b)
                memoria_particiones[clave] = (costo, dist)

            if costo < mejor_costo:
                mejor = (A, B, a, b)
                mejor_costo = costo
                mejor_dist = dist
            
            # print(f"Evaluando bipartición {A} | {a} con costo {costo:.8f}")

        # Puedes devolver también la distribución marginal de la mejor partición si lo necesitas
        return mejor, mejor_dist, mejor_costo
    
    def evaluar_coste_biparticion(self, futuro_A, futuro_B, presente_a, presente_b):
        if not hasattr(self.sia_subsistema, 'bipartir'):
            return float('inf')
        if len(self.tensores) == 1 and futuro_A and not futuro_B:
            return 0.0

        # print(f"Evaluando partición: A={presente_A} a={presente_a}")
        particion = self.sia_subsistema.bipartir(np.array(futuro_A), np.array(presente_a))
        dist = particion.distribucion_marginal()

        if not hasattr(self, 'sia_dists_marginales') or self.sia_dists_marginales is None:
            return float('inf')

        costo = emd_efecto(dist, self.sia_dists_marginales)
        return costo, dist