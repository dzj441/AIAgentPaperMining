import json
import requests
from requests.exceptions import RequestException

#输入为目标json和基准json，分别计算召回率和有效链接率
def evaluate(test_json_path, standard_json_path):

    # 读取待测试和标准链接列表
    with open(test_json_path, 'r') as f:
        test_links = json.load(f)
    with open(standard_json_path, 'r') as f:
        standard_links = json.load(f)

    # 计算召回率
    standard_set = set(standard_links)
    test_set = set(test_links)
    overlap = len(test_set & standard_set)
    recall = overlap / len(standard_set) if len(standard_set) > 0 else 0.0
    print('召回率',recall)
    print('尝试计算有效链接,计算过程基于程序访问，可能被人机测试和反爬虫拦截')
    # 计算有效链接率
    valid_count = 0
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }

    for url in test_links:
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=5,
                allow_redirects=True
            )
            if response.ok:
                valid_count += 1
        except RequestException:
            pass

    effective_rate = valid_count / len(test_links) if len(test_links) > 0 else 0.0

    return {
        'recall': recall,
        'effective_rate': effective_rate
    }

result = evaluate(
    "d:/data_mining/AIAgentPaperMining/benchmark_markdown/final_dataset_links.json",
    "d:/data_mining/AIAgentPaperMining/benchmark_markdown/hand_dataset.json"
)
print(result)