from io import BytesIO
from pathlib import Path
from threading import Lock

import cv2
import mediapipe as mp
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

MODELS = Path(__file__).resolve().parents[1] / "models"
PALETTES = {
    "Primavera": ("Coral", "Marfil", "Verde manzana", "Turquesa"),
    "Verano": ("Rosa malva", "Azul humo", "Lavanda", "Gris perla"),
    "Otoño": ("Terracota", "Oliva", "Camel", "Petróleo"),
    "Invierno": ("Fucsia", "Azul cobalto", "Blanco óptico", "Borgoña"),
}


def read_image(data):
    try:
        with Image.open(BytesIO(data)) as source:
            if source.format not in ("JPEG", "PNG", "WEBP"):
                raise ValueError("Usa una imagen JPEG, PNG o WebP.")
            if source.width * source.height > 20_000_000:
                raise ValueError("La imagen supera los 20 megapíxeles.")
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((1280, 1280))
            return np.asarray(image)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise ValueError("No se pudo leer la imagen.") from error


def face_shape(points):
    def distance(a, b):
        return float(np.linalg.norm(points[a] - points[b]))

    length, forehead, cheeks, jaw = [
        distance(a, b) for a, b in ((10, 152), (54, 284), (234, 454), (172, 397))
    ]
    if cheeks < 65:
        raise ValueError("Acércate a la cámara para distinguir los rasgos.")
    ratios = {
        "largo_pómulos": round(length / cheeks, 3),
        "frente_pómulos": round(forehead / cheeks, 3),
        "mandíbula_pómulos": round(jaw / cheeks, 3),
    }
    aspect, brow, chin = ratios.values()
    if aspect >= 1.49:
        shape = "Alargado/rectangular"
    elif brow >= .83 and brow - chin >= .09:
        shape = "Corazón/triángulo invertido"
    elif brow < .83 and chin < .77 and aspect > 1.21:
        shape = "Diamante"
    elif aspect <= 1.27:
        shape = "Cuadrado" if chin >= .82 else "Redondo"
    else:
        shape = "Ovalado"
    return shape, ratios


def check_pose(points):
    eye_line = points[263] - points[33]
    eye_width = np.linalg.norm(eye_line)
    if eye_width < 44:
        raise ValueError("El rostro ocupa muy poco espacio. Recorta la foto alrededor de la cabeza y los hombros.")
    nose_position = np.dot(points[1] - points[33], eye_line) / eye_width ** 2
    if abs(eye_line[1]) > .30 * eye_width or not .32 <= nose_position <= .68:
        raise ValueError("Mira de frente a la cámara y mantén la cabeza recta.")


def polygons(size, points, regions):
    mask = np.zeros(size, dtype=np.uint8)
    for indices in regions:
        cv2.fillConvexPoly(mask, cv2.convexHull(points[list(indices)].astype(np.int32)), 1)
    return mask.astype(bool)


def color(lab, mask):
    samples = lab[mask]
    if len(samples) < 25:
        return None
    samples = samples[::max(1, len(samples) // 3500)]
    low, high = np.percentile(samples[:, 0], [12, 90])
    middle = samples[(samples[:, 0] >= low) & (samples[:, 0] <= high)]
    median = np.median(middle, axis=0).astype(np.float32)
    rgb = cv2.cvtColor(median.reshape(1, 1, 3), cv2.COLOR_LAB2RGB)[0, 0]
    hex_color = "#" + "".join(f"{value:02x}" for value in np.rint(rgb * 255).astype(int))
    return {"hex": hex_color, "lab": [round(float(value), 1) for value in median]}


def iris_mask(size, points):
    rows, columns = np.ogrid[:size[0], :size[1]]
    mask = np.zeros(size, dtype=bool)
    for center, rim, eye in (
        (468, (469, 470, 471, 472), (33, 160, 158, 133, 153, 144)),
        (473, (474, 475, 476, 477), (362, 385, 387, 263, 373, 380)),
    ):
        x, y = points[center]
        radius = np.median(np.linalg.norm(points[list(rim)] - points[center], axis=1))
        squared = (columns - x) ** 2 + (rows - y) ** 2
        mask |= ((squared >= (.46 * radius) ** 2) & (squared <= (.83 * radius) ** 2)
                 & polygons(size, points, (eye,)))
    return mask


class Analyzer:
    def __init__(self):
        vision = mp.tasks.vision
        self.face = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(MODELS / "face_landmarker.task")),
            num_faces=2,
        ))
        self.segmenter = vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(MODELS / "selfie_multiclass.tflite")),
            output_category_mask=True,
            output_confidence_masks=False,
        ))
        self.lock = Lock()

    def analyze(self, data):
        image = read_image(data)
        height, width = image.shape[:2]
        frame = mp.Image(image_format=mp.ImageFormat.SRGB, data=image)
        with self.lock:
            faces = self.face.detect(frame).face_landmarks
            if len(faces) != 1:
                raise ValueError("Sube una selfie frontal en la que aparezca una sola persona.")
            points = np.array([(point.x * width, point.y * height) for point in faces[0]])
            check_pose(points)
            shape, ratios = face_shape(points)
            segment = self.segmenter.segment(frame).category_mask.numpy_view().copy()

        size = (height, width)
        lab = cv2.cvtColor(image.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)
        skin_regions = polygons(size, points, ((50, 101, 205, 187), (280, 330, 425, 411),
                                              (67, 109, 10, 338, 297, 9)))
        skin = color(lab, skin_regions & (segment == 3))
        if skin is None:
            raise ValueError("No se pudo aislar la piel. Prueba con una selfie despejada y luz uniforme.")
        eyebrows = polygons(size, points, ((70, 63, 105, 66, 107, 55, 65, 52, 53, 46),
                                           (336, 296, 334, 293, 300, 276, 283, 282, 295, 285)))
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        brow_pixels = eyebrows & (hsv[:, :, 2] <= np.percentile(hsv[:, :, 2][eyebrows], 45)) if eyebrows.any() else eyebrows
        colors = {"Piel": skin, "Iris": color(lab, iris_mask(size, points)),
                  "Cejas": color(lab, brow_pixels), "Cabello": color(lab, segment == 1)}
        lightness, a, b = skin["lab"]
        grayscale = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        x0, y0 = np.maximum(points[:468].min(axis=0).astype(int), 0)
        x1, y1 = np.minimum(points[:468].max(axis=0).astype(int), (width, height))
        face_patch = cv2.resize(grayscale[y0:y1, x0:x1], (160, 160), interpolation=cv2.INTER_AREA)
        if cv2.Laplacian(face_patch, cv2.CV_64F).var() < 14:
            raise ValueError("La selfie se ve borrosa. Intenta tomarla de nuevo.")
        warmth = b - .8 * a
        undertone = "Cálido" if warmth > 7 else "Frío" if warmth < 3 else "Neutro"
        chroma = float(np.hypot(a, b))
        contrast = max((abs(lightness - feature["lab"][0])
                        for name, feature in colors.items() if name != "Piel" and feature), default=None)
        if contrast is None:
            season = None
        elif undertone == "Cálido" or (undertone == "Neutro" and warmth >= 5):
            season = "Otoño" if contrast > 36 or (chroma > 27 and lightness < 65) else "Primavera"
        else:
            season = "Invierno" if contrast > 37 else "Verano"
        tone = "Claro" if lightness >= 67 else "Medio" if lightness >= 46 else "Profundo"
        return {"forma": shape, "proporciones": ratios, "tono": tone, "subtono": undertone,
                "estacion": season, "colores": colors, "paleta": PALETTES.get(season, ())}
