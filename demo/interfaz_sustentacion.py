"""Interfaz para la sustentación: simulación didáctica y ranking histórico local.

- Conserva los perfiles sintéticos A/B y la evaluación interactiva de nueve ratios.
- El ranking utiliza un CSV LOCAL precalculado, nunca solicita SQL Server.
- No entrena ni modifica el modelo Random Forest guardado.
- Las puntuaciones son relativas y NO probabilidades calibradas de insolvencia.
"""
from pathlib import Path
import sys
import tkinter as tk
from tkinter import messagebox, ttk

import joblib
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "python"))
RUTA_MODELO = RAIZ / "modelos" / "random_forest_pipeline.joblib"
RUTA_RANKING = RAIZ / "data" / "local" / "ranking_empresas_2021_2024.csv"

PERFILES = {
    "A": {
        "razon_corriente": 2.1133, "prueba_acida": 1.2860,
        "roa": 0.0295, "roe": 0.0692, "margen_neto": 0.0491,
        "endeudamiento": 0.4407, "apalancamiento": 0.7037,
        "rotacion_activos": 0.5426, "rotacion_cartera": 3.7615,
    },
    "B": {
        "razon_corriente": 1.6391, "prueba_acida": 0.9358,
        "roa": 0.0087, "roe": 0.0389, "margen_neto": 0.0087,
        "endeudamiento": 0.6812, "apalancamiento": 1.8291,
        "rotacion_activos": 0.8070, "rotacion_cartera": 2.9988,
    },
}

NOMBRES = {
    "razon_corriente": "Razón corriente", "prueba_acida": "Prueba ácida",
    "roa": "ROA", "roe": "ROE", "margen_neto": "Margen neto",
    "endeudamiento": "Endeudamiento", "apalancamiento": "Apalancamiento",
    "rotacion_activos": "Rotación de activos", "rotacion_cartera": "Rotación de cartera",
}

TEXTOS_PERFILES = {
    "A": (
        "PERFIL A · Medianas sin evento: cada valor es la mediana del respectivo "
        "indicador entre las observaciones históricas sin apertura de insolvencia "
        "en el horizonte definido. No corresponde a una empresa real."
    ),
    "B": (
        "PERFIL B · Medianas con evento: cada valor es la mediana del respectivo "
        "indicador entre las observaciones históricas con apertura de insolvencia "
        "en el horizonte definido. No corresponde a una empresa real."
    ),
}

TIPOS_POR_ANIO = {
    2021: "Desarrollo · puntuaciones fuera de fold (OOF)",
    2022: "Evaluación temporal independiente · cohorte financiera 2022",
    2023: "Aplicación exploratoria · no validada en la tesis",
    2024: "Aplicación exploratoria · no validada en la tesis",
}

AZUL = "#173A5E"
FONDO = "#F5F7FA"
TEXTO = "#25364A"
VERDE = "#147A64"
NARANJA = "#B85C14"
GRIS = "#5E6F82"


def cargar_artefacto():
    if not RUTA_MODELO.is_file():
        raise FileNotFoundError(
            "No se encontró modelos/random_forest_pipeline.joblib. "
            "Comprueba que esté dentro del repositorio."
        )
    # Cargar únicamente el archivo joblib generado por el propio proyecto.
    artefacto = joblib.load(RUTA_MODELO)
    modelo = artefacto["pipeline"]
    indicadores = list(artefacto["indicadores"])
    umbral = float(artefacto["umbral"])
    if len(indicadores) != 9 or set(indicadores) != set(PERFILES["A"]):
        raise ValueError("Los nueve indicadores del modelo no coinciden con los de la interfaz.")
    if not 0 <= umbral <= 1:
        raise ValueError("El umbral almacenado no es válido.")
    return modelo, indicadores, umbral


def convertir_entrada(texto, nombre):
    texto = texto.strip()
    if not texto:
        return np.nan  # Imputación integrada en el pipeline.
    try:
        numero = float(texto.replace(",", "."))
    except ValueError as exc:
        raise ValueError(f"{nombre}: escribe un número válido (ej.: 0,75).") from exc
    if not np.isfinite(numero):
        raise ValueError(f"{nombre}: no se permite NaN ni infinito como texto.")
    return numero


