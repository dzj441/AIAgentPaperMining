import os
import re
import time
import requests
from typing import List, Tuple

BASE_URL = "https://openreview.net"

def slugify(title: str) -> str:
    """
    将论文标题转为文件名安全的格式：  
    - 把非法字符（\/:*?"<>|）替换为下划线  
    - 空白字符替换为下划线  
    - 最多保留前 200 个字符
    """
    # 替换非法文件名字符
    safe = re.sub(r'[\\/:"*?<>|]+', '_', title)
    # 把所有空白折叠成单个下划线
    safe = re.sub(r'\s+', '_', safe)
    return safe[:200] or title

def get_papers_info(limit: int = 1000) -> List[Tuple[str, str]]:
    """
    通过 OpenReview API2 拉取所有 ICLR 2025 Oral Presentation 的 note，
    返回一个 (paper_id, title) 的列表。
    """
    API = "https://api2.openreview.net/notes"
    params = {
        "content.venue": "ICLR 2025 Oral",
        "domain": "ICLR.cc/2025/Conference",
        "details": "all",      # 拿到 note.content.title 等所有字段
        "limit": limit,
        "offset": 0
    }

    papers: List[Tuple[str, str]] = []
    while True:
        resp = requests.get(API, params=params)
        resp.raise_for_status()
        data = resp.json()
        notes = data.get("notes", [])
        if not notes:
            break

        for note in notes:
            paper_id = note.get("id") or note.get("forum")
            title = note.get("content", {}).get("title", paper_id)
            papers.append((paper_id, title))

        params["offset"] += limit

    return papers

def download_pdf_with_retry(paper_id: str, max_retries: int = 3) -> bytes:
    """
    下载单篇论文 PDF，遇到错误时最多重试 max_retries 次，采用指数退避。
    返回 PDF 的二进制内容；超过次数仍失败时返回 None。
    """
    pdf_url = f"{BASE_URL}/pdf?id={paper_id}"
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(pdf_url, timeout=60)
            resp.raise_for_status()
            return resp.content
        except Exception as e:
            print(f"[!] 第 {attempt} 次下载 {paper_id} 失败：{e}")
            if attempt < max_retries:
                wait = 2 ** (attempt - 1)
                print(f"    等待 {wait} 秒后重试…")
                time.sleep(wait)
            else:
                print(f"[✗] 超过 {max_retries} 次重试，跳过 {paper_id}")
                return None

def main(output_dir: str):
    os.makedirs(output_dir, exist_ok=True)

    print("拉取论文列表…")
    papers = get_papers_info()
    print(f"共找到 {len(papers)} 篇 Oral 论文。\n")

    for paper_id, title in papers:
        print(f"下载 {paper_id} —— “{title}”")
        pdf_bytes = download_pdf_with_retry(paper_id)
        if not pdf_bytes:
            continue

        filename = slugify(title) + ".pdf"
        path = os.path.join(output_dir, filename)
        with open(path, "wb") as f:
            f.write(pdf_bytes)
        print(f"[✓] 已保存 {path}")


'''
以上代码可能用来替换scraper.py中的内容，通过重试确保下载所有文章。
并且考虑使用论文名称来命名 论文的pdf 可能会在后续使用到。
'''