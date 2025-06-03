import tkinter as tk
from tkinter import messagebox, scrolledtext
import subprocess
import socket
import datetime
import os
import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError # Renombrar para evitar colisión con socket.timeout

# --- Configuración ---
LOG_FILE = "backup_git.log"
BACKUP_INFO_FILE = ".backup_info.txt" # Archivo para guardar el número del último backup
MAX_RETRIES = 20
ATTEMPT_TIMEOUT_SECONDS = 5 * 60  # 5 minutos
RETRY_DELAY_SECONDS = 10 # Tiempo de espera entre reintentos

# --- Configuración del Logging ---
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )

# --- Funciones Auxiliares de Backup ---
def get_next_backup_number():
    if not os.path.exists(BACKUP_INFO_FILE):
        return 1
    try:
        with open(BACKUP_INFO_FILE, 'r') as f:
            return int(f.read().strip()) + 1
    except (ValueError, FileNotFoundError):
        return 1

def save_backup_number(number):
    try:
        with open(BACKUP_INFO_FILE, 'w') as f:
            f.write(str(number))
    except IOError as e:
        logging.error(f"Error al guardar el número de backup: {e}")


def check_github_connection(log_fn, timeout=5):
    """Verifica la conexión a github.com."""
    try:
        socket.create_connection(("github.com", 443), timeout=timeout)
        log_fn("Conexión a GitHub establecida correctamente.", "INFO")
        return True
    except (socket.timeout, socket.error) as e:
        log_fn(f"No se pudo conectar a GitHub: {e}", "ERROR")
        return False

def run_git_command(log_fn, command_args, operation_name="Comando Git"):
    """Ejecuta un comando Git y devuelve su salida y código de retorno."""
    try:
        log_fn(f"Ejecutando: {' '.join(command_args)}", "INFO")
        process = subprocess.Popen(
            command_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.getcwd()
        )
        stdout, stderr = process.communicate(timeout=120) # Timeout interno para comando git (2 min)
        return_code = process.returncode

        log_message = f"{operation_name} finalizado. Código de retorno: {return_code}\n"
        if stdout:
            log_message += f"Salida estándar:\n{stdout.strip()}\n"
        if stderr:
            log_message += f"Salida de error:\n{stderr.strip()}\n"
        
        if return_code == 0:
            log_fn(log_message, "INFO")
        else:
            if operation_name == "Commit" and "nothing to commit" in stderr.lower():
                log_fn(log_message + "No había cambios para commitear.", "WARNING")
                return stdout, stderr, 0 # Tratar "nothing to commit" como éxito
            log_fn(log_message, "ERROR")
            
        return stdout, stderr, return_code
    except FileNotFoundError:
        log_fn("Error: El comando 'git' no se encontró. ¿Está Git instalado y en el PATH?", "ERROR")
        return "", "Git no encontrado", -1
    except subprocess.TimeoutExpired:
        log_fn(f"{operation_name} excedió el tiempo de espera interno (120s).", "ERROR")
        # process.kill() # communicate() ya se encarga de esto
        # stdout, stderr = process.communicate()
        return "", "Comando Git excedió el tiempo de espera", -2
    except Exception as e:
        log_fn(f"Error inesperado ejecutando {operation_name}: {e}", "ERROR")
        return "", str(e), -3

