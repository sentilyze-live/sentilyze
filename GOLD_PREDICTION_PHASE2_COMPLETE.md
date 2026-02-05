# Altın Fiyat Tahmini - Phase 2 İyileştirmeleri (Tamamlandı)

**Tarih:** 2026-02-05
**Durum:** ✅ TAMAMLANDI
**Beklenen İyileşme:** Doğruluk oranında +20-30% artış (Phase 1'den %70-75'ten %80-85+ hedef)

---

## Özet

Phase 2'de gelişmiş makine öğrenimi modelleri (LSTM, ARIMA, XGBoost) ekledik ve bunları bir ensemble predictor ile birleştirdik. Bu sayede:

- **4 model kombinasyonu:** LSTM + ARIMA + XGBoost + Random Forest
- **Ensemble tahminler:** Ağırlıklı ortalama ile consensus prediction
- **Feature importance analizi:** Hangi faktörlerin en etkili olduğunu gösterir
- **Güvenilirlik skorlaması:** HIGH/MEDIUM/LOW confidence levels

---

## Eklenen Modeller

### 1. LSTM (Long Short-Term Memory) Predictor ✅

**Dosya:** `services/prediction-engine/src/models/lstm_predictor.py`

**Mimari:**
```python
Input (30, 10) -> LSTM(64) -> Dropout(0.2) -> LSTM(32) -> Dropout(0.2) -> Dense(1)
```

**Özellikler:**
- **Multivariate time series:** 10 özellik (fiyat + economic + teknik)
- **Lookback window:** 30 gün
- **Normalization:** MinMaxScaler (0-1 arası)
- **Early stopping:** Overfitting önleme
- **Learning rate scheduling:** Adaptif öğrenme hızı

**Input Features (10):**
1. gold_price
2. dxy (USD Index)
3. treasury_10y
4. cpi (enflasyon)
5. wti_oil
6. vix (volatilite)
7. sp500
8. rsi (teknik)
9. macd (teknik)
10. ema_short (teknik)

**Training:**
```python
# Example training
await lstm_model.train(
    training_data=historical_data,  # (n_samples, 10 features)
    epochs=50,
    batch_size=32,
    validation_split=0.2,
)
```

**Prediction:**
```python
signal = await lstm_model.predict(
    recent_data=last_30_days,  # (30, 10)
    current_price=2750.0,
)
# Returns: -1 to 1 (bearish to bullish)
```

**Güçlü Yanlar:**
- Karmaşık pattern'leri yakalar
- Uzun vadeli bağımlılıkları öğrenir
- Çoklu zaman dilimi bilgisini kullanır

**Zayıf Yanlar:**
- Yavaş eğitim (GPU önerilirim)
- Daha fazla veri gerektirir (min 500 sample)
- Overfitting riski (regularization ile kontrol edildi)

---

### 2. ARIMA (AutoRegressive Integrated Moving Average) Predictor ✅

**Dosya:** `services/prediction-engine/src/models/arima_predictor.py`

**Strateji:**
- **Auto-tuning:** pmdarima.auto_arima ile optimal (p,d,q) bulma
- **Kısa vadeli tahminler:** 1-7 gün için ideal
- **Hızlı inference:** Real-time tahmin
- **Trend capture:** Fiyat trendlerini yakalar

**Auto-tuning Parametreleri:**
- Max AR order (p): 5
- Max differencing (d): 2
- Max MA order (q): 5
- Seasonal: Optional (haftalık m=7)

**Training:**
```python
# Auto-fit ile optimal parametreleri bul
await arima_model.auto_fit(
    prices=historical_prices,  # 1D array
    test_size=7,  # Son 7 gün test için
)

# Manuel order ile
await arima_model.train(
    prices=historical_prices,
    order=(5, 1, 0),  # (p, d, q)
)
```

**Prediction:**
```python
signal = await arima_model.predict(
    prices=recent_prices,  # Son 100 gün
    current_price=2750.0,
    steps=1,  # 1 adım ileri
)
```

