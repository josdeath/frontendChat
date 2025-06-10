# app_backup.py
"""
Módulo que implementa una aplicación de escritorio con Tkinter para realizar backups
a un repositorio Git.

Esta aplicación cuenta con una interfaz gráfica para el usuario, realiza las
operaciones de Git en un hilo secundario para no bloquear la GUI, y gestiona
reintentos automáticos con timeouts en caso de fallo en la conexión o en los
comandos de Git.
"""

# Biblioteca para crear interfaces gráficas de usuario (GUI)
import tkinter as tk
from tkinter import scrolledtext, messagebox  # Widgets específicos de Tkinter
import logging  # Para registrar eventos y mensajes de la aplicación
import subprocess  # Para ejecutar comandos externos del sistema (como Git)
import os  # Para interactuar con el sistema operativo (ej. verificar rutas)
# Para trabajar con fechas y horas (ej. para mensajes de commit)
import datetime
import time  # Para manejar tiempos de espera y pausas en la ejecución
import threading  # Para manejar la concurrencia y ejecutar tareas en segundo plano
# Para manejar timeout por intentos
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import socket  # Para verificar la conexión de red

# --- Configuración Global ---
ARCHIVO_LOG = "backup_git.log"  # Nombre del archivo donde se guardarán los logs
MAX_REINTENTOS = 3  # Número máximo de reintentos para el proceso de backup completo
# 5 minutos de timeout para cada intento de backup
TIMEOUT_POR_INTENTO_SEGUNDOS = 5 * 60
RETRASO_ENTRE_REINTENTOS_SEGUNDOS = 10  # Tiempo de espera entre reintentos
# Archivo para guardar información del backup
ARCHIVO_INFO_BACKUP = "backup_info.txt"

# --- Configuración del Logging ---


def configurar_logging():
    """
    Configura el sistema de logging para que los mensajes se guarden en un archivo.
    Opcionalmente, también se pueden mostrar en la consola donde se ejecuta el script.
    """
    logging.basicConfig(
        # Nivel mínimo de mensajes a registrar (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        level=logging.INFO,
        # Formato de cada línea de log
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            # Handler para escribir los logs en el archivo especificado
            logging.FileHandler(ARCHIVO_LOG),
            # logging.StreamHandler()  # Descomentar esta línea para ver los logs también en la consola
        ]
    )

# --- Funciones Auxiliares de Backup ---


def get_next_backup_number(log_fn):
    """
    Obtiene el siguiente número de backup a utilizar.
    Lee el último número guardado en ARCHIVO_INFO_BACKUP y le suma 1.
    Si el archivo no existe o está corrupto, empieza desde 1.
    """
    if not os.path.exists(ARCHIVO_INFO_BACKUP):
        if log_fn:
            log_fn(
                f"Archivo '{ARCHIVO_INFO_BACKUP}' no encontrado, iniciando contador de backup en 1.", "INFO")
        return 1
    try:
        with open(ARCHIVO_INFO_BACKUP, 'r', encoding='utf-8') as f:  # Abre el archivo en modo lectura
            last_backup_number = int(f.read().strip())
            next_number = last_backup_number + 1  # Incrementa el número de backup
            if log_fn:
                log_fn(
                    # Loguea el número de backup
                    f"Último número de backup leído: {last_backup_number}. Siguiente número: {next_number}", "INFO")
            return next_number
    except (ValueError, FileNotFoundError) as e:
        if log_fn:
            log_fn(
                f"Error al leer el número de backup de '{ARCHIVO_INFO_BACKUP}': {e}. Reiniciando a 1.", "WARNING")
        return 1


