from sklearn.ensemble import IsolationForest
import pandas as pd
import numpy as np
import random

# =========================
# 예시 정상 사용자 데이터
# =========================
# 사람이 보이는 일반적인 행동 패턴이라고 가정

df = pd.read_csv('normal_user_data.csv', endcoding='utf-8')
data = df.iloc["event"]
normal_data = data.random%10

# =========================
# Isolation Forest 생성
# =========================

model = IsolationForest(
    n_estimators=100,   # 트리 개수
    contamination=0.1,  # 이상치 비율 예상
    random_state=42
)

# =========================
# 정상 데이터 학습
# =========================

model.fit(normal_data)

print("학습 완료")


# =========================
# 테스트 데이터
# =========================

test_data = pd.DataFrame([

    # 정상 사용자 느낌
    {
        "avg_speed": 138,
        "direction_changes": 41,
        "click_variance": 0.39,
        "curvature": 0.70
    },

    # 봇 느낌
    {
        "avg_speed": 500,
        "direction_changes": 2,
        "click_variance": 0.001,
        "curvature": 0.01
    }

])

# =========================
# 예측
# =========================

predictions = model.predict(test_data)

# 결과:
#  1  = 정상
# -1  = 이상(봇 의심)

print("\n예측 결과\n")

for i, pred in enumerate(predictions):

    if pred == 1:
        print(f"{i+1}번 데이터 → 정상 사용자")
    else:
        print(f"{i+1}번 데이터 → 봇 의심")


# =========================
# anomaly score 확인
# =========================

scores = model.decision_function(test_data)

print("\nAnomaly Score\n")

for i, score in enumerate(scores):
    print(f"{i+1}번 score: {score:.4f}")