# --- Lógica Principal del Backup (modificada para retornar estado) ---
def perform_backup_logic(log_fn_threaded):
    """
    Realiza un intento de backup.
    Retorna: "SUCCESS", "NO_CHANGES", o un código de error específico como "CONNECTION_ERROR", "GIT_ADD_ERROR", etc.
    """
    start_time = time.time()
    log_fn_threaded("Iniciando intento de backup...", "INFO")

    # 1. Detectar conexión a GitHub
    log_fn_threaded("Verificando conexión a GitHub...", "INFO")
    if not check_github_connection(log_fn_threaded):
        return "CONNECTION_ERROR"

    backup_number = get_next_backup_number()
    current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_message = f"backup {backup_number} - {current_date}"

    # 2. Añadir cambios
    log_fn_threaded("Añadiendo cambios al staging area (git add .)...", "INFO")
    _, stderr_add, rc_add = run_git_command(log_fn_threaded, ["git", "add", "."], "Add")
    if rc_add != 0:
        return "GIT_ADD_ERROR"

    # Verificar si hay cambios
    stdout_status, _, rc_status = run_git_command(log_fn_threaded, ["git", "status", "--porcelain"], "Status Check")
    if rc_status == 0 and not stdout_status.strip():
        log_fn_threaded("No hay cambios para realizar commit. El árbol de trabajo está limpio.", "INFO")
        return "NO_CHANGES"
    elif rc_status != 0:
        log_fn_threaded("Error al verificar el estado de git.", "ERROR")
        # Continuar, el commit fallará si no hay nada y será manejado

    # 3. Commit
    log_fn_threaded(f"Realizando commit con mensaje: '{commit_message}'...", "INFO")
    _, stderr_commit, rc_commit = run_git_command(
        log_fn_threaded, ["git", "commit", "-m", commit_message], "Commit"
    )
    if rc_commit != 0:
        if "nothing to commit" not in stderr_commit.lower(): # Ya manejado por run_git_command
            return "GIT_COMMIT_ERROR"
        else: # "nothing to commit" (run_git_command ya lo trata como rc=0)
            log_fn_threaded("No había cambios para commitear (detectado en commit).", "WARNING")
            return "NO_CHANGES"

    # 4. Push
    log_fn_threaded("Realizando push a GitHub (git push)...", "INFO")
    _, stderr_push, rc_push = run_git_command(log_fn_threaded, ["git", "push"], "Push")
    if rc_push != 0:
        return "GIT_PUSH_ERROR"

    save_backup_number(backup_number)
    duration = time.time() - start_time
    log_fn_threaded(f"Intento de Backup número {backup_number} completado y subido exitosamente en {duration:.2f} segundos.", "INFO")
    return "SUCCESS"


