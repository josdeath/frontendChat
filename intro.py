# app_backup.py
import tkinter as tk  # Biblioteca para crear interfaces gráficas de usuario (GUI)
from tkinter import scrolledtext, messagebox  # Widgets específicos de Tkinter
import logging  # Para registrar eventos y mensajes de la aplicación
import subprocess  # Para ejecutar comandos externos del sistema (como Git)
import os  # Para interactuar con el sistema operativo (ej. verificar rutas)
import datetime  # Para trabajar con fechas y horas (ej. para mensajes de commit)

# --- Configuración Global ---
ARCHIVO_LOG = "backup_git.log"  # Nombre del archivo donde se guardarán los logs

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
        self.raiz = ventana_raiz  # Guardar una referencia a la ventana principal de Tkinter
        self.raiz.title("Herramienta de Backup a Git")  # Establecer el título de la ventana
        self.raiz.geometry("600x450")  # Establecer las dimensiones iniciales de la ventana (ancho x alto)

        # --- Verificación inicial: ¿Estamos en un repositorio Git? ---
        if not os.path.exists(".git"):
            # Si no se encuentra el directorio .git, no estamos en la raíz de un repo Git.
            self.raiz.withdraw()  # Ocultar la ventana principal para que no se vea brevemente
            messagebox.showerror("Error de Repositorio",
                                 "Este script debe ejecutarse desde la raíz de un repositorio Git.")
            logging.error("La aplicación no se inició desde la raíz de un repositorio Git.")
            self.raiz.destroy()  # Cerrar la ventana de Tkinter completamente
            return  # Salir del constructor para evitar que la app continúe

        # --- Creación de los Widgets (componentes de la GUI) ---
        self.etiqueta_bienvenida = tk.Label(self.raiz, text="Bienvenido a la Herramienta de Backup")
        self.etiqueta_bienvenida.pack(pady=10)  # Añadir la etiqueta a la ventana con un padding vertical

        self.boton_backup = tk.Button(
            self.raiz,
            text="Iniciar Backup a GitHub",
            command=self.iniciar_proceso_backup,  # Función que se llamará al hacer clic
            font=("Arial", 12, "bold"), # Estilo de fuente
            bg="lightblue", # Color de fondo
            pady=10 # Padding interno vertical
        )
        self.boton_backup.pack(pady=10, fill=tk.X) # fill=tk.X hace que el botón se expanda horizontalmente

        self.etiqueta_logs = tk.Label(self.raiz, text="Logs de Operación:")
        self.etiqueta_logs.pack(pady=(5, 0), anchor='w', padx=10) # anchor='w' alinea a la izquierda

        self.texto_logs = scrolledtext.ScrolledText(
            self.raiz,
            height=15,  # Altura en líneas de texto
            wrap=tk.WORD,  # Ajustar texto a nivel de palabra
            state=tk.DISABLED  # Empezar deshabilitado para que el usuario no escriba directamente
        )
        self.texto_logs.pack(pady=5, padx=10, fill=tk.BOTH, expand=True) # fill y expand hacen que se ajuste al tamaño de la ventana

        # Mensaje inicial en los logs al arrancar la aplicación (si pasó la verificación de .git)
        self.loguear_mensaje("Aplicación de backup iniciada en un repositorio Git.")

    def ejecutar_comando_git(self, comando_args, nombre_operacion="Comando Git"):
        """
        Ejecuta un comando Git especificado usando subprocess.
        Captura y loguea la salida estándar (stdout), la salida de error (stderr) y el código de retorno.

        Args:
            comando_args (list): Una lista de strings representando el comando y sus argumentos.
                                 Ej: ["git", "status", "--porcelain"]
            nombre_operacion (str): Un nombre descriptivo para la operación (usado en logs).

        Returns:
            tuple: (stdout_str, stderr_str, codigo_retorno_int)
                   Retorna -1, -2, o -3 para errores específicos de esta función.
        """
        try:
            self.loguear_mensaje(f"Ejecutando: {' '.join(comando_args)}", nivel="INFO")
            # Iniciar el proceso del comando Git
            proceso = subprocess.Popen(
                comando_args,
                stdout=subprocess.PIPE,  # Capturar la salida estándar
                stderr=subprocess.PIPE,  # Capturar la salida de error
                text=True,  # Decodificar stdout/stderr como texto (UTF-8 por defecto)
                cwd=os.getcwd()  # Asegurar que el comando se ejecute en el directorio actual
            )
            # Esperar a que el comando termine y obtener sus salidas.
            # Timeout para evitar que la aplicación se congele indefinidamente.
            stdout, stderr = proceso.communicate(timeout=120)  # 120 segundos = 2 minutos
            codigo_retorno = proceso.returncode  # Código de salida del comando (0 usualmente es éxito)

            # Preparar mensaje de log detallado
            mensaje_log_completo = f"{nombre_operacion} finalizado. Código: {codigo_retorno}\n"
            if stdout:
                mensaje_log_completo += f"Salida Estándar:\n{stdout.strip()}\n"
            if stderr:
                mensaje_log_completo += f"Salida de Error:\n{stderr.strip()}\n"

            # Loguear basado en el código de retorno
            if codigo_retorno == 0:
                self.loguear_mensaje(mensaje_log_completo, nivel="INFO")
            else:
                # Caso especial: "nothing to commit" de 'git commit' devuelve 1 pero no es un error crítico para nosotros.
                if nombre_operacion == "Commit" and "nothing to commit" in stderr.lower():
                    self.loguear_mensaje(mensaje_log_completo + "INFO: No había cambios para commitear.", "WARNING")
                    return stdout, stderr, 0  # Tratar como éxito para el flujo de la app, sobreescribiendo el código.
                else:
                    # Es un error real del comando Git
                    self.loguear_mensaje(mensaje_log_completo, nivel="ERROR")
            return stdout, stderr, codigo_retorno

        except FileNotFoundError:
            # El ejecutable 'git' no se encontró en el PATH del sistema.
            msg_error = "Error: El comando 'git' no se encontró. ¿Está Git instalado y en el PATH?"
            self.loguear_mensaje(msg_error, "ERROR")
            messagebox.showerror("Error de Git", msg_error)
            return "", "Git no encontrado", -1  # Código de error personalizado
        except subprocess.TimeoutExpired:
            # El comando Git tardó demasiado en ejecutarse.
            msg_error = f"La operación '{nombre_operacion}' excedió el tiempo de espera (120s) y fue cancelada."
            self.loguear_mensaje(msg_error, "ERROR")
            messagebox.showerror("Timeout", msg_error)
            return "", "Comando Git excedió el tiempo de espera", -2
        except Exception as e:
            # Cualquier otro error inesperado durante la ejecución del subproceso.
            msg_error = f"Error inesperado ejecutando '{nombre_operacion}': {e}"
            self.loguear_mensaje(msg_error, "ERROR")
            messagebox.showerror("Error Inesperado", msg_error)
            return "", str(e), -3

    def iniciar_proceso_backup(self):
        """
        Orquesta el proceso completo de backup:
        1. Verifica el estado del repositorio.
        2. Si hay cambios, ejecuta 'git add .'.
        3. Luego ejecuta 'git commit -m "mensaje"'.
        4. Finalmente, si el commit fue exitoso y hubo cambios, ejecuta 'git push'.
        Maneja errores en cada paso y actualiza la GUI.
        """
        self.loguear_mensaje("--- Iniciando proceso de backup ---", "INFO")
        self.boton_backup.config(state=tk.DISABLED)  # Deshabilitar botón para evitar clics múltiples
        hay_errores_en_proceso = False  # Bandera para rastrear si ocurrió algún error

        # --- 1. Verificar estado del repositorio Git ---
        self.loguear_mensaje("Verificando estado del repositorio...", "INFO")
        stdout_status, stderr_status, rc_status = self.ejecutar_comando_git(
            ["git", "status", "--porcelain"],  # --porcelain da salida fácil de analizar
            "Verificar Estado Git"
        )

        if rc_status != 0: # rc_status sería > 0 para error de git, o < 0 para error de ejecutar_comando_git
            self.loguear_mensaje("Error al verificar el estado de Git. Abortando backup.", "ERROR")
            # El messagebox de error ya se habrá mostrado desde ejecutar_comando_git si rc_status < 0
            hay_errores_en_proceso = True
        elif not stdout_status.strip():  # Si stdout está vacío, no hay cambios ni archivos no rastreados.
            self.loguear_mensaje("No hay cambios pendientes en el repositorio.", "INFO")
            messagebox.showinfo("Sin Cambios", "No hay cambios para respaldar.")
            # No hay errores, pero tampoco trabajo que hacer. El proceso termina aquí.
        else:
            # Hay cambios o archivos no rastreados. Procedemos con el backup.
            self.loguear_mensaje(f"Cambios detectados o archivos no rastreados:\n{stdout_status.strip()}", "INFO")
            messagebox.showinfo("Cambios Detectados", "Se procederá con el backup de los cambios.")

            # --- 2. Añadir todos los cambios al staging area (git add .) ---
            # Este paso solo se ejecuta si la verificación de estado fue exitosa Y hubo cambios.
            if not hay_errores_en_proceso:
                self.loguear_mensaje("Añadiendo todos los cambios al staging area (git add .)...", "INFO")
                # Usamos '_' para stdout_add ya que no lo necesitamos directamente aquí.
                _, stderr_add, rc_add = self.ejecutar_comando_git(["git", "add", "."], "Git Add")
                if rc_add != 0:
                    self.loguear_mensaje("Error durante 'git add .'. Abortando backup.", "ERROR")
                    hay_errores_en_proceso = True

            # --- 3. Realizar Commit ---
            # Este paso solo se ejecuta si 'git add' fue exitoso (o no necesario si no hubo errores previos).
            if not hay_errores_en_proceso:
                # Generar un mensaje de commit dinámico
                current_date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # Podrías añadir un número de backup aquí si lo gestionas.
                commit_message = f"Backup automático - {current_date_str}"
                self.loguear_mensaje(f"Realizando commit con mensaje: '{commit_message}'...", "INFO")

                _, stderr_commit, rc_commit = self.ejecutar_comando_git(
                    ["git", "commit", "-m", commit_message], "Git Commit"
                )

                if rc_commit != 0:
                    # Si rc_commit es != 0 aquí, significa que hubo un error real en 'git commit',
                    # ya que "nothing to commit" es manejado por ejecutar_comando_git para devolver 0.
                    self.loguear_mensaje("Error durante 'git commit'. Abortando backup.", "ERROR")
                    hay_errores_en_proceso = True
                elif "nothing to commit" in stderr_commit.lower() and rc_commit == 0:
                    # Este caso es cuando `git add .` no resultó en cambios reales para el commit.
                    self.loguear_mensaje("No había cambios para commitear (detectado después de 'git add').", "WARNING")
                    messagebox.showwarning("Sin Cambios Reales",
                                           "No se realizaron nuevos commits ya que no había cambios efectivos tras 'git add'.")
                    # No se considera un error que detenga el proceso, pero no se hará push.
                else:
                    # Commit exitoso y hubo cambios reales.
                    self.loguear_mensaje("Commit realizado exitosamente.", "INFO")

                    # --- 4. Realizar Push al repositorio remoto (git push) ---
                    # Solo si el commit fue exitoso, hubo cambios reales, y no hubo errores previos.
                    # La condición `not hay_errores_en_proceso` cubre los errores de status y add.
                    # El flujo de `if/elif/else` del commit asegura que solo llegamos aquí si hubo un commit real.
                    self.loguear_mensaje("Realizando push al repositorio remoto (git push)...", "INFO")
                    _, stderr_push, rc_push = self.ejecutar_comando_git(["git", "push"], "Git Push")
                    if rc_push != 0:
                        self.loguear_mensaje("Error durante 'git push'.", "ERROR")
                        messagebox.showerror("Error de Push",
                                             "Falló el 'git push'. Revisa los logs y tu conexión/configuración remota.")
                        hay_errores_en_proceso = True
                    else:
                        self.loguear_mensaje("Push realizado exitosamente.", "INFO")
                        messagebox.showinfo("Éxito", "Backup completado y subido exitosamente.")

        # --- Finalización del proceso de backup ---
        self.boton_backup.config(state=tk.NORMAL)  # Rehabilitar el botón de backup
        if hay_errores_en_proceso:
            self.loguear_mensaje("--- Proceso de backup finalizado con errores. ---", "ERROR")
        elif not stdout_status.strip() and rc_status == 0: # Si no hubo cambios desde el inicio
            self.loguear_mensaje("--- Proceso de backup finalizado (sin cambios detectados). ---", "INFO")
        else: # Si hubo cambios y (potencialmente) todo fue exitoso o se detuvo por "nothing to commit"
            self.loguear_mensaje("--- Proceso de backup finalizado. ---", "INFO")


    # def accion_backup_marcador_posicion(self): # Método antiguo, se puede eliminar si no se usa
    #     self.loguear_mensaje("Botón de backup presionado (función por implementar)")

    def agregar_log_gui(self, mensaje_gui_formateado):
        """
        Añade un mensaje al widget ScrolledText de la GUI.
        Esta función debe ser llamada de forma segura si se usa desde hilos (no es el caso aquí aún).
        """
        self.texto_logs.config(state=tk.NORMAL)  # Habilitar edición
        self.texto_logs.insert(tk.END, mensaje_gui_formateado)  # Insertar mensaje al final
        self.texto_logs.see(tk.END)  # Auto-scroll para ver el último mensaje
        self.texto_logs.config(state=tk.DISABLED)  # Deshabilitar edición nuevamente

    def loguear_mensaje(self, mensaje_original, nivel="INFO"):
        """
        Función centralizada para loguear mensajes:
        1. Los escribe en el archivo de log (usando el módulo logging).
        2. Los muestra en el área de texto de la GUI.
        """
        # Formatear mensaje para la GUI, incluyendo el nivel
        mensaje_para_gui = f"[{nivel.upper()}] {mensaje_original}\n"

        # Escribir al archivo de log usando el sistema de logging de Python
        if nivel.upper() == "ERROR":
            logging.error(mensaje_original)
        elif nivel.upper() == "WARNING":
            logging.warning(mensaje_original)
        else:  # Por defecto, o si es "INFO"
            logging.info(mensaje_original)

        # Mostrar en la GUI
        # En una app más compleja con hilos, esta llamada a la GUI debería hacerse
        # de forma segura (ej. con root.after() si se llama desde otro hilo).
        # Aquí, como todo es secuencial en el hilo principal, es seguro.
        self.agregar_log_gui(mensaje_para_gui)

# --- Código principal para ejecutar la aplicación ---
if __name__ == "__main__":
    configurar_logging()  # Configurar el logging antes de que nada más suceda

    ventana_principal_tk = tk.Tk()  # Crear la ventana raíz de Tkinter
    app_gui = AppBackup(ventana_principal_tk)  # Crear una instancia de nuestra aplicación

    # Verificar si la ventana todavía existe. Podría haber sido destruida en AppBackup.__init__
    # si no se estaba en un repositorio Git.
    if ventana_principal_tk.winfo_exists():
        ventana_principal_tk.mainloop()  # Iniciar el bucle de eventos de Tkinter
        # Esta línea se ejecuta cuando la ventana principal se cierra limpiamente
        logging.info("Aplicación de backup cerrada por el usuario.")
    else:
        # Esto se logueará si, por ejemplo, __init__ llamó a destroy()
        logging.warning("La aplicación no se inició completamente (ej. no es un repo Git o hubo un error temprano).")

    # Este log es un poco redundante si el de arriba se ejecuta, pero sirve como fallback
    # o si el cierre no fue por el mainloop terminando normalmente.
    # logging.info("Script de aplicación de backup finalizado.") # Podríamos omitir este