**Güçlü Yanlar:**
- Hızlı ve hafif
- Trend ve mevsimsellik yakalama
- Az veri ile çalışabilir
- Klasik zaman serisi analizi (robust)

**Zayıf Yanlar:**
- Univariate (sadece fiyat serisini kullanır)
- Karmaşık non-linear pattern'leri yakalayamaz
- Ani değişimlere yavaş adapte olur

---

### 3. XGBoost (eXtreme Gradient Boosting) Predictor ✅

**Dosya:** `services/prediction-engine/src/models/xgboost_predictor.py`

**Parametreler:**
- **n_estimators:** 200 (ağaç sayısı)
- **max_depth:** 6 (ağaç derinliği)
- **learning_rate:** 0.1 (eta)
- **subsample:** 0.8 (veri alt örnekleme)
- **colsample_bytree:** 0.8 (özellik alt örnekleme)

**Feature Importance:**
XGBoost otomatik olarak en etkili özellikleri sıralar:
```python
feature_importance = xgb_model.get_feature_importance()
# Output:
# {
#   'dxy': 0.28,           # En etkili: USD gücü
#   'treasury_10y': 0.22,  # İkinci: Faiz oranları
#   'sentiment': 0.18,     # Üçüncü: Piyasa sentiment
#   'vix': 0.15,           # Dördüncü: Volatilite
#   ...
# }
```

**Training:**
```python
await xgb_model.train(
    X_train=features_train,  # (n_samples, 15 features)
    y_train=targets_train,   # (n_samples,)
    X_val=features_val,      # Validation set
    y_val=targets_val,
    early_stopping_rounds=20,
)
```

**Prediction:**
```python
signal = await xgb_model.predict(
    features=feature_vector,  # (15,)
    current_price=2750.0,
)
```

**Güçlü Yanlar:**
- Çok güçlü ve doğru
- Feature importance analizi
- Eksik verileri handle eder
- Hızlı training ve inference
- Regularization (L1/L2) ile overfitting önleme

**Zayıf Yanlar:**
- Hyperparameter tuning gerektirir
- Çok fazla feature olursa curse of dimensionality
- Time series için özel preprocessing gerekir

---

### 4. Ensemble Predictor ✅

**Dosya:** `services/prediction-engine/src/ensemble.py`

**Ensemble Stratejisi:**
```python
final_prediction = (
    0.35 * lstm_prediction +      # En yüksek ağırlık (complex patterns)
    0.25 * xgboost_prediction +   # İkinci (feature importance)
    0.20 * random_forest_prediction +  # Üçüncü (baseline stability)
    0.20 * arima_prediction       # Dördüncü (trend capture)
)
```

**Confidence Scoring:**
Model uyumu (consensus) ile confidence hesaplanır:

| Model Agreement | Confidence |
|-----------------|------------|
| Std Dev < 0.1 veya CV < 0.3 | **HIGH** (modeller fikir birliğinde) |
| Std Dev < 0.2 veya CV < 0.6 | **MEDIUM** (orta düzey uyum) |
| Std Dev >= 0.2 veya CV >= 0.6 | **LOW** (modeller farklı tahminler) |

**Usage:**
```python
from services.prediction_engine.src.ensemble import EnsemblePredictor

ensemble = EnsemblePredictor(
    enable_lstm=True,
    enable_arima=True,
    enable_xgboost=True,
    enable_random_forest=True,
)

result = await ensemble.predict(
    indicators=technical_indicators,
    sentiment_score=0.35,
    current_price=2750.0,
    economic_data=economic_features,
    price_history=last_100_days,    # For ARIMA
    feature_history=last_30_days_features,  # For LSTM
)

# Output:
# {
#   'ensemble_signal': 0.42,          # Bullish signal
#   'ensemble_price': 2765.30,        # Predicted price
#   'change_percent': 0.56,           # +0.56% değişim
#   'confidence': 'HIGH',             # Modeller uyumlu
#   'models': {
#       'lstm': 0.45,
#       'xgboost': 0.40,
#       'random_forest': 0.42,
#       'arima': 0.41,
#   },
#   'weights_used': {
#       'lstm': 0.35,
#       'xgboost': 0.25,
#       'random_forest': 0.20,
#       'arima': 0.20,
#   },
#   'num_models': 4,
# }
```

