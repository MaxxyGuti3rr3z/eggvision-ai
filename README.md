# EggVision AI

Prototipo de hackathon: sistema de visión artificial para clasificar huevos de
una empresa avícola que hoy lo hace a mano. **Una foto = un huevo.**

## Problema

- En la planta los huevos se clasifican a mano, uno por uno: primero el defecto
  (`normal` / `rajado` / `roto_total`) y después el tamaño.
- La tarea es lenta, cansadora y subjetiva: cada operario "ve" distinto una fisura.
- No queda registro de lo clasificado: no se puede auditar un lote ni responder
  "¿cuántos rajados salieron el martes?".

## Solución

EggVision AI corre **en la PC de la planta, sin internet** (una vez instaladas
las dependencias). Con una foto de un huevo:

1. **Clasifica el defecto** con una red neuronal (MobileNetV2 + transfer
   learning) entrenada con las fotos del dataset.
2. **Mide el tamaño sin IA**: segmenta el huevo con OpenCV y calcula su largo y
   ancho. Hoy la cámara **no está calibrada**: la app muestra "no calibrado" en
   lugar de milímetros (ver Roadmap).
3. **Guarda cada resultado** en SQLite (fecha, lote, defecto, confianza, largo,
   ancho, tamaño) y lo muestra en un **panel** con filtros, gráficos por día/lote
   y reporte CSV descargable.

| Eje      | Categorías                                          |
|----------|-----------------------------------------------------|
| Defecto  | `normal` / `rajado` (fisura visible) / `roto_total` |
| Tamaño   | chico / mediano / grande / extra (rangos en `config.yaml`; sin calibrar hoy) |

Stack: Python, TensorFlow/Keras, OpenCV, Streamlit, SQLite, pandas, Plotly.

## Cómo correrlo desde cero

Requiere Python 3.10 o superior (probado con 3.13).

```bash
# 1) Entorno virtual
python -m venv .venv
# Windows:     .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate

# 2) Dependencias (verificado en un entorno limpio, ver "Notas")
pip install -r requirements.txt

# 3) Reparto train/test (75/25, estratificado por clase)
python scripts/split_dataset.py

# 4) Entrenar el modelo -> model/egg_classifier.keras
python scripts/train.py

# 5) (Opcional) 300 registros simulados para el panel
#    (si data/eggs.db no existe, la app los carga sola al arrancar)
python scripts/seed_demo.py

# 6) App: tres páginas (Clasificar, Panel, Acerca de)
streamlit run app/main.py
```

Si `model/egg_classifier.keras` no existe, el entrenamiento (paso 4) es
obligatorio: sin modelo la app muestra "modelo no disponible" y no clasifica.

**Deploy en Streamlit Community Cloud:** la app arranca desde un clon limpio
con `streamlit run app/main.py` (archivo principal `app/main.py`). Si
`data/eggs.db` no existe, la app la crea con sus tablas y carga los 300
registros de demo marcados como simulados. Usar Python 3.12 en Advanced
settings.

Predicción por consola:

```bash
python scripts/predict.py data/raw/normal/huevo-normal2.jpeg
```

### Estructura del proyecto

```
.
├── app/            # Interfaz web (Streamlit): main.py, classifier.py y
│   └── pages/      #   páginas: clasificar, panel, acerca_de
├── .streamlit/     # Tema propio de la interfaz (config.toml)
├── model/          # egg_classifier.keras y clases.json (entrenados)
├── data/           # raw/ (fotos), train/, test/ y eggs.db (SQLite)
├── scripts/        # split_dataset, train, predict, seed_demo,
│                   # calibrate, validate_size
├── config.yaml     # Configuración (rutas, clases, rangos, umbral de alerta)
├── requirements.txt
└── README.md
```

## Datos

**29 imágenes en total** en `data/raw/`, en tres carpetas por clase:

- **`normal/`: 11 fotos propias** de huevos normales (una foto por huevo).
- **`rajado/`: 8 fotos** y **`roto_total/`: 10 fotos** — **18 fotos en total**
  de una librería de imágenes, una foto por archivo.

**No se usaron imágenes generadas por IA:** todas las fotos del dataset son
reales (propias o de librería).

### Inventario de fotos

