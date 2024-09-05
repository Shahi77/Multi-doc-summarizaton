import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from nltk.tokenize import word_tokenize


class BiLSTMModel(nn.Module):
    def __init__(self, vocab_size, embedding_dim, hidden_dim, num_layers, num_classes, dropout=0.5):
        super(BiLSTMModel, self).__init__()
        
        # Word Encoding Layer (Embedding Layer)
        self.embedding = nn.Embedding(vocab_size, embedding_dim)
        
        # LSTM Layer
        self.lstm = nn.LSTM(input_size=embedding_dim,
                            hidden_size=hidden_dim,
                            num_layers=num_layers,
                            bidirectional=True,
                            dropout=dropout,
                            batch_first=True)
        
        # Ranking Layer (Fully Connected Layer)
        self.fc = nn.Linear(hidden_dim * 2, num_classes)
        
        # Dropout for regularization
        self.dropout = nn.Dropout(dropout)
        
    def forward(self, x):
        # Step 4.1: Word Encoding Layer
        x = self.embedding(x)
        
        # Step 4.4: LSTM Layer
        lstm_out, (hn, cn) = self.lstm(x)
        
        # Take the output from the last LSTM layer and apply dropout
        lstm_out = self.dropout(lstm_out)
        
        # Aggregate LSTM output for the ranking layer
        # Here we take the last hidden state of each sequence
        lstm_out = lstm_out[:, -1, :]  # [batch_size, hidden_dim * 2]
        
        # Step 4.5: Output Layer
        out = self.fc(lstm_out)
        
        return out


class TextSummarizationDataset(Dataset):
    def __init__(self, data_path, vocab, max_seq_length):
        self.data_path = data_path
        self.vocab = vocab
        self.max_seq_length = max_seq_length
        self.data = self.load_data()
        
        # Check if the dataset is empty
        if len(self.data) == 0:
            raise ValueError("Dataset is empty. Please check the data files.")
        
    def load_data(self):
        texts = []
        labels = []
        for root, _, files in os.walk(self.data_path):
            print(f"Checking directory: {root}, Files: {files}")
            for file_name in files:
                file_path = os.path.join(root, file_name)
                print(f"Reading file: {file_path}")
                with open(file_path, 'r') as file:
                    lines = file.readlines()
                    for line in lines:
                        parts = line.strip().split('\t')
                        if len(parts) >= 2:
                            text, label = parts[0], parts[1]
                            texts.append(text)
                            labels.append(label)
                        else:
                            print(f"Skipping malformed line: {line}")
        print(f"Loaded {len(texts)} texts and {len(labels)} labels")
        return list(zip(texts, labels))

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        text, label = self.data[idx]
        tokens = word_tokenize(text.lower())
        indexed_tokens = [self.vocab.get(token, 0) for token in tokens[:self.max_seq_length]]
        indexed_tokens += [0] * (self.max_seq_length - len(indexed_tokens))  # padding
        label = int(label)  # Assuming binary classification
        return torch.tensor(indexed_tokens), torch.tensor(label, dtype=torch.float)


def train_model(model, dataloader, criterion, optimizer, num_epochs=5):
    model.train()
    for epoch in range(num_epochs):
        running_loss = 0.0
        for inputs, labels in dataloader:
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs.squeeze(), labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item()
        print(f"Epoch {epoch + 1}/{num_epochs}, Loss: {running_loss / len(dataloader)}")


def main():
    # Hyperparameters
    vocab_size = 10000  # Example vocab size
    embedding_dim = 300
    hidden_dim = 128
    num_layers = 2
    num_classes = 1  # Binary classification
    dropout = 0.5
    max_seq_length = 50
    batch_size = 32
    num_epochs = 5

    # Load the vocabulary (you need to provide or build this)
    vocab = {}  # Replace with your vocabulary loading mechanism

    # Prepare dataset and dataloader
    data_path = os.path.join(os.path.dirname(__file__), '..', '..', 'preprocessed_data')
    dataset = TextSummarizationDataset(data_path, vocab, max_seq_length)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    # Initialize model, loss function, and optimizer
    model = BiLSTMModel(vocab_size, embedding_dim, hidden_dim, num_layers, num_classes, dropout)
    criterion = nn.BCEWithLogitsLoss()  # Binary classification
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    # Train the model
    train_model(model, dataloader, criterion, optimizer, num_epochs)


if __name__ == "__main__":
    main()
