import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
from datetime import datetime

def load_data(csv_filepath):
    """Carga los datos desde el archivo CSV."""
    if not os.path.exists(csv_filepath):
        print(f"Error: El archivo '{csv_filepath}' no fue encontrado.")
        return None
    try:
        df = pd.read_csv(csv_filepath)
        # Convertir columnas numéricas, los errores se convierten a NaN
        for col in df.columns:
            if col != "Timestamp": # Asumiendo que Timestamp ya es numérico o se manejará
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df
    except Exception as e:
        print(f"Error al leer el archivo CSV: {e}")
        return None

def generate_summary_table(df, resource_columns):
    """Genera y muestra una tabla resumen (Min, Promedio, Máx)."""
    summary_data = {}
    valid_columns = [col for col in resource_columns if col in df.columns and not df[col].isnull().all()]

    if not valid_columns:
        print("No hay datos válidos en las columnas de recursos para generar un resumen.")
        return None

    for col in valid_columns:
        summary_data[col] = {
            "Mínimo": df[col].min(),
            "Promedio": df[col].mean(),
            "Máximo": df[col].max()
        }
    summary_df = pd.DataFrame(summary_data).T # Transponer para tener recursos como filas
    summary_df = summary_df[["Mínimo", "Promedio", "Máximo"]] # Asegurar el orden de las columnas
    
    print("\n--- Tabla Resumen del Uso de Recursos ---")
    if not summary_df.empty:
        print(summary_df.to_string(float_format="%.2f"))
    else:
        print("No se pudo generar la tabla resumen (sin datos válidos).")
    return summary_df


def plot_resource_usage(df, resource_columns, output_dir="graficos_recursos"):
    """Genera y guarda gráficos de uso de recursos a lo largo del tiempo."""
    if 'Timestamp' not in df.columns:
        print("Error: La columna 'Timestamp' es necesaria para los gráficos y no se encontró.")
        return

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Directorio '{output_dir}' creado para guardar los gráficos.")

    sns.set_theme(style="whitegrid") # Estilo de Seaborn

    valid_plot_columns = [col for col in resource_columns if col in df.columns and not df[col].isnull().all()]

    if not valid_plot_columns:
        print("No hay datos válidos en las columnas de recursos para graficar.")
        return

    for col in valid_plot_columns:
        plt.figure(figsize=(12, 6))
        sns.lineplot(x='Timestamp', y=col, data=df, label=col, errorbar=None) # errorbar=None para evitar bandas de confianza si hay pocas muestras
        plt.title(f'Uso de {col.replace("_Percent", "")} a lo largo del Tiempo', fontsize=16)
        plt.xlabel('Tiempo (segundos)', fontsize=12)
        plt.ylabel(f'{col.replace("_Percent", "")} (%)', fontsize=12)
        plt.legend()
        plt.tight_layout()
        plot_filename = os.path.join(output_dir, f"{col.lower()}_usage_plot.png")
        try:
            plt.savefig(plot_filename)
            print(f"Gráfico guardado en: {plot_filename}")
        except Exception as e:
            print(f"Error al guardar el gráfico {plot_filename}: {e}")
        plt.close() # Cerrar la figura para liberar memoria

def main():
    csv_file = input("Introduce la ruta al archivo CSV de recursos (ej: resource_log.csv): ")

    df = load_data(csv_file)

    if df is None:
        return

    # Definir las columnas que contienen los datos de recursos
    # Ajusta estos nombres si son diferentes en tu CSV
    resource_metric_columns = ["CPU_Percent", "Memory_Percent", "GPU_Percent", "GPU_Memory_Percent"]

    # Filtrar columnas que realmente existen en el DataFrame
    actual_resource_columns = [col for col in resource_metric_columns if col in df.columns]

    if not actual_resource_columns:
        print("No se encontraron columnas de métricas de recursos en el CSV.")
        print(f"Columnas encontradas: {df.columns.tolist()}")
        print(f"Columnas esperadas (alguna de estas): {resource_metric_columns}")
        return

    # Generar y mostrar tabla resumen
    summary_table = generate_summary_table(df, actual_resource_columns)

    # Generar y guardar gráficos
    # Crear un subdirectorio con timestamp para evitar sobrescribir gráficos de ejecuciones anteriores
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_plot_dir = f"graficos_recursos_{os.path.basename(csv_file).replace('.csv', '')}_{timestamp_str}"
    plot_resource_usage(df, actual_resource_columns, output_dir=output_plot_dir)

    if summary_table is not None and not summary_table.empty:
        # Opcional: Guardar la tabla resumen en un archivo CSV o de texto
        summary_filename_base = os.path.basename(csv_file).replace('.csv', '')
        summary_csv_path = os.path.join(output_plot_dir, f"resumen_{summary_filename_base}.csv")
        summary_txt_path = os.path.join(output_plot_dir, f"resumen_{summary_filename_base}.txt")
        try:
            summary_table.to_csv(summary_csv_path)
            print(f"Tabla resumen guardada en: {summary_csv_path}")
            with open(summary_txt_path, 'w') as f:
                f.write("--- Tabla Resumen del Uso de Recursos ---\n")
                f.write(summary_table.to_string(float_format="%.2f"))
            print(f"Tabla resumen guardada en: {summary_txt_path}")
        except Exception as e:
            print(f"Error al guardar la tabla resumen: {e}")


if __name__ == "__main__":
    main()