| Archivo | Clase | Fuente | Autor | Enlace | Licencia |
|---------|-------|--------|-------|--------|----------|
| `data/raw/normal/huevo-normal.jpeg` | `normal` | propia | pendiente | pendiente | pendiente |
| `data/raw/normal/huevo-normal1.jpeg` | `normal` | propia | pendiente | pendiente | pendiente |
| `data/raw/normal/huevo-normal2.jpeg` | `normal` | propia | pendiente | pendiente | pendiente |
| `data/raw/normal/huevo-normal3.jpeg` | `normal` | propia | pendiente | pendiente | pendiente |
| `data/raw/normal/huevo-normal4.jpeg` | `normal` | propia | pendiente | pendiente | pendiente |
| `data/raw/normal/huevo-normal5.jpeg` | `normal` | propia | pendiente | pendiente | pendiente |
| `data/raw/normal/huevo-normal6.jpeg` | `normal` | propia | pendiente | pendiente | pendiente |
| `data/raw/normal/huevo-normal7.jpeg` | `normal` | propia | pendiente | pendiente | pendiente |
| `data/raw/normal/huevo-normal8.jpeg` | `normal` | propia | pendiente | pendiente | pendiente |
| `data/raw/normal/huevo-normal9.jpeg` | `normal` | propia | pendiente | pendiente | pendiente |
| `data/raw/normal/huevo-normal10.jpg` | `normal` | propia | pendiente | pendiente | pendiente |
| `data/raw/rajado/huevo-rajado1.jpg` | `rajado` | Libreria | pendiente | pendiente | Gratuita |
| `data/raw/rajado/huevo-rajado2.jpg` | `rajado` | Libreria | pendiente | pendiente | Gratuita |
| `data/raw/rajado/huevo-rajado3.jpg` | `rajado` | Libreria | pendiente | pendiente | Gratuita |
| `data/raw/rajado/huevo-rajado4.jpg` | `rajado` | Libreria | pendiente | pendiente | Gratuita |
| `data/raw/rajado/huevo-rajado5.jpg` | `rajado` | Libreria | pendiente | pendiente | Gratuita |
| `data/raw/rajado/huevo-rajado6.jpg` | `rajado` | Libreria | pendiente | pendiente | Gratuita |
| `data/raw/rajado/huevo-rajado7.jpg` | `rajado` | Libreria | pendiente | pendiente | Gratuita |
| `data/raw/rajado/huevo-rajado8.jpg` | `rajado` | Libreria | pendiente | pendiente | Gratuita |
| `data/raw/roto_total/huevo-roto1.jpg` | `roto_total` | Libreria | pendiente | pendiente | Gratuita |
| `data/raw/roto_total/huevo-roto2.jpg` | `roto_total` | Libreria | pendiente | pendiente | Gratuita |
| `data/raw/roto_total/huevo-roto3.jpg` | `roto_total` | Libreria | pendiente | pendiente | Gratuita |
| `data/raw/roto_total/huevo-roto4.jpg` | `roto_total` | Libreria | pendiente | pendiente | Gratuita |
| `data/raw/roto_total/huevo-roto5.jpg` | `roto_total` | Libreria | pendiente | pendiente | Gratuita |
| `data/raw/roto_total/huevo-roto6.jpg` | `roto_total` | Libreria | pendiente | pendiente | Gratuita |
| `data/raw/roto_total/huevo-roto7.jpg` | `roto_total` | Libreria | pendiente | pendiente | Gratuita |
| `data/raw/roto_total/huevo-roto8.jpg` | `roto_total` | Libreria | pendiente | pendiente | Gratuita |
| `data/raw/roto_total/huevo-roto9.jpg` | `roto_total` | Libreria | pendiente | pendiente | Gratuita |
| `data/raw/roto_total/huevo-roto10.jpg` | `roto_total` | Libreria | pendiente | pendiente | Gratuita |

### Registros del panel

- **300 registros de demostración, SIMULADOS** (`scripts/seed_demo.py`,
  `es_demo = 1`). No representan clasificaciones reales.
- Están **marcados en pantalla**: en el panel, el interruptor "Incluir datos de
  demostración (simulados)" los agrega a los gráficos y al aparecer se muestra
  el aviso **"DATOS SIMULADOS"**. Sin activarlo, el panel solo muestra
  clasificaciones hechas con la app.

## Resultados del modelo

> **Aviso:** esto es una **prueba preliminar con muy pocos datos** (29 fotos).
> Los números no prometen ese desempeño con más datos ni con fotos de la
> planta (ver Limitaciones).

**Entrenamiento** (`scripts/train.py`): MobileNetV2 preentrenada en ImageNet,
entrada 224×224; aumento de datos moderado (volteo horizontal, rotación leve,
brillo ±15%); class weights para compensar el desbalance; fase 1 con la base
congelada durante 10 épocas (lr 1e-3) y fase 2 con fine-tune de las últimas 30
capas durante 5 épocas (lr 1e-4); lote de 32.

