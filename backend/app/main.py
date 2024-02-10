"""
from fastapi import FastAPI
import os
import requests

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


@app.get("/route")
def route(currentLat: str, currentLng: str, radius: str):
    origin = f"{currentLat},{currentLng}"
    url = "https://maps.googleapis.com/maps/api/directions/json?"

    
    payload = {"origin": origin, "destination": "横浜国立大学", "key": os.getenv("GOOGLE_MAP_API_KEY")}
    #print(payload)
    r = requests.get(url, params=payload)

    if r.status_code == 200:
        return r.json()
    else:
        return "500: backend error"
>>>>>>> Stashed changes
