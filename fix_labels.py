import pandas as pd

# Load the dataset
data = pd.read_csv("commands_dataset.csv", encoding='utf-8')

# Print initial inspection
print("First 10 rows before correction:")
print(data.head(10))
print("\nData types before correction:")
print(data.dtypes)
print("\nUnique values in labels column before correction:")
print(data['labels'].unique())

# Remove rows where labels is "labels" or non-numeric
data = data[data['labels'] != "labels"]
data['labels'] = pd.to_numeric(data['labels'], errors='coerce').fillna(-1).astype(int)  # Convert to int, use -1 for invalid

# Filter out any rows with invalid labels (e.g., -1)
data = data[data['labels'] >= 0]

# Save the corrected dataset
data.to_csv("commands_dataset_with_labels.csv", index=False, encoding='utf-8')
print("\nDataset corrected and saved with integer labels.")
print("First 10 rows after correction:")
print(data.head(10))
print(f"Total rows after correction: {len(data)}")