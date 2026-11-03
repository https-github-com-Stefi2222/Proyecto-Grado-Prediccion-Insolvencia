"""Interfaz de sustentación: inferencia local con el Random Forest ya entrenado.

No requiere SQL Server ni reentrena el modelo. Los perfiles precargados son
ilustrativos: no corresponden a empresas observadas individualmente.
"""
from pathlib import Path
import sys
import tkinter as tk
from tkinter import messagebox, ttk

import joblib
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "python"))  # Módulo del transformador usado al serializar.
RUTA_MODELO = RAIZ / "modelos" / "random_forest_pipeline.joblib"

PERFILES = {
    "A": {
        "razon_corriente": 2.1133,
        "prueba_acida": 1.2860,
        "roa": 0.0295,
        "roe": 0.0692,
        "margen_neto": 0.0491,
        "endeudamiento": 0.4407,
        "apalancamiento": 0.7037,
        "rotacion_activos": 0.5426,
        "rotacion_cartera": 3.7615,
    },
    "B": {
        "razon_corriente": 1.6391,
        "prueba_acida": 0.9358,
        "roa": 0.0087,
        "roe": 0.0389,
        "margen_neto": 0.0087,
        "endeudamiento": 0.6812,
        "apalancamiento": 1.8291,
        "rotacion_activos": 0.8070,
        "rotacion_cartera": 2.9988,
    },
}

NOMBRES = {
    "razon_corriente": "Razón corriente",
    "prueba_acida": "Prueba ácida",
    "roa": "ROA",
    "roe": "ROE",
    "margen_neto": "Margen neto",
    "endeudamiento": "Endeudamiento",
    "apalancamiento": "Apalancamiento",
    "rotacion_activos": "Rotación de activos",
    "rotacion_cartera": "Rotación de cartera",
}

AZUL = "#143554"
FONDO = "#F4F7FB"
TEXTO = "#28384B"
VERDE = "#147D64"
NARANJA = "#B45309"


def cargar_artefacto():
    if not RUTA_MODELO.is_file():
        raise FileNotFoundError(
            "No se encontró modelos/random_forest_pipeline.joblib. "
            "Comprueba que está dentro del repositorio."
        )
    # Solo cargar el artefacto joblib propio del proyecto, nunca uno desconocido.
    artefacto = joblib.load(RUTA_MODELO)
    modelo = artefacto["pipeline"]
    indicadores = list(artefacto["indicadores"])
    umbral = float(artefacto["umbral"])
    if len(indicadores) != 9 or set(indicadores) != set(PERFILES["A"]):
        raise ValueError("Los indicadores del artefacto no coinciden con la demostración.")
    if not 0 <= umbral <= 1:
        raise ValueError("El umbral almacenado no es válido.")
    return modelo, indicadores, umbral


def convertir_entrada(texto, nombre):
    texto = texto.strip()
    if not texto:
        return np.nan  # El pipeline ya dispone de imputador.
    try:
        numero = float(texto.replace(",", "."))
    except ValueError as exc:
        raise ValueError(f"{nombre}: escribe un número válido (p. ej., 0.75).") from exc
    if not np.isfinite(numero):
        raise ValueError(f"{nombre}: no se permite infinito ni NaN como texto.")
    return numero


