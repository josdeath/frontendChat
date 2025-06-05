# app_backup.py
import tkinter as tk  # Biblioteca para crear interfaces gráficas de usuario (GUI)
from tkinter import scrolledtext, messagebox  # Widgets específicos de Tkinter
import logging  # Para registrar eventos y mensajes de la aplicación
import subprocess  # Para ejecutar comandos externos del sistema (como Git)
import os  # Para interactuar con el sistema operativo (ej. verificar rutas)
import datetime  # Para trabajar con fechas y horas (ej. para mensajes de commit)
import time  # Para manejar tiempos de espera y pausas en la ejecución
import threading  # Para manejar la concurrencia y ejecutar tareas en segundo plano
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError  # Para manejar timeout por intentos
import socket # Para verificar la conexión de red

# --- Configuración Global ---
ARCHIVO_LOG = "backup_git.log"  # Nombre del archivo donde se guardarán los logs
MAX_REINTENTOS = 3  # Número máximo de reintentos para el proceso de backup completo
TIMEOUT_POR_INTENTO_SEGUNDOS = 5 * 60  # 5 minutos de timeout para cada intento de backup
RETRASO_ENTRE_REINTENTOS_SEGUNDOS = 10 # Tiempo de espera entre reintentos
ARCHIVO_INFO_BACKUP = "backup_info.txt"  # Archivo para guardar información del backup

# --- Configuración del Logging ---
def configurar_logging():
    """
    Configura el sistema de logging para que los mensajes se guarden en un archivo.
    Opcionalmente, también se pueden mostrar en la consola donde se ejecuta el script.
    """
    logging.basicConfig(
        level=logging.INFO,  # Nivel mínimo de mensajes a registrar (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format='%(asctime)s - %(levelname)s - %(message)s',  # Formato de cada línea de log
        handlers=[
            logging.FileHandler(ARCHIVO_LOG),  # Handler para escribir los logs en el archivo especificado
            # logging.StreamHandler()  # Descomentar esta línea para ver los logs también en la consola
        ]
    )
# --- Funciones Auxiliares de Backup ---

def get_next_backup_number(log_fn): # Pasamos log_fn para poder loguear desde aquí si es necesario
    """
    Obtiene el siguiente número de backup a utilizar.
    Lee el último número guardado en ARCHIVO_INFO_BACKUP y le suma 1.
    Si el archivo no existe o está corrupto, empieza desde 1.
    """
    if not os.path.exists(ARCHIVO_INFO_BACKUP):
        if log_fn: log_fn(f"Archivo '{ARCHIVO_INFO_BACKUP}' no encontrado, iniciando contador de backup en 1.", "INFO")
        return 1
    try:
        with open(ARCHIVO_INFO_BACKUP, 'r') as f:
            last_backup_number = int(f.read().strip())
            next_number = last_backup_number + 1
            if log_fn: log_fn(f"Último número de backup leído: {last_backup_number}. Siguiente número: {next_number}", "INFO")
            return next_number
    except (ValueError, FileNotFoundError) as e:
        # FileNotFoundError es redundante si ya comprobamos os.path.exists, pero por si acaso.
        # ValueError si el contenido no es un número.
        if log_fn: log_fn(f"Error al leer el número de backup de '{ARCHIVO_INFO_BACKUP}': {e}. Reiniciando a 1.", "WARNING")
        return 1

def save_backup_number(number, log_fn):
    """
    Guarda el número de backup proporcionado en ARCHIVO_INFO_BACKUP.
    """
    try:
        with open(ARCHIVO_INFO_BACKUP, 'w') as f:
            f.write(str(number))
        if log_fn: log_fn(f"Número de backup {number} guardado en '{ARCHIVO_INFO_BACKUP}'.", "INFO")
    except IOError as e:
        # Usamos logging.error directamente aquí porque es un error crítico para esta función
        # y log_fn podría ser None si se llama desde un contexto sin GUI.
        logging.error(f"Error crítico al guardar el número de backup {number} en '{ARCHIVO_INFO_BACKUP}': {e}")
        if log_fn: log_fn(f"Error al guardar el número de backup {number}: {e}", "ERROR")
        # Considerar si se debe lanzar una excepción aquí para que el proceso de backup falle.
        # Por ahora, solo lo logueamos.

