from transformers import BartForSequenceClassification, BartTokenizer, TrainingArguments, Trainer
from datasets import Dataset
import pandas as pd
from sklearn.model_selection import train_test_split

import torch
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU Device Name: {torch.cuda.get_device_name(0)}")
    print(f"GPU Device Count: {torch.cuda.device_count()}")

# Check GPU availability and details
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU Device Name: {torch.cuda.get_device_name(0)}")
    print(f"GPU Device Count: {torch.cuda.device_count()}")
else:
    print("CUDA is not available. Training will use CPU.")

# Set device
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")

# Load your dataset
data = pd.read_csv("commands_dataset.csv")
train_data, val_data = train_test_split(data, test_size=0.2, random_state=42)

# Initialize tokenizer and model
model_name = "facebook/bart-large-mnli"
tokenizer = BartTokenizer.from_pretrained(model_name)
model = BartForSequenceClassification.from_pretrained(model_name, num_labels=len(data['intent'].unique()))

# Move model to GPU
model.to(device)
print(f"Model moved to {device}")

# Tokenize dataset
def tokenize_function(examples):
    return tokenizer(examples['command'], padding="max_length", truncation=True, max_length=128)

train_dataset = Dataset.from_pandas(train_data).map(tokenize_function, batched=True)
val_dataset = Dataset.from_pandas(val_data).map(tokenize_function, batched=True)

# Define training arguments, optimized for GPU
training_args = TrainingArguments(
    output_dir="./bart_finetuned",
    evaluation_strategy="epoch",
    learning_rate=2e-5,
    per_device_train_batch_size=16,  # Adjust if memory issues
    per_device_eval_batch_size=16,
    num_train_epochs=3,
    weight_decay=0.01,
    push_to_hub=False,
    fp16=True,  # Mixed precision for GPU
)

# Define Trainer with GPU support
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
    tokenizer=tokenizer,
)

# Train the model
trainer.train()

# Save the model
model.save_pretrained("./bart_finetuned")
tokenizer.save_pretrained("./bart_finetuned")