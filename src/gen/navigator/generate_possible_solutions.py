import logging

from gen.utils import load_yaml, dict_to_yaml
from settings.config_loader import get_settings
from log import get_logger
from gen.utils import extract_code
logger = get_logger(__name__)


async def generate_possible_solutions(self, problem):
    counter_retry = 0
    while True:
        try:
            logger.info("--[NAVIGATOR] generate possible solutions stage--")
            if get_settings().get("solve.use_direct_solutions", False):
                return problem
            problem['max_num_of_possible_solutions'] = get_settings().get('possible_solutions.max_num_of_possible_solutions')
            problem['use_test_explanations_possible_solutions'] = get_settings().get('possible_solutions.use_test_explanations')
            problem['s_possible_solutions'] = []
            problem['s_possible_solutions_str'] = ''
            response_possible_solutions_list, _ = await self.send_inference(
                problem=problem, 
                prompt="prompt_navigator_generate_possible_solutions"
            )
            if isinstance(response_possible_solutions_list, str):
                response_possible_solutions = response_possible_solutions_list
                response_possible_solutions = extract_code(response_possible_solutions, 'yaml')
                response_possible_solutions = response_possible_solutions.rstrip("'` \n")
                if response_possible_solutions.startswith("```yaml"):
                    response_possible_solutions = response_possible_solutions[8:]
                if '```yaml' in response_possible_solutions:
                    response_possible_solutions = response_possible_solutions.replace('```yaml','').replace('```','')
                response_possible_solutions_yaml = load_yaml(response_possible_solutions,
                                                            keys_fix_yaml=["name:", "key_observations:", "content:", "why_it_works:", "labels:", "complexity:", "- "])
                problem['s_possible_solutions'] += response_possible_solutions_yaml['possible_solutions']
                problem['s_possible_solutions_str'] += response_possible_solutions.split('possible_solutions:')[1].strip()
                problem['representative_solutions'] = problem['s_possible_solutions']
                problem['solutions_details'] = [{'tried': False, 'attempts': []} for _ in range(len(problem['representative_solutions'] ))]
            else:
                for response_possible_solutions in response_possible_solutions_list:
                    response_possible_solutions = extract_code(response_possible_solutions, 'yaml')
                    response_possible_solutions = response_possible_solutions.rstrip("'` \n") 
                    if response_possible_solutions.startswith("```yaml"):
                        response_possible_solutions = response_possible_solutions[8:]
                    if '```yaml' in response_possible_solutions:
                        response_possible_solutions = response_possible_solutions.replace('```yaml','').replace('```','')
                    response_possible_solutions_yaml = load_yaml(response_possible_solutions,
                                                                keys_fix_yaml=["name:", "key_observations:", "content:", "why_it_works:", "labels:", "complexity:", "- "])

                    problem['s_possible_solutions'] += response_possible_solutions_yaml['possible_solutions']
                    problem['s_possible_solutions_str'] += response_possible_solutions.split('possible_solutions:')[1].strip()
                cluster_results = cluster(self, problem['s_possible_solutions'])
                problem['cluster_results'] = cluster_results
                problem['representative_solutions'] = [problem['s_possible_solutions'][cen] for cen, _ in cluster_results]
                problem['solutions_details'] = [{'tried': False, 'attempts': []} for _ in range(len(cluster_results))]
            return problem
        except Exception as e:
            logging.error(f"[NAVIGATOR] generate possible solutions stage, counter_retry {counter_retry}, Error: {e}")
            if response_possible_solutions:
                logging.info(f"Parsing the response may fail: {response_possible_solutions}")
            counter_retry += 1
            if counter_retry > 2:
                raise e


def cluster(self, results, method='kmeans', eps=0.5, min_samples=5):
    from sklearn.cluster import KMeans, AgglomerativeClustering, DBSCAN
    import numpy as np

    str_list = [dict_to_yaml(solution_dict) for solution_dict in results]
    model = get_settings().config.embedding_model
    response = self.ai_handler.text_embedding(
        model = model, 
        texts = str_list
    )
    embeddings = [e['embedding'] for e in response['data']]
    embeddings = np.array(embeddings)

    if method == 'kmeans':
        num_clusters = get_settings().possible_solutions.num_clusters
        logger.info(f"[NAVIGATOR] Using {method} method to cluster {len(str_list)} strings into {num_clusters} clusters")
        kmeans = KMeans(n_clusters=num_clusters)
        kmeans.fit(embeddings)
        cluster_centers = kmeans.cluster_centers_
        labels = kmeans.labels_
    elif method == 'hierarchical':
        clustering = AgglomerativeClustering(linkage='ward')
        clustering.fit(embeddings)
        labels = clustering.labels_
    elif method == 'dbscan':
        dbscan = DBSCAN(eps=eps, min_samples=min_samples)
        dbscan.fit(embeddings)
        labels = dbscan.labels_
    else:
        raise ValueError(f'Invalid clustering method: {method}')
    representative_indexs = []
    representative_examples_str = []
    cluster_indexs = {i: [] for i in range(num_clusters)}
    cluster_results = []
    for cluster_id in np.unique(labels):
        if method == 'dbscan' and cluster_id == -1:
            continue
        cluster_embeddings = embeddings[labels == cluster_id]
        cluster_texts = [str_list[i] for i, label in enumerate(labels) if label == cluster_id]
        if method == 'kmeans':
            cluster_center = cluster_centers[cluster_id]
        else:
            cluster_center = np.mean(cluster_embeddings, axis=0)
        distances = [np.linalg.norm(embedding - cluster_center) for embedding in cluster_embeddings]
        representative_index = np.argmin(distances)
        representative_example = cluster_texts[representative_index]
        representative_examples_str.append(representative_example)
        original_indexs = [i for i, label in enumerate(labels) if label == cluster_id]
        representative_original_index = original_indexs[representative_index]
        representative_indexs.append(representative_original_index)
        cluster_results.append([representative_original_index, original_indexs])
        cluster_indexs[cluster_id] = original_indexs

    return cluster_results