def save_backup_number(number, log_fn):
    """
    Guarda el número de backup proporcionado en ARCHIVO_INFO_BACKUP.
    """
    try:
        with open(ARCHIVO_INFO_BACKUP, 'w', encoding='utf-8') as f:
            f.write(str(number))
        if log_fn:
            log_fn(
                f"Número de backup {number} guardado en '{ARCHIVO_INFO_BACKUP}'.", "INFO")
    except IOError as e:
        logging.error(
            f"Error crítico al guardar el número de backup {number} en '{ARCHIVO_INFO_BACKUP}': {e}")
        if log_fn:
            log_fn(
                f"Error al guardar el número de backup {number}: {e}", "ERROR")


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
        if log_fn:
            log_fn("Verificando conexión a GitHub (github.com:443)...", "INFO")
        socket.create_connection(("github.com", 443), timeout=timeout)
        if log_fn:
            log_fn("Conexión a GitHub establecida correctamente.", "INFO")
        return True
    except socket.timeout:
        if log_fn:
            log_fn(
                "No se pudo conectar a GitHub: Timeout durante el intento de conexión.", "ERROR")
        return False
    except (socket.error, OSError) as e:
        if log_fn:
            log_fn(f"No se pudo conectar a GitHub: {e}", "ERROR")
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
        self.raiz.title("Herramienta de Backup a Git con Reintentos")
        self.raiz.geometry("700x500")

        self.executor = ThreadPoolExecutor(max_workers=1)

        if not os.path.exists(".git"):
            self.raiz.withdraw()
            messagebox.showerror("Error de Repositorio",
                                 "Este script debe ejecutarse desde la raíz de un repositorio Git.")
            logging.error(
                "La aplicación no se inició desde la raíz de un repositorio Git.")
            if hasattr(self, 'executor') and self.executor and not self.executor._shutdown:
                self.executor.shutdown(wait=False, cancel_futures=True)
            self.raiz.destroy()
            return

        self.etiqueta_bienvenida = tk.Label(
            self.raiz, text="Bienvenido a la Herramienta de Backup con Reintentos")
        self.etiqueta_bienvenida.pack(pady=10)

        self.boton_backup = tk.Button(
            self.raiz,
            text="Iniciar Backup a GitHub",
            command=self.iniciar_proceso_backup_con_reintentos_en_hilo,
            font=("Arial", 12, "bold"),
            bg="lightblue",
            pady=10
        )
        self.boton_backup.pack(pady=10, fill=tk.X, padx=10)

        self.etiqueta_logs = tk.Label(self.raiz, text="Logs de Operación:")
        self.etiqueta_logs.pack(pady=(5, 0), anchor='w', padx=10)

        self.texto_logs = scrolledtext.ScrolledText(
            self.raiz,
            height=18,
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.texto_logs.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)

        self.loguear_mensaje(
            "Aplicación de backup iniciada en un repositorio Git.")

        self.raiz.protocol("WM_DELETE_WINDOW", self.al_cerrar_ventana)

    def al_cerrar_ventana(self):
        """
        Se llama cuando el usuario intenta cerrar la ventana.
        Se asegura de que el ThreadPoolExecutor se cierre limpiamente.
        """
        self.loguear_mensaje("Cerrando aplicación...", "INFO")
        if hasattr(self, 'executor') and self.executor and not self.executor._shutdown:
            self.loguear_mensaje(
                "Intentando cerrar el ThreadPoolExecutor...", "INFO")
            self.executor.shutdown(wait=False, cancel_futures=True)
            self.loguear_mensaje("ThreadPoolExecutor cerrado.", "INFO")
        self.raiz.destroy()

    def ejecutar_comando_git(self, comando_args, nombre_operacion="Comando Git"):
        """
        Ejecuta un comando Git y loguea la salida.
        """
        try:
            self.loguear_mensaje(
                f"Ejecutando: {' '.join(comando_args)}", nivel="INFO")
            proceso = subprocess.Popen(
                comando_args,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, cwd=os.getcwd()
            )
            stdout, stderr = proceso.communicate(timeout=120)
            codigo_retorno = proceso.returncode

            mensaje_log_completo = f"{nombre_operacion} finalizado. Código: {codigo_retorno}\n"
            if stdout:
                mensaje_log_completo += f"Salida Estándar:\n{stdout.strip()}\n"
            if stderr:
                mensaje_log_completo += f"Salida de Error:\n{stderr.strip()}\n"

            if codigo_retorno == 0:
                self.loguear_mensaje(mensaje_log_completo, nivel="INFO")
            else:
                if "nothing to commit" in stderr.lower():
                    self.loguear_mensaje(
                        mensaje_log_completo + "INFO: No había cambios para commitear.", "WARNING")
                    return stdout, stderr, 0  # Se trata como un caso especial de éxito
                self.loguear_mensaje(mensaje_log_completo, nivel="ERROR")
            return stdout, stderr, codigo_retorno
        except FileNotFoundError:
            msg_error = "Error: El comando 'git' no se encontró. ¿Está Git instalado y en el PATH?"
            self.loguear_mensaje(msg_error, "ERROR")
            return "", "Git no encontrado", -1
        except subprocess.TimeoutExpired:
            msg_error = f"La operación '{nombre_operacion}' excedió el tiempo de espera (120s) y fue cancelada."
            self.loguear_mensaje(msg_error, "ERROR")
            return "", "Comando Git excedió el tiempo de espera", -2
        except Exception as e:
            msg_error = f"Error inesperado ejecutando '{nombre_operacion}': {e}"
            self.loguear_mensaje(msg_error, "ERROR")
            return "", str(e), -3

    def _realizar_intento_backup_logica(self):
        """
        Contiene la lógica de un solo intento de backup.
        Diseñada para ser ejecutada en un hilo por ThreadPoolExecutor.
        """
        self.loguear_mensaje(
            "Iniciando intento de lógica de backup...", "INFO")

        numero_backup_actual = get_next_backup_number(self.loguear_mensaje)

        if not check_github_connection(self.loguear_mensaje):
            return "CONNECTION_ERROR"

        stdout_status, _, rc_status = self.ejecutar_comando_git(
            ["git", "status", "--porcelain"], "Verificar Estado Git"
        )
        if rc_status != 0:
            return "GIT_STATUS_ERROR"
        if not stdout_status.strip():
            self.loguear_mensaje(
                "No hay cambios pendientes en el repositorio.", "INFO")
            return "NO_CHANGES"
        self.loguear_mensaje(
            f"Cambios detectados o archivos no rastreados:\n{stdout_status.strip()}", "INFO")

        _, _, rc_add = self.ejecutar_comando_git(
            ["git", "add", "."], "Git Add")
        if rc_add != 0:
            return "GIT_ADD_ERROR"

        current_date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_message = f"Backup #{numero_backup_actual} - {current_date_str}"
        self.loguear_mensaje(
            f"Realizando commit con mensaje: '{commit_message}'...", "INFO")
        _, stderr_commit, rc_commit = self.ejecutar_comando_git(
            ["git", "commit", "-m", commit_message], "Git Commit"
        )
        if rc_commit != 0:
            if "nothing to commit" in stderr_commit.lower():
                self.loguear_mensaje(
                    "No había cambios para commitear (detectado después de 'git add').", "WARNING")
                return "NO_CHANGES_AFTER_ADD"
            return "GIT_COMMIT_ERROR"
        self.loguear_mensaje("Commit realizado exitosamente.", "INFO")

        self.loguear_mensaje(
            "Realizando push al repositorio remoto (git push)...", "INFO")
        _, _, rc_push = self.ejecutar_comando_git(["git", "push"], "Git Push")
        if rc_push != 0:
            return "GIT_PUSH_ERROR"
        self.loguear_mensaje("Push realizado exitosamente.", "INFO")

        save_backup_number(numero_backup_actual, self.loguear_mensaje)
        return "SUCCESS"

    def _bucle_trabajador_backup(self):
        """
        Gestiona los reintentos para el proceso de backup en un hilo separado.
        """
        overall_start_time = time.time()
        success = False

        for attempt in range(1, MAX_REINTENTOS + 1):
            self.loguear_mensaje(
                f"--- Iniciando Intento de Backup {attempt}/{MAX_REINTENTOS} ---", "INFO")
            attempt_start_time = time.time()

            future = self.executor.submit(self._realizar_intento_backup_logica)
            status_intento = "UNKNOWN_ERROR"
            try:
                status_intento = future.result(
                    timeout=TIMEOUT_POR_INTENTO_SEGUNDOS)
            except FutureTimeoutError:
                status_intento = "TIMEOUT_ATTEMPT"
                self.loguear_mensaje(
                    f"Intento {attempt} excedió el tiempo límite de {TIMEOUT_POR_INTENTO_SEGUNDOS / 60:.0f} minutos.", "ERROR")
                if future.running():
                    future.cancel()
            except Exception as e:
                status_intento = "EXCEPTION_IN_LOGIC"
                self.loguear_mensaje(
                    f"Excepción no controlada durante el intento {attempt}: {e}", "CRITICAL")
                logging.exception(
                    f"Excepción no controlada en _bucle_trabajador_backup, intento {attempt}")

            attempt_duration = time.time() - attempt_start_time
            self.loguear_mensaje(
                f"Intento {attempt} finalizado en {attempt_duration:.2f}s con estado: {status_intento}", "INFO")

            if status_intento == "SUCCESS":
                overall_duration = time.time() - overall_start_time
                self.loguear_mensaje(
                    f"Backup completado exitosamente después de {attempt} intento(s).", "INFO")
                self.loguear_mensaje(
                    f"Duración total del proceso: {overall_duration:.2f} segundos.", "INFO")
                self.raiz.after(0, lambda: messagebox.showinfo(
                    "Éxito", f"Backup realizado con éxito en el intento {attempt}."))
                success = True
                break

            elif status_intento in ["NO_CHANGES", "NO_CHANGES_AFTER_ADD"]:
                self.loguear_mensaje("No hay cambios para el backup.", "INFO")
                self.raiz.after(0, lambda: messagebox.showinfo(
                    "Sin Cambios", "No se detectaron cambios para el backup."))
                success = True
                break

            else:
                self.loguear_mensaje(
                    f"Intento {attempt} falló. Estado: {status_intento}", "ERROR")
                if attempt < MAX_REINTENTOS:
                    self.loguear_mensaje(
                        f"Esperando {RETRASO_ENTRE_REINTENTOS_SEGUNDOS}s antes del próximo intento...", "INFO")
                    time.sleep(RETRASO_ENTRE_REINTENTOS_SEGUNDOS)

        if not success:
            overall_duration = time.time() - overall_start_time
            self.loguear_mensaje(
                f"Todos los {MAX_REINTENTOS} intentos de backup fallaron.", "ERROR")
            self.loguear_mensaje(
                f"Duración total del proceso (fallido): {overall_duration:.2f} segundos.", "ERROR")
            self.raiz.after(0, lambda: messagebox.showerror(
                "Fallo Total", f"No se pudo completar el backup después de {MAX_REINTENTOS} intentos."))

        self.raiz.after(0, lambda: self.boton_backup.config(state=tk.NORMAL))

    def iniciar_proceso_backup_con_reintentos_en_hilo(self):
        """
        Función llamada por el botón de backup. Inicia el proceso en un hilo.
        """
        self.boton_backup.config(state=tk.DISABLED)
        self.texto_logs.config(state=tk.NORMAL)
        self.texto_logs.delete('1.0', tk.END)
        self.texto_logs.config(state=tk.DISABLED)

        self.loguear_mensaje(
            "Iniciando proceso de backup con reintentos...", "INFO")

        worker_thread = threading.Thread(
            target=self._bucle_trabajador_backup, daemon=True)
        worker_thread.start()

    def agregar_log_gui(self, mensaje_gui_formateado):
        """
        Añade un mensaje al widget ScrolledText de la GUI de forma segura.
        """
        if not self.raiz.winfo_exists():
            return
        self.texto_logs.config(state=tk.NORMAL)
        self.texto_logs.insert(tk.END, mensaje_gui_formateado)
        self.texto_logs.see(tk.END)
        self.texto_logs.config(state=tk.DISABLED)

    def loguear_mensaje(self, mensaje_original, nivel="INFO"):
        """
        Función centralizada para loguear en archivo y en la GUI.
        """
        mensaje_para_gui = f"[{nivel.upper()}] {mensaje_original}\n"

        if nivel.upper() == "ERROR":
            logging.error(mensaje_original)
        elif nivel.upper() == "WARNING":
            logging.warning(mensaje_original)
        elif nivel.upper() == "CRITICAL":
            logging.critical(mensaje_original)
        else:
            logging.info(mensaje_original)

        if threading.current_thread() is threading.main_thread():
            if self.raiz.winfo_exists():
                self.agregar_log_gui(mensaje_para_gui)
        else:
            if self.raiz.winfo_exists():
                self.raiz.after(0, self.agregar_log_gui, mensaje_para_gui)


