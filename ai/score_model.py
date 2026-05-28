import json
import os
import sys
import warnings

import joblib
import numpy as np
import pandas as pd
from sklearn.exceptions import InconsistentVersionWarning

warnings.filterwarnings('ignore', category=InconsistentVersionWarning)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_MODEL_PATH = os.path.abspath(os.path.join(BASE_DIR, '..', 'captcha_bot_detector.pkl'))
AI_MODEL_PATH = os.path.join(BASE_DIR, 'captcha_bot_detector.pkl')
MODEL_PATH = ROOT_MODEL_PATH if os.path.exists(ROOT_MODEL_PATH) else AI_MODEL_PATH
THRESHOLD = -0.05

FEATURE_NAMES = [
    'avg_speed',
    'max_speed',
    'speed_std',
    'direction_changes',
    'curvature',
    'click_variance',
    'avg_pause',
    'pause_std',
    'move_count',
    'click_count',
]


def extract_features(data):
    events = data.get('events', [])
    if not isinstance(events, list):
        raise ValueError('events must be a list')

    moves = [e for e in events if e.get('type') == 'move']
    clicks = [e for e in events if e.get('type') == 'click']

    distances = []
    for i in range(1, len(moves)):
        dx = (moves[i].get('x', 0) or 0) - (moves[i - 1].get('x', 0) or 0)
        dy = (moves[i].get('y', 0) or 0) - (moves[i - 1].get('y', 0) or 0)
        distances.append(np.sqrt(dx**2 + dy**2))

    avg_speed = np.mean(distances) if distances else 0
    max_speed = np.max(distances) if distances else 0
    speed_std = np.std(distances) if distances else 0

    direction_changes = 0
    angles = []
    for i in range(2, len(moves)):
        dx1 = (moves[i - 1].get('x', 0) or 0) - (moves[i - 2].get('x', 0) or 0)
        dy1 = (moves[i - 1].get('y', 0) or 0) - (moves[i - 2].get('y', 0) or 0)
        dx2 = (moves[i].get('x', 0) or 0) - (moves[i - 1].get('x', 0) or 0)
        dy2 = (moves[i].get('y', 0) or 0) - (moves[i - 1].get('y', 0) or 0)

        angle1 = np.arctan2(dy1, dx1)
        angle2 = np.arctan2(dy2, dx2)
        diff = abs(angle2 - angle1)
        angles.append(diff)
        if diff > 0.5:
            direction_changes += 1

    curvature = np.mean(angles) if angles else 0

    click_times = [e.get('elapsed_ms', 0) for e in clicks]
    click_variance = np.var(click_times) if len(click_times) > 1 else 0

    elapsed = [e.get('elapsed_ms', 0) for e in events if isinstance(e.get('elapsed_ms'), (int, float))]
    gaps = []
    for i in range(1, len(elapsed)):
        gaps.append(elapsed[i] - elapsed[i - 1])

    avg_pause = np.mean(gaps) if gaps else 0
    pause_std = np.std(gaps) if gaps else 0

    return [
        avg_speed,
        max_speed,
        speed_std,
        direction_changes,
        curvature,
        click_variance,
        avg_pause,
        pause_std,
        len(moves),
        len(clicks),
    ]


if __name__ == '__main__':
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as err:
        print(json.dumps({'error': f'Invalid JSON payload: {err}'}))
        sys.exit(1)

    try:
        loaded = joblib.load(MODEL_PATH)
    except Exception as err:
        print(json.dumps({'error': f'Failed to load model: {err}'}))
        sys.exit(1)

    if isinstance(loaded, dict):
        model = loaded.get('model')
        scaler = loaded.get('scaler')
    elif isinstance(loaded, tuple) and len(loaded) == 2:
        model, scaler = loaded
    else:
        model = loaded
        scaler = None

    if model is None:
        print(json.dumps({'error': 'Model not found in pickle file'}))
        sys.exit(1)

    try:
        features = extract_features(payload)
    except Exception as err:
        print(json.dumps({'error': f'Feature extraction failed: {err}'}))
        sys.exit(1)

    try:
        feature_df = pd.DataFrame([features], columns=FEATURE_NAMES)
        feature_array = feature_df
        if scaler is not None:
            feature_array = scaler.transform(feature_df)
    except Exception as err:
        print(json.dumps({'error': f'Scaling failed: {err}'}))
        sys.exit(1)

    try:
        score = float(model.decision_function(feature_array)[0])
        is_human = score >= THRESHOLD
        print(json.dumps({
            'is_human': is_human,
            'score': score,
            'threshold': THRESHOLD,
        }))
        sys.exit(0)
    except Exception as err:
        print(json.dumps({'error': f'Model scoring failed: {err}'}))
        sys.exit(1)
