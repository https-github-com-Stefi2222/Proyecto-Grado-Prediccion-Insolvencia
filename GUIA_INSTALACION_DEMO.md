# Demostración para sustentación — Proyecto de grado CUN

Esta versión permite ejecutar **inferencia con un modelo Random Forest ya entrenado**, con su preprocesamiento y umbral de decisión, sin instalar SQL Server ni descargar las bases de datos originales.

## Qué debe haber en el repositorio

- `demo/interfaz_sustentacion.py` (interfaz gráfica, incluida en este paquete).
- `demo/ejecutar_demo.py` (demostración de consola, ya creada previamente).
- `python/percentile_clipper.py` (clase necesaria para cargar el pipeline).
- `modelos/random_forest_pipeline.joblib` (modelo **propio**, generado en el computador de desarrollo).
- `requirements-demo.txt` (las versiones que ya se probaron con éxito).
- `INICIAR_DEMO.bat` (ejecutable de inicio, incluido en este paquete).

## Instalación en otro computador con Windows

1. Instalar Python **3.14.6** (o una versión compatible previamente verificada) y permitir su uso desde terminal.
2. Clonar el repositorio privado con GitHub Desktop o descargarlo desde GitHub con acceso autorizado.
3. Abrir PowerShell **en la carpeta principal del repositorio**.
4. Ejecutar:

```powershell
py -3.14 -m venv .venv-demo
.\.venv-demo\Scripts\python.exe -m pip install -r requirements-demo.txt
.\.venv-demo\Scripts\python.exe .\demo\interfaz_sustentacion.py
```

Si el comando `py -3.14` no está disponible, sustituirlo por la ruta del ejecutable `python.exe` de Python 3.14.6. No copies carpetas `.venv` de un computador a otro.

## Uso durante la sustentación

Una vez instalada la demo, hacer doble clic en **`INICIAR_DEMO.bat`** desde la carpeta raíz. En la ventana, seleccionar **Perfil A** o **Perfil B**, pulsar **EVALUAR PERFIL**, explicar la puntuación relativa y el umbral de clasificación. También es posible modificar los nueve indicadores y volver a evaluar.

- Perfil A: medianas ilustrativas del grupo sin evento.
- Perfil B: medianas ilustrativas del grupo con evento.
- Estos perfiles **no representan empresas individuales**, ni permiten determinar la quiebra de una empresa.
- Las puntuaciones **no son probabilidades calibradas de insolvencia**. Una señal negativa tampoco descarta riesgo financiero.
- Las métricas de evaluación temporal (ROC-AUC 0,7813; PR-AUC 0,0186; captura top 20 % del 59,56 %) son resultados de la evaluación original; **no son métricas calculadas con los dos perfiles ilustrativos**.

## Validación previa a la presentación

Verificar que la interfaz pueda evaluar ambos perfiles, que la consola y la interfaz muestren los mismos resultados (aproximadamente **0,205986** y **0,718834**) y que el umbral mostrado sea **0,575598**. Si las puntuaciones difieren, no presentar la demostración hasta revisar las dependencias y el artefacto.

**Seguridad:** cargar únicamente el archivo `.joblib` generado por el equipo; el formato puede ejecutar código al deserializar datos manipulados por terceros.
