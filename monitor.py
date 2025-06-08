# filepath: monitor_recursos.py
import psutil
import time
import statistics  # Para calcular el promedio fácilmente
import csv

# Intenta importar GPUtil, pero no falles si no está o no es NVIDIA
try:
    import GPUtil
    GPUTIL_AVAILABLE = True
except ImportError:
    GPUTIL_AVAILABLE = False
    print("Advertencia: La biblioteca GPUtil no está instalada. No se monitoreará la GPU.")
    print("Puedes instalarla con: pip install GPUtil")
except Exception as e:
    GPUTIL_AVAILABLE = False
    print(f"Advertencia: No se pudo inicializar GPUtil (puede que no tengas una GPU NVIDIA o los drivers no sean compatibles): {e}")
    print("No se monitoreará la GPU.")


# --- Configuración ---
MONITOR_INTERVAL_SECONDS = 1  # Con qué frecuencia tomar muestras (en segundos)
OUTPUT_CSV_FILE = "resource_log.csv" # Nombre del archivo CSV para guardar los datos
# --------------------

def get_gpu_stats():
    """
    Obtiene el uso de GPU y memoria de GPU.
    Devuelve (uso_gpu_percent, uso_memoria_gpu_percent) o (None, None) si no está disponible.
    """
    if not GPUTIL_AVAILABLE:
        return None, None
    try:
        gpus = GPUtil.getGPUs()
        if not gpus:
            # print("Advertencia: No se encontraron GPUs con GPUtil.")
            return None, None
        gpu = gpus[0]  # Asume la primera GPU
        return gpu.load * 100, gpu.memoryUtil * 100  # Convertir a porcentaje
    except Exception as e:
        # print(f"Advertencia: No se pudo obtener el uso de GPU con GPUtil: {e}")
        return None, None

def main():
    cpu_usage_list = []
    memory_usage_list = []
    gpu_usage_list = []
    gpu_memory_usage_list = []

    print(f"Iniciando monitoreo. Presiona Ctrl+C para detener y ver resultados.")
    print(f"Intervalo de muestreo: {MONITOR_INTERVAL_SECONDS} segundos.")
    print(f"Guardando datos detallados en: {OUTPUT_CSV_FILE}")

    # Encabezado del CSV
    with open(OUTPUT_CSV_FILE, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        header = ["Timestamp", "CPU_Percent", "Memory_Percent"]
        if GPUTIL_AVAILABLE:
            header.extend(["GPU_Percent", "GPU_Memory_Percent"])
        csv_writer.writerow(header)

    try:
        start_time = time.time()
        while True:
            current_time = time.time()
            elapsed_time = current_time - start_time

            # Uso de CPU
            cpu_percent = psutil.cpu_percent(interval=None)  # No bloqueante
            cpu_usage_list.append(cpu_percent)

            # Uso de Memoria RAM
            memory_info = psutil.virtual_memory()
            memory_percent = memory_info.percent
            memory_usage_list.append(memory_percent)

            row_data = [f"{elapsed_time:.2f}", cpu_percent, memory_percent]

            # Uso de GPU (si está disponible)
            gpu_percent, gpu_mem_percent = get_gpu_stats()
            if gpu_percent is not None:
                gpu_usage_list.append(gpu_percent)
                row_data.append(gpu_percent)
            elif GPUTIL_AVAILABLE: # Si se esperaba GPUtil pero no dio datos
                row_data.append('')

            if gpu_mem_percent is not None:
                gpu_memory_usage_list.append(gpu_mem_percent)
                row_data.append(gpu_mem_percent)
            elif GPUTIL_AVAILABLE: # Si se esperaba GPUtil pero no dio datos
                row_data.append('')

            # Guardar la fila en CSV
            with open(OUTPUT_CSV_FILE, 'a', newline='') as csvfile:
                csv_writer = csv.writer(csvfile)
                csv_writer.writerow(row_data)

            # Esperar para el próximo intervalo
            time.sleep(MONITOR_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\nMonitoreo detenido por el usuario.")
    except Exception as e:
        print(f"\nOcurrió un error durante el monitoreo: {e}")
    finally:
        print("\n--- Resultados del Monitoreo ---")

        if cpu_usage_list:
            print("\nUso de CPU (%):")
            print(f"  Mínimo: {min(cpu_usage_list):.2f}")
            print(f"  Promedio: {statistics.mean(cpu_usage_list):.2f}")
            print(f"  Máximo: {max(cpu_usage_list):.2f}")

        if memory_usage_list:
            print("\nUso de Memoria RAM (%):")
            print(f"  Mínimo: {min(memory_usage_list):.2f}")
            print(f"  Promedio: {statistics.mean(memory_usage_list):.2f}")
            print(f"  Máximo: {max(memory_usage_list):.2f}")

        if gpu_usage_list:
            print("\nUso de GPU (%):")
            print(f"  Mínimo: {min(gpu_usage_list):.2f}")
            print(f"  Promedio: {statistics.mean(gpu_usage_list):.2f}")
            print(f"  Máximo: {max(gpu_usage_list):.2f}")
        elif GPUTIL_AVAILABLE:
            print("\nNo se recolectaron datos de uso de GPU.")


        if gpu_memory_usage_list:
            print("\nUso de Memoria de GPU (%):")
            print(f"  Mínimo: {min(gpu_memory_usage_list):.2f}")
            print(f"  Promedio: {statistics.mean(gpu_memory_usage_list):.2f}")
            print(f"  Máximo: {max(gpu_memory_usage_list):.2f}")
        elif GPUTIL_AVAILABLE:
            print("\nNo se recolectaron datos de memoria de GPU.")

        if not GPUTIL_AVAILABLE:
             print("\nRecordatorio: El monitoreo de GPU no estuvo activo.")
        elif not gpu_usage_list and not gpu_memory_usage_list:
             print("\nAdvertencia: GPUtil estuvo activo pero no se recolectaron datos de GPU. Verifica tu GPU y drivers NVIDIA.")


        print(f"\nLos datos detallados de esta sesión se guardaron en: {OUTPUT_CSV_FILE}")
        print("Para la siguiente estrategia, considera renombrar o mover este archivo, o modificar el script para usar nombres de archivo únicos.")

if __name__ == "__main__":
    main()