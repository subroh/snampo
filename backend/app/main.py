"""
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}
"""

from fastapi import FastAPI
from typing import Optional
import requests

app = FastAPI()

@app.get("/current-location/")
def get_current_location(api_key: str):
    # Google Maps Geolocation API を使用して現在の位置情報を取得する
    url = f"https://www.googleapis.com/geolocation/v1/geolocate?key=AIzaSyCSqiX8UM1Gmhyk1stmq4mQOl2VkzNbovc"
    response = requests.post(url)
    data = response.json()

    # 取得した位置情報を返す
    return data