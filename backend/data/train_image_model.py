"""
train_image_model.py — Fine-tune EfficientNet-B0 for injury severity triage.

Run from the backend directory:
    python data/train_image_model.py

NOTE: The model file (models/image_triage.pt) already exists if it was
previously trained. Re-running this script will overwrite it.

For production accuracy, replace the synthetic tensors with a real labelled
injury/wound image dataset (e.g. ISIC skin lesion, wound care datasets).
"""

import os
import sys

# Ensure backend root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def train():
    print("=" * 60)
    print("Training EfficientNet-B0 for injury triage (4 classes)")
    print("Classes: 0=P1 Critical, 1=P2 Serious, 2=P3 Moderate, 3=P4 Minor")
    print("=" * 60)

    import numpy as np
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset
    import timm

    # ── Synthetic training data ────────────────────────────────
    # In production: replace with real labelled injury images.
    n_samples = 800
    print(f"\nGenerating {n_samples} synthetic training samples...")

    torch.manual_seed(42)
    np.random.seed(42)

    # Simulate class-imbalanced distribution (mirrors real-world crash data)
    # P1: 15%, P2: 30%, P3: 35%, P4: 20%
    class_probs = [0.15, 0.30, 0.35, 0.20]
    labels = np.random.choice(4, size=n_samples, p=class_probs)
    X = torch.randn(n_samples, 3, 224, 224)
    y = torch.tensor(labels, dtype=torch.long)

    # ── Model setup ────────────────────────────────────────────
    model = timm.create_model("efficientnet_b0", pretrained=True, num_classes=4)

    # Freeze backbone — only train the classifier head
    for name, param in model.named_parameters():
        if "classifier" not in name:
            param.requires_grad = False

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Trainable parameters: {trainable:,}")

    # ── Training ───────────────────────────────────────────────
    dataset   = TensorDataset(X, y)
    loader    = DataLoader(dataset, batch_size=32, shuffle=True)
    optimizer = torch.optim.Adam(
        filter(lambda p: p.requires_grad, model.parameters()), lr=1e-3
    )
    criterion = nn.CrossEntropyLoss()

    model.train()
    n_epochs = 5
    for epoch in range(n_epochs):
        total_loss, correct, total = 0.0, 0, 0
        for Xb, yb in loader:
            optimizer.zero_grad()
            logits = model(Xb)
            loss   = criterion(logits, yb)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            preds   = logits.argmax(dim=1)
            correct += (preds == yb).sum().item()
            total   += len(yb)
        acc = 100 * correct / total
        print(
            f"Epoch {epoch + 1}/{n_epochs}  "
            f"loss: {total_loss / len(loader):.4f}  "
            f"acc: {acc:.1f}%"
        )

    # ── Save ───────────────────────────────────────────────────
    os.makedirs("models", exist_ok=True)
    out_path = "models/image_triage.pt"
    torch.save(model.state_dict(), out_path)
    print(f"\nSaved → backend/{out_path}")
    print("image_triage.py will load these weights on next server start.")


if __name__ == "__main__":
    train()
