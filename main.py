import fastapi
import uvicorn
import os
import requests
import ipaddress
import logging
import asyncio
from fastapi.responses import HTMLResponse, Response, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# --- Настройка логгера ---
# Логгер уже настроен в bot.py, здесь мы просто получаем его экземпляр
activity_logger = logging.getLogger("activity_logger")

# --- Инициализация FastAPI ---
# Переименовываем в 'app' для соответствия стандартам и импорту в bot.py
app = fastapi.FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

NO_CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0"
}

# --- Модель данных Pydantic (без изменений) ---
class TestResult(BaseModel):
    ping: str
    download: str
    upload: str
    clientInfo: str
    fullLog: str

# --- Основные эндпоинты (без изменений) ---
@app.get("/", response_class=HTMLResponse)
async def get_root(request: fastapi.Request):
    return templates.TemplateResponse("index.html", {"request": request})

def get_user_ip(request: fastapi.Request) -> str:
    """Надежно определяет IP-адрес пользователя, проверяя заголовок x-forwarded-for."""
    forwarded_for = request.headers.get("x-forwarded-for")
    user_ip = ""
    if forwarded_for:
        ips = [ip.strip() for ip in forwarded_for.split(',')]
        for ip_str in ips:
            try:
                ip_obj = ipaddress.ip_address(ip_str)
                if not ip_obj.is_private and not ip_obj.is_loopback:
                    user_ip = ip_str
                    break
            except ValueError:
                continue
    
    if not user_ip:
        user_ip = request.client.host
    
    return user_ip

@app.get("/get_geo_info")
async def get_geo_info(request: fastapi.Request):
    user_ip = get_user_ip(request)
    
    user_geo = {"ip": user_ip, "country": "Недоступно", "city": ""}
    server_geo = {"ip": "Недоступно", "country": "Недоступно", "city": ""}

    try:
        res = requests.get(f"http://ip-api.com/json/{user_ip}")
        res.raise_for_status()
        data = res.json()
        if data.get("status") == "success":
            user_geo["country"] = data.get("country", "Неизвестно")
            user_geo["city"] = data.get("city", "Неизвестно")
            activity_logger.info(f"VISIT from IP: {user_ip}, Location: {user_geo.get('city')}, {user_geo.get('country')}")
    except requests.RequestException as e:
        activity_logger.error(f"VISIT from IP: {user_ip}, Geo lookup failed: {e}")

    try:
        res = requests.get("http://ip-api.com/json/")
        res.raise_for_status()
        data = res.json()
        if data.get("status") == "success":
            server_geo["ip"] = data.get("query", "Неизвестно")
            server_geo["country"] = data.get("country", "Неизвестно")
            server_geo["city"] = data.get("city", "Неизвестно")
    except requests.RequestException:
        pass

    return JSONResponse(content={"user": user_geo, "server": server_geo})

# Этот эндпоинт больше не нужен, так как результаты отправляются через Mini App API
# и логируются напрямую в боте.
# @app.post("/log_results")
# async def log_results(results: TestResult, request: fastapi.Request):
#     ...

@app.get("/ping")
async def get_ping():
    return Response(content="pong", headers=NO_CACHE_HEADERS)

async def data_generator(total_size: int):
    """Асинхронный генератор, который создает случайные байты "на лету"."""
    chunk_size = 65536
    bytes_sent = 0
    while bytes_sent < total_size:
        data_chunk = os.urandom(min(chunk_size, total_size - bytes_sent))
        yield data_chunk
        bytes_sent += len(data_chunk)
        await asyncio.sleep(0.001)

@app.get("/download")
async def get_download_chunk(size: int = 1024 * 1024):
    """Отдает поток случайных данных заданного размера без хранения их в памяти."""
    max_size = 16 * 1024 * 1024 
    size_to_generate = min(size, max_size)
    
    return StreamingResponse(
        data_generator(size_to_generate), 
        media_type="application/octet-stream", 
        headers=NO_CACHE_HEADERS
    )

@app.post("/upload")
async def handle_upload(request: fastapi.Request):
    await request.body()
    return Response(status_code=200, content="OK", headers=NO_CACHE_HEADERS)

# Блок запуска удален, так как запуск теперь контролируется из bot.py
# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8000)
