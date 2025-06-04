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
                [tuple(mejor[2]), tuple(mejor[0])],
                [tuple(mejor[3]), tuple(mejor[1])],
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
    
    def identificar_biparticiones_candidatas3(self):
        if not self.tabla_transiciones:
            return []

        first_key = next(iter(self.tabla_transiciones))
        num_states = len(self.tabla_transiciones[first_key])
        num_bits = (num_states - 1).bit_length()
        estado_inicial = self.bits_to_int(self.sia_subsistema.estado_inicial)

        candidatas = []

        for var in range(num_bits):
            fila = self.tabla_transiciones[var]
            min_costo = np.min(fila[1:])  # Excluye el estado inicial (asume que es 0)
            estados_min = [j for j in range(num_states) if j != estado_inicial and fila[j] == min_costo]
            
            
            for estado in estados_min:
                grupo1 = [var]
                grupo2 = []
                estado_inverso = estado ^ ((1 << num_bits) - 1)
                # Para cada otra variable, ver en qué transición tiene su menor costo
                # print(f"Evaluando estado {estado} ({format(estado, f'0{num_bits}b')}) con mínimo costo {min_costo:.8f} en variable {var}")
                for otra_var in range(num_bits):
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
                mecanismo_grupo1 = [idx for idx in range(num_bits) if bits_ini[idx] == bits_estado[idx]]
                # Mecanismo grupo 2: TODAS las variables que NO cambian en la transición estado_inicial -> estado_inverso
                mecanismo_grupo2 = [idx for idx in range(num_bits) if bits_ini[idx] == bits_inverso[idx]]
                
                # print(f"Grupo 1: {grupo1} con mecanismos {mecanismo_grupo1}")
                # print(f"Grupo 2: {grupo2} con mecanismos {mecanismo_grupo2}")

                # Solo considerar biparticiones no triviales
                if grupo1 and grupo2:
                    candidatas.append((grupo1, grupo2, mecanismo_grupo1, mecanismo_grupo2))

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

        print(f"Se encontraron {len(candidatas_unicas)} biparticiones candidatas.")
        return candidatas_unicas
       
    def identificar_biparticiones_candidatas2(self):
        if not self.tabla_transiciones:
            return []

        first_key = next(iter(self.tabla_transiciones))
        num_states = len(self.tabla_transiciones[first_key])
        num_bits = (num_states - 1).bit_length()
        estado_inicial = self.bits_to_int(self.sia_subsistema.estado_inicial)
        complemento_inicial = estado_inicial ^ ((1 << num_bits) - 1)

        candidatas = []

        for var in range(num_bits):
            fila = self.tabla_transiciones[var]
            min_costo = np.min(fila[1:])  # Excluye el estado inicial (asume que es 0)
            estados_min = [j for j in range(num_states) if j != estado_inicial and fila[j] == min_costo]

            for estado in estados_min:

                estado_inverso = estado ^ ((1 << num_bits) - 1)

                opciones = [
                    ("natural", estado, estado_inverso),
                    ("artificial", estado, complemento_inicial)
                ]
                
                mejor_opcion = None
                mejor_discrepancia = float('inf')
                mejor_grupo1 = mejor_grupo2 = mejor_mec1 = mejor_mec2 = None

                for tipo, e1, e2 in opciones:
                    grupo1 = [var]
                    grupo2 = []
                    for otra_var in range(num_bits):
                        if otra_var == var:
                            continue
                        fila_otra = self.tabla_transiciones[otra_var]
                        costo_e1 = fila_otra[e1]
                        costo_e2 = fila_otra[e2]
                        if costo_e1 < costo_e2:
                            grupo1.append(otra_var)
                        elif costo_e2 < costo_e1:
                            grupo2.append(otra_var)
                        else:
                            grupo1.append(otra_var)
                            
                    # Ordenar grupo
                    grupo1.sort()
                    grupo2.sort()
                    # Mecanismos
                    bits_ini = format(estado_inicial, f'0{num_bits}b')
                    bits_e1 = format(e1, f'0{num_bits}b')
                    bits_e2 = format(e2, f'0{num_bits}b')
                    mecanismo_grupo1 = [idx for idx in range(num_bits) if bits_ini[idx] == bits_e1[idx]]
                    mecanismo_grupo2 = [idx for idx in range(num_bits) if bits_ini[idx] == bits_e2[idx]]

                    if grupo1 and grupo2:
                        # Discrepancia total: suma de mínimos costos de cada grupo
                        discrepancia = sum(self.tabla_transiciones[v][e1] for v in grupo1) + \
                                    sum(self.tabla_transiciones[v][e2] for v in grupo2)
                        if discrepancia < mejor_discrepancia:
                            mejor_discrepancia = discrepancia
                            mejor_opcion = tipo
                            mejor_grupo1 = grupo1.copy()
                            mejor_grupo2 = grupo2.copy()
                            mejor_mec1 = mecanismo_grupo1
                            mejor_mec2 = mecanismo_grupo2
                    
                if mejor_grupo1 and mejor_grupo2:
                    candidatas.append((mejor_grupo1, mejor_grupo2, mejor_mec1, mejor_mec2))

        # Elimina duplicados (considerando que (A,B) y (B,A) son iguales)
        print(f"Se encontraron {len(candidatas)} biparticiones candidatas antes de eliminar duplicados.")
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

        print(f"Se encontraron {len(candidatas_unicas)} biparticiones candidatas.")
        return candidatas_unicas
          
    def identificar_biparticiones_candidatas(self):
        if not self.tabla_transiciones or not self.sia_subsistema or self.sia_subsistema.estado_inicial is None:
            print("Error: tabla_transiciones o sia_subsistema.estado_inicial no están disponibles.")
            return []

        # Determinar número de variables futuras y presentes
        try:
            first_future_var_key = next(iter(self.tabla_transiciones))
            if not self.tabla_transiciones[first_future_var_key].size > 0: # Check if array is not empty
                 print("Error: El array de costos para la primera variable futura está vacío.")
                 return []
        except StopIteration:
            print("Error: tabla_transiciones está vacía.")
            return []
            
        num_future_vars = len(self.tabla_transiciones)
        num_states_present = len(self.tabla_transiciones[first_future_var_key])
        
        if num_states_present == 0:
            print("Error: num_states_present es 0, no se pueden determinar num_present_vars.")
            return []
        num_present_vars = (num_states_present - 1).bit_length()
        if num_states_present == 1 and num_present_vars == 0: # Special case for single state (0 variables present)
             num_present_vars = 0 # (1-1).bit_length() is 0. If num_states_present is 1, means 2^0 states.

        estado_inicial_int = self.bits_to_int(self.sia_subsistema.estado_inicial)
        
        # Máscara para operaciones bitwise NOT para mantenerse dentro de num_present_vars
        mask_present_state = (1 << num_present_vars) - 1 if num_present_vars > 0 else 0
        complemento_inicial_present = estado_inicial_int ^ mask_present_state

        candidatas_lista = []
        
        # Iterar sobre cada variable FUTURA como ancla para fut_grupo1
        for anchor_future_var_idx in range(num_future_vars):
            if anchor_future_var_idx not in self.tabla_transiciones:
                print(f"Advertencia: No hay costos para la variable futura {anchor_future_var_idx}")
                continue
            
            costos_anchor_fut_var = self.tabla_transiciones[anchor_future_var_idx]

            # Encontrar el costo mínimo excluyendo la transición a estado_inicial_int
            valid_indices_for_min = [j for j in range(num_states_present) if j != estado_inicial_int]
            
            if not valid_indices_for_min:
                # Esto solo ocurriría si num_states_present == 1 y estado_inicial_int es ese único estado.
                # O si num_states_present == 0.
                continue 
            
            costs_for_min_search = costos_anchor_fut_var[valid_indices_for_min]
            if costs_for_min_search.size == 0:
                continue # No hay otros estados a los que transitar

            min_costo_val = np.min(costs_for_min_search)

            # Encontrar todos los estados presentes (target_present_states_min_cost) que resultan en este min_costo_val
            target_present_states_min_cost = [
                j for j in range(num_states_present)
                if j != estado_inicial_int and np.isclose(costos_anchor_fut_var[j], min_costo_val)
            ]

            for current_e1_present_state in target_present_states_min_cost:
                # current_e1_present_state es el estado presente objetivo para anchor_future_var_idx
                # que da el min_costo_val.

                # Opciones para el segundo estado presente (e2_pres) para comparar costos de otras variables futuras
                e2_natural_present_state = current_e1_present_state ^ mask_present_state # Inverso bitwise de current_e1_present_state
                e2_artificial_present_state = complemento_inicial_present

                opciones_config_present_states = [
                    ("natural", current_e1_present_state, e2_natural_present_state),
                    ("artificial", current_e1_present_state, e2_artificial_present_state)
                ]

                mejor_opcion_discrepancia = float('inf')
                mejor_opcion_fut_grupo1_list = None
                mejor_opcion_fut_grupo2_list = None
                mejor_tipo_opcion = None
                # print(f"Evaluando variable futura {anchor_future_var_idx} con estado presente {current_e1_present_state} (min costo {min_costo_val:.8f})")
                for tipo_opcion, e1_pres_ref, e2_pres_ref in opciones_config_present_states:
                    # Formar grupos de variables FUTURAS
                    # fut_grupo1 siempre contendrá anchor_future_var_idx
                    # Se distribuyen las otras variables futuras basadas en sus costos hacia e1_pres_ref vs e2_pres_ref
                    
                    current_fut_grupo1_set = {anchor_future_var_idx}
                    current_fut_grupo2_set = set()

                    for other_fut_var_idx in range(num_future_vars):
                        if other_fut_var_idx == anchor_future_var_idx:
                            continue
                        if other_fut_var_idx not in self.tabla_transiciones: continue

                        costos_other_fut_var = self.tabla_transiciones[other_fut_var_idx]
                        cost_at_e1_ref = costos_other_fut_var[e1_pres_ref]
                        cost_at_e2_ref = costos_other_fut_var[e2_pres_ref]

                        if cost_at_e1_ref <= cost_at_e2_ref: # Empate va a grupo1
                            current_fut_grupo1_set.add(other_fut_var_idx)
                        else:
                            current_fut_grupo2_set.add(other_fut_var_idx)
                    
                    current_fut_grupo1_list = sorted(list(current_fut_grupo1_set))
                    current_fut_grupo2_list = sorted(list(current_fut_grupo2_set))

                    # Calcular discrepancia (según la lógica del usuario)
                    # Ambas partes futuras deben ser no vacías para una bipartición válida
                    if current_fut_grupo1_list and current_fut_grupo2_list:
                        discrepancia = sum(self.tabla_transiciones[v_fut][e1_pres_ref] for v_fut in current_fut_grupo1_list) + \
                                       sum(self.tabla_transiciones[v_fut][e2_pres_ref] for v_fut in current_fut_grupo2_list)
                        
                        if discrepancia < mejor_opcion_discrepancia:
                            mejor_opcion_discrepancia = discrepancia
                            mejor_opcion_fut_grupo1_list = current_fut_grupo1_list
                            mejor_opcion_fut_grupo2_list = current_fut_grupo2_list
                            mejor_tipo_opcion = tipo_opcion
                            
                    # print(f"  Opción {tipo_opcion}: Grupo1={current_fut_grupo1_list}, Grupo2={current_fut_grupo2_list}, Discrepancia={discrepancia:.8f}")
                
                # Si se encontró una mejor opción para los grupos futuros
                if mejor_opcion_fut_grupo1_list and mejor_opcion_fut_grupo2_list:
                    # Definir mecanismos PRESENTES basados *únicamente* en la transición primaria:
                    # estado_inicial_int -> current_e1_present_state
                    
                    # Asegurarse de que num_present_vars sea correcto para formateo de bits
                    # (ya calculado arriba, pero bueno verificar si el estado tiene bits)
                    if num_present_vars == 0 and estado_inicial_int == 0 and current_e1_present_state == 0:
                        # Caso especial: 0 variables presentes, 1 estado (0)
                        mecanismos_A_present_list = []
                        mecanismos_B_present_list = []
                    elif num_present_vars > 0 :
                        bits_ini_str = format(estado_inicial_int, f'0{num_present_vars}b')
                        bits_current_e1_str = format(current_e1_present_state, f'0{num_present_vars}b')
                        
                        
                            

                        mecanismos_A_present_list = sorted([
                            idx for idx in range(num_present_vars) if bits_ini_str[idx] == bits_current_e1_str[idx]
                        ])
                        if (tipo_opcion == "natural"):
                            mecanismos_B_present_list = sorted([
                                idx for idx in range(num_present_vars) if bits_ini_str[idx] != bits_current_e1_str[idx]
                        ]) 
                        else:
                            bits_artificial_present_state = format(e2_artificial_present_state, f'0{num_present_vars}b')
                            mecanismos_B_present_list = sorted([
                                idx for idx in range(num_present_vars) if bits_ini_str[idx] == bits_artificial_present_state[idx]
                            ])
                    else: # num_present_vars es 0, pero los estados no son ambos 0 (situación anómala)
                        mecanismos_A_present_list = []
                        mecanismos_B_present_list = []

                    # print(f"Mejor tipo de opción: {mejor_tipo_opcion} con discrepancia {mejor_opcion_discrepancia:.8f}")
                    # print(f"  Mejor opción encontrada: Grupo1={mejor_opcion_fut_grupo1_list}, Grupo2={mejor_opcion_fut_grupo2_list}, ")
                    # print(f"               Mecanismos:      A={mecanismos_A_present_list}, Mecanismos B={mecanismos_B_present_list}")
                    
                    candidatas_lista.append((
                        mejor_opcion_fut_grupo1_list,
                        mejor_opcion_fut_grupo2_list,
                        mecanismos_A_present_list,
                        mecanismos_B_present_list
                    ))

        # Eliminar duplicados y manejar simetría (A,B,a,b) es igual a (B,A,b,a) etc.
        # Y (A,B,a,b) es igual a (A,B,b,a) si los mecanismos son solo conjuntos.
        print(f"Se encontraron {len(candidatas_lista)} biparticiones candidatas antes de eliminar duplicados.")
        
        candidatas_unicas_final = []
        claves_vistas_set = set()

        for cand_futA, cand_futB, cand_presA, cand_presB in candidatas_lista:
            # Crear representación canónica para la partición futura
            key_fut_part = tuple(sorted((frozenset(cand_futA), frozenset(cand_futB))))
            
            # Crear representación canónica para la partición presente
            key_pres_part = tuple(sorted((frozenset(cand_presA), frozenset(cand_presB))))
            
            combined_key = (key_fut_part, key_pres_part)

            if combined_key not in claves_vistas_set:
                # Guardar con el orden original que se encontró, o un orden canónico si se prefiere
                # Aquí se guardan las listas originales (ya ordenadas internamente).
                candidatas_unicas_final.append(list(map(list, (cand_futA, cand_futB, cand_presA, cand_presB))))
                claves_vistas_set.add(combined_key)

        print(f"Se encontraron {len(candidatas_unicas_final)} biparticiones candidatas únicas.")
        return candidatas_unicas_final      
          
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
    