"""
Train XGBoost traffic congestion prediction model.
Run: python ml/train_model.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from preprocess import train_model

if __name__ == '__main__':
    train_model()