# --- Interfaz Gráfica ---
class BackupApp:
    def __init__(self, root_window):
        self.root = root_window
        root_window.title("Herramienta de Backup a GitHub con Reintentos")
        root_window.geometry("700x450")

        self.main_frame = tk.Frame(root_window, padx=10, pady=10)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.backup_button = tk.Button(
            self.main_frame,
            text="Realizar Backup a GitHub",
            command=self.start_backup_process_threaded,
            font=("Arial", 12, "bold"),
            bg="lightblue",
            pady=10
        )
        self.backup_button.pack(pady=10, fill=tk.X)

        self.status_label = tk.Label(self.main_frame, text="Log de Operaciones:", anchor="w")
        self.status_label.pack(pady=(10,0), fill=tk.X)

        self.status_text = scrolledtext.ScrolledText(
            self.main_frame,
            height=15,
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.status_text.pack(pady=5, fill=tk.BOTH, expand=True)

        self.executor = ThreadPoolExecutor(max_workers=1) # Para ejecutar perform_backup_logic con timeout

    def log_to_gui_and_file(self, message, level="INFO"):
        """Loguea al archivo y a la GUI de forma segura para hilos."""
        timestamped_message_for_file = message # logging ya añade timestamp y nivel
        timestamped_message_for_gui = f"[{level}] {message}\n"
        
        if level == "ERROR":
            logging.error(timestamped_message_for_file)
        elif level == "WARNING":
            logging.warning(timestamped_message_for_file)
        else:
            logging.info(timestamped_message_for_file)
        
        # Actualizar GUI en el hilo principal
        self.root.after(0, self._update_status_widget, timestamped_message_for_gui)

    def _update_status_widget(self, message_line):
        """Actualiza el widget de texto. Debe ser llamado desde el hilo principal."""
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, message_line)
        self.status_text.see(tk.END) # Auto-scroll
        self.status_text.config(state=tk.DISABLED)
        # self.status_text.update_idletasks() # root.after se encarga del ciclo de eventos

    def start_backup_process_threaded(self):
        """Inicia el proceso de backup con reintentos en un hilo separado."""
        self.backup_button.config(state=tk.DISABLED)
        self.status_text.config(state=tk.NORMAL)
        self.status_text.delete('1.0', tk.END)
        self.status_text.config(state=tk.DISABLED)

        self.log_to_gui_and_file("Iniciando proceso de backup con reintentos...", "INFO")

        # Crear y empezar el hilo trabajador
        worker_thread = threading.Thread(target=self._backup_worker_loop, daemon=True)
        worker_thread.start()

    def _backup_worker_loop(self):
        """Contiene el bucle de reintentos. Se ejecuta en un hilo separado."""
        overall_start_time = time.time()
        
        for attempt in range(1, MAX_RETRIES + 1):
            self.log_to_gui_and_file(f"--- Intento de Backup {attempt}/{MAX_RETRIES} ---", "INFO")
            attempt_start_time = time.time()
            
            future = self.executor.submit(perform_backup_logic, self.log_to_gui_and_file)
            
            try:
                # Esperar el resultado con timeout
                result_status = future.result(timeout=ATTEMPT_TIMEOUT_SECONDS)
            except FutureTimeoutError:
                result_status = "TIMEOUT_ATTEMPT"
                self.log_to_gui_and_file(f"Intento {attempt} excedió el tiempo límite de {ATTEMPT_TIMEOUT_SECONDS / 60:.0f} minutos.", "ERROR")
                # Intentar cancelar la tarea (puede que no funcione si está bloqueada en C)
                if future.running():
                    future.cancel() # No garantiza la detención inmediata
            except Exception as e: # Excepción inesperada dentro de perform_backup_logic si no es capturada allí
                result_status = "EXCEPTION_IN_LOGIC"
                self.log_to_gui_and_file(f"Excepción no controlada durante el intento {attempt}: {e}", "CRITICAL")
                logging.exception(f"Excepción no controlada en _backup_worker_loop, intento {attempt}")


            attempt_duration = time.time() - attempt_start_time
            self.log_to_gui_and_file(f"Intento {attempt} finalizado en {attempt_duration:.2f}s con estado: {result_status}", "INFO")

            if result_status == "SUCCESS":
                overall_duration = time.time() - overall_start_time
                self.log_to_gui_and_file(f"Backup completado exitosamente después de {attempt} intento(s).", "INFO")
                self.log_to_gui_and_file(f"Duración total del proceso: {overall_duration:.2f} segundos.", "INFO")
                self.root.after(0, lambda: messagebox.showinfo("Éxito", f"Backup realizado con éxito en el intento {attempt}."))
                break # Salir del bucle de reintentos
            
            elif result_status == "NO_CHANGES":
                overall_duration = time.time() - overall_start_time
                self.log_to_gui_and_file("No hay cambios para el backup.", "INFO")
                self.log_to_gui_and_file(f"Duración total del proceso (sin cambios): {overall_duration:.2f} segundos.", "INFO")
                self.root.after(0, lambda: messagebox.showinfo("Sin Cambios", "No se detectaron cambios para el backup."))
                break # Salir del bucle de reintentos
            
            else: # Cualquier tipo de error o timeout del intento
                self.log_to_gui_and_file(f"Intento {attempt} falló. Estado: {result_status}", "ERROR")
                if attempt < MAX_RETRIES:
                    self.log_to_gui_and_file(f"Esperando {RETRY_DELAY_SECONDS} segundos antes del próximo intento...", "INFO")
                    time.sleep(RETRY_DELAY_SECONDS)
                else:
                    overall_duration = time.time() - overall_start_time
                    self.log_to_gui_and_file(f"Todos los {MAX_RETRIES} intentos de backup fallaron.", "ERROR")
                    self.log_to_gui_and_file(f"Duración total del proceso (fallido): {overall_duration:.2f} segundos.", "ERROR")
                    self.root.after(0, lambda: messagebox.showerror("Fallo Total", f"No se pudo completar el backup después de {MAX_RETRIES} intentos."))
        
        # Siempre rehabilitar el botón al final del proceso (éxito, sin cambios o fallo total)
        self.root.after(0, lambda: self.backup_button.config(state=tk.NORMAL))

    def on_closing(self):
        """Maneja el cierre de la ventana."""
        self.log_to_gui_and_file("Cerrando aplicación de backup...", "INFO")
        self.executor.shutdown(wait=False, cancel_futures=True) # Intenta cancelar tareas pendientes
        self.root.destroy()


if __name__ == "__main__":
    if not os.path.exists(".git"):
        # Mostrar error en una ventana de Tkinter simple si la GUI principal no se va a iniciar
        root_check = tk.Tk()
        root_check.withdraw()
        messagebox.showerror("Error de Repositorio", "Este script debe ejecutarse desde la raíz de un repositorio Git.")
        root_check.destroy()
        print("ERROR: Este script debe ejecutarse desde la raíz de un repositorio Git.")
        exit(1)
        
    setup_logging()
    logging.info("Aplicación de backup iniciada.")
    
    gui_root = tk.Tk()
    app = BackupApp(gui_root)
    gui_root.protocol("WM_DELETE_WINDOW", app.on_closing) # Manejar cierre de ventana
    gui_root.mainloop()
    
    logging.info("Aplicación de backup cerrada limpiamente.")