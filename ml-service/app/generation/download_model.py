from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

from app.generation.service import generative_model_cache, generative_model_name


def main():
    model_name = generative_model_name()
    cache_dir = generative_model_cache()
    AutoTokenizer.from_pretrained(model_name, cache_dir=cache_dir, use_fast=False, legacy=False)
    AutoModelForSeq2SeqLM.from_pretrained(model_name, cache_dir=cache_dir)
    print(f"Предобученная генеративная модель {model_name} загружена в {cache_dir}", flush=True)


if __name__ == "__main__":
    main()
