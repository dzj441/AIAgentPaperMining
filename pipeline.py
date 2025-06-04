import argparse
import asyncio # 导入 asyncio
import time # 用于计时
import logging # 用于日志记录
import requests # 用来检测是否为国外网站
from utils import load_config, save_json # 确保 save_json 被导入
from scraper import OpenReviewScraper
from PDFparser import PdfLinkExtractor
# 导入 urlchecker 的接口
from urlchecker.main import check_url_is_dataset #, check_url_likely_dataset
import urllib3

# 设置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- (可选) 初步过滤的辅助函数 ---
# 定义一些可能需要保留的域（除了 skip_domains 之外）
# 可以根据需要扩展这个列表
PRELIMINARY_KEEP_DOMAINS = [
    "github.com",
    "gitlab.com",
    "github.io",
    "bitbucket.org",
    "hf.co", # huggingface.co 已经被替换为 hf-mirror.com, 但保留以防万一
    "huggingface.co",
    "hf-mirror.com",
    "google.com/drive", # Google Drive
    "dropbox.com",
    "zenodo.org",
    "figshare.com",
    "kaggle.com/datasets",
    "corpus",
    "Corpus",
    "archive.ics.uci.edu/dataset/",
    "archive.ics.uci.edu/datasets",
    "mkl.ucsd.edu/dataset/",
    "mkl.ucsd.edu/datasets",
    "archive.ics.uci.edu/dataset"
]

def preliminary_filter(url: str, skip_domains: list) -> bool:
    """对 URL 进行快速初步过滤，返回 True 表示可能需要进一步检查，False 表示可以跳过"""
    # 1. 如果 URL 在 skip_domains 中，直接跳过 (这个已在 PdfLinkExtractor 中处理，但双重检查无害)
    if any(skip in url for skip in skip_domains):
        return False
    # 2. 如果 URL 包含常见的代码/数据托管平台域名，保留
    if any(keep in url for keep in PRELIMINARY_KEEP_DOMAINS):
        return True
    # 3. (更宽松的规则) 如果 URL 包含 'dataset', 'code', 'repo', 'github', 'data' 等关键词，也暂时保留
    keywords = ["dataset", "code", "repo", "github", "data", "download", "model", "pretrained","hf-mirror"]
    if any(keyword in url.lower() for keyword in keywords):
         return True
    # 4. 其他情况，暂时跳过（可以调整此逻辑）
    logger.debug(f"初步过滤跳过 URL: {url}")
    return True

def is_blacklisted(url: str, skip_domains: list) -> bool:
    """
    返回 True 表示该 URL 命中"黑名单"，可以直接跳过；
    skip_domains 里是你在配置里读进来的、所有需要跳过的域名片段。
    """
    lower = url.lower()
    for skip in skip_domains:
        if skip in lower:
            return True
    return False


def is_whitelisted(url: str,keep_domains: list) -> bool:
    """
    返回 True 表示该 URL 命中"白名单"，可以直接当成数据集链接，不用再让 Agent 判断。
    """
    lower = url.lower()
    for keep in keep_domains:
        if keep in lower:
            return True
    return False