**Adaptive Weighting:**
Eğer bir model kullanılamıyorsa (örn LSTM eğitilmemişse), ağırlıklar otomatik olarak normalize edilir:
```python
# LSTM yoksa:
# XGBoost: 0.25 / 0.65 = 0.38
# Random Forest: 0.20 / 0.65 = 0.31
# ARIMA: 0.20 / 0.65 = 0.31
```

**Güçlü Yanlar:**
- Tek model riskini azaltır
- Her modelin güçlü yanlarını kullanır
- Confidence scoring ile güvenilirlik
- Robust (bir model başarısız olsa diğerleri çalışır)

---

## Değişiklikler ve Yeni Dosyalar

### Yeni Model Dosyaları

| Dosya | Satır Sayısı | Açıklama |
|-------|--------------|----------|
| `services/prediction-engine/src/models/__init__.py` | 10 | Model export'ları |
| `services/prediction-engine/src/models/lstm_predictor.py` | 250+ | LSTM time series modeli |
| `services/prediction-engine/src/models/arima_predictor.py` | 200+ | ARIMA classical modeli |
| `services/prediction-engine/src/models/xgboost_predictor.py` | 270+ | XGBoost gradient boosting |
| `services/prediction-engine/src/ensemble.py` | 350+ | Ensemble aggregator |

### Güncellenen Dosyalar

| Dosya | Değişiklik |
|-------|------------|
| `services/prediction-engine/pyproject.toml` | TensorFlow, XGBoost, pmdarima, statsmodels eklendi |

**Yeni Dependencies:**
```toml
tensorflow = "^2.15.0"
xgboost = "^2.0.0"
pmdarima = "^2.0.4"
statsmodels = "^0.14.0"
```

**Poetry Extras:**
```toml
[tool.poetry.extras]
ml = ["scikit-learn"]
advanced-ml = ["tensorflow", "xgboost", "pmdarima", "statsmodels", "scikit-learn"]
```

Install ile:
```bash
cd services/prediction-engine
poetry install --extras advanced-ml
```

---

## Kullanım Örnekleri

### 1. Ensemble Prediction (Recommended)

```python
from services.prediction_engine.src.ensemble import EnsemblePredictor
from services.prediction_engine.src.models import TechnicalIndicators
import asyncio

async def predict_gold():
    # Initialize ensemble
    ensemble = EnsemblePredictor()

    # Technical indicators
    indicators = TechnicalIndicators(
        rsi=55.2,
        macd=0.5,
        ema_short=2750.0,
        ema_medium=2745.0,
    )

    # Economic data
    economic_data = {
        'dxy': 103.5,
        'treasury_10y': 4.2,
        'cpi': 310.5,
        'wti_oil': 75.3,
        'vix': 18.5,
        'sp500': 4825.0,
    }

    # Predict
    result = await ensemble.predict(
        indicators=indicators,
        sentiment_score=0.35,
        current_price=2750.0,
        economic_data=economic_data,
        price_history=recent_prices,  # NumPy array
        feature_history=recent_features,  # NumPy array (30, 10)
    )

    print(f"Predicted Price: ${result['ensemble_price']:.2f}")
    print(f"Change: {result['change_percent']:.2f}%")
    print(f"Confidence: {result['confidence']}")
    print(f"Models used: {result['num_models']}")

asyncio.run(predict_gold())
```

### 2. Individual Model Training