# --- Código principal para ejecutar la aplicación ---
if __name__ == "__main__":
    configurar_logging()

    ventana_principal_tk = tk.Tk()
    app_gui = AppBackup(ventana_principal_tk)

    if ventana_principal_tk.winfo_exists():
        try:
            ventana_principal_tk.mainloop()
            logging.info(
                "Aplicación de backup cerrada por el usuario (mainloop terminado).")
        except KeyboardInterrupt:
            logging.info("Aplicación interrumpida por el usuario (Ctrl+C).")
            if hasattr(app_gui, 'al_cerrar_ventana'):
                app_gui.al_cerrar_ventana()
        except Exception as e:
            logging.exception(
                f"Error inesperado en el mainloop de Tkinter: {e}")
            if hasattr(app_gui, 'al_cerrar_ventana'):
                app_gui.al_cerrar_ventana()
    else:
        logging.warning(
            "La aplicación no se inició completamente (ventana no existe al llegar al mainloop).")

    if hasattr(app_gui, 'executor') and app_gui.executor and not app_gui.executor._shutdown:
        logging.info(
            "Asegurando cierre del ThreadPoolExecutor al finalizar el script.")
        app_gui.executor.shutdown(wait=False, cancel_futures=True)

    logging.info("Script de aplicación de backup finalizado.")
