import pandas as pd
import torch
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification, Trainer, TrainingArguments
from datasets import Dataset
from sklearn.model_selection import train_test_split
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load and prepare dataset
data = pd.read_csv("commands_dataset_with_labels.csv", encoding='utf-8')
train_data, eval_data = train_test_split(data, test_size=0.2, random_state=42)

# Convert labels to integers if they are strings
train_data['labels'] = train_data['labels'].astype(int)
eval_data['labels'] = eval_data['labels'].astype(int)

# Initialize tokenizer and model
model_name = "distilbert-base-uncased"
tokenizer = DistilBertTokenizer.from_pretrained(model_name)
model = DistilBertForSequenceClassification.from_pretrained(model_name, num_labels=len(data['intent'].unique()), ignore_mismatched_sizes=True)

# Tokenize dataset
def tokenize_function(examples):
    return tokenizer(examples['command'], padding="max_length", truncation=True, max_length=64)

# Convert to Hugging Face Dataset
train_dataset = Dataset.from_pandas(train_data)
eval_dataset = Dataset.from_pandas(eval_data)

# Apply tokenization
train_dataset = train_dataset.map(tokenize_function, batched=True)
eval_dataset = eval_dataset.map(tokenize_function, batched=True)

# Set format for PyTorch, including labels
train_dataset.set_format('torch', columns=['input_ids', 'attention_mask', 'labels'])
eval_dataset.set_format('torch', columns=['input_ids', 'attention_mask', 'labels'])

# Custom collate function to ensure labels are included in the batch
def collate_fn(batch):
    input_ids = torch.stack([item['input_ids'] for item in batch])
    attention_mask = torch.stack([item['attention_mask'] for item in batch])
    labels = torch.tensor([item['labels'] for item in batch], dtype=torch.long)  # Ensure long type
    return {'input_ids': input_ids, 'attention_mask': attention_mask, 'labels': labels}

# Training arguments
training_args = TrainingArguments(
    output_dir="./distilbert_finetuned",
    eval_strategy="epoch",
    save_strategy="epoch",
    learning_rate=2e-5,
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    num_train_epochs=5,
    weight_decay=0.01,
    logging_dir='./logs',
    logging_steps=10,
    fp16=True,
    load_best_model_at_end=True,
)

# Trainer with custom collate function
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
    data_collator=collate_fn,
)

# Train and save
logger.info("Starting training...")
trainer.train()
trainer.save_model("./distilbert_finetuned")
tokenizer.save_pretrained("./distilbert_finetuned")
logger.info("Saving trained model and tokenizer...")