class VentanaDemo(tk.Tk):
    def __init__(self, modelo, indicadores, umbral):
        super().__init__()
        self.title("Proyecto de grado | Modelo predictivo de riesgo de insolvencia")
        # Se adapta al espacio disponible, incluso en portátiles con escala de Windows.
        pantalla_ancho = self.winfo_screenwidth()
        pantalla_alto = self.winfo_screenheight()
        ancho = min(1220, max(680, pantalla_ancho - 80))
        alto = min(800, max(460, pantalla_alto - 105))
        self.geometry(f"{ancho}x{alto}")
        self.minsize(min(820, pantalla_ancho - 40), min(490, pantalla_alto - 75))
        self.configure(bg=FONDO)
        self.modelo, self.indicadores, self.umbral = modelo, indicadores, umbral
        self.campos = {}
        self.resultado = tk.StringVar(value="Pendiente de evaluación")
        self.puntaje = tk.StringVar(value="—")
        self.explicacion = tk.StringVar(value="Puntuación relativa del modelo (escala 0 a 1)")
        self.perfil_actual = tk.StringVar(value="Perfil ilustrativo A · medianas sin evento")
        self._crear_interfaz()
        self.cargar_perfil("A")

    def _etiqueta(self, padre, texto, *, tam=11, negrita=False, color=TEXTO,
                  fondo="white", ancho=None, wraplength=None):
        return tk.Label(
            padre, text=texto, font=("Segoe UI", tam, "bold" if negrita else "normal"),
            fg=color, bg=fondo, anchor="w", justify="left", width=ancho,
            wraplength=wraplength,
        )

    def _crear_interfaz(self):
        cabecera = tk.Frame(self, bg=AZUL, pady=22, padx=34)
        cabecera.pack(fill="x")
        self._etiqueta(cabecera, "PROYECTO DE GRADO · CUN", tam=10,
                       negrita=True, color="#BDE9E7", fondo=AZUL).pack(anchor="w")
        self._etiqueta(cabecera, "Predicción del riesgo relativo de insolvencia empresarial",
                       tam=19, negrita=True, color="white", fondo=AZUL).pack(anchor="w", pady=(7, 4))
        self._etiqueta(cabecera, "Random Forest · Indicadores financieros · Colombia, 2021–2024",
                       tam=11, color="#D9E5F0", fondo=AZUL).pack(anchor="w")

        # El pie se reserva ANTES que el contenido desplazable: así nunca queda
        # escondido por el tamaño de la pantalla ni por el escalado de Windows.
        pie = tk.Frame(self, bg="#E6EEF5", padx=18, pady=8)
        pie.pack(side="bottom", fill="x")
        nota = self._etiqueta(
            pie,
            "NOTA METODOLÓGICA · Perfiles ilustrativos. Las puntuaciones expresan "
            "riesgo relativo, no probabilidades calibradas; la señal orienta la "
            "priorización de revisión, no determina la insolvencia.",
            tam=9, color=AZUL, fondo="#E6EEF5", wraplength=800,
        )
        nota.pack(anchor="w")
        pie.bind(
            "<Configure>",
            lambda e: nota.configure(wraplength=max(260, e.width - 38)),
        )

        # Solo el panel central es desplazable; encabezado y nota permanecen
        # visibles. Se conserva la distribución original en pantallas grandes.
        barra_vertical = ttk.Scrollbar(self, orient="vertical")
        barra_vertical.pack(side="right", fill="y")
        self.canvas = tk.Canvas(self, bg=FONDO, borderwidth=0, highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        barra_vertical.configure(command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=barra_vertical.set)

        cuerpo = tk.Frame(self.canvas, bg=FONDO, padx=16, pady=14)
        self._ventana_canvas = self.canvas.create_window((0, 0), window=cuerpo, anchor="nw")
        cuerpo.bind(
            "<Configure>",
            lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.bind("<Configure>", self._ajustar_distribucion)
        self.bind_all("<MouseWheel>", self._desplazar_rueda, add="+")

        cuerpo.columnconfigure(0, weight=3)
        cuerpo.columnconfigure(1, weight=2)
        cuerpo.rowconfigure(0, weight=1)
        self._cuerpo = cuerpo
        self._columnas_apiladas = False

        entrada = tk.Frame(cuerpo, bg="white", padx=22, pady=18,
                           highlightbackground="#DAE3ED", highlightthickness=1)
        entrada.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        salida = tk.Frame(cuerpo, bg="white", padx=23, pady=18,
                          highlightbackground="#DAE3ED", highlightthickness=1)
        salida.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        self._entrada, self._salida = entrada, salida

        self._etiqueta(entrada, "1  Indicadores financieros", tam=14, negrita=True).pack(anchor="w")
        self._etiqueta(entrada, "Carga un perfil ilustrativo o modifica los valores para simular un caso.",
                       tam=10, color="#556779", wraplength=560).pack(anchor="w", pady=(7, 12))

        botones = tk.Frame(entrada, bg="white")
        botones.pack(fill="x", pady=(0, 14))
        tk.Button(botones, text="Perfil A · sin evento", font=("Segoe UI", 10, "bold"),
                  bg="#E5F2F4", fg=AZUL, relief="flat", padx=10, pady=8,
                  command=lambda: self.cargar_perfil("A")).pack(side="left", padx=(0, 8))
        tk.Button(botones, text="Perfil B · con evento", font=("Segoe UI", 10, "bold"),
                  bg="#E5F2F4", fg=AZUL, relief="flat", padx=10, pady=8,
                  command=lambda: self.cargar_perfil("B")).pack(side="left")
        # Acción visible junto a los selectores: no queda cortada en pantallas pequeñas.
        tk.Button(botones, text="EVALUAR PERFIL", font=("Segoe UI", 10, "bold"),
                  bg=AZUL, fg="white", activebackground="#205477",
                  activeforeground="white", relief="flat", padx=10, pady=8,
                  command=self.evaluar).pack(side="right")
        self._etiqueta(entrada, "Perfiles ilustrativos construidos a partir de medianas por clase.",
                       tam=9, color="#65758A").pack(anchor="w", pady=(0, 10))

        campos_frame = tk.Frame(entrada, bg="white")
        campos_frame.pack(fill="x")
        for i, nombre in enumerate(self.indicadores):
            self._etiqueta(campos_frame, NOMBRES.get(nombre, nombre), tam=11).grid(
                row=i, column=0, sticky="w", pady=7, padx=(0, 15)
            )
            var = tk.StringVar()
            campo = ttk.Entry(campos_frame, textvariable=var, width=20, font=("Segoe UI", 11))
            campo.grid(row=i, column=1, sticky="ew", pady=7)
            campo.bind("<KeyRelease>", self._marcar_editado)
            self.campos[nombre] = var
        campos_frame.columnconfigure(1, weight=1)
        self._etiqueta(entrada, "Puedes dejar un campo vacío: se aplicará la imputación del pipeline.",
                       tam=9, color="#65758A", wraplength=550).pack(anchor="w", pady=(12, 8))

        self._etiqueta(salida, "2  Resultado del modelo", tam=14, negrita=True).pack(anchor="w")
        self._etiqueta(salida, "Puntuación calculada", tam=10, color="#556779").pack(anchor="w", pady=(25, 5))
        self._etiqueta(salida, "La puntuación NO es una probabilidad calibrada de insolvencia.",
                       tam=9, color="#65758A", wraplength=360).pack(anchor="w")
        self._etiqueta(salida, "", tam=3).pack()
        tk.Label(salida, textvariable=self.puntaje, bg="white", fg=AZUL,
                 font=("Segoe UI", 33, "bold"), anchor="w").pack(anchor="w")
        self.barra = ttk.Progressbar(salida, orient="horizontal", length=330,
                                     maximum=1.0, mode="determinate")
        self.barra.pack(fill="x", pady=(12, 7))
        self._etiqueta(salida, f"Umbral de decisión (OOF): {self.umbral:.6f}",
                       tam=10, color="#556779").pack(anchor="w")
        self._etiqueta(salida, "Señal de clasificación según el umbral", tam=10,
                       color="#556779").pack(anchor="w", pady=(27, 7))
        self.estado = tk.Label(salida, textvariable=self.resultado,
                               font=("Segoe UI", 12, "bold"), fg=AZUL, bg="#EFF3F8",
                               padx=12, pady=12, wraplength=330, justify="center")
        self.estado.pack(fill="x")
        self._etiqueta(salida, "INTERPRETACIÓN", tam=10, negrita=True,
                       color="#556779").pack(anchor="w", pady=(26, 8))
        tk.Label(salida, textvariable=self.explicacion, bg="white", fg=TEXTO,
                 font=("Segoe UI", 10), justify="left", wraplength=350,
                 anchor="nw").pack(fill="x")
        self._etiqueta(salida, "Datos de evaluación temporal (no del caso simulado)",
                       tam=10, negrita=True, color="#556779", wraplength=360).pack(
                           anchor="w", pady=(28, 8))
        self._etiqueta(salida, "ROC-AUC: 0,7813   ·   PR-AUC: 0,0186", tam=10).pack(anchor="w")
        self._etiqueta(salida, "Top 20 % del ranking: 59,56 % de los eventos capturados",
                       tam=10, wraplength=350).pack(anchor="w", pady=(7, 0))

    def _ajustar_distribucion(self, evento):
        """Dos columnas cuando caben; una columna y scroll en pantallas angostas."""
        self.canvas.itemconfigure(self._ventana_canvas, width=evento.width)
        apilar = evento.width < 1020
        if apilar == self._columnas_apiladas:
            return
        self._columnas_apiladas = apilar
        if apilar:
            self._entrada.grid_configure(row=0, column=0, padx=0, pady=(0, 12))
            self._salida.grid_configure(row=1, column=0, padx=0, pady=0)
            self._cuerpo.columnconfigure(0, weight=1)
            self._cuerpo.columnconfigure(1, weight=0)
        else:
            self._entrada.grid_configure(row=0, column=0, padx=(0, 12), pady=0)
            self._salida.grid_configure(row=0, column=1, padx=(12, 0), pady=0)
            self._cuerpo.columnconfigure(0, weight=3)
            self._cuerpo.columnconfigure(1, weight=2)
        self.canvas.yview_moveto(0)

    def _desplazar_rueda(self, evento):
        """Rueda del ratón para consultar toda la interfaz en un portátil."""
        if self.canvas.winfo_exists() and self._cuerpo.winfo_reqheight() > self.canvas.winfo_height():
            pasos = int(-evento.delta / 120)
            if pasos:
                self.canvas.yview_scroll(pasos * 3, "units")

    def _marcar_editado(self, _event):
        self.perfil_actual.set("Perfil modificado manualmente")

    def cargar_perfil(self, letra):
        for nombre, valor in PERFILES[letra].items():
            self.campos[nombre].set(f"{valor:.4f}")
        self.perfil_actual.set(f"Perfil ilustrativo {letra}")
        self.puntaje.set("—")
        self.resultado.set("Pendiente de evaluación")
        self.estado.configure(bg="#EFF3F8", fg=AZUL)
        self.barra["value"] = 0
        self.explicacion.set("El modelo evaluará los nueve indicadores mediante el mismo preprocesamiento usado en el estudio.")

    def evaluar(self):
        try:
            valores = {
                nombre: convertir_entrada(self.campos[nombre].get(), NOMBRES.get(nombre, nombre))
                for nombre in self.indicadores
            }
            if all(pd.isna(valor) for valor in valores.values()):
                raise ValueError("Ingresa al menos un indicador financiero.")
            fila = pd.DataFrame([valores], columns=self.indicadores)
            puntuacion = float(self.modelo.predict_proba(fila)[0, 1])
            if not np.isfinite(puntuacion):
                raise ValueError("El modelo devolvió una puntuación no válida.")
        except (ValueError, TypeError, KeyError) as exc:
            messagebox.showerror("No se pudo evaluar el perfil", str(exc), parent=self)
            return
        except Exception as exc:
            messagebox.showerror("Error del modelo", f"No se pudo generar la predicción: {exc}", parent=self)
            return

        self.puntaje.set(f"{puntuacion:.6f}")
        self.barra["value"] = puntuacion
        if puntuacion >= self.umbral:
            self.resultado.set("SEÑAL POSITIVA · PRIORIDAD DE REVISIÓN")
            self.estado.configure(bg="#FFF1E6", fg=NARANJA)
            interpretacion = (
                f"La puntuación ({puntuacion:.6f}) supera o iguala el umbral "
                f"({self.umbral:.6f}). El perfil recibe una señal positiva según "
                "la regla de clasificación. No significa quiebra asegurada."
            )
        else:
            self.resultado.set("SEÑAL NEGATIVA · BAJO EL UMBRAL")
            self.estado.configure(bg="#E9F6F1", fg=VERDE)
            interpretacion = (
                f"La puntuación ({puntuacion:.6f}) está por debajo del umbral "
                f"({self.umbral:.6f}). El perfil recibe una señal negativa según "
                "la regla de clasificación. No descarta dificultades financieras."
            )
        self.explicacion.set(interpretacion)


def main():
    try:
        modelo, indicadores, umbral = cargar_artefacto()
    except Exception as exc:
        # Evita cerrar la consola inmediatamente si el archivo falta o es incompatible.
        print(f"ERROR AL CARGAR EL MODELO: {exc}", file=sys.stderr)
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("No se pudo iniciar la demostración", str(exc), parent=root)
            root.destroy()
        except tk.TclError:
            pass
        return 1
    app = VentanaDemo(modelo, indicadores, umbral)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
