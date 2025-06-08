from numba import cuda
from numba.cuda.cudadrv.driver import driver

device = cuda.get_current_device()

print("🖥️ Información del dispositivo CUDA:")
print(f"Nombre                        : {device.name.decode()}")
print(f"Número de multiprocesadores  : {device.MULTIPROCESSOR_COUNT}")
print(f"Hilos por bloque             : {device.MAX_THREADS_PER_BLOCK}")
print(f"Hilos por warp               : {device.WARP_SIZE}")
print(f"Máximo bloques por dimensión : {device.MAX_GRID_DIM_X}, {device.MAX_GRID_DIM_Y}, {device.MAX_GRID_DIM_Z}")
print(f"Máximo hilos por dimensión   : {device.MAX_BLOCK_DIM_X}, {device.MAX_BLOCK_DIM_Y}, {device.MAX_BLOCK_DIM_Z}")

device = cuda.get_current_device()
ctx = cuda.current_context()
free_mem = ctx.get_memory_info()[0]
total_mem = ctx.get_memory_info()[1]

print("Memoria total       : {:.2f} MB".format(total_mem / 1e6))
print("Memoria disponible  : {:.2f} MB".format(free_mem / 1e6))