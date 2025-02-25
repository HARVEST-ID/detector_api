import json
import cv2
import numpy as np
from ultralytics import YOLO
from collections import defaultdict

class Detector:
    def __init__(self, main_model, model_dir):
        self.main_model = YOLO(main_model)  
        self.model_dir = model_dir  
        self.models_cache = {}  

    def load_json(self, json_path):
        """Lê o JSON e retorna um dicionário com o mapeamento de classes para modelos."""
        with open(json_path, "r") as f:
            return json.load(f)

    def predict_image_yolo(self, model, image_data, iterations=5):
        """Executa predição com um modelo YOLO e retorna a classe detectada mais confiável."""
        if isinstance(image_data, str):  
            with open(image_data, "rb") as f:
                image_data = f.read()

        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise ValueError("Falha ao carregar a imagem.")

        class_count = defaultdict(lambda: {"count": 0, "confidence_sum": 0})

        for _ in range(iterations):
            results = model(img)  # Faz a predição
            predictions = results[0].boxes.data

            for pred in predictions:
                _, _, _, _, conf, class_idx = pred.tolist()
                predicted_class = model.names[int(class_idx)]

                class_count[predicted_class]["count"] += 1
                class_count[predicted_class]["confidence_sum"] += conf

        if not class_count:
            return {"class": "Nenhuma detecção", "average_confidence": 0, "occurrences": 0}

        final_class = max(
            class_count.items(),
            key=lambda item: (item[1]["count"], item[1]["confidence_sum"] / item[1]["count"]),
        )

        predicted_class, metrics = final_class
        average_confidence = (metrics["confidence_sum"] / metrics["count"]) * 100

        return {
            "class": predicted_class,
            "average_confidence": round(average_confidence, 2),
            "occurrences": metrics["count"],
        }

    def detect_with_mapping(self, json_path, image_data):
        """Executa a predição usando o modelo principal e depois verifica se há um modelo específico para a classe detectada."""
        # Carrega o JSON com o mapeamento de classes -> modelos
        class_to_model = self.load_json(json_path)

        # Primeira predição com o modelo principal
        first_prediction = self.predict_image_yolo(self.main_model, image_data)

        detected_class = first_prediction["class"]
        print(f"Primeira predição: {detected_class}")

        # Verifica se há um modelo associado a essa classe no JSON
        if detected_class in class_to_model:
            model_path = f"{self.model_dir}/{class_to_model[detected_class]}"
            
            # Carrega o modelo se ainda não estiver no cache
            if model_path not in self.models_cache:
                self.models_cache[model_path] = YOLO(model_path)

            # Segunda predição com o modelo específico
            second_prediction = self.predict_image_yolo(self.models_cache[model_path], image_data)
            print(f"Segunda predição com {model_path}: {second_prediction}")

            return {
                "main_prediction": first_prediction,
                "refined_prediction": second_prediction
            }

        return {"main_prediction": first_prediction, "refined_prediction": None}
