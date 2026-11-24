# Prueba real (fotos propias)

Esta carpeta alimenta la **prueba real** del evaluador. Se evalúa por separado de
`Test/` de Fruits-360. Sin fotos, `ml_training/evaluate.py` reporta `pendiente`.

## Estructura

```
data/real_test/
├── banano/
├── fresa/
├── limon/
├── manzana/
├── naranja/
├── pera/
├── tomate/
└── uva/
```

El nombre de cada carpeta es la etiqueta exacta que usa el modelo. Los nombres
válidos son: `banano`, `fresa`, `limon` (sin tilde), `manzana`, `naranja`,
`pera`, `tomate`, `uva`. Una carpeta con otro nombre se ignora. Git no versiona
carpetas vacías: si clonas el repositorio, crea las carpetas de clase a mano
(o ejecuta la evaluación y guárdalas tú mismo).

## Cómo tomar y guardar las fotos

1. Toma unas **10 fotos por clase** (80 en total).
2. Usa varios ejemplares de cada fruta y varía **fondo, iluminación y ángulo**.
3. Encuadra la **fruta entera y centrada**: el preprocesamiento recorta un
   cuadrado central y una fruta descentrada puede quedar fuera.
4. Redimensiona a unos **1024 px en el lado más largo**.
5. Guarda en **JPG, JPEG, PNG, WebP o BMP**. Si la foto es HEIC, conviértela.
6. Coloca cada foto **solo** en la carpeta de su fruta. No mezcles clases.

Puedes incluir un grupo de 2 o 3 frutas **de la misma clase** (por ejemplo, tres
limones en `limon/`): la etiqueta es por imagen, no por objeto. Aun así, prioriza
una fruta entera y centrada, porque el modelo se entrenó con una fruta por
fotograma y un grupo cambia la composición.

## Evaluar

```sh
uv run python ml_training/evaluate.py
```

Salidas en `ml_training/reports/`:

- `metrics.json`: prueba oficial y prueba real por separado.
- `summary.md`: resumen legible.
- `confusion_matrix_real.png`: matriz de confusión de las fotos propias.

Estados de la prueba real:

- `pendiente`: no hay fotos.
- `incompleta`: hay fotos, pero falta alguna clase.
- `ok`: hay fotos de las ocho clases.

La interfaz y `GET /api/v1/model` muestran ese estado. Si está `incompleta`,
indican «faltan clases».

## Importante

- **No subas estas fotos a Git.** Son datos locales de evaluación. El
  `.gitignore` local las excluye y solo versiona este README. El código tolera
  que la carpeta no exista o esté vacía.
- La imagen entra al modelo por el mismo preprocesamiento que cámara y subida:
  orientación EXIF, RGB, recorte central, 224×224 y normalización ImageNet.
