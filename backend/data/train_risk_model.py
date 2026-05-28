import numpy as np, pandas as pd, joblib, os
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error

WX = {"clear":0,"clouds":1,"drizzle":2,"rain":3,"thunderstorm":4,"fog":5,"haze":5}

def gen(n=6000):
    np.random.seed(42)
    rows=[]
    for _ in range(n):
        h=np.random.randint(0,24); d=np.random.randint(0,7)
        w=np.random.choice(list(WX.keys()),p=[0.4,0.2,0.1,0.15,0.05,0.05,0.05])
        rain=np.random.uniform(0,50) if w in["rain","thunderstorm"] else 0
        vis=np.random.uniform(0.5,10) if w in["fog","haze"] else np.random.uniform(5,10)
        wind=np.random.uniform(0,80)
        bs=np.random.randint(0,8)
        ai=np.random.uniform(0,1) if bs>0 else 0
        mi=np.random.uniform(ai,1) if bs>0 else 0
        dist=np.random.uniform(0.5,50)
        score=20
        if h in[0,1,2,3,22,23]: score+=25
        elif h in[8,9,17,18,19]: score+=15
        elif h in[7,10,16,20]:   score+=8
        if d in[5,6]: score-=5
        score+=WX.get(w,0)*8+min(rain*0.4,20)+max(0,(5-vis)*4)+min(wind*0.15,10)
        score+=bs*5+ai*15+mi*10+min(dist*0.3,15)
        score=max(0,min(100,score+np.random.normal(0,5)))
        rows.append({"hour_of_day":h,"day_of_week":d,"weather_code":WX.get(w,0),
                     "rain_mm":rain,"visibility_km":vis,"wind_speed_kmh":wind,
                     "blackspot_count":bs,"avg_bs_intensity":ai,
                     "max_bs_intensity":mi,"distance_km":dist,"risk_score":score})
    return pd.DataFrame(rows)

FEATS=["hour_of_day","day_of_week","weather_code","rain_mm","visibility_km",
       "wind_speed_kmh","blackspot_count","avg_bs_intensity","max_bs_intensity","distance_km"]

def train():
    df=gen(); X,y=df[FEATS],df["risk_score"]
    Xtr,Xte,ytr,yte=train_test_split(X,y,test_size=0.2,random_state=42)
    m=XGBRegressor(n_estimators=200,max_depth=5,learning_rate=0.1,random_state=42)
    m.fit(Xtr,ytr,eval_set=[(Xte,yte)],verbose=False)
    print(f"MAE: {mean_absolute_error(yte,m.predict(Xte)):.2f}")
    os.makedirs("models",exist_ok=True)
    joblib.dump(m,"models/risk_scorer.pkl")
    print("Saved → backend/models/risk_scorer.pkl")

if __name__=="__main__": train()