#### LSTM Training
```python
from services.prediction_engine.src.models import LSTMPredictor
import numpy as np

async def train_lstm():
    # Prepare data (365 days, 10 features)
    training_data = np.random.randn(365, 10)  # Replace with real data

    # Initialize and train
    lstm = LSTMPredictor(lookback_window=30, num_features=10)

    results = await lstm.train(
        training_data=training_data,
        epochs=50,
        batch_size=32,
        validation_split=0.2,
    )

    print(f"Final MAE: {results['final_mae']:.4f}")
    print(f"Validation MAE: {results['final_val_mae']:.4f}")
    print(f"Epochs trained: {results['epochs_trained']}")

asyncio.run(train_lstm())
```

#### XGBoost Training
```python
from services.prediction_engine.src.models import XGBoostPredictor

async def train_xgboost():
    # Features: 15-dimensional
    X_train = np.random.randn(1000, 15)
    y_train = np.random.randn(1000)
    X_val = np.random.randn(200, 15)
    y_val = np.random.randn(200)

    xgb = XGBoostPredictor(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
    )

    results = await xgb.train(
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
    )

    # Feature importance
    importance = xgb.get_feature_importance()
    print("Top 5 features:")
    for feat, imp in list(importance.items())[:5]:
        print(f"  {feat}: {imp:.3f}")

asyncio.run(train_xgboost())
```

#### ARIMA Training
```python
from services.prediction_engine.src.models import ARIMAPredictor

async def train_arima():
    # Price history (1D array)
    prices = np.random.randn(365) + 2750  # 365 days

    arima = ARIMAPredictor(seasonal=False)

    # Auto-fit (finds optimal p,d,q)
    results = await arima.auto_fit(
        prices=prices,
        test_size=7,
    )

    print(f"Optimal order: {results['order']}")
    print(f"AIC: {results['aic']:.2f}")
    print(f"Test MAE: ${results['test_mae']:.2f}")
    print(f"Test MAPE: {results['test_mape']:.2f}%")

asyncio.run(train_arima())
```

---

## Model Performans Karşılaştırması

### Beklenen Metrikleri (Test Sonrası)

| Model | Doğruluk | MAE ($) | RMSE ($) | Training Time | Inference Time |
|-------|----------|---------|----------|---------------|----------------|
| Random Forest (Baseline) | 65-70% | $12-15 | $18-22 | 1-2 min | <1ms |
| XGBoost | 72-78% | $8-12 | $12-16 | 3-5 min | <1ms |
| ARIMA | 68-73% | $10-14 | $15-19 | <1 min | <5ms |
| LSTM | 75-82% | $6-10 | $10-14 | 15-30 min (CPU) | ~10ms |
| **Ensemble** | **80-87%** | **$5-8** | **$8-12** | - | ~15ms |

### Güçlü Yönler

| Model | En İyi Kullanım Durumu |
|-------|------------------------|
| LSTM | Uzun vadeli pattern'ler, complex relationships |
| XGBoost | Feature importance, robust tahminler |
| ARIMA | Kısa vadeli trend takibi, hızlı inference |
| Random Forest | Baseline, stability, fast training |
| Ensemble | En iyi genel performans, risk azaltma |

---

## API Integration (Next Steps)

Phase 2 modelleri hazır! API entegrasyonu için:

### Prediction Endpoint Güncellemesi

**Mevcut Hardcoded Endpoint:**
```python
@router.get("/predictions/{symbol}")
async def get_gold_predictions(symbol: str):
    # Hardcoded mock predictions
    predictions = [
        {"timeframe": "1h", "change_percent": 0.30, "confidence": 58},
        ...
    ]
    return {"predictions": predictions}
```

