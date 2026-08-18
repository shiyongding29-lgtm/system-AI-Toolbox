"""Sentiment Analyzer API — 情感分析（正面/负面/中性）。

优先加载本地训练的模型（models/sentiment_classifier/，
由 train_sentiment_classifier.py 产出）；模型不存在时回退到
未训练的预训练模型（输出不可靠，仅保证接口可用）。
"""
import os
import torch
from fastapi import APIRouter
from pydantic import BaseModel
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification

from backend.config import config

router = APIRouter(prefix="/api/sentiment", tags=["sentiment-analyzer"])

LOCAL_MODEL_PATH = os.path.join(config.models_dir, "sentiment_classifier")
FALLBACK_MODEL_NAME = "distilbert-base-multilingual-cased"
FALLBACK_LABELS = ["negative", "neutral", "positive"]

_model = None
_tokenizer = None
_device = None
LABELS = FALLBACK_LABELS


def _load():
    global _model, _tokenizer, _device, LABELS
    if _model is not None:
        return
    _device = torch.device('mps' if torch.backends.mps.is_available() else 'cpu')

    # 本地训练模型优先（labels.txt 由训练脚本自动生成）
    labels_path = os.path.join(LOCAL_MODEL_PATH, "labels.txt")
    if os.path.exists(labels_path):
        with open(labels_path) as f:
            LABELS = [l.strip() for l in f if l.strip()]
        _tokenizer = DistilBertTokenizer.from_pretrained(LOCAL_MODEL_PATH)
        _model = DistilBertForSequenceClassification.from_pretrained(LOCAL_MODEL_PATH)
        print(f"✅ 情感分析模型已加载（本地训练，{len(LABELS)} 类，设备: {_device}）")
    else:
        # 回退：未训练的分类头，输出不可靠，仅保证接口可用
        LABELS = FALLBACK_LABELS
        _tokenizer = DistilBertTokenizer.from_pretrained(FALLBACK_MODEL_NAME)
        _model = DistilBertForSequenceClassification.from_pretrained(FALLBACK_MODEL_NAME, num_labels=3)
        print(f"⚠️ 情感分析模型未训练（回退预训练模型），建议运行 train_sentiment_classifier.py")
    _model.to(_device)
    _model.eval()


class SentimentRequest(BaseModel):
    text: str = ""
    texts: list[str] = []


@router.post("/analyze")
def analyze(req: SentimentRequest):
    """分析单条或多条文本情感。"""
    _load()
    texts = req.texts if req.texts else [req.text] if req.text else []
    if not texts: return {"code": 400, "msg": "No text", "data": None}

    results = []
    for t in texts:
        inputs = _tokenizer(t, return_tensors='pt', truncation=True, padding=True, max_length=128)
        inputs = {k: v.to(_device) for k, v in inputs.items()}
        with torch.no_grad():
            scores = torch.softmax(_model(**inputs).logits, dim=-1)[0]
            pred = torch.argmax(scores).item()
        results.append({
            "text": t[:200],
            "sentiment": LABELS[pred],
            "confidence": round(scores[pred].item(), 4),
            "scores": {LABELS[i]: round(scores[i].item(), 4) for i in range(3)}
        })

    if len(results) == 1:
        return {"code": 0, "msg": "ok", "data": results[0]}
    return {"code": 0, "msg": "ok", "data": {"results": results, "summary": {
        "positive": sum(1 for r in results if r['sentiment']=='positive'),
        "negative": sum(1 for r in results if r['sentiment']=='negative'),
        "neutral": sum(1 for r in results if r['sentiment']=='neutral'),
    }}}
