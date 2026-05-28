import os
import json
import numpy as np
import pandas as pd
import joblib

from sklearn.ensemble import IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, classification_report
from sklearn.preprocessing import StandardScaler

# ==========================================
# FEATURE EXTRACTION
# ==========================================

def extract_features(filepath):

    with open(filepath,'r',encoding='utf-8') as f:
        data=json.load(f)

    events=data["events"]

    moves=[e for e in events if e["type"]=="move"]
    clicks=[e for e in events if e["type"]=="click"]

    # --------------------
    # distance features
    # --------------------

    distances=[]

    for i in range(1,len(moves)):

        dx=moves[i]["x"]-moves[i-1]["x"]
        dy=moves[i]["y"]-moves[i-1]["y"]

        dist=np.sqrt(dx**2+dy**2)

        distances.append(dist)

    avg_speed=np.mean(distances) if distances else 0
    max_speed=np.max(distances) if distances else 0
    speed_std=np.std(distances) if distances else 0

    # --------------------
    # direction features
    # --------------------

    direction_changes=0
    angles=[]

    for i in range(2,len(moves)):

        dx1=moves[i-1]["x"]-moves[i-2]["x"]
        dy1=moves[i-1]["y"]-moves[i-2]["y"]

        dx2=moves[i]["x"]-moves[i-1]["x"]
        dy2=moves[i]["y"]-moves[i-1]["y"]

        angle1=np.arctan2(dy1,dx1)
        angle2=np.arctan2(dy2,dx2)

        diff=abs(angle2-angle1)

        angles.append(diff)

        if diff>0.5:
            direction_changes += 1

    curvature=np.mean(angles) if angles else 0

    # --------------------
    # click timing
    # --------------------

    click_times=[e["elapsed_ms"] for e in clicks]

    click_variance=np.var(click_times) if len(click_times)>1 else 0

    # --------------------
    # pause timing
    # --------------------

    elapsed=[e["elapsed_ms"] for e in events]

    gaps=[]

    for i in range(1,len(elapsed)):

        gaps.append(
            elapsed[i]-elapsed[i-1]
        )

    avg_pause=np.mean(gaps) if gaps else 0
    pause_std=np.std(gaps) if gaps else 0

    return {

        "avg_speed":avg_speed,
        "max_speed":max_speed,
        "speed_std":speed_std,

        "direction_changes":direction_changes,
        "curvature":curvature,

        "click_variance":click_variance,

        "avg_pause":avg_pause,
        "pause_std":pause_std,

        "move_count":len(moves),
        "click_count":len(clicks)
    }

# ==========================================
# LOAD HUMAN DATA
# ==========================================

human_folder=r"C:\Users\kimda\Desktop\dasol\cc\captcha\ai\human\human"

human_features=[]

for root,dirs,files in os.walk(human_folder):

    for file in files:

        if file.endswith(".json"):

            filepath=os.path.join(root,file)

            feature=extract_features(filepath)

            human_features.append(feature)

            print("HUMAN LOAD →",filepath)

human_df=pd.DataFrame(human_features)

print("\nHuman samples :",len(human_df))

# ==========================================
# TRAIN / TEST SPLIT
# ==========================================

train_df,test_human=train_test_split(

    human_df,

    test_size=0.1,

    random_state=42
)

print("Train :",len(train_df))
print("Human Test :",len(test_human))

# ==========================================
# LOAD BOT DATA
# ==========================================

bot_folder=r"C:\Users\kimda\Desktop\dasol\cc\captcha\dataset\bot"

bot_features=[]

for root,dirs,files in os.walk(bot_folder):

    for file in files:

        if file.endswith(".json"):

            filepath=os.path.join(root,file)

            feature=extract_features(filepath)

            bot_features.append(feature)

            print("BOT LOAD →",filepath)

bot_df=pd.DataFrame(bot_features)

print("Bot samples :",len(bot_df))

# ==========================================
# STANDARD SCALER
# ==========================================

scaler=StandardScaler()

train_scaled=pd.DataFrame(

    scaler.fit_transform(train_df),

    columns=train_df.columns
)

test_scaled=pd.DataFrame(

    scaler.transform(test_human),

    columns=test_human.columns
)

bot_scaled=pd.DataFrame(

    scaler.transform(bot_df),

    columns=bot_df.columns
)

# ==========================================
# MODEL CREATE
# ==========================================

model=IsolationForest(

    n_estimators=200,

    contamination=0.10,

    random_state=42
)

# ==========================================
# TRAIN
# ==========================================

model.fit(train_scaled)

print("\nMODEL TRAIN COMPLETE")

# ==========================================
# SAVE
# ==========================================

joblib.dump(
    {
        "model": model,
        "scaler": scaler,
    },
    "captcha_bot_detector.pkl"
)

print("MODEL SAVE COMPLETE")

# ==========================================
# LOAD MODEL
# ==========================================

loaded = joblib.load(
    "captcha_bot_detector.pkl"
)

if isinstance(loaded, dict) and "model" in loaded and "scaler" in loaded:
    loaded_model = loaded["model"]
    loaded_scaler = loaded["scaler"]
else:
    loaded_model = loaded
    loaded_scaler = None

print("MODEL LOAD COMPLETE")

# ==========================================
# SCORE CALCULATION
# ==========================================

human_scores=loaded_model.decision_function(

    test_scaled
)

bot_scores=loaded_model.decision_function(

    bot_scaled
)

# ==========================================
# CUSTOM THRESHOLD
# ==========================================

THRESHOLD = -0.05

def custom_predict(scores):

    return np.array([

        -1 if s < THRESHOLD else 1

        for s in scores
    ])

human_pred=custom_predict(

    human_scores
)

bot_pred=custom_predict(

    bot_scores
)

# ==========================================
# HUMAN TEST
# ==========================================

print("\n===== HUMAN TEST =====")

human_correct=0

for i,(pred,score) in enumerate(

    zip(human_pred,human_scores)

):

    if pred==1:

        print(

            f"{i+1} → 정상 "

            f"(score={score:.4f})"
        )

        human_correct+=1

    else:

        print(

            f"{i+1} → 이상탐지 "

            f"(score={score:.4f})"
        )

human_acc=human_correct/len(test_human)

print(

    f"\nHuman Accuracy : "

    f"{human_acc:.2%}"
)

# ==========================================
# BOT TEST
# ==========================================

print("\n===== BOT TEST =====")

bot_correct=0

for i,(pred,score) in enumerate(

    zip(bot_pred,bot_scores)

):

    if pred==-1:

        print(

            f"BOT {i+1} → 탐지 성공 "

            f"(score={score:.4f})"
        )

        bot_correct+=1

    else:

        print(

            f"BOT {i+1} → 정상으로 오인 "

            f"(score={score:.4f})"
        )

bot_acc=bot_correct/len(bot_df)

print(

    f"\nBot Detection Rate : "

    f"{bot_acc:.2%}"
)

# ==========================================
# FINAL EVALUATION
# ==========================================

y_true=[1]*len(test_human)+[-1]*len(bot_df)

y_pred=list(human_pred)+list(bot_pred)

print("\n===== CONFUSION MATRIX =====")

print(

    confusion_matrix(

        y_true,

        y_pred
    )
)

print("\n===== REPORT =====")

print(

    classification_report(

        y_true,

        y_pred
    )
)