def cargar_ranking():
    """Lee los registros precalculados, sin requerir conexión a SQL Server."""
    if not RUTA_RANKING.is_file():
        return None, (
            "El ranking local no está instalado. Copia el archivo "
            "ranking_empresas_2021_2024.csv a la carpeta data/local/ del repositorio. "
            "La simulación A/B funciona igualmente sin este archivo."
        )
    try:
        datos = pd.read_csv(
            RUTA_RANKING,
            encoding="utf-8-sig",
            dtype={"nit_normalizado": "string", "razon_social": "string",
                   "numero_radicado": "string", "tipo_analisis": "string"},
            low_memory=False,
        )
        requeridas = {
            "anio_corte", "posicion_anual", "nit_normalizado", "razon_social",
            "puntuacion", *NOMBRES.keys(),
        }
        faltantes = requeridas.difference(datos.columns)
        if faltantes:
            raise ValueError("Faltan columnas: " + ", ".join(sorted(faltantes)))
        datos["anio_corte"] = pd.to_numeric(datos["anio_corte"], errors="raise").astype(int)
        datos["posicion_anual"] = pd.to_numeric(
            datos["posicion_anual"], errors="raise"
        ).astype(int)
        datos["puntuacion"] = pd.to_numeric(datos["puntuacion"], errors="raise")
        if datos["puntuacion"].isna().any() or not datos["puntuacion"].between(0, 1).all():
            raise ValueError("Hay puntuaciones nulas o fuera de la escala de 0 a 1.")
        if datos.duplicated(["anio_corte", "nit_normalizado"]).any():
            raise ValueError("Hay empresas duplicadas dentro de un mismo año financiero.")
        datos["razon_social"] = datos["razon_social"].fillna("Sin nombre disponible")
        datos = datos.sort_values(
            ["anio_corte", "posicion_anual", "nit_normalizado"],
            kind="stable",
        ).reset_index(drop=True)
        return datos, None
    except (OSError, UnicodeError, ValueError, KeyError, pd.errors.ParserError) as exc:
        return None, f"No se pudo leer el CSV de ranking local: {exc}"


def valor_texto(valor, decimales=4):
    if pd.isna(valor):
        return "No disponible"
    try:
        numero = float(valor)
        if not np.isfinite(numero):
            return "No disponible"
        return f"{numero:.{decimales}f}"
    except (ValueError, TypeError):
        return str(valor)