def check_github_connection(log_fn=None, timeout=5):
    """
    Verifica la conexión a github.com en el puerto 443 (HTTPS).

    Args:
        log_fn (function, optional): Función para loguear mensajes (ej. self.loguear_mensaje).
        timeout (int, optional): Tiempo de espera en segundos para establecer la conexión.

    Returns:
        bool: True si la conexión es exitosa, False en caso contrario.
    """
    try:
        if log_fn: log_fn("Verificando conexión a GitHub (github.com:443)...", "INFO")
        # Intentar crear una conexión TCP a github.com en el puerto 443
        socket.create_connection(("github.com", 443), timeout=timeout)
        if log_fn: log_fn("Conexión a GitHub establecida correctamente.", "INFO")
        return True
    except socket.timeout:
        # Error específico si la conexión excede el timeout
        if log_fn: log_fn("No se pudo conectar a GitHub: Timeout durante el intento de conexión.", "ERROR")
        return False
    except (socket.error, OSError) as e: # OSError puede cubrir algunos errores de red también
        # Otros errores de socket o de red
        if log_fn: log_fn(f"No se pudo conectar a GitHub: {e}", "ERROR")
        return False




# --- Clase Principal de la Aplicación ---
class AppBackup:
    """
    Clase que encapsula toda la lógica y la interfaz gráfica de la herramienta de backup.
    """
    def __init__(self, ventana_raiz):
        """
        Constructor de la aplicación. Se llama cuando se crea una instancia de AppBackup.
        Inicializa la ventana principal y sus componentes.
        """
        self.raiz = ventana_raiz
        self.raiz.title("Herramienta de Backup a Git con Reintentos") # Título actualizado
        self.raiz.geometry("700x500") # Un poco más grande para los logs y mensajes

        # Executor para manejar la lógica de backup con timeout en un hilo.
        # max_workers=1 asegura que solo un intento de backup se ejecute a la vez.
        self.executor = ThreadPoolExecutor(max_workers=1)

        # --- Verificación inicial: ¿Estamos en un repositorio Git? ---
        if not os.path.exists(".git"):
            self.raiz.withdraw()
            messagebox.showerror("Error de Repositorio",
                                 "Este script debe ejecutarse desde la raíz de un repositorio Git.")
            logging.error("La aplicación no se inició desde la raíz de un repositorio Git.")
            # Si hay un error aquí, el executor no se cerrará con al_cerrar_ventana,
            # así que es importante manejar su cierre en el bloque __main__ si la app no arranca.
            if hasattr(self, 'executor') and self.executor and not self.executor._shutdown:
                self.executor.shutdown(wait=False, cancel_futures=True)
            self.raiz.destroy()
            return

        # --- Creación de los Widgets (componentes de la GUI) ---
        self.etiqueta_bienvenida = tk.Label(self.raiz, text="Bienvenido a la Herramienta de Backup con Reintentos")
        self.etiqueta_bienvenida.pack(pady=10)

        self.boton_backup = tk.Button(
            self.raiz,
            text="Iniciar Backup a GitHub",
            # El comando del botón ahora llama a la función que maneja hilos y reintentos
            command=self.iniciar_proceso_backup_con_reintentos_en_hilo,
            font=("Arial", 12, "bold"),
            bg="lightblue",
            pady=10
        )
        self.boton_backup.pack(pady=10, fill=tk.X)

        self.etiqueta_logs = tk.Label(self.raiz, text="Logs de Operación:")
        self.etiqueta_logs.pack(pady=(5, 0), anchor='w', padx=10)

        self.texto_logs = scrolledtext.ScrolledText(
            self.raiz,
            height=18, # Un poco más de altura para los logs
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.texto_logs.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)

        self.loguear_mensaje("Aplicación de backup iniciada en un repositorio Git.")

        # Manejar el cierre de la ventana (ej. clic en la 'X') para limpiar el executor
        self.raiz.protocol("WM_DELETE_WINDOW", self.al_cerrar_ventana)

    def al_cerrar_ventana(self):
        """
        Se llama cuando el usuario intenta cerrar la ventana.
        Se asegura de que el ThreadPoolExecutor se cierre limpiamente.
        """
        self.loguear_mensaje("Cerrando aplicación...", "INFO")
        if hasattr(self, 'executor') and self.executor and not self.executor._shutdown:
            # `cancel_futures=True` es para Python 3.9+ e intenta cancelar tareas pendientes.
            # `wait=True` (o False) depende de si quieres esperar a que las tareas terminen o no.
            # Para un cierre rápido, `wait=False` podría ser mejor, pero `wait=True` es más seguro
            # si las tareas realizan operaciones críticas que no deben interrumpirse bruscamente.
            # Dado que los comandos Git pueden ser largos, `wait=False` con `cancel_futures=True` es un buen compromiso.
            self.loguear_mensaje("Intentando cerrar el ThreadPoolExecutor...", "INFO")
            self.executor.shutdown(wait=False, cancel_futures=True)
            self.loguear_mensaje("ThreadPoolExecutor cerrado.", "INFO")
        self.raiz.destroy()

    def ejecutar_comando_git(self, comando_args, nombre_operacion="Comando Git"):
        """
        Ejecuta un comando Git. Esta función es llamada desde un hilo de trabajo,
        por lo que sus logs se enrutan a través de `loguear_mensaje` para actualizar la GUI de forma segura.
        Los `messagebox` directos han sido eliminados de aquí; el llamador debe manejarlos.
        """
        # (El cuerpo de esta función parece estar correcto y ya fue comentado en la versión anterior)
        # Solo me aseguro de que los comentarios sobre los messagebox eliminados sean claros.
        try:
            self.loguear_mensaje(f"Ejecutando: {' '.join(comando_args)}", nivel="INFO")
            proceso = subprocess.Popen(
                comando_args,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, cwd=os.getcwd()
            )
            stdout, stderr = proceso.communicate(timeout=120)
            codigo_retorno = proceso.returncode

            mensaje_log_completo = f"{nombre_operacion} finalizado. Código: {codigo_retorno}\n"
            if stdout: mensaje_log_completo += f"Salida Estándar:\n{stdout.strip()}\n"
            if stderr: mensaje_log_completo += f"Salida de Error:\n{stderr.strip()}\n"

            if codigo_retorno == 0:
                self.loguear_mensaje(mensaje_log_completo, nivel="INFO")
            else:
                if nombre_operacion == "Commit" and "nothing to commit" in stderr.lower():
                    self.loguear_mensaje(mensaje_log_completo + "INFO: No había cambios para commitear.", "WARNING")
                    return stdout, stderr, 0
                else:
                    self.loguear_mensaje(mensaje_log_completo, nivel="ERROR")
            return stdout, stderr, codigo_retorno
        except FileNotFoundError:
            msg_error = "Error: El comando 'git' no se encontró. ¿Está Git instalado y en el PATH?"
            self.loguear_mensaje(msg_error, "ERROR")
            # No mostrar messagebox desde aquí (hilo de trabajo)
            return "", "Git no encontrado", -1
        except subprocess.TimeoutExpired:
            msg_error = f"La operación '{nombre_operacion}' excedió el tiempo de espera (120s) y fue cancelada."
            self.loguear_mensaje(msg_error, "ERROR")
            # No mostrar messagebox desde aquí
            return "", "Comando Git excedió el tiempo de espera", -2
        except Exception as e:
            msg_error = f"Error inesperado ejecutando '{nombre_operacion}': {e}"
            self.loguear_mensaje(msg_error, "ERROR")
            # No mostrar messagebox desde aquí
            return "", str(e), -3

    def _realizar_intento_backup_logica(self):
        """
        Contiene la lógica de un solo intento de backup.
        Esta función está diseñada para ser ejecutada en un hilo por ThreadPoolExecutor.
        NO debe interactuar directamente con la GUI (messagebox, config de widgets).
        Retorna un string: "SUCCESS", "NO_CHANGES", "NO_CHANGES_AFTER_ADD", o un código de error.
        """
        # (El cuerpo de esta función parece estar correcto y ya fue comentado en la versión anterior)
        self.loguear_mensaje("Iniciando intento de lógica de backup...", "INFO")

        # --- Obtener número de backup ---
        # Usamos self.loguear_mensaje como la función de log para get_next_backup_number
        numero_backup_actual = get_next_backup_number(self.loguear_mensaje)

          # --- NUEVO: Chequeo de Conexión a GitHub ---
        if not check_github_connection(self.loguear_mensaje):
            # No es necesario loguear un error aquí de nuevo, check_github_connection ya lo hace.
            return "CONNECTION_ERROR" # Nuevo estado de retorno
        

        # --- 1. Verificar estado del repositorio Git ---
        stdout_status, _, rc_status = self.ejecutar_comando_git(
            ["git", "status", "--porcelain"], "Verificar Estado Git"
        )
        if rc_status < 0: return "GIT_EXECUTION_ERROR"
        if rc_status > 0:
            self.loguear_mensaje("Error al verificar el estado de Git.", "ERROR")
            return "GIT_STATUS_ERROR"
        if not stdout_status.strip():
            self.loguear_mensaje("No hay cambios pendientes en el repositorio.", "INFO")
            return "NO_CHANGES"
        self.loguear_mensaje(f"Cambios detectados o archivos no rastreados:\n{stdout_status.strip()}", "INFO")

        _, _, rc_add = self.ejecutar_comando_git(["git", "add", "."], "Git Add")
        if rc_add != 0:
            self.loguear_mensaje("Error durante 'git add .'.", "ERROR")
            return "GIT_ADD_ERROR"

        current_date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_message = f"Backup #{numero_backup_actual} - {current_date_str}"
        self.loguear_mensaje(f"Realizando commit con mensaje: '{commit_message}'...", "INFO")
        _, stderr_commit, rc_commit = self.ejecutar_comando_git(
            ["git", "commit", "-m", commit_message], "Git Commit"
        )
        if rc_commit < 0: return "GIT_EXECUTION_ERROR"
        if rc_commit > 0:
            self.loguear_mensaje("Error durante 'git commit'.", "ERROR")
            return "GIT_COMMIT_ERROR"
        if "nothing to commit" in stderr_commit.lower() and rc_commit == 0:
            self.loguear_mensaje("No había cambios para commitear (detectado después de 'git add').", "WARNING")
            return "NO_CHANGES_AFTER_ADD"
        self.loguear_mensaje("Commit realizado exitosamente.", "INFO")

        self.loguear_mensaje("Realizando push al repositorio remoto (git push)...", "INFO")
        _, _, rc_push = self.ejecutar_comando_git(["git", "push"], "Git Push")
        if rc_push != 0:
            self.loguear_mensaje("Error durante 'git push'.", "ERROR")
            return "GIT_PUSH_ERROR"

        self.loguear_mensaje("Push realizado exitosamente.", "INFO")

          # --- 5. Guardar el número de backup DESPUÉS de un push exitoso ---
        save_backup_number(numero_backup_actual, self.loguear_mensaje)
        return "SUCCESS"

    # ESTE MÉTODO DEBE ESTAR CORRECTAMENTE INDENTADO COMO MÉTODO DE LA CLASE
    def _bucle_trabajador_backup(self):
        """
        Se ejecuta en un hilo separado (creado por iniciar_proceso_backup_con_reintentos_en_hilo).
        Gestiona los reintentos para el proceso de backup.
        Llama a _realizar_intento_backup_logica usando ThreadPoolExecutor para aplicar un timeout por intento.
        Actualiza la GUI de forma segura usando self.raiz.after().
        """
        overall_start_time = time.time()
        success = False # Indica si el proceso general de backup (con reintentos) fue exitoso

        for attempt in range(1, MAX_REINTENTOS + 1):
            # Loguear inicio del intento (usará self.raiz.after desde loguear_mensaje)
            self.loguear_mensaje(f"--- Iniciando Intento de Backup {attempt}/{MAX_REINTENTOS} ---", "INFO")
            attempt_start_time = time.time()
            
            # Enviar la tarea _realizar_intento_backup_logica al ThreadPoolExecutor.
            # Esto permite que se ejecute en uno de los hilos del pool (en nuestro caso, solo 1).
            future = self.executor.submit(self._realizar_intento_backup_logica)
            status_intento = "UNKNOWN_ERROR" # Valor por defecto
            try:
                # Esperar el resultado de la tarea (future.result()) con un timeout.
                # Si la tarea no termina dentro del timeout, se lanza FutureTimeoutError.
                status_intento = future.result(timeout=TIMEOUT_POR_INTENTO_SEGUNDOS)
            except FutureTimeoutError:
                status_intento = "TIMEOUT_ATTEMPT"
                self.loguear_mensaje(f"Intento {attempt} excedió el tiempo límite de {TIMEOUT_POR_INTENTO_SEGUNDOS / 60:.0f} minutos.", "ERROR")
                # Intentar cancelar la tarea si sigue corriendo.
                # future.cancel() devuelve True si la tarea fue cancelada, False si ya terminó o no pudo ser cancelada.
                if future.running():
                    future.cancel()
            except Exception as e: # Captura cualquier otra excepción que pudiera ocurrir en _realizar_intento_backup_logica
                                   # o durante la gestión del future, aunque es menos común aquí.
                status_intento = "EXCEPTION_IN_LOGIC"
                self.loguear_mensaje(f"Excepción no controlada durante el intento {attempt}: {str(e)}", "CRITICAL")
                # Loguear el traceback completo al archivo de log para depuración.
                logging.exception(f"Excepción no controlada en _bucle_trabajador_backup, intento {attempt}")

            attempt_duration = time.time() - attempt_start_time
            self.loguear_mensaje(f"Intento {attempt} finalizado en {attempt_duration:.2f}s con estado: {status_intento}", "INFO")

            if status_intento == "SUCCESS":
                overall_duration = time.time() - overall_start_time
                self.loguear_mensaje(f"Backup completado exitosamente después de {attempt} intento(s).", "INFO")
                self.loguear_mensaje(f"Duración total del proceso: {overall_duration:.2f} segundos.", "INFO")
                # Mostrar messagebox en el hilo principal
                self.raiz.after(0, lambda: messagebox.showinfo("Éxito", f"Backup realizado con éxito en el intento {attempt}."))
                success = True # El proceso general fue exitoso
                break # Salir del bucle de reintentos

            elif status_intento in ["NO_CHANGES", "NO_CHANGES_AFTER_ADD"]:
                overall_duration = time.time() - overall_start_time
                self.loguear_mensaje("No hay cambios para el backup.", "INFO")
                self.loguear_mensaje(f"Duración total del proceso (sin cambios): {overall_duration:.2f} segundos.", "INFO")
                self.raiz.after(0, lambda: messagebox.showinfo("Sin Cambios", "No se detectaron cambios para el backup."))
                success = True # Se considera un "éxito" funcional ya que no había nada que hacer
                break # Salir del bucle de reintentos
            
            else: # El intento falló (GIT_ERROR, TIMEOUT_ATTEMPT, EXCEPTION_IN_LOGIC, etc.)
                self.loguear_mensaje(f"Intento {attempt} falló. Estado: {status_intento}", "ERROR")
                if attempt < MAX_REINTENTOS:
                    self.loguear_mensaje(f"Esperando {RETRASO_ENTRE_REINTENTOS_SEGUNDOS}s antes del próximo intento...", "INFO")
                    time.sleep(RETRASO_ENTRE_REINTENTOS_SEGUNDOS) # Pausa en el hilo trabajador
                # Si es el último intento, el mensaje de fallo total se mostrará después del bucle.

        # --- Después de todos los intentos ---
        if not success: # Si ningún intento fue exitoso (SUCCESS o NO_CHANGES*)
            overall_duration = time.time() - overall_start_time
            self.loguear_mensaje(f"Todos los {MAX_REINTENTOS} intentos de backup fallaron.", "ERROR")
            self.loguear_mensaje(f"Duración total del proceso (fallido): {overall_duration:.2f} segundos.", "ERROR")
            self.raiz.after(0, lambda: messagebox.showerror("Fallo Total", f"No se pudo completar el backup después de {MAX_REINTENTOS} intentos."))
        
        # Siempre rehabilitar el botón de backup al final del proceso completo.
        # Se usa self.raiz.after para asegurar que se ejecuta en el hilo principal de Tkinter.
        self.raiz.after(0, lambda: self.boton_backup.config(state=tk.NORMAL))

    # ESTE MÉTODO DEBE ESTAR CORRECTAMENTE INDENTADO COMO MÉTODO DE LA CLASE
    def iniciar_proceso_backup_con_reintentos_en_hilo(self):
        """
        Función llamada cuando el usuario presiona el botón de backup.
        Deshabilita el botón e inicia el `_bucle_trabajador_backup` en un nuevo hilo
        para no bloquear la interfaz gráfica.
        """
        self.boton_backup.config(state=tk.DISABLED) # Deshabilitar inmediatamente
        # Limpiar logs anteriores de la GUI para mejor legibilidad en cada ejecución
        self.texto_logs.config(state=tk.NORMAL)
        self.texto_logs.delete('1.0', tk.END)
        self.texto_logs.config(state=tk.DISABLED)

        self.loguear_mensaje("Iniciando proceso de backup con reintentos...", "INFO")

        # Crear un nuevo hilo que ejecutará el bucle de trabajo.
        # `daemon=True` permite que el programa principal termine incluso si este hilo sigue corriendo
        # (aunque con `executor.shutdown(wait=True)` en el cierre, intentamos que terminen).
        worker_thread = threading.Thread(target=self._bucle_trabajador_backup, daemon=True)
        worker_thread.start() # Iniciar la ejecución del hilo

    def agregar_log_gui(self, mensaje_gui_formateado):
        """
        Añade un mensaje al widget ScrolledText de la GUI.
        Esta función SIEMPRE debe ser llamada desde el hilo principal de Tkinter.
        `loguear_mensaje` se encarga de esto usando `self.raiz.after` si es necesario.
        """
        if not self.raiz.winfo_exists(): # Prevenir error si la ventana ya se cerró
            return
        self.texto_logs.config(state=tk.NORMAL)
        self.texto_logs.insert(tk.END, mensaje_gui_formateado)
        self.texto_logs.see(tk.END)
        self.texto_logs.config(state=tk.DISABLED)
        # self.raiz.update_idletasks() # Generalmente no es necesario con root.after

    def loguear_mensaje(self, mensaje_original, nivel="INFO"):
        """
        Función centralizada para loguear mensajes:
        1. Escribe al archivo de log (usando el módulo `logging`).
        2. Muestra en el área de texto de la GUI (de forma segura para hilos).
        """
        # Formatear mensaje para la GUI, incluyendo el nivel
        mensaje_para_gui = f"[{nivel.upper()}] {mensaje_original}\n"

        # Escribir al archivo de log
        if nivel.upper() == "ERROR":
            logging.error(mensaje_original)
        elif nivel.upper() == "WARNING":
            logging.warning(mensaje_original)
        elif nivel.upper() == "CRITICAL": # Añadido para EXCEPTION_IN_LOGIC
            logging.critical(mensaje_original)
        else:  # INFO o cualquier otro
            logging.info(mensaje_original)
        
        # Actualizar la GUI de forma segura para hilos
        if threading.current_thread() is threading.main_thread():
            # Si ya estamos en el hilo principal, actualizamos directamente
            if self.raiz.winfo_exists(): # Solo si la ventana aún existe
                 self.agregar_log_gui(mensaje_para_gui)
        else:
            # Si estamos en otro hilo, programamos la actualización en el hilo principal
            # after(0, ...) lo pone en la cola de eventos de Tkinter para ejecutarlo tan pronto como sea posible.
            if self.raiz.winfo_exists(): # Solo si la ventana aún existe
                self.raiz.after(0, self.agregar_log_gui, mensaje_para_gui)

