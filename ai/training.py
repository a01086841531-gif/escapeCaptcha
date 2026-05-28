import os
import json
import numpy as np
import pandas as pd
import joblib

from sklearn.ensemble import IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, classification_report

# ==========================================
# FEATURE EXTRACTION
# ==========================================

def extract_features(filepath):

    with open(filepath,'r',encoding='utf-8') as f:
        data=json.load(f)

    events=data["events"]

    moves=[e for e in events if e["type"]=="move"]
    clicks=[e for e in events if e["type"]=="click"]

    # avg_speed

    distances=[]

    for i in range(1,len(moves)):

        dx=moves[i]["x"]-moves[i-1]["x"]
        dy=moves[i]["y"]-moves[i-1]["y"]

        dist=np.sqrt(dx**2+dy**2)

        distances.append(dist)

    avg_speed=np.mean(distances) if distances else 0

    # direction_changes

    direction_changes=0

    for i in range(2,len(moves)):

        dx1=moves[i-1]["x"]-moves[i-2]["x"]
        dy1=moves[i-1]["y"]-moves[i-2]["y"]

        dx2=moves[i]["x"]-moves[i-1]["x"]
        dy2=moves[i]["y"]-moves[i-1]["y"]

        angle1=np.arctan2(dy1,dx1)
        angle2=np.arctan2(dy2,dx2)

        if abs(angle2-angle1)>0.5:
            direction_changes += 1

    # click variance

    click_times=[e["elapsed_ms"] for e in clicks]

    click_variance=np.var(click_times) if len(click_times)>1 else 0

    # curvature

    curvature=direction_changes/max(len(moves),1)

    return {
        "avg_speed":avg_speed,
        "direction_changes":direction_changes,
        "click_variance":click_variance,
        "curvature":curvature
    }

# ==========================================
# LOAD HUMAN JSON
# ==========================================

root_folder="human/human"

human_features=[]

for root,dirs,files in os.walk(root_folder):

    for file in files:

        if file.endswith(".json"):

            filepath=os.path.join(root,file)

            feature=extract_features(filepath)

            human_features.append(feature)

            print(f"로드 완료 → {filepath}")

df=pd.DataFrame(human_features)

print("\n전체 데이터 개수 :",len(df))

# ==========================================
# TRAIN / TEST SPLIT
# ==========================================

train_df,test_human=train_test_split(
    df,
    test_size=0.1,
    random_state=42
)

print("Train :",len(train_df))
print("Test :",len(test_human))

# ==========================================
# MODEL 생성
# ==========================================

model=IsolationForest(

    n_estimators=100,
    contamination=0.05,
    random_state=42

)

# ==========================================
# MODEL TRAIN
# ==========================================

model.fit(train_df)

print("\n모델 학습 완료")

# ==========================================
# MODEL SAVE
# ==========================================

joblib.dump(
    model,
    "captcha_bot_detector.pkl"
)

print("모델 저장 완료")

# ==========================================
# MODEL LOAD
# ==========================================

loaded_model=joblib.load(
    "captcha_bot_detector.pkl"
)

print("모델 로드 완료")

# ==========================================
# HUMAN TEST
# ==========================================

human_pred=loaded_model.predict(test_human)

print("\n===== HUMAN TEST =====")

human_correct=0

for i,pred in enumerate(human_pred):

    if pred==1:

        print(f"{i+1} → 정상")

        human_correct+=1

    else:

        print(f"{i+1} → 이상탐지")

human_acc=human_correct/len(test_human)

print(f"\nHuman Accuracy : {human_acc:.2%}")

# ==========================================
# BOT TEST DATA
# ==========================================

bot_data=pd.DataFrame([

    {"avg_speed":520,"direction_changes":1,"click_variance":0.001,"curvature":0.01},
    {"avg_speed":650,"direction_changes":0,"click_variance":0.0001,"curvature":0.005},
    {"avg_speed":700,"direction_changes":2,"click_variance":0.001,"curvature":0.01},
    {"avg_speed":580,"direction_changes":1,"click_variance":0.002,"curvature":0.02},
    {"avg_speed":490,"direction_changes":0,"click_variance":0.0005,"curvature":0.01},

    {"avg_speed":620,"direction_changes":1,"click_variance":0.001,"curvature":0.02},
    {"avg_speed":540,"direction_changes":0,"click_variance":0.0003,"curvature":0.01},
    {"avg_speed":600,"direction_changes":2,"click_variance":0.001,"curvature":0.02},
    {"avg_speed":720,"direction_changes":1,"click_variance":0.0001,"curvature":0.005},
    {"avg_speed":560,"direction_changes":0,"click_variance":0.001,"curvature":0.01}

])

# ==========================================
# BOT TEST
# ==========================================

bot_pred=loaded_model.predict(bot_data)

print("\n===== BOT TEST =====")

bot_correct=0

for i,pred in enumerate(bot_pred):

    if pred==-1:

        print(f"BOT {i+1} → 탐지 성공")

        bot_correct+=1

    else:

        print(f"BOT {i+1} → 정상으로 오인")

bot_acc=bot_correct/len(bot_data)

print(f"\nBot Detection Rate : {bot_acc:.2%}")

# ==========================================
# FINAL EVALUATION
# ==========================================

y_true=[1]*len(test_human)+[-1]*len(bot_data)

y_pred=list(human_pred)+list(bot_pred)

print("\n===== CONFUSION MATRIX =====")

print(confusion_matrix(y_true,y_pred))

print("\n===== REPORT =====")

print(classification_report(y_true,y_pred))