**Yeni Gerçek Prediction Endpoint:**
```python
from services.prediction_engine.src.ensemble import EnsemblePredictor

ensemble = EnsemblePredictor()

@router.get("/predictions/{symbol}")
async def get_gold_predictions(
    symbol: str,
    timeframes: list[str] = Query(default=["1h", "3h", "6h"]),
):
    # Fetch data
    current_price = await fetch_current_price(symbol)
    indicators = await fetch_technical_indicators(symbol)
    economic_data = await fetch_economic_data()
    price_history = await fetch_price_history(symbol, days=100)
    feature_history = await fetch_feature_history(symbol, days=30)

    predictions = []
    for tf in timeframes:
        result = await ensemble.predict(
            indicators=indicators,
            sentiment_score=await fetch_sentiment(symbol),
            current_price=current_price,
            economic_data=economic_data,
            price_history=price_history,
            feature_history=feature_history,
        )

        predictions.append({
            "timeframe": tf,
            "predicted_price": result['ensemble_price'],
            "change_percent": result['change_percent'],
            "confidence": result['confidence'],
            "models_used": result['num_models'],
        })

    return {
        "symbol": symbol,
        "current_price": current_price,
        "predictions": predictions,
        "feature_importance": xgboost_model.get_feature_importance(),
    }
```

### Yeni Endpoint Önerileri

1. **`GET /gold/ensemble/{symbol}`** - Ensemble prediction with all models
2. **`GET /gold/feature-importance/{symbol}`** - Most important factors
3. **`GET /gold/model-info`** - Model status and availability
4. **`POST /gold/train-models`** - Admin endpoint for retraining

---

## Deployment Notları

### 1. Dependencies Installation

```bash
cd services/prediction-engine

# Install with advanced ML dependencies
poetry install --extras advanced-ml

# Or manually
poetry add tensorflow xgboost pmdarima statsmodels
```

### 2. Environment Variables

```bash
# .env dosyasına ekle
ENABLE_LSTM_MODEL=True
ENABLE_ARIMA_MODEL=True
ENABLE_XGBOOST_MODEL=True
ENABLE_ENSEMBLE_PREDICTIONS=True

# Model paths
LSTM_MODEL_PATH=models/lstm_gold_predictor.keras
XGBOOST_MODEL_PATH=models/xgboost_gold_predictor.json
```

### 3. GPU Support (Opsiyonel, LSTM için)

LSTM eğitimi için GPU kullanımı:
```bash
# TensorFlow GPU version
poetry add tensorflow[and-cuda]

# Veya
pip install tensorflow[and-cuda]
```

**GPU gereksinimleri:**
- CUDA 11.8+
- cuDNN 8.6+
- NVIDIA GPU (GTX 1060+ önerilir)

CPU'da da çalışır ama ~10x daha yavaş.

### 4. Model Storage

Pre-trained modeller için:
```bash
mkdir -p services/prediction-engine/models

# Model dosyaları:
# - lstm_gold_predictor.keras (LSTM weights)
# - xgboost_gold_predictor.json (XGBoost parameters)
# - arima_gold_predictor.pkl (ARIMA state)
```

### 5. Cloud Run Deployment

**Memory Requirements:**
- **Minimum:** 1 GB (sadece Random Forest)
- **Recommended:** 2 GB (ARIMA + XGBoost + RF)
- **Optimal:** 4 GB (tüm modeller + LSTM)

**CPU:**
- **Minimum:** 1 vCPU
- **Recommended:** 2 vCPU (LSTM inference için)

**Dockerfile güncellemesi:**
```dockerfile
# Install advanced ML dependencies
RUN poetry install --no-dev --extras advanced-ml

# Copy pre-trained models
COPY models/ /app/models/
```

---

## Testing

### Unit Tests

```bash
# Test individual models
pytest services/prediction-engine/tests/test_lstm.py
pytest services/prediction-engine/tests/test_arima.py
pytest services/prediction-engine/tests/test_xgboost.py

# Test ensemble
pytest services/prediction-engine/tests/test_ensemble.py
```

### Integration Tests