class MiningPipeline:
    """
    挖掘流程：(可选抓取PDF) -> 提取链接 -> 调用 Agent 检查链接 -> 输出结果
    """
    def __init__(self, config_path: str):
        cfg = load_config(config_path)
        scraper_cfg = cfg.get("scraper", {})
        parser_cfg = cfg.get("PDFparser", {})
        self.agent_cfg = cfg.get("agent", {})

        # 抓取器初始化保持不变
        self.scraper = OpenReviewScraper(
            pdf_dir=scraper_cfg.get("pdf_dir"),
            json_dir=scraper_cfg.get("json_dir"),
            headless=scraper_cfg.get("headless", True)
        )

        # 提取器初始化保持不变
        self.extractor = PdfLinkExtractor(
            pdf_root_dir=scraper_cfg.get("pdf_dir"), 
            output_file=parser_cfg.get("output_path"),
            flatten=parser_cfg.get("flatten", True),
            skip_domains=parser_cfg.get("skip_domains",None), # 获取 skip_domains 用于初步过滤
            replacements=parser_cfg.get("replacements",None)
        )
        # 保存 skip_domains 列表以供后续使用
        self.skip_domains = self.extractor.skip_domains

    # 将 run 方法改为异步
    async def run(self, urls: list):
        start_time = time.time()
        
        final_output_data = [] # 用于存储最终的 [{paper_name: ..., links: [{url:..., thought:...}]}]

        # 步骤1: (可选) 抓取 PDF (当前默认不执行此步骤)
        # logger.info("[Pipeline] 开始抓取 PDF")
        # self.scraper.run(urls) 

        # 步骤2: 从 PDF 提取论文名和链接
        logger.info("[Pipeline] 开始从 PDF 提取论文名和链接...")
        # self.extractor.run() 现在返回 List[Dict[str, Any]]
        # 每个字典是 {'paper_name': '...', 'extracted_links': ['url1', 'url2', ...]}
        papers_with_extracted_links = self.extractor.run()
        
        if not papers_with_extracted_links:
            logger.info("[Pipeline] 未从 PDF 提取到任何论文或链接，流程结束。")
            return

        logger.info(f"[Pipeline] 从 PDF 共提取到 {len(papers_with_extracted_links)} 篇论文的链接信息。")

        # 遍历每篇论文及其提取的链接
        for paper_data in papers_with_extracted_links:
            paper_name = paper_data.get("paper_name", "未知论文")
            extracted_urls_for_paper = paper_data.get("extracted_links", [])

            if not extracted_urls_for_paper:
                logger.info(f"[Pipeline] 论文 '{paper_name}' 未提取到链接，跳过。")
                continue

            logger.info(f"[Pipeline] 开始处理论文: '{paper_name}'，包含 {len(extracted_urls_for_paper)} 个初步链接。")
            
            current_paper_confirmed_links = [] # 存储当前论文确认的链接及其 thought

            # 步骤3: 初步过滤链接 (黑/白名单)
            candidate_urls_for_paper = []
            blacklisted_count = 0
            whitelisted_count = 0

            for url in extracted_urls_for_paper:
                if is_blacklisted(url, self.agent_cfg.get("blacklist", [])):
                    blacklisted_count += 1
                    continue
                
                # 白名单逻辑：如果命中白名单，直接认为是有效链接，但目前没有 thought
                # 为了保持格式统一，可以给白名单链接一个默认的 thought
                if is_whitelisted(url, self.agent_cfg.get("whitelist", [])):
                    whitelisted_count += 1
                    current_paper_confirmed_links.append({"url": url, "thought": "通过白名单规则自动确认"})
                else:
                    candidate_urls_for_paper.append(url)
            
            logger.info(
                f"[Pipeline] 论文 '{paper_name}': 黑名单跳过 {blacklisted_count} 个；"
                f"白名单直接纳入 {whitelisted_count} 个；"
                f"{len(candidate_urls_for_paper)} 个待进一步判断。"
            )

            if not candidate_urls_for_paper and not whitelisted_count:
                logger.info(f"[Pipeline] 论文 '{paper_name}' 初步过滤后无候选链接，且无白名单命中。")
                # 如果这篇论文没有任何确认的链接（包括白名单），则不添加到最终输出
                # continue # 如果希望即使论文没有链接也输出空的 paper_name 条目，则注释掉此行
            
            # 步骤4: 连通性检查 (针对候选链接)
            urls_to_agent = []
            if candidate_urls_for_paper: # 仅当有候选链接时才进行连通性检查
                logger.info(f"[Pipeline] 论文 '{paper_name}': 开始对 {len(candidate_urls_for_paper)} 个候选链接进行连通性检查...")
                for url in candidate_urls_for_paper:
                    logger.info(f"正在验证连通性: {url}")
                    try:
                        # 增加 headers 模拟浏览器，减少被拒的可能性
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                        }
                        response = requests.get(url, timeout=10, headers=headers, allow_redirects=True)
                        # if response.status_code == 200:
                        urls_to_agent.append(url) # 更宽松的可连接性检测条件
                        # else:
                        #     logger.warning(f"请求非200状态 ({response.status_code})，丢弃: {url}")
                    except requests.exceptions.Timeout:
                        logger.warning(f"请求超时 (Timeout)，丢弃: {url}")
                    except requests.exceptions.RequestException as e:
                        logger.warning(f"请求异常 ({type(e).__name__}) 丢弃: {url}；异常: {e}")
                
                logger.info(f"[Pipeline] 论文 '{paper_name}': 连通性检查完成，{len(urls_to_agent)} 个 URL 供 Agent 进一步判断。")

            # 步骤5: 调用 urlchecker Agent 进行检查 (针对通过连通性检查的链接)
            if urls_to_agent:
                logger.info(f"[Pipeline] 论文 '{paper_name}': 开始顺序调用 Agent 检查 {len(urls_to_agent)} 个链接...")
                
                for url in urls_to_agent:
                    logger.info(f"[Pipeline] 论文 '{paper_name}' 正在检查 URL: {url}")
                    try:
                        # check_url_is_dataset 现在返回 (status, thought)
                        status, thought = await check_url_is_dataset(url)
                        
                        if status == "YES":
                            logger.info(f"[Agent确认✅] URL: {url} -> YES. Thought: {thought}")
                            current_paper_confirmed_links.append({"url": url, "thought": thought if thought else "Agent确认，但未提供明确思考过程"})
                        elif status == "NO":
                            logger.info(f"[Agent确认❌] URL: {url} -> NO.")
                        else: # 处理 Error 情况
                            logger.warning(f"[Agent检查警告/错误] URL: {url}, 返回状态: {status}")
                            
                    except Exception as e:
                        logger.error(f"[Agent检查严重错误] URL: {url} 在调用 check_url_is_dataset 时发生异常: {e}")
                    # await asyncio.sleep(1) # 可选的延时
            
            # 步骤6: 处理当前论文的结果并准备添加到最终输出
            if current_paper_confirmed_links:
                # 进行域名反向替换
                restored_links_for_paper = []
                reverse_replacements = self.agent_cfg.get("reverse_replacements",{})
                for link_info in current_paper_confirmed_links:
                    restored_url = link_info["url"]
                    for src, tgt in reverse_replacements.items():
                        if src in restored_url:
                            restored_url = restored_url.replace(src, tgt)
                    restored_links_for_paper.append({"url": restored_url, "thought": link_info["thought"]})
                
                final_output_data.append({
                    "paper_name": paper_name,
                    "links": restored_links_for_paper
                })
                logger.info(f"[Pipeline] 论文 '{paper_name}' 处理完成，找到 {len(restored_links_for_paper)} 个确认的链接。")
            else:
                logger.info(f"[Pipeline] 论文 '{paper_name}' 未找到任何确认的数据集/代码链接。")

        # 步骤7: 保存最终的 JSON 数据
        end_time = time.time()
        logger.info(f"[Pipeline] 所有论文处理完成。总耗时: {end_time - start_time:.2f} 秒。")
        
        if final_output_data:
            output_json_path = self.agent_cfg.get("final_json_name", "final_dataset_urls.json")
            try:
                save_json(output_json_path, final_output_data) # 使用 utils 中的 save_json
                logger.info(f"已将所有确认的链接（按论文组织并包含思考过程）保存到: {output_json_path}")
                
                # 打印到控制台以方便查看
                print("\n--- 最终确认的数据集/代码链接 (按论文组织) ---")
                for paper_entry in final_output_data:
                    print(f"\n论文: {paper_entry['paper_name']}")
                    if paper_entry['links']:
                        for link_detail in paper_entry['links']:
                            print(f"  - URL: {link_detail['url']}")
                            print(f"    Thought: {link_detail['thought']}")
                    else:
                        print("  (此论文没有找到确认的链接)")
                        
            except Exception as e:
                logger.error(f"保存最终 JSON 文件 '{output_json_path}' 时发生错误: {e}")
        else:
            logger.info("[Pipeline] 未找到任何论文的任何确认链接，不生成输出文件。")
            print("\n未找到确认的数据集/代码链接。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="论文挖掘 Pipeline：提取 PDF 链接 -> Agent 检查 -> 输出确认的链接"
    )
    parser.add_argument(
        "urls",
        nargs="*",
        default=[
            "https://openreview.net/group?id=ICML.cc/2024/Conference#tab-accept-spotlight",
            # "https://openreview.net/group?id=ICLR.cc/2025/Conference#tab-accept-oral",
            # "https://openreview.net/group?id=ICLR.cc/2025/Conference#tab-accept-spotlight",
            #"https://openreview.net/group?id=ICLR.cc/2025/Conference#tab-accept-poster"
        ],
        help="要抓取的 OpenReview 页面 URL 列表 (当前抓取功能未启用)"
    )
            # more testcases
            # "https://openreview.net/group?id=ICLR.cc/2025/Conference#tab-accept-oral",
            # "https://openreview.net/group?id=ICLR.cc/2025/Conference#tab-accept-spotlight",
            # "https://openreview.net/group?id=ICLR.cc/2025/Conference#tab-accept-poster",
            # "https://openreview.net/group?id=NeurIPS.cc/2024/Conference#tab-accept-oral",
            # "https://openreview.net/group?id=NeurIPS.cc/2024/Conference#tab-accept-spotlight",
            # "https://openreview.net/group?id=NeurIPS.cc/2024/Conference#tab-accept-poster",
            # "https://openreview.net/group?id=ICML.cc/2024/Conference#tab-accept-oral",
            # "https://openreview.net/group?id=ICML.cc/2024/Conference#tab-accept-spotlight",
            # "https://openreview.net/group?id=ICML.cc/2024/Conference#tab-accept-poster"  
              
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="YAML 配置文件路径"
    )
    args = parser.parse_args()

    # 确保 urlchecker 的依赖和 Playwright 已安装
    # (urlchecker/main.py 中已有自动检查和尝试安装逻辑)
    logger.info("确保 urlchecker 依赖和 Playwright 浏览器已准备就绪...")

    pipeline = MiningPipeline(config_path=args.config)
    
    # 使用 asyncio.run() 运行异步的 run 方法
    try:
        asyncio.run(pipeline.run(args.urls))
    except Exception as e:
        logger.exception(f"Pipeline 运行时发生未处理的异常: {e}")
