# backend/main.py
# Loading .env file for local testing:
from dotenv import load_dotenv
load_dotenv()

# Other Library imports:
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import httpx    # better alternative to requests

# Making Fast API Object/Instance:
app = FastAPI(title="DayMate API")

# Retrieving All API Keys from Env var:---
OPENWEATHER_KEY = os.getenv("OPENWEATHER_KEY")
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")

# API Base Links:---
WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"     #GET https://api.openweathermap.org/data/2.5/weather ?lat={lat}&lon={lon}&appid={API key}
NEWS_URL = "https://newsapi.org/v2/top-headlines"       #GET https://newsapi.org/v2/top-headlines ?country=us&apiKey=API_KEY
GNEWS_URL = "https://gnews.io/api/v4/top-headlines"


# Homepage route (Default):---
# from fastapi.responses import RedirectResponse
# @app.get("/")
# async def docs_redirect():
#     return RedirectResponse(url="/docs")

@app.get("/")
async def root():
    return {
        "message": "Welcome to DayMate API!",
        "swagger_ui": "https://daymate-bitmascot-backend.onrender.com/docs",
        "docs_url": "/docs",
        "status": "running"
    }


# My Main APIs:---
# @app.get("/health")
# async def health():
#     return {"status": "ok"}


@app.get("/weather")
async def get_weather(lat: float, lon: float):
    # GET, 'http://127.0.0.1:8000/weather?lat=23.7104&lon=90.40744' #my_backend_api
    if not OPENWEATHER_KEY:
        raise HTTPException(status_code=500, detail="OPENWEATHER_KEY not configured")
    params = {"lat": lat, "lon": lon, "appid": OPENWEATHER_KEY, "units": "metric"}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(WEATHER_URL, params=params)    #"https://api.openweathermap.org/data/2.5/weather"
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail="Weather API error")
    return r.json()


@app.get("/news")
async def get_news(country: str = "bd", q: str | None = None):
    if not GNEWS_API_KEY:
        # It's better practice to use the actual variable name in the error message
        raise HTTPException(status_code=500, detail="GNEWS_API_KEY not configured")

    params = {
        "apikey": GNEWS_API_KEY,      # GNews API KEY
        "category": "general",       # category
        "lang": "en",                # language
        "max": 5,                    # max results
        "country": country           # Dynamic country (defaults to 'bd')
    }

    if q:
        params["q"] = q

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(GNEWS_URL, params=params)

    if r.status_code != 200:
        # Check the response text for specific GNews error messages
        raise HTTPException(status_code=502, detail=f"GNews API error: {r.text}")

    # news = r.json()
    # print([a.get("title") for a in news.get("articles", [])[:5]])
    return r.json()

# LLM Integration Function:
from langchain_openai import ChatOpenAI
def load_llm(model_name, base_url, api_key_env):
    return ChatOpenAI(
        model=model_name,
        openai_api_base = base_url,
        openai_api_key = os.getenv(api_key_env),
        timeout=60,
        max_tokens=350,
        # temperature=0.2,
        # top_p=0.95,
        max_retries=2
    )


# LLM Final Reasoning:---
class PlanRequest(BaseModel): # Post body
    # BD lat == 23.7104
    # BD lon == 90.40744

    lat: float
    lon: float
    location_name: str | None = None

@app.post("/plan")
async def generate_plan(req: PlanRequest):
    # fetching weather (my backend api call)
    weather = await get_weather(req.lat, req.lon)

    # fetching news [Default Country: BD] (my backend api call)
    news = await get_news(country="bd")
    headlines = [a.get("title") for a in news.get("articles", [])[:5]]  # Safe extraction of the dict.get() value with default value []

    # Prompt for the RAG system:
    prompt = (
        f"User is at {req.location_name or f'{req.lat},{req.lon}'}. "
        f"Weather: {weather.get('weather')[0].get('description')}, temp {weather.get('main').get('temp')}°C. "
        f"Top headlines: {headlines}. "
        "Generate a concise daily plan (3-6 items) and practical recommendations (carry items, suggest reschedule if needed)."
    )
    # print("Prompt is ===>\n",prompt)

    # Calling AI Model:--
    if GROQ_API_KEY:
        print("\nLLM key is Found. Prompting with LLM...\n")
        llm = load_llm(
            model_name="llama-3.3-70b-versatile",
            base_url="https://api.groq.com/openai/v1",
            api_key_env="GROQ_API_KEY"
        )
        response = llm.invoke([
            {"role": "system",
             "content": "You are DayMate, a helpful daily planner."},
            {"role": "user",
             "content": prompt}
        ])
        text = response.content
        return {"planning": text, "prompt": prompt}

    else:   # //fallback logic: manual//
        print("LLM key not Found. manual reasoning...")
        plan = []
        desc = weather.get('weather')[0].get('main', '')
        if 'rain' in desc.lower():
            plan.append("Carry an umbrella / waterproof jacket.")
            plan.append("Avoid scheduling long outdoor meetings; consider indoor alternatives.")
        elif 'clear' in desc.lower() or 'sun' in desc.lower():
            plan.append("Good day for outdoor activities: short walk or exercise.")
        else:
            plan.append("Check local conditions before leaving; bring a light jacket.")
        # Add a headline-driven advisory if serious news present (basic heuristic: look for 'alert', 'storm', 'strike')
        critical = [h for h in headlines if
                    h and any(k in h.lower() for k in ['alert', 'storm', 'strike', 'emergency', 'flood'])]
        if critical:
            plan.append(f"Important news: {critical[0]} — consider rescheduling sensitive plans.")
        plan.append("Suggested schedule: morning focus work, afternoon errands with buffer time.")
        return {"planning": '\n'.join(plan), "prompt": prompt}

if __name__ == "__main__":
    # Test Payload:
    payload = PlanRequest(
        location_name="bd",
        lat=23.7104,
        lon=90.40744
    )

    # Async runner to call the async function
    import asyncio
    result = asyncio.run(generate_plan(payload))
    print("Prompt is ===>\n",result.get("prompt","No Prompt Pushed!"))
    print("\nLLM Result ===>\n",result.get("planning","No Result from LLM!"))



# My Notes:----
# uvicorn command for Render
    # Start command: uvicorn main:app --host 0.0.0.0 --port $PORT

# During Dev:--
    # uvicorn filename:fastapiObj --reload
    # uvicorn main:app --reload

    # pyenv shell 3.11.14
    # uvicorn main:app --reload --port $PORT