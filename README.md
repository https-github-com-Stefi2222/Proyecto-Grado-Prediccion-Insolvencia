# Modelo predictivo del riesgo de insolvencia empresarial en Colombia

**Proyecto de grado — Especialización en Analítica de Datos**  
**Corporación Unificada Nacional de Educación Superior (CUN)**  
**Colombia · Período de estudio: 2021–2024**

## Descripción

Este proyecto desarrolla y evalúa un modelo para **priorizar la revisión del riesgo relativo de insolvencia empresarial** a partir de nueve indicadores financieros. La investigación utiliza información financiera y registros de insolvencia de la Superintendencia de Sociedades de Colombia.

Se compararon modelos de regresión logística, Random Forest e HistGradientBoosting. El modelo seleccionado para la demostración es **Random Forest**.

> **Alcance:** las puntuaciones sirven para ordenar perfiles según riesgo relativo; no son probabilidades calibradas de insolvencia ni constituyen un diagnóstico jurídico.

## Demostración para la sustentación

La demostración ejecuta el **pipeline previamente entrenado**, incluidos su preprocesamiento y umbral de decisión. No requiere SQL Server, bases de datos originales ni volver a entrenar el modelo.

Se puede interactuar con los nueve indicadores financieros, utilizar dos perfiles ilustrativos y observar la puntuación y clasificación que genera el modelo.

### Requisitos

- Windows con **Python 3.14.6** (versión utilizada para validar esta demostración).
- Acceso a una terminal de PowerShell.
- Conexión a internet para instalar dependencias la primera vez.

### Instalación

Abrir PowerShell en la carpeta principal del repositorio y ejecutar los siguientes comandos, uno a uno:

**1. Crear el entorno virtual**

```powershell
python -m venv .venv-demo
```

**2. Instalar las dependencias**

```powershell
.\.venv-demo\Scripts\python.exe -m pip install -r requirements-demo.txt
```

**3. Abrir la interfaz gráfica**

```powershell
.\.venv-demo\Scripts\python.exe .\demo\interfaz_sustentacion.py
```

**4. Alternativa: ejecutar la demostración en consola**

```powershell
.\.venv-demo\Scripts\python.exe .\demo\ejecutar_demo.py
```

> Si `python` no se reconoce, verificar la instalación de Python y su disponibilidad en el PATH. Si la interfaz no abre, comprobar que la instalación de Python incluya **Tkinter**.

### Verificación rápida

Al cargar los dos perfiles ilustrativos y pulsar **EVALUAR PERFIL**, los resultados observados en el entorno de desarrollo fueron:

| Perfil | Puntuación relativa | Señal según umbral |
|:--|--:|:--|
| Perfil A (sin evento) | 0,205986 | Negativa |
| Perfil B (con evento) | 0,718834 | Positiva |

**Umbral de clasificación:** 0,575598, seleccionado mediante predicciones fuera de muestra (*out-of-fold*) en la cohorte de desarrollo.

Los perfiles son ilustrativos, no corresponden a empresas reales. Los resultados pueden variar si se modifican los indicadores.

## Resultados de la evaluación temporal

Estas métricas corresponden a la **evaluación de la investigación**, no a los dos perfiles de demostración.

| Indicador | Resultado |
|:--|--:|
| ROC-AUC | 0,7813 |
| PR-AUC | 0,0186 |
| Precisión | 2,35 % |
| Sensibilidad | 22,06 % |
| Eventos capturados en el 20 % de mayor puntuación | 59,56 % |

## Estructura del repositorio

```text
Proyecto-Grado-Prediccion-Insolvencia/
├── demo/                  # Interfaz gráfica y demostración en consola
├── modelos/               # Pipeline entrenado (.joblib)
├── python/                # Scripts de procesamiento y modelado
├── sql/                   # Scripts del procesamiento original en SQL Server
├── outputs/graficos/      # Visualizaciones de la investigación
├── requirements-demo.txt  # Dependencias de la demostración
└── README.md              # Esta guía
```

## Investigación completa y reproducción

El repositorio conserva scripts del procesamiento y modelado realizados durante el proyecto de grado. Para reproducir el **flujo completo de investigación** se requieren las fuentes de datos, SQL Server y la configuración correspondiente. Los archivos originales de gran tamaño no se incluyen en el repositorio.

La interfaz de sustentación es una **demostración técnica del modelo desarrollado** y no reemplaza el documento académico entregado ni modifica sus resultados.
