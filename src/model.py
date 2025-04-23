import torch
from transformers import AutoTokenizer, AutoModel
from torch import nn
import time

class BERTClassifier(nn.Module):
  def __init__(self, bert_model_name, num_classes):
    super(BERTClassifier, self).__init__()
    # self.bert = BertModel.from_pretrained(bert_model_name)
    self.bert = AutoModel.from_pretrained('prajjwal1/bert-tiny')
    self.dropout = nn.Dropout(0.1)
    self.fc = nn.Linear(self.bert.config.hidden_size, num_classes)

  def forward(self, input_ids, attention_mask):
    outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
    pooled_output = outputs.pooler_output
    x = self.dropout(pooled_output)
    logits = self.fc(x)
    return logits

MODEL = BERTClassifier('prajjwal1/bert-tiny', 2)
MODEL.load_state_dict(torch.load('models/bert_model_2.pth', weights_only=True, map_location='cpu'))
TOKENIZER = AutoTokenizer.from_pretrained('prajjwal1/bert-tiny')

CALL_MODEL = BERTClassifier('prajjwal1/bert-tiny', 2)
CALL_MODEL.load_state_dict(torch.load('models/bert_model_calls.pth', map_location='cpu'))

def predict_label(text, model=MODEL, tokenizer=TOKENIZER, device='cpu', max_length=512, k=1):
    model.eval()
    encoding = tokenizer(text, return_tensors='pt', max_length=max_length, padding='max_length', truncation=True)
    input_ids = encoding['input_ids'].to(device)
    attention_mask = encoding['attention_mask'].to(device)

    with torch.no_grad():
      model.to(device)
      outputs = model(input_ids=input_ids, attention_mask=attention_mask)
      outputs = torch.softmax(outputs, dim=1)
    return float(outputs[0][0])

def predict_call_spam(text, model=CALL_MODEL, tokenizer=TOKENIZER, device='cpu', max_length=512, k=1):
    start = time.time()
    model.eval()
    text = text.replace("Input:", "Speaker 1:")
    text = text.replace("Output:", "Speaker 2:")
    encoding = tokenizer(text, return_tensors='pt', max_length=max_length, padding='max_length', truncation=True)
    input_ids = encoding['input_ids'].to(device)
    attention_mask = encoding['attention_mask'].to(device)

    with torch.no_grad():
      model.to(device)
      outputs = model(input_ids=input_ids, attention_mask=attention_mask)
      outputs = torch.softmax(outputs, dim=1)
    end = time.time()
    print(f"Time taken: {end - start}")
    return float(outputs[0][0])

# print("Done")
# print(predict_label('Hii! How are you doing today?'))
# print(predict_call_spam('Speaker 2: Hi, I am calling from the IRS today to let you know that your tax forms are incorrect.\nSpeaker 1: Oh what? What should I be doing?\nSpeaker 2: There are a few legal procedures'))