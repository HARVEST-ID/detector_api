from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from detector import Detector
from fastapi.security import OAuth2PasswordBearer
import jwt
import datetime
from pydantic import BaseModel
from firebase_service import Firebase
import os
from dotenv import load_dotenv


load_dotenv("env.env")

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
FIREBASE = os.getenv("FIREBASE")
MAIN_MODEL = os.getenv("MAIN_MODEL")
MODEL_DIR = os.getenv("MODEL_DIR")
JSON_PATH = os.getenv("JSON_PATH")

detector = Detector(MAIN_MODEL, MODEL_DIR)
firabase = Firebase(FIREBASE)

app = FastAPI(title="API de Detecção com YOLO - Blob")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

class TokenRequest(BaseModel):
    token_cusum: str


def gerar_jwt(token_id: str) -> str:
    """Gera o JWT usando a chave secreta fixa."""
    if firabase.is_token_valid(token_id):
        payload = {
            "sub": token_id,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)  
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    else:
        raise HTTPException(status_code=401, detail="Token Firebase inválido")

def verificar_jwt(token_jwt: str) -> dict:
    """Verifica e decodifica o JWT usando a chave secreta fixa."""
    try:
        decoded_token = jwt.decode(token_jwt, SECRET_KEY, algorithms=[ALGORITHM])
        return decoded_token
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token JWT expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token JWT inválido")

@app.post("/predict", summary="Faz a predição de uma imagem recebida como Blob")
async def predict_image(request: Request, token_jwt: str = Depends(oauth2_scheme)):
    try:
        decoded_token = verificar_jwt(token_jwt)
        image_bytes = await request.body()
        if not image_bytes:
            raise HTTPException(status_code=400, detail="Nenhuma imagem recebida.")
        
        prediction = detector.detect_with_mapping(JSON_PATH, image_bytes)
        
        content_type = "image/jpeg"
        image_url = firabase.save_image_to_storage(image_bytes, content_type)
        
        if not image_url.startswith("gs://"):
            raise HTTPException(status_code=500, detail="Erro ao salvar imagem no Firebase.")
        
        user_id = firabase.get_uid_from_token(token_jwt)
        if not user_id:
            raise HTTPException(status_code=401, detail="Token inválido ou usuário não encontrado.")
        
        firabase.save_image_reference_to_firestore(user_id, item_id=1, image_url=image_url, prediction_result=prediction)
        
        return JSONResponse(content={"prediction": prediction, "image_url": image_url})
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar a imagem: {str(e)}")


@app.post("/token")
async def criar_token(token_cusum: str):
    """Rota que recebe o token do Firebase e retorna o JWT."""
    return {"access_token": gerar_jwt(token_cusum), "token_type": "bearer"}

@app.get("/protegida")
async def acessar_protegido(token_jwt: str = Depends(oauth2_scheme)):
    """Rota que exige um token JWT válido para acessar dados protegidos."""
    decoded_token = verificar_jwt(token_jwt)
    return {"message": "Acesso autorizado", "user_info": decoded_token}

@app.post("/firebase_login")
async def firebase_login(token_firebase: str):
    """Valida o token do Firebase e retorna uma mensagem de autenticação."""
    if firabase.is_token_valid(token_firebase):
        return {"message": "Usuário autenticado"}
    else:
        raise HTTPException(status_code=401, detail="Token Firebase inválido")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
