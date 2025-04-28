import os
import requests
from urllib.parse import urlparse, parse_qs
from typing_extensions import Tuple

BASE_URL = "https://openreview.net"

def get_paper_links_via_api(limit: int = 1000) -> list:
    """
    通过 OpenReview API2 接口拉取 ICLR 2025 Oral Presentation 的所有 note，
    并返回对应的 /forum?id=… 链接列表。
    """
    API = "https://api2.openreview.net/notes"
    params = {
        "content.venue": "ICLR 2025 Oral",
        "domain": "ICLR.cc/2025/Conference",
        "details": "replyCount,presentation,writable",
        "limit": limit,
        "offset": 0
    }

    links = []
    while True:
        resp = requests.get(API, params=params)
        resp.raise_for_status()
        data = resp.json()
        notes = data.get("notes", [])
        if not notes:
            break

        for note in notes:
            # 有时 id 字段直接就是 forum id
            paper_id = note.get("id") or note.get("forum")
            if paper_id:
                links.append(f"{BASE_URL}/forum?id={paper_id}")

        # 翻页
        params["offset"] += limit

    return links

def download_pdf_bytes(paper_url: str) -> Tuple[str, bytes]:
    """
    给定论文 forum URL，下载对应的 PDF。
    返回 (paper_id, pdf_bytes)。
    """
    parsed = urlparse(paper_url)
    query = parse_qs(parsed.query)
    paper_id = query.get('id', [None])[0]
    if not paper_id:
        raise ValueError(f"无法从 URL 中解析出 paper id：{paper_url}")
    pdf_url = f"{BASE_URL}/pdf?id={paper_id}"
    resp = requests.get(pdf_url)
    resp.raise_for_status()
    return paper_id, resp.content



if __name__ == "__main__":
    def main(output_dir: str):
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)

        # 获取所有论文链接
        print("正在通过 OpenReview API 拉取 Oral 论文列表…")
        links = get_paper_links_via_api()
        print(f"共找到 {len(links)} 篇 Oral 论文链接。\n")

        # 逐篇下载 PDF
        for url in links:
            try:
                paper_id, pdf_bytes = download_pdf_bytes(url)
                filename = os.path.join(output_dir, f"{paper_id}.pdf")
                with open(filename, "wb") as f:
                    f.write(pdf_bytes)
                print(f"[✓] 已保存 {paper_id}.pdf")
            except Exception as e:
                print(f"[✗] 下载失败 {url} ：{e}")
    import argparse

    parser = argparse.ArgumentParser(
        description="抓取 ICLR 2025 接受（Oral）论文并保存 PDF（通过 OpenReview API）"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./iclr2025_oral_papers",
        help="PDF dir"
    )
    args = parser.parse_args()

    main(args.output_dir)
