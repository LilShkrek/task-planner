import os

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer


DEFAULT_GENERATIVE_MODEL_NAME = "cointegrated/rut5-base-multitask"
DEFAULT_GENERATIVE_MODEL_CACHE = "/app/model-cache"
_GENERATOR = None


def generative_model_name():
    return os.getenv("GENERATIVE_MODEL_NAME", DEFAULT_GENERATIVE_MODEL_NAME)


def generative_model_cache():
    return os.getenv("GENERATIVE_MODEL_CACHE", DEFAULT_GENERATIVE_MODEL_CACHE)


def int_env(name, fallback):
    raw = os.getenv(name)
    if not raw:
        return fallback
    try:
        value = int(raw)
    except ValueError:
        return fallback
    return value if value > 0 else fallback


def get_text_generator():
    global _GENERATOR
    if _GENERATOR is None:
        _GENERATOR = NeuralTextGenerator()
    return _GENERATOR


class NeuralTextGenerator:
    def __init__(self, model_name=None, cache_dir=None):
        self.model_name = model_name or generative_model_name()
        self.cache_dir = cache_dir or generative_model_cache()
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            cache_dir=self.cache_dir,
            use_fast=False,
            legacy=False,
        )
        self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name, cache_dir=self.cache_dir)
        self.model.eval()
        self.max_input_tokens = int_env("GENERATIVE_MAX_INPUT_TOKENS", 384)
        self.max_new_tokens = int_env("GENERATIVE_MAX_NEW_TOKENS", 64)
        self.num_beams = int_env("GENERATIVE_NUM_BEAMS", 1)
        print(f"Загружена предобученная генеративная модель {self.model_name}", flush=True)

    def generate(self, prompt, max_chars=220):
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=self.max_input_tokens,
        )
        max_new_tokens = max(8, min(self.max_new_tokens, max_chars))

        try:
            with torch.no_grad():
                output_ids = self.model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    num_beams=self.num_beams,
                    do_sample=False,
                    no_repeat_ngram_size=0,
                    early_stopping=self.num_beams > 1,
                )
        except Exception as exc:
            raise RuntimeError(f"ошибка генеративной модели: {exc}") from exc

        return self.tokenizer.decode(output_ids[0], skip_special_tokens=True).strip()
