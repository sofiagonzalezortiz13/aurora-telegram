from pathlib import Path
from urllib.request import urlretrieve

root = Path(__file__).resolve().parent / "models"
root.mkdir(exist_ok=True)
base = "https://storage.googleapis.com/mediapipe-models/"
for name, url in {
    "face_landmarker.task": "face_landmarker/face_landmarker/float16/1/face_landmarker.task",
    "selfie_multiclass.tflite": "image_segmenter/selfie_multiclass_256x256/float32/1/selfie_multiclass_256x256.tflite",
}.items():
    temporary = root / (name + ".download")
    urlretrieve(base + url, temporary)
    temporary.replace(root / name)
