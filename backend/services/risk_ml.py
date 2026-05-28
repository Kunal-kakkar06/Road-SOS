import joblib, numpy as np
from pathlib import Path

MODEL_PATH = Path(__file__).parent.parent/"models"/"risk_scorer.pkl"
WX = {"clear":0,"clouds":1,"drizzle":2,"rain":3,"thunderstorm":4,"fog":5,"haze":5,"mist":5}
_model = None

def get_model():
    global _model
    if _model is None: _model = joblib.load(MODEL_PATH)
    return _model

def predict_risk_score(hour_of_day,day_of_week,weather_condition,
                       rain_mm,visibility_km,wind_speed_kmh,
                       blackspot_count,avg_bs_intensity,
                       max_bs_intensity,distance_km) -> dict:
    wx = WX.get(str(weather_condition).lower(),0)
    try:
        score = float(get_model().predict(np.array([[
            hour_of_day,day_of_week,wx,rain_mm,visibility_km,
            wind_speed_kmh,blackspot_count,avg_bs_intensity,
            max_bs_intensity,distance_km,
        ]]))[0])
        score = max(0,min(100,score))
    except:
        score = 20
        if hour_of_day in[0,1,2,3,22,23]: score+=25
        elif hour_of_day in[8,9,17,18,19]: score+=15
        if weather_condition in["rain","thunderstorm"]: score+=20
        score += blackspot_count*5

    if   score>=75: label,color="Critical","#ba1a1a"
    elif score>=50: label,color="High","#fca311"
    elif score>=25: label,color="Moderate","#006687"
    else:           label,color="Low","#27AE60"

    factors=[]
    if hour_of_day in[0,1,2,3,22,23]: factors.append("Late night driving")
    if hour_of_day in[8,9,17,18,19]:  factors.append("Rush hour")
    if weather_condition in["rain","thunderstorm"]: factors.append("Rain — wet roads")
    if weather_condition in["fog","haze","mist"]:   factors.append("Low visibility")
    if blackspot_count>=3: factors.append(f"{blackspot_count} accident zones on route")
    if rain_mm>10: factors.append(f"Heavy rain ({rain_mm:.0f}mm)")

    return {"score":round(score,1),"label":label,"color":color,"factors":factors[:3]}