class VentanaDemo(tk.Tk):
    def __init__(self, modelo, indicadores, umbral):
        super().__init__()
        self.title("Proyecto de grado | Simulación y ranking empresarial")
        pantalla_ancho = self.winfo_screenwidth()
        pantalla_alto = self.winfo_screenheight()
        ancho = min(1240, max(700, pantalla_ancho - 80))
        alto = min(840, max(500, pantalla_alto - 105))
        self.geometry(f"{ancho}x{alto}")
        self.minsize(min(820, pantalla_ancho - 40), min(500, pantalla_alto - 75))
        self.configure(bg=FONDO)
        self.modelo, self.indicadores, self.umbral = modelo, indicadores, umbral
        self.ranking, self.error_ranking = cargar_ranking()
        self.campos = {}
        self.resultado = tk.StringVar(value="Pendiente de evaluación")
        self.puntaje = tk.StringVar(value="—")
        self.explicacion = tk.StringVar(value="La puntuación relativa se expresa entre 0 y 1.")
        self.perfil_actual = tk.StringVar(value="")
        self.comparacion = tk.StringVar(value="Pulsa COMPARAR A Y B para contrastar los dos perfiles sintéticos.")
        self.anio_ranking = tk.StringVar(value="2022")
        self.limite_ranking = tk.StringVar(value="10")
        self.busqueda_ranking = tk.StringVar(value="")
        self.info_ranking = tk.StringVar(value="")
        self.tipo_ranking = tk.StringVar(value="")
        self._crear_interfaz()
        self.cargar_perfil("A")
        self.actualizar_tabla_ranking()

    @staticmethod
    def _etiqueta(padre, texto, *, tam=11, negrita=False, color=TEXTO,
                  fondo="white", wraplength=None):
        return tk.Label(
            padre, text=texto, font=("Segoe UI", tam, "bold" if negrita else "normal"),
            fg=color, bg=fondo, anchor="w", justify="left", wraplength=wraplength,
        )

    def _crear_interfaz(self):
        cabecera = tk.Frame(self, bg=AZUL, pady=12, padx=22)
        cabecera.pack(fill="x")
        self._etiqueta(
            cabecera, "PROYECTO DE GRADO · CUN", tam=9,
            negrita=True, color="#BDE9E7", fondo=AZUL
        ).pack(anchor="w")
        self._etiqueta(
            cabecera, "Priorización de revisión financiera mediante Random Forest",
            tam=17, negrita=True, color="white", fondo=AZUL,
        ).pack(anchor="w", pady=(3, 1))
        self._etiqueta(
            cabecera, "Simulación didáctica y ranking histórico para la sustentación",
            tam=10, color="#D9E5F0", fondo=AZUL,
        ).pack(anchor="w")

        # Pie fijo, independiente de las pestañas y sus barras de desplazamiento.
        pie = tk.Frame(self, bg="#E6EEF5", padx=16, pady=6)
        pie.pack(side="bottom", fill="x")
        nota = self._etiqueta(
            pie,
            "NOTA METODOLÓGICA · Los perfiles A/B no son empresas reales. "
            "El ranking es histórico y orienta la revisión: la puntuación no es una "
            "probabilidad calibrada ni demuestra insolvencia actual.",
            tam=9, color=AZUL, fondo="#E6EEF5", wraplength=850,
        )
        nota.pack(anchor="w")
        pie.bind("<Configure>", lambda e: nota.configure(wraplength=max(300, e.width - 32)))

        estilo = ttk.Style(self)
        try:
            estilo.theme_use("clam")
        except tk.TclError:
            pass
        try:
            estilo.configure("TNotebook", background=FONDO, borderwidth=0)
            estilo.configure(
                "TNotebook.Tab", padding=(18, 9),
                font=("Segoe UI", 10, "bold"),
                background="#E7EDF4", foreground=AZUL,
            )
            estilo.map(
                "TNotebook.Tab",
                background=[("selected", "white")],
                foreground=[("selected", AZUL)],
            )
            estilo.configure(
                "Treeview", background="white", fieldbackground="white",
                foreground=TEXTO, rowheight=28, font=("Segoe UI", 10),
            )
            estilo.configure(
                "Treeview.Heading", background="#E7EDF4", foreground=AZUL,
                font=("Segoe UI", 10, "bold"), relief="flat",
            )
            estilo.map(
                "Treeview",
                background=[("selected", "#DCEAF7")],
                foreground=[("selected", AZUL)],
            )
            estilo.configure(
                "Horizontal.TProgressbar",
                troughcolor="#E6EBF0", background="#16A34A",
                bordercolor="#E6EBF0", lightcolor="#16A34A", darkcolor="#16A34A",
            )
        except tk.TclError:
            pass
        self.pestanas = ttk.Notebook(self)
        self.pestanas.pack(fill="both", expand=True, padx=10, pady=(8, 6))
        self.tab_simulacion = tk.Frame(self.pestanas, bg=FONDO)
        self.tab_ranking = tk.Frame(self.pestanas, bg=FONDO)
        self.pestanas.add(self.tab_simulacion, text="1  Simulación y explicación")
        self.pestanas.add(self.tab_ranking, text="2  Ranking empresarial histórico")
        self._crear_simulacion()
        self._crear_ranking()

    def _crear_simulacion(self):
        barra_vertical = ttk.Scrollbar(self.tab_simulacion, orient="vertical")
        barra_vertical.pack(side="right", fill="y")
        self.canvas = tk.Canvas(
            self.tab_simulacion, bg=FONDO, borderwidth=0, highlightthickness=0
        )
        self.canvas.pack(side="left", fill="both", expand=True)
        barra_vertical.configure(command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=barra_vertical.set)

        cuerpo = tk.Frame(self.canvas, bg=FONDO, padx=12, pady=11)
        self._ventana_canvas = self.canvas.create_window((0, 0), window=cuerpo, anchor="nw")
        cuerpo.bind(
            "<Configure>",
            lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.bind("<Configure>", self._ajustar_distribucion)
        self.bind_all("<MouseWheel>", self._desplazar_rueda, add="+")

        cuerpo.columnconfigure(0, weight=3)
        cuerpo.columnconfigure(1, weight=2)
        self._cuerpo = cuerpo
        self._columnas_apiladas = False

        entrada = tk.Frame(
            cuerpo, bg="white", padx=18, pady=14,
            highlightbackground="#DAE3ED", highlightthickness=1,
        )
        entrada.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        salida = tk.Frame(
            cuerpo, bg="white", padx=18, pady=14,
            highlightbackground="#DAE3ED", highlightthickness=1,
        )
        salida.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self._entrada, self._salida = entrada, salida

        self._etiqueta(
            entrada, "¿Para qué sirven los perfiles A y B?", tam=13, negrita=True,
        ).pack(anchor="w")
        intro = (
            "Son dos perfiles sintéticos construidos con las medianas de los nueve "
            "indicadores, separadas por la ocurrencia histórica del evento objetivo. "
            "Sirven para explicar el funcionamiento del modelo y comparar cómo "
            "responde al cambiar los valores. No son empresas reales ni prueban "
            "por sí solos el desempeño predictivo."
        )
        explicacion = self._etiqueta(
            entrada, intro, tam=10, color=GRIS, wraplength=540,
        )
        explicacion.pack(anchor="w", pady=(7, 12))
        entrada.bind(
            "<Configure>",
            lambda e: explicacion.configure(wraplength=max(250, e.width - 42)),
        )

        botones = tk.Frame(entrada, bg="white")
        botones.pack(fill="x", pady=(0, 9))
        botones.columnconfigure(0, weight=1)
        botones.columnconfigure(1, weight=1)
        tk.Button(
            botones, text="Cargar A · sin evento", font=("Segoe UI", 9, "bold"),
            bg="#EAF5F1", fg=VERDE, relief="flat", padx=7, pady=8,
            command=lambda: self.cargar_perfil("A"),
        ).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        tk.Button(
            botones, text="Cargar B · con evento", font=("Segoe UI", 9, "bold"),
            bg="#FFF1E7", fg=NARANJA, relief="flat", padx=7, pady=8,
            command=lambda: self.cargar_perfil("B"),
        ).grid(row=0, column=1, sticky="ew", padx=(4, 0))
        tk.Button(
            botones, text="COMPARAR A Y B", font=("Segoe UI", 9, "bold"),
            bg="#E7EDF4", fg=AZUL, relief="flat", padx=7, pady=8,
            command=self.comparar_perfiles,
        ).grid(row=1, column=0, sticky="ew", padx=(0, 4), pady=(7, 0))
        tk.Button(
            botones, text="EVALUAR VALORES", font=("Segoe UI", 9, "bold"),
            bg=AZUL, fg="white", activebackground="#205477",
            activeforeground="white", relief="flat", padx=7, pady=8,
            command=self.evaluar,
        ).grid(row=1, column=1, sticky="ew", padx=(4, 0), pady=(7, 0))

        perfil_texto = tk.Label(
            entrada, textvariable=self.perfil_actual, font=("Segoe UI", 9),
            fg=AZUL, bg="#EFF5F9", anchor="w", justify="left", padx=10, pady=10,
            wraplength=510,
        )
        perfil_texto.pack(fill="x", pady=(0, 13))
        perfil_texto.bind(
            "<Configure>",
            lambda e: perfil_texto.configure(wraplength=max(240, e.width - 28)),
        )

        self._etiqueta(
            entrada, "Nueve indicadores financieros", tam=12, negrita=True,
        ).pack(anchor="w", pady=(0, 7))
        campos_frame = tk.Frame(entrada, bg="white")
        campos_frame.pack(fill="x")
        for i, nombre in enumerate(self.indicadores):
            self._etiqueta(campos_frame, NOMBRES[nombre], tam=10).grid(
                row=i, column=0, sticky="w", pady=5, padx=(0, 12)
            )
            var = tk.StringVar()
            campo = ttk.Entry(campos_frame, textvariable=var, width=15, font=("Segoe UI", 10))
            campo.grid(row=i, column=1, sticky="ew", pady=5)
            campo.bind("<KeyRelease>", self._marcar_editado)
            self.campos[nombre] = var
        campos_frame.columnconfigure(1, weight=1)
        self._etiqueta(
            entrada, "Los campos vacíos usan la imputación integrada en el pipeline.",
            tam=9, color=GRIS, wraplength=510,
        ).pack(anchor="w", pady=(10, 0))

        self._etiqueta(salida, "Resultado del modelo", tam=13, negrita=True).pack(anchor="w")
        self._etiqueta(
            salida, "Puntuación relativa (0 a 1; no calibrada)", tam=10, color=GRIS,
        ).pack(anchor="w", pady=(18, 4))
        tk.Label(
            salida, textvariable=self.puntaje, bg="white", fg=AZUL,
            font=("Segoe UI", 30, "bold"), anchor="w",
        ).pack(anchor="w")
        self.barra = ttk.Progressbar(
            salida, orient="horizontal", length=300, maximum=1.0, mode="determinate"
        )
        self.barra.pack(fill="x", pady=(8, 7))
        self._etiqueta(
            salida, f"Umbral OOF de clasificación: {self.umbral:.6f}",
            tam=10, color=GRIS,
        ).pack(anchor="w")
        self.estado = tk.Label(
            salida, textvariable=self.resultado,
            font=("Segoe UI", 11, "bold"), fg=AZUL, bg="#EFF3F8",
            padx=10, pady=12, wraplength=340, justify="center",
        )
        self.estado.pack(fill="x", pady=(17, 10))
        self._etiqueta(salida, "INTERPRETACIÓN", tam=10, negrita=True, color=GRIS).pack(
            anchor="w", pady=(8, 7)
        )
        interpretacion = tk.Label(
            salida, textvariable=self.explicacion, bg="white", fg=TEXTO,
            font=("Segoe UI", 10), justify="left", wraplength=350, anchor="nw",
        )
        interpretacion.pack(fill="x")
        salida.bind(
            "<Configure>",
            lambda e: interpretacion.configure(wraplength=max(220, e.width - 42)),
        )
        self._etiqueta(
            salida, "COMPARACIÓN DIDÁCTICA", tam=10, negrita=True, color=GRIS,
        ).pack(anchor="w", pady=(22, 7))
        self.comparacion_label = tk.Label(
            salida, textvariable=self.comparacion, bg="#EFF5F9", fg=AZUL,
            font=("Segoe UI", 10), padx=10, pady=12,
            wraplength=350, justify="left", anchor="w",
            highlightbackground="#D8E2EC", highlightthickness=1,
        )
        self.comparacion_label.pack(fill="x")
        self._etiqueta(
            salida, "RESULTADOS DE VALIDACIÓN TEMPORAL (2022)",
            tam=10, negrita=True, color=GRIS,
        ).pack(anchor="w", pady=(22, 6))
        self._etiqueta(
            salida, "ROC-AUC: 0,7813  ·  PR-AUC: 0,0186", tam=10,
        ).pack(anchor="w")
        self._etiqueta(
            salida, "Top 20 %: capturó el 59,56 % de los eventos.",
            tam=10, wraplength=350,
        ).pack(anchor="w", pady=(5, 0))
        self._etiqueta(
            salida, "Estas métricas provienen de empresas observadas en la cohorte "
            "de evaluación, NO de los perfiles sintéticos A/B.",
            tam=9, color=GRIS, wraplength=350,
        ).pack(anchor="w", pady=(7, 0))

    def _crear_ranking(self):
        contenedor = tk.Frame(self.tab_ranking, bg=FONDO, padx=12, pady=10)
        contenedor.pack(fill="both", expand=True)
        self._etiqueta(
            contenedor, "Empresas reales · registros financieros históricos",
            tam=13, negrita=True, fondo=FONDO,
        ).pack(anchor="w")
        self._etiqueta(
            contenedor,
            "Ordenadas por puntuación del modelo, NO por una declaración de "
            "insolvencia ni por una probabilidad de quiebra. Datos locales; sin SQL Server.",
            tam=10, color=GRIS, fondo=FONDO, wraplength=1000,
        ).pack(anchor="w", pady=(3, 9))

        filtros = tk.Frame(contenedor, bg="white", padx=11, pady=10)
        filtros.pack(fill="x")
        self._etiqueta(filtros, "Año financiero", tam=9).grid(
            row=0, column=0, sticky="w", padx=(0, 7)
        )
        anios = (
            sorted(map(str, self.ranking["anio_corte"].unique()))
            if self.ranking is not None else ["2021", "2022", "2023", "2024"]
        )
        if "2022" not in anios and anios:
            self.anio_ranking.set(anios[0])
        self.combo_anio = ttk.Combobox(
            filtros, values=anios, textvariable=self.anio_ranking,
            state="readonly", width=8,
        )
        self.combo_anio.grid(row=0, column=1, sticky="w", padx=(0, 17))
        self.combo_anio.bind("<<ComboboxSelected>>", lambda _e: self.actualizar_tabla_ranking())
        self._etiqueta(filtros, "Mostrar", tam=9).grid(
            row=0, column=2, sticky="w", padx=(0, 7)
        )
        combo_top = ttk.Combobox(
            filtros, values=["5", "10", "20", "50", "100"],
            textvariable=self.limite_ranking, state="readonly", width=6,
        )
        combo_top.grid(row=0, column=3, sticky="w", padx=(0, 17))
        combo_top.bind("<<ComboboxSelected>>", lambda _e: self.actualizar_tabla_ranking())
        self._etiqueta(filtros, "Buscar nombre o NIT", tam=9).grid(
            row=0, column=4, sticky="w", padx=(0, 7)
        )
        ttk.Entry(
            filtros, textvariable=self.busqueda_ranking,
            font=("Segoe UI", 10), width=24,
        ).grid(row=0, column=5, sticky="ew")
        filtros.columnconfigure(5, weight=1)
        self.busqueda_ranking.trace_add("write", lambda *_: self.actualizar_tabla_ranking())

        informacion = tk.Frame(contenedor, bg=FONDO)
        informacion.pack(fill="x", pady=(8, 6))
        tk.Label(
            informacion, textvariable=self.tipo_ranking, bg=FONDO,
            fg=AZUL, font=("Segoe UI", 10, "bold"), anchor="w",
        ).pack(anchor="w")
        tk.Label(
            informacion, textvariable=self.info_ranking, bg=FONDO,
            fg=GRIS, font=("Segoe UI", 9), anchor="w",
        ).pack(anchor="w", pady=(3, 0))

        tabla_contenedor = tk.Frame(contenedor, bg="white")
        tabla_contenedor.pack(fill="both", expand=True)
        columnas = ("posicion", "empresa", "nit", "puntuacion", "senal")
        self.tabla_ranking = ttk.Treeview(
            tabla_contenedor, columns=columnas, show="headings", height=8,
            selectmode="browse",
        )
        for col, texto, ancho, anclaje in [
            ("posicion", "Pos.", 65, "center"),
            ("empresa", "Razón social", 390, "w"),
            ("nit", "NIT", 130, "center"),
            ("puntuacion", "Puntuación", 112, "center"),
            ("senal", "Señal por umbral", 150, "center"),
        ]:
            self.tabla_ranking.heading(col, text=texto)
            self.tabla_ranking.column(
                col, width=ancho, minwidth=65, stretch=(col == "empresa"), anchor=anclaje,
            )
        vertical = ttk.Scrollbar(tabla_contenedor, orient="vertical", command=self.tabla_ranking.yview)
        horizontal = ttk.Scrollbar(tabla_contenedor, orient="horizontal", command=self.tabla_ranking.xview)
        self.tabla_ranking.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.tabla_ranking.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        tabla_contenedor.rowconfigure(0, weight=1)
        tabla_contenedor.columnconfigure(0, weight=1)
        self.tabla_ranking.tag_configure("par", background="#FBFCFE")
        self.tabla_ranking.tag_configure("impar", background="white")
        self.tabla_ranking.bind("<<TreeviewSelect>>", self.mostrar_detalle)

        self._etiqueta(
            contenedor, "Detalle de la empresa seleccionada · nueve indicadores",
            tam=11, negrita=True, fondo=FONDO,
        ).pack(anchor="w", pady=(9, 5))
        detalle_contenedor = tk.Frame(contenedor, bg="white")
        detalle_contenedor.pack(fill="x")
        self.detalle = tk.Text(
            detalle_contenedor, height=7, wrap="word", font=("Consolas", 10),
            bg="white", fg=TEXTO, relief="flat", padx=10, pady=7,
            state="disabled",
        )
        scroll_detalle = ttk.Scrollbar(detalle_contenedor, command=self.detalle.yview)
        self.detalle.configure(yscrollcommand=scroll_detalle.set)
        self.detalle.pack(side="left", fill="both", expand=True)
        scroll_detalle.pack(side="right", fill="y")
        self._establecer_detalle("Selecciona una fila para ver sus indicadores y su radicado.")

    def _ajustar_distribucion(self, evento):
        self.canvas.itemconfigure(self._ventana_canvas, width=evento.width)
        apilar = evento.width < 1020
        if apilar == self._columnas_apiladas:
            return
        self._columnas_apiladas = apilar
        if apilar:
            self._entrada.grid_configure(row=0, column=0, padx=0, pady=(0, 10))
            self._salida.grid_configure(row=1, column=0, padx=0, pady=0)
            self._cuerpo.columnconfigure(0, weight=1)
            self._cuerpo.columnconfigure(1, weight=0)
        else:
            self._entrada.grid_configure(row=0, column=0, padx=(0, 10), pady=0)
            self._salida.grid_configure(row=0, column=1, padx=(10, 0), pady=0)
            self._cuerpo.columnconfigure(0, weight=3)
            self._cuerpo.columnconfigure(1, weight=2)
        self.canvas.yview_moveto(0)

    def _desplazar_rueda(self, evento):
        if self.pestanas.select() != str(self.tab_simulacion):
            return
        if self.canvas.winfo_exists() and self._cuerpo.winfo_reqheight() > self.canvas.winfo_height():
            pasos = int(-evento.delta / 120)
            if pasos:
                self.canvas.yview_scroll(pasos * 3, "units")

    def _marcar_editado(self, _event):
        self.perfil_actual.set(
            "VALORES MODIFICADOS · Ya no corresponden exactamente a las medianas "
            "del perfil A ni del B. Es una simulación editable."
        )

    def cargar_perfil(self, letra):
        for nombre, valor in PERFILES[letra].items():
            self.campos[nombre].set(f"{valor:.4f}")
        self.perfil_actual.set(TEXTOS_PERFILES[letra])
        self.puntaje.set("—")
        self.resultado.set("Pendiente de evaluación")
        self.estado.configure(bg="#EFF3F8", fg=AZUL)
        self.comparacion.set("Pulsa COMPARAR A Y B para contrastar los dos perfiles sintéticos.")
        if hasattr(self, "comparacion_label"):
            self.comparacion_label.configure(bg="#EFF5F9", fg=AZUL)
        self.barra["value"] = 0
        self.explicacion.set(
            "Pulsa EVALUAR VALORES para calcular la puntuación con el modelo. "
            "Puedes modificar indicadores para observar su respuesta."
        )

    def comparar_perfiles(self):
        """Compara los perfiles A y B con el mismo pipeline del modelo."""
        try:
            def puntuar(perfil):
                fila = pd.DataFrame(
                    [{nombre: float(perfil[nombre]) for nombre in self.indicadores}],
                    columns=self.indicadores,
                )
                salida = np.asarray(self.modelo.predict_proba(fila))
                if salida.ndim != 2 or salida.shape[0] != 1 or salida.shape[1] < 2:
                    raise ValueError("El modelo no devolvió una salida de clasificación válida.")
                valor = float(salida[0, 1])
                if not np.isfinite(valor):
                    raise ValueError("El modelo devolvió una puntuación no válida.")
                return valor

            a = puntuar(PERFILES["A"])
            b = puntuar(PERFILES["B"])
            diferencia = b - a
            senal_a = "POSITIVA" if a >= self.umbral else "NEGATIVA"
            senal_b = "POSITIVA" if b >= self.umbral else "NEGATIVA"

            self.comparacion.set(
                f"Perfil A · sin evento: {a:.6f}  ·  señal {senal_a}\n"
                f"Perfil B · con evento: {b:.6f}  ·  señal {senal_b}\n"
                f"Diferencia B − A: {diferencia:+.6f}\n\n"
                "La comparación es didáctica: muestra cómo responde el mismo "
                "modelo a dos perfiles sintéticos construidos con medianas históricas."
            )
            self.comparacion_label.configure(bg="#EAF2F8", fg=AZUL)
            self.puntaje.set(f"A {a:.3f}  |  B {b:.3f}")
            self.barra["value"] = max(a, b)

            if b > a:
                self.resultado.set("COMPARACIÓN LISTA · PERFIL B CON MAYOR PUNTUACIÓN")
                self.estado.configure(bg="#FFF1E6", fg=NARANJA)
            elif a > b:
                self.resultado.set("COMPARACIÓN LISTA · PERFIL A CON MAYOR PUNTUACIÓN")
                self.estado.configure(bg="#E9F6F1", fg=VERDE)
            else:
                self.resultado.set("COMPARACIÓN LISTA · PUNTUACIONES IGUALES")
                self.estado.configure(bg="#EFF3F8", fg=AZUL)

            self.explicacion.set(
                f"El perfil A obtuvo {a:.6f} y el perfil B {b:.6f}. "
                f"La diferencia B − A fue {diferencia:+.6f}. "
                "Estas puntuaciones son relativas y no probabilidades calibradas de insolvencia."
            )

        except (ValueError, TypeError, KeyError) as exc:
            messagebox.showerror("No se pudo comparar", str(exc), parent=self)
        except Exception as exc:
            messagebox.showerror(
                "Error del modelo",
                f"No se pudo generar la comparación A/B: {exc}",
                parent=self,
            )

    def evaluar(self):
        try:
            valores = {
                nombre: convertir_entrada(self.campos[nombre].get(), NOMBRES[nombre])
                for nombre in self.indicadores
            }
            if all(pd.isna(valor) for valor in valores.values()):
                raise ValueError("Ingresa al menos un indicador financiero.")
            fila = pd.DataFrame([valores], columns=self.indicadores)
            puntuacion = float(self.modelo.predict_proba(fila)[0, 1])
            if not np.isfinite(puntuacion):
                raise ValueError("El modelo devolvió una puntuación no válida.")
        except (ValueError, TypeError, KeyError) as exc:
            messagebox.showerror("No se pudo evaluar", str(exc), parent=self)
            return
        except Exception as exc:
            messagebox.showerror("Error del modelo", str(exc), parent=self)
            return
        self.puntaje.set(f"{puntuacion:.6f}")
        self.barra["value"] = puntuacion
        if puntuacion >= self.umbral:
            self.resultado.set("SEÑAL POSITIVA · PRIORIDAD DE REVISIÓN")
            self.estado.configure(bg="#FFF1E6", fg=NARANJA)
            self.explicacion.set(
                f"La puntuación {puntuacion:.6f} alcanza o supera el umbral "
                f"{self.umbral:.6f}. El modelo emite una señal positiva. "
                "No equivale a insolvencia confirmada."
            )
        else:
            self.resultado.set("SEÑAL NEGATIVA · BAJO EL UMBRAL")
            self.estado.configure(bg="#E9F6F1", fg=VERDE)
            self.explicacion.set(
                f"La puntuación {puntuacion:.6f} queda bajo el umbral "
                f"{self.umbral:.6f}. Una señal negativa tampoco descarta "
                "dificultades financieras."
            )

    def actualizar_tabla_ranking(self):
        if not hasattr(self, "tabla_ranking"):
            return
        filas_anteriores = self.tabla_ranking.get_children()
        if filas_anteriores:
            self.tabla_ranking.delete(*filas_anteriores)
        self._establecer_detalle("Selecciona una empresa de la tabla para consultar sus indicadores.")
        try:
            anio = int(self.anio_ranking.get())
            cantidad = int(self.limite_ranking.get())
        except ValueError:
            return
        self.tipo_ranking.set(TIPOS_POR_ANIO.get(anio, "Aplicación histórica"))
        if self.ranking is None:
            self.info_ranking.set(self.error_ranking or "No hay datos disponibles.")
            return
        datos_anio = self.ranking.loc[self.ranking["anio_corte"] == anio]
        consulta = self.busqueda_ranking.get().strip()
        if consulta:
            coincide_nombre = datos_anio["razon_social"].str.contains(
                consulta, case=False, regex=False, na=False
            )
            coincide_nit = datos_anio["nit_normalizado"].str.contains(
                consulta, regex=False, na=False
            )
            datos_anio = datos_anio.loc[coincide_nombre | coincide_nit]
        mostrados = datos_anio.head(cantidad)
        for orden, (idx, fila) in enumerate(mostrados.iterrows()):
            nombre = str(fila["razon_social"])
            senal = "Positiva" if float(fila["puntuacion"]) >= self.umbral else "Negativa"
            self.tabla_ranking.insert(
                "", "end", iid=str(idx),
                values=(
                    int(fila["posicion_anual"]), nombre,
                    str(fila["nit_normalizado"]),
                    valor_texto(fila["puntuacion"], 6), senal,
                ),
                tags=(("par" if orden % 2 == 0 else "impar"),),
            )
        self.info_ranking.set(
            f"{len(mostrados):,} mostradas de {len(datos_anio):,} coincidencias "
            f"({len(self.ranking.loc[self.ranking['anio_corte'] == anio]):,} "
            "observaciones del año). Las posiciones corresponden al año completo."
        )

    def _establecer_detalle(self, texto):
        if not hasattr(self, "detalle"):
            return
        self.detalle.configure(state="normal")
        self.detalle.delete("1.0", "end")
        self.detalle.insert("1.0", texto)
        self.detalle.configure(state="disabled")

    def mostrar_detalle(self, _evento=None):
        seleccion = self.tabla_ranking.selection()
        if not seleccion or self.ranking is None:
            return
        fila = self.ranking.iloc[int(seleccion[0])]
        anio = int(fila["anio_corte"])
        nombre = str(fila["razon_social"])
        nit = str(fila["nit_normalizado"])
        score = float(fila["puntuacion"])
        etiqueta = "Positiva" if score >= self.umbral else "Negativa"
        radicado = str(fila.get("numero_radicado", "No disponible"))
        anio_radicado = fila.get("anio_radicado", pd.NA)
        if pd.notna(anio_radicado):
            anio_radicado = str(int(float(anio_radicado)))
        else:
            anio_radicado = "No disponible"
        lineas = [
            f"EMPRESA: {nombre}",
            f"NIT: {nit}    Año financiero: {anio}    Radicación: {anio_radicado}",
            f"Radicado: {radicado}    Posición anual: {int(fila['posicion_anual']):,}",
            f"Puntuación: {score:.6f}    Señal por umbral: {etiqueta}",
            f"Tipo: {TIPOS_POR_ANIO.get(anio, 'Histórico')}",
            "",
            "INDICADORES FINANCIEROS (valores usados por el modelo):",
        ]
        for indicador in self.indicadores:
            lineas.append(f"  {NOMBRES[indicador]:<23} {valor_texto(fila[indicador], 5)}")
        lineas.extend([
            "",
            "Lectura: puntuación relativa de priorización HISTÓRICA. No es una "
            "probabilidad calibrada ni certifica insolvencia actual.",
        ])
        self._establecer_detalle("\n".join(lineas))


def main():
    try:
        modelo, indicadores, umbral = cargar_artefacto()
    except Exception as exc:
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
