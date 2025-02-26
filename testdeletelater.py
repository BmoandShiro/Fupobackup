import pandas as pd

# Load the dataset
data = pd.read_csv("commands_dataset.csv", encoding='utf-8')

# Print the first 10 rows and data types
print("First 10 rows:")
print(data.head(10))
print("\nData types:")
print(data.dtypes)
print("\nUnique values in labels column:")
print(data['labels'].unique())

# Check for non-numeric or invalid values
non_numeric_labels = data[~data['labels'].str.match(r'^\d+$', na=False)]['labels']
if not non_numeric_labels.empty:
    print("\nNon-numeric or invalid labels found:")
    print(non_numeric_labels)
    print("\nRows with invalid labels:")
    print(data[data['labels'].isin(non_numeric_labels)])