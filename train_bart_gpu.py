from transformers import BartForSequenceClassification, BartTokenizer, TrainingArguments, Trainer
from datasets import Dataset
import pandas as pd
from sklearn.model_selection import train_test_split
import torch
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check GPU availability and details
logger.info(f"PyTorch version: {torch.__version__}")
logger.info(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    logger.info(f"GPU Device Name: {torch.cuda.get_device_name(0)}")
    logger.info(f"GPU Device Count: {torch.cuda.device_count()}")
else:
    logger.error("CUDA is not available. Training will use CPU. Check PyTorch, NVIDIA drivers, and CUDA Toolkit installation.")

# Set device
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
logger.info(f"Using device: {device}")

try:
    # Load your dataset with explicit encoding and labels
    logger.info("Loading dataset...")
    data = pd.read_csv("commands_dataset.csv", encoding='utf-8')
    logger.info(f"Dataset intents: {data['intent'].unique()}")
    logger.info(f"Number of unique intents: {len(data['intent'].unique())}")

    train_data, val_data = train_test_split(data, test_size=0.2, random_state=42)

    # Initialize tokenizer and model with size mismatch handling
    model_name = "facebook/bart-large-mnli"
    logger.info(f"Loading model and tokenizer from {model_name}")
    tokenizer = BartTokenizer.from_pretrained(model_name)
    model = BartForSequenceClassification.from_pretrained(model_name, num_labels=len(data['intent'].unique()), ignore_mismatched_sizes=True)

    # Move model to GPU
    model.to(device)
    logger.info(f"Model moved to {device}")

    # Tokenize dataset with labels
    def tokenize_function(examples):
        try:
            tokenized = tokenizer(examples['command'], padding="max_length", truncation=True, max_length=64, return_tensors="pt")
            tokenized['labels'] = examples['labels']
            return tokenized
        except Exception as e:
            logger.error(f"Tokenization error: {e}")
            raise

    logger.info("Tokenizing dataset...")
    train_dataset = Dataset.from_pandas(train_data).map(tokenize_function, batched=True)
    val_dataset = Dataset.from_pandas(val_data).map(tokenize_function, batched=True)

    # Define training arguments, optimized for GPU
    training_args = TrainingArguments(
        output_dir="./bart_finetuned",
        eval_strategy="epoch",  # Updated from evaluation_strategy
        learning_rate=2e-5,
        per_device_train_batch_size=4,  # Reduced for stability
        per_device_eval_batch_size=4,
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
    logger.info("Starting training...")
    trainer.train()

    # Save the model
    logger.info("Saving trained model and tokenizer...")
    model.save_pretrained("./bart_finetuned")
    tokenizer.save_pretrained("./bart_finetuned")

except Exception as e:
    logger.error(f"Training failed: {e}")
    raise