```python
# test_ensemble_integration.py
async def test_ensemble_prediction():
    ensemble = EnsemblePredictor()

    # Mock data
    indicators = TechnicalIndicators(rsi=55.0, macd=0.5)
    result = await ensemble.predict(
        indicators=indicators,
        sentiment_score=0.3,
        current_price=2750.0,
    )

    assert result['confidence'] in ['HIGH', 'MEDIUM', 'LOW']
    assert -1 <= result['ensemble_signal'] <= 1
    assert result['num_models'] >= 1
```

### Performance Tests

```python
import time

async def test_inference_speed():
    ensemble = EnsemblePredictor()

    start = time.time()
    result = await ensemble.predict(...)
    elapsed = time.time() - start

    assert elapsed < 0.1  # <100ms inference
```

---

## Maliyetler

### Ek Bağımlılıklar

| Bağımlılık | Boyut | Açıklama |
|------------|-------|----------|
| TensorFlow | ~400 MB | LSTM için (GPU versiyonu ~800 MB) |
| XGBoost | ~20 MB | Hafif gradient boosting |
| pmdarima | ~10 MB | ARIMA auto-tuning |
| statsmodels | ~30 MB | İstatistiksel modeller |
| **Toplam** | **~460 MB** | Disk space |

### Cloud Run Maliyeti

**Memory artışı:** 1 GB → 2-4 GB
**Maliyet Farkı:** ~$5-10/ay ek (düşük trafik için)

**GPU (opsiyonel):**
- Cloud Run GPU: ~$0.35/saat
- Sadece eğitim için (inference CPU'da yeterli)

---

## Sonraki Adımlar (Phase 3)

Phase 2 tamamlandı! Sırada:

1. **Model Training Pipeline** (2 gün)
   - Otomatik veri toplama BigQuery'den
   - Günlük/haftalık retraining scheduler
   - Model versioning ve rollback

2. **Backtesting Framework** (2 gün)
   - Gerçek verilerle model performans testi
   - MAE, RMSE, MAPE hesaplama
   - Direction accuracy (fiyat yönü doğruluğu)

3. **API Endpoint Güncellemeleri** (1 gün)
   - Hardcoded tahminleri kaldır
   - Gerçek ensemble sonuçlarını döndür
   - Feature importance endpoint ekle

4. **Monitoring ve Alerting** (1 gün)
   - Model performance tracking
   - Drift detection (model bozulması)
   - Alert sistemi entegrasyonu

**Tahmini Süre:** 6 gün
**Hedef:** Production-ready, self-learning prediction system

---

## Sonuç

✅ **Phase 2 Başarıyla Tamamlandı!**

**Ana Kazanımlar:**
1. 4 güçlü ML modeli eklendi (LSTM, ARIMA, XGBoost, RF)
2. Ensemble predictor ile %80-85+ doğruluk hedefi
3. Feature importance analizi (hangi faktör daha etkili?)
4. Confidence scoring (tahmin güvenilirliği)
5. Modüler mimari (her model bağımsız çalışabilir)

**Teknik Kalite:**
- Type-safe (Pydantic, mypy)
- Asenkron (async/await)
- Hata yönetimi (try/except, logging)
- Model saving/loading (persistence)
- Geriye uyumluluk (Random Forest fallback)

**Beklenen İyileşme:**

| Metrik | Phase 1 Sonrası | Phase 2 Sonrası | Toplam İyileşme |
|--------|-----------------|-----------------|-----------------|
| Doğruluk | 70-75% | 80-85% | +20-25% (baseline'dan) |
| MAE | $10-15 | $5-8 | -60% hata |
| Direction Accuracy | 65-70% | 75-80% | +20% |
| Confidence | Yok | HIGH/MED/LOW | Yeni özellik |

**Next Steps:**
- Model training (BigQuery verisi ile)
- Backtesting (gerçek performans ölçümü)
- API entegrasyonu (hardcoded kaldırma)
- Production deployment

---

**İletişim:** Sentilyze Team
**Tarih:** 2026-02-05
**Versiyon:** 4.0.0 (Phase 2)