# --- Código principal para ejecutar la aplicación ---
if __name__ == "__main__":
    configurar_logging()  # Configurar el logging al inicio

    ventana_principal_tk = tk.Tk()  # Crear la ventana raíz
    app_gui = AppBackup(ventana_principal_tk)  # Crear la instancia de la aplicación

    # Verificar si la ventana todavía existe.
    # Podría haber sido destruida en AppBackup.__init__ si no es un repo Git.
    if ventana_principal_tk.winfo_exists():
        try:
            ventana_principal_tk.mainloop()  # Iniciar el bucle de eventos de Tkinter
            logging.info("Aplicación de backup cerrada por el usuario (mainloop terminado).")
        except KeyboardInterrupt:
            logging.info("Aplicación interrumpida por el usuario (Ctrl+C).")
            if hasattr(app_gui, 'al_cerrar_ventana'): # Intentar cierre limpio
                app_gui.al_cerrar_ventana()
        except Exception as e:
            logging.exception(f"Error inesperado en el mainloop de Tkinter: {e}")
            if hasattr(app_gui, 'al_cerrar_ventana'): # Intentar cierre limpio
                app_gui.al_cerrar_ventana()
    else:
        logging.warning("La aplicación no se inició completamente (ventana no existe al llegar al mainloop).")
    
    # Intento final de cerrar el executor si __init__ falló antes de asignar al_cerrar_ventana
    # o si el mainloop terminó abruptamente sin llamar a al_cerrar_ventana.
    if hasattr(app_gui, 'executor') and app_gui.executor and not app_gui.executor._shutdown:
        logging.info("Asegurando cierre del ThreadPoolExecutor al finalizar el script.")
        app_gui.executor.shutdown(wait=False, cancel_futures=True)

    logging.info("Script de aplicación de backup finalizado.")
    #######