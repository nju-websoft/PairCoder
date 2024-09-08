import logging
import os

import litellm
import openai
from aiolimiter import AsyncLimiter
from litellm import acompletion
from litellm import embedding
from litellm import RateLimitError
from litellm.exceptions import APIError
from retry import retry

from settings.config_loader import get_settings
from log import get_logger

logger = get_logger(__name__)
OPENAI_RETRIES = 5


class AiHandler:
    """
    This class handles interactions with the OpenAI API for chat completions.
    It initializes the API key and other settings from a configuration file,
    and provides a method for performing chat completions using the OpenAI ChatCompletion API.
    """

    def __init__(self):
        """
        Initializes the OpenAI API key and other settings from a configuration file.
        Raises a ValueError if the OpenAI key is missing.
        """
        self.limiter = AsyncLimiter(get_settings().config.max_requests_per_minute)
        try:
            if "gpt" in get_settings().get("config.model").lower() or \
                "text" in get_settings().get("config.embedding_model").lower():
                openai.api_key = get_settings().openai.key
                litellm.openai_key = get_settings().openai.key
        except AttributeError as e:
            raise ValueError("OpenAI key is required") from e


    @retry(
        exceptions=(AttributeError, RateLimitError),
        tries=OPENAI_RETRIES,
        delay=2,
        backoff=2,
        jitter=(1, 3),
    )
    async def chat_completion(
            self, model: str,
            system: str,
            user: str,
            temperature: float = 0.2,
            frequency_penalty: float = 0.0,
            n: int = 1,
            top_p: float = 1.0
    ):
        try:
            if get_settings().config.verbosity_level >= 2:
                logging.debug(
                    f"Generating completion with {model}"
                )

            async with self.limiter:
                logger.info("-----------------")
                logger.info("Running inference ...")
                logger.debug(f"system:\n{system}")
                logger.debug(f"user:\n{user}")
                response = await acompletion(
                    model=model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    temperature=temperature,
                    frequency_penalty=frequency_penalty,
                    n = n, 
                    top_p=top_p,
                    force_timeout=get_settings().config.ai_timeout,
                )
        except (APIError) as e:
            logging.error("Error during OpenAI inference")
            raise
        except RateLimitError as e:
            logging.error("Rate limit error during OpenAI inference")
            raise
        except Exception as e:
            logging.error("Unknown error during OpenAI inference: ", e)
            raise APIError from e
        if response is None or len(response["choices"]) == 0:
            raise APIError
        
        if len(response["choices"]) == 1:
            resp = response["choices"][0]["message"]["content"]
            finish_reason = response["choices"][0]["finish_reason"]
        else:
            resp = [choice["message"]["content"] for choice in response["choices"]]
            finish_reason = [choice["finish_reason"] for choice in response["choices"]]
        logger.debug(f"response:\n{resp}")
        logger.info('done')
        logger.info("-----------------")
        return resp, finish_reason

    def text_embedding(
            self, model: str,
            texts: list[str],
    ):
        logger.info("-----------------")
        logger.info(f"Generating embeddings with {model}")
        try:
            embeddings = embedding(
                model = model, 
                input = texts,
            )
        except (APIError) as e:
            logging.error("Error during OpenAI inference")
            raise
        except RateLimitError as e:
            logging.error("Rate limit error during OpenAI inference")
            raise
        except Exception as e:
            logging.error("Unknown error during OpenAI inference: ", e)
            raise APIError from e
        if embeddings is None or len(embeddings["data"]) == 0:
            raise APIError
        logger.info('done')
        logger.info("-----------------")
        return embeddings
    
if __name__ == '__main__':
    def dict_to_string(solution_dict):
        string = ""
        for key, value in solution_dict.items():
            if isinstance(value, list):
                value = ', '.join(value)
            string += f"{key}: {value}\n"
        return string
    import json
    from sklearn.cluster import KMeans
    import numpy as np
    with open('bbbbb.json', 'r') as f:
        data = json.load(f)
    
    str_list = [dict_to_string(solution_dict) for solution_dict in data]
    ai_handler = AiHandler()
    model = get_settings().config.embedding_model
    num_clusters = get_settings().possible_solutions.num_clusters
    response = ai_handler.text_embedding(
        model = model, 
        texts = str_list
    )
    embeddings = [e['embedding'] for e in response['data']]
    embeddings = np.array(embeddings)
    kmeans = KMeans(n_clusters=num_clusters)
    kmeans.fit(embeddings)
    cluster_centers = kmeans.cluster_centers_ 
    labels = kmeans.labels_ 
    representative_examples = []
    representative_indices = []
    for cluster_id in range(num_clusters):
        cluster_embeddings = embeddings[labels == cluster_id]
        cluster_texts = [str_list[i] for i, label in enumerate(labels) if label == cluster_id]
        distances = [np.linalg.norm(embedding - cluster_centers[cluster_id]) for embedding in cluster_embeddings]
        representative_index = np.argmin(distances)
        representative_example = cluster_texts[representative_index]
        representative_examples.append(representative_example)
        original_index = [i for i, label in enumerate(labels) if label == cluster_id][representative_index]
        representative_indices.append(original_index)