"""
train_model.py — bot/human 행동 분류 모델 학습
위치: model/train_model.py

실행:  python train_model.py
입력:  model/features.csv   (feature_extraction.py 출력)
출력:  model/classifier.pkl
"""

import pickle
import sys
import logging
from pathlib import Path
from typing import Tuple, Optional

# ── Import 안정화 ────────────────────────────────────────
try:
    import pandas as pd
except ImportError:
    print("ERROR: pandas 패키지가 설치되지 않았습니다.")
    print("       설치 명령: pip install pandas")
    sys.exit(1)

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, confusion_matrix
except ImportError:
    print("ERROR: scikit-learn 패키지가 설치되지 않았습니다.")
    print("       설치 명령: pip install scikit-learn")
    sys.exit(1)

# ── 로깅 설정 ────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s: %(message)s'
)
logger = logging.getLogger(__name__)

# ── 경로 ──────────────────────────────────────────────────
MODEL_DIR   = Path(__file__).parent
FEATURES_CSV = MODEL_DIR / "features.csv"
MODEL_PKL    = MODEL_DIR / "classifier.pkl"

FEATURES = [
    "avg_speed",
    "total_dist",
    "direction_changes",
    "click_gap_mean",
    "click_gap_std",
    "duration_sec",
]

logger.info(f"모델 디렉토리: {MODEL_DIR}")
logger.info(f"입력 파일: {FEATURES_CSV}")
logger.info(f"출력 파일: {MODEL_PKL}")

# ── 경로 검증 ────────────────────────────────────────────
if not FEATURES_CSV.exists():
    logger.error(f"features.csv 파일이 없습니다: {FEATURES_CSV}")
    logger.error("feature_extraction.py를 먼저 실행하세요.")
    sys.exit(1)

if not FEATURES_CSV.is_file():
    logger.error(f"features.csv가 파일이 아닙니다: {FEATURES_CSV}")
    sys.exit(1)

# ── 1. 데이터 로드 ────────────────────────────────────────
logger.info("데이터 로드 중...")

try:
    df = pd.read_csv(FEATURES_CSV)
except pd.errors.ParserError as e:
    logger.error(f"CSV 파일 파싱 오류: {e}")
    sys.exit(1)
except Exception as e:
    logger.error(f"CSV 파일 로드 오류: {e}")
    sys.exit(1)

# ── 데이터 검증 ─────────────────────────────────────────
if df.empty:
    logger.error("features.csv가 비어있습니다.")
    sys.exit(1)

logger.info(f"로드된 행 수: {len(df)}")

# label 칼럼 검증
if "label" not in df.columns:
    logger.error(f"필수 칼럼 'label'이 없습니다. 있는 칼럼: {list(df.columns)}")
    sys.exit(1)

# FEATURES 칼럼 검증
missing_features = [f for f in FEATURES if f not in df.columns]
if missing_features:
    logger.error(f"필수 칼럼이 없습니다: {missing_features}")
    logger.error(f"CSV에 있는 칼럼: {list(df.columns)}")
    sys.exit(1)

# 데이터 타입 검증 및 결측치 확인
try:
    X = df[FEATURES].copy()
    
    # NaN 값 확인
    if X.isnull().any().any():
        null_counts = X.isnull().sum()
        logger.warning(f"결측치 발견: {null_counts[null_counts > 0].to_dict()}")
        logger.info("결측치 행 제거 중...")
        X = X.dropna()
        df = df.loc[X.index]
    
    # 데이터 타입 변환
    X = X.astype(float)
    
except (KeyError, ValueError, TypeError) as e:
    logger.error(f"데이터 처리 오류: {e}")
    sys.exit(1)

try:
    y = (df["label"] == "human").astype(int)   # bot=0, human=1
except Exception as e:
    logger.error(f"라벨 변환 오류: {e}")
    sys.exit(1)

# 데이터 분포 확인
bot_count = (y == 0).sum()
human_count = (y == 1).sum()
logger.info(f"데이터: {len(df)}행 (bot {bot_count}개 / human {human_count}개)")

# 최소 데이터 검증
if len(df) < 4:
    logger.error(f"데이터가 너무 적습니다. 최소 4개 필요 (현재 {len(df)}개)")
    sys.exit(1)

# 라벨 불균형 확인
if bot_count == 0 or human_count == 0:
    logger.error("한 라벨만 존재합니다. bot과 human 데이터가 모두 필요합니다.")
    sys.exit(1)

