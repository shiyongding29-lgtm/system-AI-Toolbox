"""
PyTorch + DistilBERT 情感分类器 — 正面/负面/中性 3 分类
训练前当前 sentiment_analyzer 服务加载的是未训练的 head，输出基本随机；
跑完本脚本后服务自动加载 models/sentiment_classifier/ 下的本地模型。

用法：python3 train_sentiment_classifier.py [csv文件路径]
"""
import sys
import csv
from pathlib import Path
from collections import Counter

import torch
from torch.utils.data import Dataset, DataLoader
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification, get_scheduler
from torch.optim import AdamW
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

SCRIPT_DIR = Path(__file__).resolve().parent
CSV_PATH = sys.argv[1] if len(sys.argv) > 1 else str(SCRIPT_DIR / 'training_data_sentiment.csv')
SAVE_PATH = str(SCRIPT_DIR / 'models' / 'sentiment_classifier')

# ═══════════ 从 CSV 读取数据 ═══════════
texts, raw_labels = [], []
with open(CSV_PATH, 'r', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        texts.append(row['text'].strip())
        raw_labels.append(row['label'].strip())

# 自动发现所有类别
LABELS = sorted(set(raw_labels))
print(f'从 {CSV_PATH} 加载 {len(texts)} 条数据')
print(f'发现 {len(LABELS)} 个类别: {LABELS}')

labels = [LABELS.index(l) for l in raw_labels]
for lbl, cnt in Counter(raw_labels).most_common():
    print(f'  {lbl}: {cnt} 条')

# ═══════════ 训练/测试分割 ═══════════
train_texts, test_texts, train_labels, test_labels = train_test_split(
    texts, labels, test_size=0.2, random_state=42, stratify=labels
)
print(f'\n训练集: {len(train_texts)} 条  |  测试集: {len(test_texts)} 条')

# ═══════════ Tokenization ═══════════
TOKENIZER = DistilBertTokenizer.from_pretrained('distilbert-base-multilingual-cased')


class SentimentDataset(Dataset):
    def __init__(self, texts, labels):
        self.encodings = TOKENIZER(texts, truncation=True, padding=True, max_length=128, return_tensors='pt')
        self.labels = torch.tensor(labels)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return {'input_ids': self.encodings['input_ids'][idx],
                'attention_mask': self.encodings['attention_mask'][idx],
                'labels': self.labels[idx]}


train_loader = DataLoader(SentimentDataset(train_texts, train_labels), batch_size=16, shuffle=True)
test_loader = DataLoader(SentimentDataset(test_texts, test_labels), batch_size=16)

# ═══════════ 加载模型 ═══════════
MODEL = DistilBertForSequenceClassification.from_pretrained(
    'distilbert-base-multilingual-cased', num_labels=len(LABELS)
)

# ═══════════ 训练 ═══════════
DEVICE = torch.device('mps' if torch.backends.mps.is_available() else 'cpu')
MODEL.to(DEVICE)
OPTIMIZER = AdamW(MODEL.parameters(), lr=5e-5)
NUM_EPOCHS = 12
SCHEDULER = get_scheduler('linear', optimizer=OPTIMIZER, num_warmup_steps=len(train_loader),
                          num_training_steps=NUM_EPOCHS * len(train_loader))

print(f'\n设备: {DEVICE}  |  参数: {sum(p.numel() for p in MODEL.parameters()):,}  |  {NUM_EPOCHS} 轮')

MODEL.train()
for epoch in range(NUM_EPOCHS):
    total_loss = 0
    for batch in train_loader:
        batch = {k: v.to(DEVICE) for k, v in batch.items()}
        loss = MODEL(**batch).loss
        loss.backward()
        OPTIMIZER.step()
        SCHEDULER.step()
        OPTIMIZER.zero_grad()
        total_loss += loss.item()
    print(f'Epoch {epoch + 1:2d}/{NUM_EPOCHS}  |  Loss: {total_loss / len(train_loader):.4f}')

# ═══════════ 评估 ═══════════
MODEL.eval()
all_preds, all_labels = [], []
with torch.no_grad():
    for batch in test_loader:
        batch = {k: v.to(DEVICE) for k, v in batch.items()}
        preds = torch.argmax(MODEL(**batch).logits, dim=-1)
        all_preds.extend(preds.cpu().numpy())
        all_labels.extend(batch['labels'].cpu().numpy())

acc = accuracy_score(all_labels, all_preds)
print(f'\n✅ 测试准确率: {acc:.2%}')
print(classification_report(all_labels, all_preds, target_names=LABELS))

# ═══════════ 保存 ═══════════
MODEL.save_pretrained(SAVE_PATH)
TOKENIZER.save_pretrained(SAVE_PATH)

# 导出 LABELS 给服务使用（sentiment_analyzer 自动读取）
with open(Path(SAVE_PATH) / 'labels.txt', 'w') as f:
    f.write('\n'.join(LABELS))
print(f'\n模型已保存: {SAVE_PATH}')
print('重启后端后情感分析自动使用本地训练模型')
