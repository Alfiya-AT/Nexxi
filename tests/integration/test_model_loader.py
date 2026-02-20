"""
tests/integration/test_model_loader.py

Integration tests for the model loader.
These tests mock the HuggingFace library to avoid downloading real models.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.utils.exceptions import ConfigurationError, ModelNotLoadedError


class TestModelLoader:
    def test_missing_hf_token_raises_config_error(self):
        """Missing HF_TOKEN should raise ConfigurationError."""
        import importlib
        import app.services.model_loader as loader

        # Reset singleton state
        loader._model = None
        loader._tokenizer = None

        with patch.dict("os.environ", {"HF_TOKEN": "", "HF_MODEL_NAME": "test/model"}):
            with pytest.raises(ConfigurationError, match="token"):
                loader.load_model()

    def test_missing_model_name_raises_config_error(self):
        """Missing HF_MODEL_NAME should raise ConfigurationError."""
        import app.services.model_loader as loader

        loader._model = None
        loader._tokenizer = None

        with patch.dict("os.environ", {"HF_TOKEN": "fake-token", "HF_MODEL_NAME": ""}):
            with pytest.raises(ConfigurationError, match="not specified"):
                loader.load_model(model_name=None)

    def test_get_model_before_load_raises(self):
        """Calling get_model() before load raises ModelNotLoadedError."""
        import app.services.model_loader as loader

        loader._model = None
        with pytest.raises(ModelNotLoadedError):
            loader.get_model()

    def test_device_resolution_prefers_gpu(self):
        """When CUDA is available, device should be 'cuda'."""
        from app.services.model_loader import _resolve_device

        with patch("app.services.model_loader.torch.cuda.is_available", return_value=True), \
             patch("app.services.model_loader.torch.cuda.get_device_name", return_value="A100"):
            device = _resolve_device("auto")
        assert device == "cuda"

    def test_get_model_name_strips_org_prefix(self):
        """get_model_name() should return only the model ID without org prefix."""
        import app.services.model_loader as loader

        loader._model_name = "mistralai/Mistral-7B-Instruct-v0.3"
        name = loader.get_model_name()
        assert name == "Mistral-7B-Instruct-v0.3"
        assert "mistralai" not in name
