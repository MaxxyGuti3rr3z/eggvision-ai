"""
Paso 1a: reparte las fotos de data/raw en data/train (75%) y data/test (25%).

Reglas del reparto:
  * Estratificado por clase: cada clase (normal, rajado, roto_total) queda
    representada en train y en test.
  * Separado POR HUEVO: todas las fotos de "huevo07_..." van al mismo lado.
    Si el mismo huevo apareciera en train y en test, el modelo "hace trampa"
    reconociendo al huevo en vez del defecto.
  * Si el archivo no tiene número de huevo (datasets públicos), se reparte
    foto por foto.

Uso:  python scripts/split_dataset.py
"""

import random
import re
import shutil
from pathlib import Path

import yaml

# Raíz del proyecto: la carpeta que contiene scripts/
RAIZ = Path(__file__).resolve().parent.parent

# Formatos de imagen que aceptamos
EXTENSIONES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

# "huevo07_rajado_2.jpg" -> devuelve "07" (el número de huevo)
PATRON_HUEVO = re.compile(r"^huevo[_-]?(\d+)", re.IGNORECASE)

# Reparto aproximado train/test y semilla para que sea siempre el mismo
PROPORCION_TRAIN = 0.75
SEMILLA = 42


def cargar_config():
    """Lee config.yaml (clases y rutas)."""
    with open(RAIZ / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def detectar_clase(ruta, clases):
    """Busca la clase en el nombre del archivo o, si no, en su carpeta."""
    nombre = ruta.stem.lower().replace("-", "_")
    # Se prueba la clase más larga primero: "roto_total" antes que "normal"
    for clase in sorted(clases, key=len, reverse=True):
        if clase in nombre:
            return clase
    # Datasets públicos: la clase puede estar en el nombre de la carpeta
    carpeta = ruta.parent.name.lower().replace("-", "_")
    if carpeta in clases:
        return carpeta
    return None


def repartir(grupos):
    """Divide los grupos de una clase en train/test (~75/25).

    Los grupos se mezclan al azar y se van cargando en train hasta llegar
    al 75%. Un grupo completo (un huevo) nunca se parte en dos.
    """
    items = list(grupos.items())            # [(id_grupo, [archivos]), ...]
    random.Random(SEMILLA).shuffle(items)

    total = sum(len(archivos) for _, archivos in items)
    objetivo = round(total * PROPORCION_TRAIN)

    train, test = [], []
    fotos_en_train = 0
    for id_grupo, archivos in items:
        if fotos_en_train < objetivo:
            train.append((id_grupo, archivos))
            fotos_en_train += len(archivos)
        else:
            test.append((id_grupo, archivos))

    # Si un huevo es tan grande que se llevó todo a train,
    # dejamos el último grupo para test (nunca si solo hay un grupo)
    if len(items) >= 2 and not test:
        test.append(train.pop())

    return train, test


def main():
    cfg = cargar_config()
    clases = [str(c).lower() for c in cfg["clases_defecto"]]
    datos = RAIZ / cfg["rutas"]["datos"]
    origen = datos / "raw"

    if not origen.is_dir():
        print(f"No existe la carpeta {origen}.")
        print("Creala y poné ahí las fotos (ej: huevo07_rajado_2.jpg).")
        return

    # 1) Leer las fotos y agruparlas por huevo dentro de cada clase
    grupos = {c: {} for c in clases}
    ignoradas = []
    fotos_por_huevo = 0     # fotos que sí tienen número de huevo
    fotos_por_foto = 0      # fotos de datasets públicos (sin número de huevo)

    for ruta in sorted(origen.rglob("*")):
        if not ruta.is_file() or ruta.suffix.lower() not in EXTENSIONES:
            continue

        clase = detectar_clase(ruta, clases)
        if clase is None:
            ignoradas.append(ruta)
            continue

        match = PATRON_HUEVO.match(ruta.stem)
        if match:
            grupo = f"huevo{match.group(1)}"
            fotos_por_huevo += 1
        else:
            # Sin número de huevo: cada archivo es su propio grupo
            grupo = ruta.relative_to(origen).as_posix()
            fotos_por_foto += 1

        grupos[clase].setdefault(grupo, []).append(ruta)

    if fotos_por_huevo + fotos_por_foto == 0:
        print(f"No se encontraron imágenes en {origen}.")
        print(f"Formatos aceptados: {', '.join(sorted(EXTENSIONES))}")
        return

    # 2) Repartir cada clase por separado (estratificado)
    plan = {}
    clases_vacias = []
    for clase in clases:
        if not grupos[clase]:
            clases_vacias.append(clase)
            continue
        plan[clase] = repartir(grupos[clase])

    # 3) Imprimir el reporte
    print("=" * 74)
    print("REPARTO DEL DATASET  (train 75% / test 25%, separado por huevo)")
    print("=" * 74)
    print(f"{'CLASE':<14}{'TOTAL':>14}{'TRAIN':>14}{'TEST':>14}   (huevos / fotos)")

    totales = [0, 0, 0, 0, 0, 0]
    for clase in clases:
        if clase not in plan:
            print(f"{clase:<14}{'sin fotos':>14}")
            continue
        train, test = plan[clase]
        huevos = len(grupos[clase])
        fotos = sum(len(a) for a in grupos[clase].values())
        h_train = len(train)
        f_train = sum(len(a) for _, a in train)
        h_test = len(test)
        f_test = sum(len(a) for _, a in test)
        print(
            f"{clase:<14}"
            f"{f'{huevos} / {fotos}':>14}"
            f"{f'{h_train} / {f_train}':>14}"
            f"{f'{h_test} / {f_test}':>14}"
        )
        totales[0] += huevos
        totales[1] += fotos
        totales[2] += h_train
        totales[3] += f_train
        totales[4] += h_test
        totales[5] += f_test

    print("-" * 74)
    print(
        f"{'TOTAL':<14}"
        f"{f'{totales[0]} / {totales[1]}':>14}"
        f"{f'{totales[2]} / {totales[3]}':>14}"
        f"{f'{totales[4]} / {totales[5]}':>14}"
    )
    print(
        f"\nSeparadas por huevo: {fotos_por_huevo} fotos | "
        f"por foto (sin número de huevo): {fotos_por_foto} fotos"
    )

    # 4) Copiar (no mover) los archivos, para poder volver a correr el script
    for lado in ("train", "test"):
        if (datos / lado).exists():
            shutil.rmtree(datos / lado)

    copiadas = {"train": 0, "test": 0}
    for clase, (train, test) in plan.items():
        for lado, grupos_lado in (("train", train), ("test", test)):
            for _, archivos in grupos_lado:
                for ruta in archivos:
                    # Si vino de una subcarpeta, se antepone su nombre
                    # para que dos archivos iguales no se pisen
                    if ruta.parent == origen:
                        nombre = ruta.name
                    else:
                        nombre = f"{ruta.parent.name}_{ruta.name}"
                    destino = datos / lado / clase / nombre
                    destino.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(ruta, destino)
                    copiadas[lado] += 1

    print(f"\nCopiadas {copiadas['train']} fotos a data/train")
    print(f"Copiadas {copiadas['test']} fotos a data/test")

    # 5) Avisos
    if clases_vacias:
        print(f"\nAVISO: clases sin fotos -> {', '.join(clases_vacias)}")
    for clase, (_, test) in plan.items():
        if not test:
            print(
                f"\nAVISO: la clase '{clase}' quedó toda en train "
                f"(solo tiene un huevo / una foto): no hay ejemplos de test."
            )
    if ignoradas:
        plural = "archivo" if len(ignoradas) == 1 else "archivos"
        print(f"\nAVISO: {len(ignoradas)} {plural} sin clase reconocida "
              f"(no se usaron):")
        for ruta in ignoradas[:10]:
            print(f"  - {ruta.relative_to(origen)}")
        if len(ignoradas) > 10:
            print(f"  ... y {len(ignoradas) - 10} más")


if __name__ == "__main__":
    main()
