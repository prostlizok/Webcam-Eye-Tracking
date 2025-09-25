from __future__ import annotations

import numpy as np
from sklearn.neural_network import MLPRegressor

from . import register_model
from .base import BaseModel


class EnhancedMLPModel(BaseModel):
    def __init__(
        self,
        *,
        hidden_layer_sizes: tuple[int, ...] = (128, 64, 32),
        activation: str = "relu",
        alpha: float = 5e-5,
        learning_rate_init: float = 5e-4,
        max_iter: int = 1000,
        early_stopping: bool = True,
        validation_fraction: float = 0.2,
    ) -> None:
        super().__init__()
        self._init_native(
            hidden_layer_sizes=hidden_layer_sizes,
            activation=activation,
            alpha=alpha,
            learning_rate_init=learning_rate_init,
            max_iter=max_iter,
            early_stopping=early_stopping,
            validation_fraction=validation_fraction,
        )

    def _init_native(self, **kw):
        self.model = MLPRegressor(
            solver="adam",
            batch_size="auto",
            random_state=0,
            verbose=False,
            **kw,
        )

    def _native_train(self, X, y):
        n_samples = X.shape[0]
        augmented_X = []
        augmented_y = []
        
        for i in range(n_samples):
            augmented_X.append(X[i])
            augmented_y.append(y[i])
            
            for _ in range(3):
                noise = np.random.normal(0, 0.01, X[i].shape)
                noisy_sample = X[i] + noise
                augmented_X.append(noisy_sample)
                augmented_y.append(y[i])
        
        augmented_X = np.array(augmented_X)
        augmented_y = np.array(augmented_y)
        
        self.model.fit(augmented_X, augmented_y)

    def _native_predict(self, X):
        return self.model.predict(X)


register_model("enhanced_mlp", EnhancedMLPModel) 