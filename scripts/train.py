"""
Paso 1b: entrena el clasificador de defectos con MobileNetV2.

  * MobileNetV2 preentrenada en ImageNet (transfer learning).
  * Imágenes de 224x224.
  * Aumento de datos moderado: giros, rotación leve y brillo.
  * class_weight para compensar el desbalance entre clases.
  * Al final: accuracy en test, matriz de confusión y precisión/recall
    por clase.

Uso:  python scripts/train.py     (primero corré scripts/split_dataset.py)
"""

import json
from pathlib import Path

import numpy as np
import tensorflow as tf
import yaml
from tensorflow import keras

# Raíz del proyecto: la carpeta que contiene scripts/
RAIZ = Path(__file__).resolve().parent.parent

# Hiperparámetros del entrenamiento
EPOCAS = 10        # fase 1: capa base congelada, se entrena solo la cabeza
EPOCAS_AJUSTE = 5  # fase 2: se afino las últimas capas de MobileNetV2
LOTE = 32          # fotos por lote

# Formatos de imagen que aceptamos
EXTENSIONES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def cargar_config():
    """Lee config.yaml (clases, tamaño de imagen y rutas)."""
    with open(RAIZ / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def contar_fotos(carpeta, clases):
    """Cuenta cuántas fotos hay por clase dentro de una carpeta."""
    conteo = {}
    for clase in clases:
        subcarpeta = carpeta / clase
        if not subcarpeta.is_dir():
            conteo[clase] = 0
            continue
        conteo[clase] = len([
            f for f in subcarpeta.glob("*") if f.suffix.lower() in EXTENSIONES
        ])
    return conteo


def pesos_de_clase(conteo, orden_clases):
    """class_weight para el desbalance: clase con pocas fotos pesa más.

    Fórmula: total_fotos / (cantidad_de_clases * fotos_de_la_clase)
    """
    total = sum(conteo.values())
    return {
        i: total / (len(orden_clases) * conteo[nombre])
        for i, nombre in enumerate(orden_clases)
    }


def construir_modelo(config, cantidad_clases):
    """MobileNetV2 preentrenada + cabeza propia para nuestras clases."""
    ancho, alto = config["ancho_imagen"], config["alto_imagen"]

    base = keras.applications.MobileNetV2(
        weights="imagenet",        # pesos entrenados en ImageNet
        include_top=False,         # sin la capa final de 1000 categorías
        input_shape=(ancho, alto, 3),
    )
    base.trainable = False         # fase 1: no toco la base preentrenada

    modelo = keras.Sequential([
        keras.layers.Input(shape=(ancho, alto, 3)),
        # MobileNetV2 espera los píxeles en el rango [-1, 1].
        # Ponerlo adentro del modelo hace que predict.py no tenga
        # que acordarse de ningún preprocesamiento.
        keras.layers.Rescaling(1.0 / 127.5, offset=-1),
        base,
        keras.layers.GlobalAveragePooling2D(),
        keras.layers.Dropout(0.2),
        keras.layers.Dense(cantidad_clases, activation="softmax"),
    ])
    return modelo, base


def compilar(modelo, learning_rate):
    modelo.compile(
        optimizer=keras.optimizers.Adam(learning_rate),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )


def evaluar(modelo, test_ds, clases):
    """Imprime accuracy, matriz de confusión y precisión/recall por clase."""
    # Recorremos el set de test una sola vez y guardamos real vs predicho
    y_real, y_pred = [], []
    for imagenes, etiquetas in test_ds:
        predicciones = modelo.predict(imagenes, verbose=0)
        y_real.extend(etiquetas.numpy().tolist())
        y_pred.extend(np.argmax(predicciones, axis=1).tolist())

    y_real = np.array(y_real)
    y_pred = np.array(y_pred)
    n = len(clases)

    # Matriz de confusión: fila = clase real, columna = clase predicha
    matriz = np.zeros((n, n), dtype=int)
    for real, pred in zip(y_real, y_pred):
        matriz[real, pred] += 1

    aciertos = int((y_real == y_pred).sum())
    accuracy = aciertos / len(y_real) if len(y_real) else 0.0

    print("\n" + "=" * 60)
    print(f"RESULTADOS EN TEST  ({len(y_real)} fotos)")
    print("=" * 60)
    print(f"Accuracy: {accuracy:.4f}  ({aciertos}/{len(y_real)} fotos bien)")

    # Matriz de confusión
    print("\nMatriz de confusión (filas = real, columnas = predicha):")
    print(f"{'':<16}" + "".join(f"{'pred_' + c:>18}" for c in clases))
    for i, clase in enumerate(clases):
        fila = "".join(f"{matriz[i, j]:>18}" for j in range(n))
        print(f"{'real_' + clase:<16}{fila}")

    # Precisión y recall por clase
    print("\nPrecisión y recall por clase:")
    recall_rajado = None
    for i, clase in enumerate(clases):
        soporte = int(matriz[i].sum())              # fotos reales de la clase
        predichos = int(matriz[:, i].sum())         # fotos predichas como la clase
        verdaderos = int(matriz[i, i])
        precision = verdaderos / predichos if predichos else 0.0
        recall = verdaderos / soporte if soporte else 0.0
        print(f"  {clase:<12} precision={precision:.3f}  "
              f"recall={recall:.3f}  (soporte={soporte})")
        if clase == "rajado":
            recall_rajado = (recall, verdaderos, soporte)

    # El recall de "rajado" es la métrica que más nos interesa:
    # de todos los huevos rajados, ¿cuántos detectamos?
    if recall_rajado is not None:
        recall, verdaderos, soporte = recall_rajado
        print(f"\nRecall de 'rajado': {recall:.3f} -> detectó "
              f"{verdaderos} de {soporte} huevos rajados.")


def main():
    config = cargar_config()
    clases = [str(c).lower() for c in config["clases_defecto"]]
    ancho, alto = config["ancho_imagen"], config["alto_imagen"]
    datos = RAIZ / config["rutas"]["datos"]
    train_dir, test_dir = datos / "train", datos / "test"

    if not train_dir.is_dir() or not test_dir.is_dir():
        print(f"Faltan {train_dir} o {test_dir}.")
        print("Primero corré: python scripts/split_dataset.py")
        return

    # 1) Cargar los datasets (Keras ordena las clases alfabéticamente)
    train_ds = keras.utils.image_dataset_from_directory(
        train_dir, image_size=(ancho, alto), batch_size=LOTE,
        shuffle=True, seed=42,
    )
    test_ds = keras.utils.image_dataset_from_directory(
        test_dir, image_size=(ancho, alto), batch_size=LOTE,
        shuffle=False,
    )

    orden_clases = train_ds.class_names
    if set(orden_clases) != set(clases):
        raise SystemExit(
            f"Las carpetas de data/train no coinciden con config.yaml:\n"
            f"  carpetas: {orden_clases}\n  config:   {sorted(clases)}"
        )

    # 2) class_weight por el desbalance de clases
    conteo = contar_fotos(train_dir, orden_clases)
    if any(v == 0 for v in conteo.values()):
        raise SystemExit(f"Hay clases sin fotos en data/train: {conteo}")
    class_weight = pesos_de_clase(conteo, orden_clases)

    n_test = sum(
        1 for f in test_dir.rglob("*") if f.suffix.lower() in EXTENSIONES
    )
    print(f"Clases: {orden_clases}")
    print(f"Fotos de train: {sum(conteo.values())} | Fotos de test: {n_test}")
    print(f"Fotos por clase (train): {conteo}")
    print("Class weight: "
          f"{ {c: round(w, 2) for c, w in zip(orden_clases, class_weight.values())} }")

    # 3) Aumento de datos moderado (solo en train, nunca en test)
    aumento = keras.Sequential([
        keras.layers.RandomFlip("horizontal"),  # giros
        keras.layers.RandomRotation(0.05),      # rotación leve (~18°)
        keras.layers.RandomBrightness(0.15),    # brillo
    ], name="aumento")
    train_ds = train_ds.map(
        lambda x, y: (aumento(x, training=True), y)
    ).prefetch(tf.data.AUTOTUNE)
    test_ds = test_ds.prefetch(tf.data.AUTOTUNE)

    # 4) Fase 1: base congelada, entreno solo la cabeza
    modelo, base = construir_modelo(config, len(orden_clases))
    compilar(modelo, learning_rate=1e-3)
    modelo.summary()

    print("\n--- Fase 1: MobileNetV2 congelada, entreno la cabeza ---")
    historial = modelo.fit(
        train_ds, epochs=EPOCAS, class_weight=class_weight, verbose=2,
        shuffle=False,  # el dataset ya viene mezclado (Keras lo ignora)
    )

    # 5) Fase 2: afino las últimas capas de la red (fine-tuning)
    print("\n--- Fase 2: afino las últimas 30 capas de MobileNetV2 ---")
    base.trainable = True
    for capa in base.layers[:-30]:
        capa.trainable = False
    print(f"Capas entrenables: {len(modelo.trainable_weights)} tensores")
    compilar(modelo, learning_rate=1e-4)
    modelo.fit(
        train_ds,
        epochs=EPOCAS + EPOCAS_AJUSTE,
        initial_epoch=len(historial.history["loss"]),
        class_weight=class_weight,
        verbose=2,
        shuffle=False,  # el dataset ya viene mezclado (Keras lo ignora)
    )

    # 6) Guardar el modelo y el orden de las clases
    modelo_dir = RAIZ / config["rutas"]["modelo"]
    modelo_dir.mkdir(parents=True, exist_ok=True)
    ruta_modelo = modelo_dir / "egg_classifier.keras"
    modelo.save(ruta_modelo)
    with open(modelo_dir / "clases.json", "w", encoding="utf-8") as f:
        json.dump(orden_clases, f, ensure_ascii=False, indent=2)
    print(f"\nModelo guardado en {ruta_modelo.relative_to(RAIZ)}")
    print(f"Clases guardadas en model/clases.json -> {orden_clases}")

    # 7) Métricas finales
    evaluar(modelo, test_ds, orden_clases)


if __name__ == "__main__":
    main()
