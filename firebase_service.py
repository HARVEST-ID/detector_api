import os
import uuid
import tempfile
from firebase_admin import credentials, firestore, initialize_app, storage,auth
from datetime import datetime
from firebase_admin.exceptions import FirebaseError

class Firebase:
    def __init__(self, cred_path: str):
        try:
            # Inicializa as credenciais e a conexão com o Firestore e Firebase Storage
            self.cred = credentials.Certificate(cred_path)
            initialize_app(self.cred, {
                'storageBucket': 'harvest-id.appspot.com'  
            })
            self.db = firestore.client()
            self.bucket = storage.bucket()
        except Exception as e:
            print(f"Erro ao inicializar o Firebase: {e}")
            raise
    def is_token_valid(self, token_id):
        try:
            decoded_token = auth.verify_id_token(token_id)
            print(f"Token decodificado: {decoded_token}")
            return True
        except FirebaseError as e:  
            print(f"Erro ao verificar o token Firebase: {str(e)}")
            return False
    def get_uid_from_token(self, token_id):
        try:
            decoded_token = auth.verify_id_token(token_id)
            return decoded_token["uid"]
        except FirebaseError as e:
            print(f"Erro ao obter UID do token Firebase: {str(e)}")
            return None


    def save_image_to_storage(self, image_data: bytes, content_type: str):
        try:
            
            current_datetime = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            file_name = f"images/inspection_{current_datetime}_{uuid.uuid4().hex}.jpg"  

            
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(image_data)  
                temp_path = temp_file.name  

            
            if not os.path.exists(temp_path):
                raise Exception("Erro: Arquivo temporário não foi criado corretamente.")

            
            print(f"Iniciando upload para o Firebase Storage: {temp_path}")
            blob = self.bucket.blob(file_name)
            blob.upload_from_filename(temp_path, content_type=content_type)
            blob.make_public() 
        

            
            os.remove(temp_path)

            
            return f"gs://{blob.bucket.name}/{file_name}"

        except Exception as e:
            print(f"Erro ao salvar imagem no Firebase Storage: {e}")
            return {"error": str(e)}

    def save_image_reference_to_firestore(self, user_id: str, item_id: int, image_url: str, prediction_result: str):
        try:
            
            doc_ref = self.db.collection('User').document(user_id).collection('inspection').add({
                "image_url": image_url,
                "prediction": prediction_result,
                "timestamp": firestore.SERVER_TIMESTAMP
            })
            
            
            
            return 
        except Exception as e:
            print(f"Erro ao salvar referência no Firestore: {e}")
            return {"error": str(e)}

