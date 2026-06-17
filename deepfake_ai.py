import os
from typing import Dict, Optional, Tuple

import numpy as np

# IMPORTANT: DeepFace sets TF_USE_LEGACY_KERAS=1 which forces tf.keras to
# redirect to tf_keras (Keras 2).  The saved model was trained on Colab with
# Keras 3, so we MUST use the standalone `keras` package (Keras 3) directly.
# `import keras` is NOT affected by the TF_USE_LEGACY_KERAS env var.
import keras


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MODEL_PATH = os.path.join(BASE_DIR, "models", "deepfake_detector.keras")
DEFAULT_IMAGE_SIZE = (224, 224)


def build_training_model(input_shape: Tuple[int, int, int] = (224, 224, 3)) -> keras.Model:
    """Simple CNN used by train_deepfake_model.py (not the saved model's arch)."""
    inputs = keras.Input(shape=input_shape)
    x = keras.layers.Rescaling(1.0 / 255.0)(inputs)
    x = keras.layers.Conv2D(32, 3, activation="relu", padding="same")(x)
    x = keras.layers.MaxPooling2D()(x)
    x = keras.layers.Conv2D(64, 3, activation="relu", padding="same")(x)
    x = keras.layers.MaxPooling2D()(x)
    x = keras.layers.Conv2D(128, 3, activation="relu", padding="same")(x)
    x = keras.layers.MaxPooling2D()(x)
    x = keras.layers.Conv2D(128, 3, activation="relu", padding="same")(x)
    x = keras.layers.GlobalAveragePooling2D()(x)
    x = keras.layers.Dense(128, activation="relu")(x)
    x = keras.layers.Dropout(0.35)(x)
    outputs = keras.layers.Dense(1, activation="sigmoid")(x)

    model = keras.Model(inputs=inputs, outputs=outputs, name="deepfake_detector")
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=1e-3),
        loss="binary_crossentropy",
        metrics=["accuracy", keras.metrics.AUC(name="auc")],
    )
    return model


class DeepfakeDetector:
    def __init__(self, model_path: str = DEFAULT_MODEL_PATH, image_size: Tuple[int, int] = DEFAULT_IMAGE_SIZE):
        self.model_path = model_path
        self.image_size = image_size
        self._model: Optional[keras.Model] = None
        self._load_error: Optional[str] = None

    def _load_model(self) -> Optional[keras.Model]:
        if self._model is not None:
            return self._model

        if not os.path.exists(self.model_path):
            self._load_error = f"Model file not found at {self.model_path}"
            return None

        try:
            self._model = keras.models.load_model(self.model_path, compile=False)
            return self._model
        except Exception as exc:
            self._load_error = f"Failed to load model: {exc}"
            self._model = None
            return None

    @property
    def available(self) -> bool:
        return self._load_model() is not None

    @property
    def status(self) -> str:
        if self.available:
            return f"Loaded model from {self.model_path}"
        return self._load_error or "Model unavailable"

    def preprocess(self, image_path: str) -> np.ndarray:
        image = keras.utils.load_img(image_path, target_size=self.image_size)
        array = keras.utils.img_to_array(image).astype("float32")
        return np.expand_dims(array, axis=0)

    def predict(self, image_path: str) -> Dict[str, object]:
        model = self._load_model()
        if model is None:
            return {
                "available": False,
                "label": "unknown",
                "confidence": 0.0,
                "reason": self._load_error or "Model unavailable",
            }

        input_batch = self.preprocess(image_path)
        raw_prediction = model.predict(input_batch, verbose=0)
        probability = float(np.squeeze(raw_prediction))
        probability = max(0.0, min(1.0, probability))
        label = "deepfake" if probability >= 0.5 else "authentic"

        return {
            "available": True,
            "label": label,
            "confidence": probability,
            "reason": "Inference completed successfully",
        }