**Reparto** (`scripts/split_dataset.py`, 75/25 estratificado):

| Clase       | Total | Train | Test |
|-------------|-------|-------|------|
| normal      | 11    | 8     | 3    |
| rajado      | 8     | 6     | 2    |
| roto_total  | 10    | 8     | 2    |
| **Total**   | **29**| **22**| **7**|

**Evaluación en test (7 fotos):**

| Métrica    | Resultado        |
|------------|------------------|
| **Accuracy** | **85,7% (6/7)** |

Matriz de confusión (filas = real, columnas = predicha):

| real \ predicho | normal | rajado | roto_total |
|-----------------|--------|--------|------------|
| **normal**      | 3      | 0      | 0          |
| **rajado**      | 1      | 1      | 0          |
| **roto_total**  | 0      | 0      | 2          |

Recall por clase (de los reales de cada clase, cuántos detectó):

| Clase      | Recall  |
|------------|---------|
| normal     | 100% (3/3) |
| rajado     | **50% (1/2)** |
| roto_total | 100% (2/2) |

Con solo 7 fotos en test, **una foto cambia el accuracy en ~14 puntos**: el
resultado hay que leerlo como una verificación de que el flujo funciona, no
como una medición estable del modelo.

## Capturas

<!-- Pegar acá las capturas de la demo. -->

| Pantalla                                                      | Captura |
|---------------------------------------------------------------|---------|
| Clasificar: tarjeta con defecto, confianza y "no calibrado"    | _TODO: captura_ |
| Revisión manual (confianza menor al 60%)                      | _TODO: captura_ |
| Panel: KPIs, filtros y gráficos                                | _TODO: captura_ |
| Panel: datos de demostración marcados como simulados y CSV    | _TODO: captura_ |
| Acerca de                                                     | _TODO: captura_ |

## Video

**Enlace al video de la demo:** _TODO: pegar el enlace_

## Limitaciones

- **Pocos datos:** 29 fotos en total y 7 en test: el modelo no está probado
  de forma confiable.
- **Posible sesgo de estilo:** las fotos `normal/` son propias y las de defecto
  vienen de internet (resoluciones y estilos muy distintos). El modelo podría
  estar distinguiendo el estilo de la foto y no el defecto; el test comparte
  el mismo sesgo.
- **Recall de rajado: 1 sobre 2** — el defecto que más importa detectar es el
  que más falla (ver Resultados).
- **Tamaño sin calibrar:** no hay foto de referencia con medida conocida, así
  que la app muestra "no calibrado" en lugar de milímetros.
- **Una foto por huevo:** no detecta varios huevos en la misma imagen.

## Roadmap

- **Más datos reales de la empresa:** fotos propias de las tres clases
  (con sus enlaces, autores y licencias donde corresponda) y recomentar.
- **Análisis de maple completo:** clasificar la bandeja entera en una sola
  foto: contar los huevos, ubicar cada uno y marcar el defecto en su lugar.
- **Calibración de tamaño:** foto de referencia con medida conocida
  (`scripts/calibrate.py`) para mostrar largo, ancho y categoría en mm.
- **Ovoscopía:** integrar transiluminación (ovoscopio) para detectar defectos
  internos que la cámara normal no ve.
- **Alertas:** avisos automáticos (no solo en el panel) cuando sube el
  porcentaje de rajados en un lote o un turno. Hoy el panel ya avisa cuando un
  lote supera el umbral de `config.yaml`.
- **Trazabilidad:** quién clasificó, con qué dispositivo y en qué momento;
  historial por lote y exportación para auditorías.

## Notas

- Todo corre en local, sin internet una vez instaladas las dependencias.
- El código está comentado en español para poder explicarlo al jurado.
- `requirements.txt` **con versiones fijas**, probado en un entorno virtual
  nuevo (Python 3.13.0): `pip install -r requirements.txt` instala todo
  (tensorflow-cpu 2.21.0, opencv-python 4.14.0.94, streamlit 1.67.0,
  pandas 3.1.1, plotly 7.1.0, PyYAML 6.0.3), `pip check` no encuentra
  conflictos y los imports funcionan.
- **Python requerido: 3.10 a 3.13** (lo que soporta TensorFlow 2.21).
  En Streamlit Community Cloud: elegir **3.12** en Advanced settings.