# ── 2. 학습 / 테스트 분리 ─────────────────────────────────
logger.info("학습/테스트 데이터 분리 중...")

try:
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    logger.info(f"학습 데이터: {len(X_train)}개, 테스트 데이터: {len(X_test)}개")
except ValueError as e:
    logger.error(f"train_test_split 오류: {e}")
    sys.exit(1)

# ── 3. 모델 학습 ──────────────────────────────────────────
logger.info("모델 학습 중 (RandomForest, n_estimators=100)...")

try:
    clf = RandomForestClassifier(
        n_estimators=100, 
        random_state=42,
        n_jobs=-1,  # 멀티프로세싱 활성화
        verbose=0
    )
    clf.fit(X_train, y_train)
    logger.info("모델 학습 완료")
except Exception as e:
    logger.error(f"모델 학습 오류: {e}")
    sys.exit(1)

# ── 4. 평가 ───────────────────────────────────────────────
logger.info("모델 평가 중...")

try:
    y_pred = clf.predict(X_test)
except Exception as e:
    logger.error(f"예측 오류: {e}")
    sys.exit(1)

try:
    accuracy = accuracy_score(y_test, y_pred)
    logger.info(f"Accuracy: {accuracy:.4f}")
    
    cm = confusion_matrix(y_test, y_pred)
    
    print("\n" + "="*50)
    print("모델 성능 평가")
    print("="*50)
    print(f"Accuracy: {accuracy:.4f}")
    print("\nConfusion Matrix:")
    print("                pred_bot  pred_human")
    print(f"  actual_bot      {cm[0][0]:^6}      {cm[0][1]:^6}")
    print(f"  actual_human    {cm[1][0]:^6}      {cm[1][1]:^6}")
    
    # Precision, Recall 계산
    if cm[0][0] + cm[1][0] > 0:
        precision_bot = cm[0][0] / (cm[0][0] + cm[1][0])
    else:
        precision_bot = 0
    
    if cm[0][0] + cm[0][1] > 0:
        recall_bot = cm[0][0] / (cm[0][0] + cm[0][1])
    else:
        recall_bot = 0
    
    if cm[1][1] + cm[0][1] > 0:
        precision_human = cm[1][1] / (cm[1][1] + cm[0][1])
    else:
        precision_human = 0
    
    if cm[1][1] + cm[1][0] > 0:
        recall_human = cm[1][1] / (cm[1][1] + cm[1][0])
    else:
        recall_human = 0
    
    print(f"\nBot Precision: {precision_bot:.4f}, Recall: {recall_bot:.4f}")
    print(f"Human Precision: {precision_human:.4f}, Recall: {recall_human:.4f}")
    
except Exception as e:
    logger.error(f"평가 지표 계산 오류: {e}")
    sys.exit(1)

# ── 5. Feature 중요도 ─────────────────────────────────────
logger.info("Feature 중요도 분석 중...")

try:
    feature_importance = list(zip(FEATURES, clf.feature_importances_))
    feature_importance.sort(key=lambda x: -x[1])
    
    print("\nFeature 중요도:")
    print("-" * 50)
    for name, score in feature_importance:
        bar = "█" * int(score * 40)
        print(f"  {name:<22} {score:.4f}  {bar}")
    print("-" * 50)
    
except Exception as e:
    logger.error(f"Feature 중요도 계산 오류: {e}")
    sys.exit(1)

# ── 6. 모델 저장 ──────────────────────────────────────────
logger.info("모델 저장 중...")

try:
    # 디렉토리 생성 (필요시)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    
    # 모델 저장
    with open(MODEL_PKL, "wb") as f:
        pickle.dump(clf, f)
    
    # 저장된 파일 크기 확인
    file_size = MODEL_PKL.stat().st_size
    logger.info(f"모델 저장 완료: {MODEL_PKL} ({file_size} bytes)")
    
    print("\n" + "="*50)
    print(f"모델 저장 완료: {MODEL_PKL}")
    print("="*50)
    sys.exit(0)
    
except PermissionError:
    logger.error(f"권한 오류: {MODEL_PKL}에 쓸 수 없습니다")
    sys.exit(1)
except IOError as e:
    logger.error(f"I/O 오류: {MODEL_PKL}에 저장 실패: {e}")
    sys.exit(1)
except Exception as e:
    logger.error(f"예상치 못한 오류: 모델 저장 실패: {e}")
    sys.exit(1)