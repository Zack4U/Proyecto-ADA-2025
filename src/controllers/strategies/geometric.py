import time
import numpy as np
import pandas as pd
import math

from src.models.base.sia import SIA
from src.models.core.solution import Solution
from src.funcs.base import emd_efecto, ABECEDARY
from src.funcs.format import fmt_biparticion

from src.middlewares.profile import profile

from src.constants.models import (GEOMETRIC_LABEL, GEOMETRIC_ANALYSIS_TAG)
from src.constants.base import (TYPE_TAG)

MAX_VAR = -1                    # Número máximo de variables a considerar en la evaluación de biparticiones
ANALYSIS_PERCENTAGE = 0.5       # Porcentaje de costo máximo para considerar una variable como candidata extra

class GeometricSIA(SIA):
    def __init__(self, gestor):
        super().__init__(gestor)
        self.tensores = {}
        self.tabla_transiciones = {}

    # @profile(context={TYPE_TAG: GEOMETRIC_ANALYSIS_TAG})
    def aplicar_estrategia(self, condicion: str, alcance: str, mecanismo: str) -> Solution:
        #print("Iniciando SIA Geométrica...")
        #tiempo_inicio = time.time()
        self.sia_preparar_subsistema(condicion, alcance, mecanismo)
        #print(f"Tiempo de preparación del subsistema: {time.time() - tiempo_inicio:.8f} segundos")

        #tiempo_inicio = time.time()
        #print("Descomponiendo en tensores...")
        self.tensores = self.descomponer_en_tensores()
        #print(f"Tiempo de descomposición: {time.time() - tiempo_inicio:.8f} segundos")

        #tiempo_inicio = time.time()
        #print("Calculando tabla de costos...")
        self.tabla_transiciones = self.calcular_tabla_costos()
        #print(f"Tiempo de cálculo de tabla de costos: {time.time() - tiempo_inicio:.8f} segundos")

        # tiempo_inicio = time.time()
        # print("Guardando tablas de costos en Excel...")
        # self.guardar_tabla_costos_excel() 
        # print(f"Tiempo de guardado de tablas: {time.time() - tiempo_inicio:.8f} segundos")
        
        #tiempo_inicio = time.time()
        #print("Identificando biparticiones candidatas...")
        candidatos = self.identificar_biparticiones_candidatas()
        candidatos = self.identificar_biparticiones_candidatas_extra(candidatos)
        candidatos = self.filtrar_candidatos_por_tamano(candidatos) 
        #print(f"Tiempo de identificación de candidatas: {time.time() - tiempo_inicio:.8f} segundos")

        #tiempo_inicio = time.time()
        #print("Evaluando biparticiones...")
        mejor, mejor_dist, mejor_cost = self.evaluar_biparticiones(candidatos)
        #print(f"Tiempo de evaluación de biparticiones: {time.time() - tiempo_inicio:.8f} segundos")
        
        #print("Obteniendo particion final...")
        #print(f"Mejor partición: {mejor} con costo {mejor_cost}")
        

        return Solution(
            estrategia=GEOMETRIC_LABEL,
            perdida=mejor_cost,
            distribucion_subsistema=self.sia_dists_marginales,
            distribucion_particion=mejor_dist,
            tiempo_total=time.time() - self.sia_tiempo_inicio,
            particion=fmt_biparticion(
                [tuple(mejor[2]), tuple(mejor[0])],
                [tuple(mejor[3]), tuple(mejor[1])],
            ),
        )

    def descomponer_en_tensores(self):
        tensores = {}
        for ncubo in self.sia_subsistema.ncubos:
            # print(f"Tensor {i} (forma {ncubo.data.shape}):\n{ncubo.data}\n")
            tensores[ncubo.indice] = ncubo.data.flatten()
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

        tablas = {}
        # Variables en el mecanismo (presente)
        mecanismo = self.sia_subsistema.dims_ncubos
        num_bits = len(mecanismo)
        num_states = 2 ** num_bits

        # Estado fuente: solo las variables del mecanismo
        bits_fuente = [self.sia_subsistema.estado_inicial[i] for i in mecanismo]
        source_state = self.bits_to_int(bits_fuente)

        for var in self.sia_subsistema.indices_ncubos:  # Solo variables en el alcance (futuro)
            # print(f"Calculando tabla de costos para variable {var}...")
            tensor = self.tensores[var]
            fila = np.zeros(num_states)
            for d in range(1, num_bits + 1):
                for j in range(num_states):
                    if self.hamming_distance(source_state, j) == d:
                        gamma = 2 ** -d
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
            # if j == estado_inicial:
            #     continue
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
        mecanismo = self.sia_subsistema.dims_ncubos
        bits_fuente = [self.sia_subsistema.estado_inicial[i] for i in mecanismo]
        
        estado_inicial = self.bits_to_int(bits_fuente)

        candidatas = []
        #print(f"Identificando biparticiones candidatas para {len(self.sia_subsistema.indices_ncubos)} variables y {num_states} estados...")

        for var in self.sia_subsistema.indices_ncubos:
            fila = self.tabla_transiciones[var]
            min_costo = np.min([fila[j] for j in range(num_states) if j != estado_inicial])
            estados_min = [j for j in range(num_states) if j != estado_inicial and fila[j] == min_costo]
            
            #print(f"Variable {var} tiene mínimo costo {min_costo:.8f} en estados: {', '.join(format(e, f'0{num_bits}b') for e in estados_min)}")
            
            
            for estado in estados_min:
                grupo1 = [var]
                grupo2 = []
                estado_inverso = estado ^ ((1 << num_bits) - 1)
                # Para cada otra variable, ver en qué transición tiene su menor costo
                #print(f"Evaluando estado {estado} ({format(estado, f'0{num_bits}b')}) con mínimo costo {min_costo:.8f} en variable {var}")
                for otra_var in self.sia_subsistema.indices_ncubos:
                    if otra_var == var:
                        continue
                    fila_otra = self.tabla_transiciones[otra_var]
                    costo_estado = fila_otra[estado]
                    costo_inverso = fila_otra[estado_inverso]
                
                    if costo_estado < costo_inverso:
                        grupo1.append(otra_var)
                    elif costo_inverso < costo_estado:
                        grupo2.append(otra_var)
                    else:
                        grupo1.append(otra_var)

                bits_ini = format(estado_inicial, f'0{num_bits}b')
                bits_estado = format(estado, f'0{num_bits}b')
                bits_inverso = format(estado_inverso, f'0{num_bits}b')
                # print(f"Estado Inicial: {bits_ini}")
                # print(f"Estado Final  : {bits_estado}")
                # print(f"Estado Inverso: {bits_inverso}")

                # Mecanismo grupo 1: TODAS las variables que NO cambian en la transición estado_inicial -> estado
                mecanismo_grupo1 = [self.sia_subsistema.dims_ncubos[i] for i in range(num_bits) if bits_ini[i] == bits_estado[i]]
                # Mecanismo grupo 2: TODAS las variables que NO cambian en la transición estado_inicial -> estado_inverso
                mecanismo_grupo2 = [self.sia_subsistema.dims_ncubos[i] for i in range(num_bits) if bits_ini[i] == bits_inverso[i]]
                
                #print(f"Grupo 1: {grupo1} con mecanismos {mecanismo_grupo1}")
                #print(f"Grupo 2: {grupo2} con mecanismos {mecanismo_grupo2}")

                # Solo considerar biparticiones no triviales
                if grupo1 and not grupo2:
                    candidatas.append((grupo2, grupo1, mecanismo_grupo2, mecanismo_grupo1))
                else:
                    candidatas.append((grupo1, grupo2, mecanismo_grupo1, mecanismo_grupo2))
                    
                #print(f"Encontrada bipartición: {grupo1} | {grupo2} con mecanismos {mecanismo_grupo1} | {mecanismo_grupo2}")
            
        
        # Elimina duplicados (considerando que (A,B) y (B,A) son iguales)
        candidatas_unicas = []
        claves_vistas = set()
        for c in candidatas:
            grupoA, grupoB, mecA, mecB = map(frozenset, c)
            clave = (grupoA, grupoB, mecA, mecB)
            clave_inv = (grupoB, grupoA, mecB, mecA)
            if clave not in claves_vistas and clave_inv not in claves_vistas:
                candidatas_unicas.append(c)
                claves_vistas.add(clave)
                claves_vistas.add(clave_inv)
                #print(f"Encontrada bipartición única: {c}")

        #print(f"Se encontraron {len(candidatas_unicas)} biparticiones candidatas.")
        return candidatas_unicas
    
    def identificar_biparticiones_candidatas_extra(self, candidatos):
        if not self.tabla_transiciones:
            return candidatos

        first_key = next(iter(self.tabla_transiciones))
        num_states = len(self.tabla_transiciones[first_key])
        num_bits = (num_states - 1).bit_length()
        mecanismo = self.sia_subsistema.dims_ncubos
        bits_fuente = [self.sia_subsistema.estado_inicial[i] for i in mecanismo]
        
        estado_inicial = self.bits_to_int(bits_fuente)
        
        num_bits = len(mecanismo)
        estado_complementario = estado_inicial ^ ((1 << num_bits) - 1)
        
        # Buscar variables con costo mínimo en el estado complementario
        costos_complementarios = [self.tabla_transiciones[var][estado_complementario] for var in self.sia_subsistema.indices_ncubos]

        max_costo = max(costos_complementarios)
        umbral = ANALYSIS_PERCENTAGE * max_costo
        vars_min = [var for var, costo in zip(self.sia_subsistema.indices_ncubos, costos_complementarios) if costo < umbral]
        # print(f"Variables con costo mínimo {min_costo:.8f} en estado complementario {estado_complementario} ({format(estado_complementario, f'0{num_bits}b')}): {vars_min}")

        # print(vars_min)

        for var in vars_min:
            grupo1 = [var]
            grupo2 = [v for v in self.sia_subsistema.indices_ncubos if v != var]
            
            # print(f"Evaluando variable {var} con costo mínimo {min_costo:.8f} en estado complementario {estado_complementario} ({format(estado_complementario, f'0{num_bits}b')})")

            bits_ini = format(estado_inicial, f'0{num_bits}b')
            bits_comp = format(estado_complementario, f'0{num_bits}b')

            # Mecanismo grupo 1: TODAS las variables que NO cambian en la transición estado_inicial -> estado_inverso
            mecanismo_grupo1 = [self.sia_subsistema.dims_ncubos[i] for i in range(num_bits) if bits_ini[i] == bits_comp[i]]
            # Mecanismo grupo 2: TODAS las variables que NO cambian en la transición estado_inicial -> estado_inicial
            mecanismo_grupo2 = [self.sia_subsistema.dims_ncubos[i] for i in range(num_bits)]

            # Solo considerar biparticiones no triviales
            if grupo1 and not grupo2:
                candidatos.append((grupo2, grupo1, mecanismo_grupo2, mecanismo_grupo1))
            else:
                candidatos.append((grupo1, grupo2, mecanismo_grupo1, mecanismo_grupo2))
                
            # print(f"Biparticion extra agregada {candidatos[-1]}") 
            # print(f"Encontrada bipartición extra: {grupo1} | {grupo2} con mecanismos {mecanismo_grupo1} | {mecanismo_grupo2}")
            
        # Elimina duplicados (considerando que (A,B) y (B,A) son iguales)
        
        # print(f"Se encontraron {len(candidatos)} biparticiones candidatas (incluyendo extra).")
        return candidatos
      
    def filtrar_candidatos_por_tamano(self, candidatos):
        if not candidatos:
            return []
        
        min_size = min(len(c[0]) + len(c[2]) for c in candidatos)
        max_size = max(len(c[0]) + len(c[2]) for c in candidatos)

        if MAX_VAR == 0:
            umbral = min_size + math.floor((max_size - min_size) / 2)
        elif MAX_VAR > min_size and MAX_VAR < max_size:
            umbral = MAX_VAR
        elif MAX_VAR == -1:
            umbral = min_size + 2
        else:
            umbral = max_size
            
        filtrados = [c for c in candidatos if (len(c[0]) + len(c[2])) <= umbral]
        #print(f"Filtrando candidatos: tamaño mínimo {min_size}, máximo {max_size}, umbral {umbral}. Quedan {len(filtrados)} de {len(candidatos)}.")
        return filtrados  
      
    def evaluar_biparticiones(self, candidatos):
        mejor = None
        mejor_costo = float('inf')
        mejor_dist = None
        memoria_particiones = {}

        for A, B, a, b in candidatos:
            clave = (frozenset(A), frozenset(a))
            if clave in memoria_particiones:
                # print(f"Usando memoria para clave {clave}")
                costo, dist = memoria_particiones[clave]
            else:
                costo, dist = self.evaluar_coste_biparticion(A, a)
                memoria_particiones[clave] = (costo, dist)

            if costo < mejor_costo:
                mejor = (A, B, a, b)
                mejor_costo = costo
                mejor_dist = dist

        return mejor, mejor_dist, mejor_costo
    
    def evaluar_coste_biparticion(self, futuro_A, presente_a):  
        particion = self.sia_subsistema.bipartir(np.array(futuro_A), np.array(presente_a))
        dist = particion.distribucion_marginal()

        costo = emd_efecto(dist, self.sia_dists_marginales)
        
        return costo, dist
    