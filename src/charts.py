"""Figures for the report. Saved to out/."""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix

sys.path.insert(0, str(Path(__file__).parent.parent))
import config as cfg


def class_distribution(data, target="major") -> Path:
    fig, ax = plt.subplots(figsize=(9, 4.5))
    data[target].value_counts().sort_values().plot(
        kind="barh", ax=ax, color=cfg.PALETTE["accent"])
    ax.set_xlabel("incidents")
    ax.set_title("Severe workplace injuries by OIICS major event group\n"
                 "(OSHA, Jan 2015 - Sep 2023)")
    path = cfg.OUT / "fig_distribution.png"
    fig.tight_layout(); fig.savefig(path, dpi=160); plt.close(fig)
    return path


def confusion(y_true, y_pred) -> Path:
    labels = sorted(set(y_true))
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    norm = cm / cm.sum(axis=1, keepdims=True).clip(min=1)

    fig, ax = plt.subplots(figsize=(8.5, 7))
    im = ax.imshow(norm, cmap="Blues", vmin=0, vmax=1)
    short = [l[:34] for l in labels]
    ax.set_xticks(range(len(labels))); ax.set_xticklabels(short, rotation=40, ha="right", fontsize=8)
    ax.set_yticks(range(len(labels))); ax.set_yticklabels(short, fontsize=8)
    for i in range(len(labels)):
        for j in range(len(labels)):
            ax.text(j, i, f"{norm[i, j]:.2f}", ha="center", va="center", fontsize=7,
                    color="white" if norm[i, j] > 0.5 else "black")
    ax.set_xlabel("predicted"); ax.set_ylabel("actual")
    ax.set_title("Confusion matrix - OIICS major event group")
    fig.colorbar(im)
    path = cfg.OUT / "fig_confusion.png"
    fig.tight_layout(); fig.savefig(path, dpi=160); plt.close(fig)
    return path
