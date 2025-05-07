import argparse
import asyncio # 导入 asyncio
import time # 用于计时
import logging # 用于日志记录
import requests # 用来检测是否为国外网站
from utils import load_config
from scraper import OpenReviewScraper
from PDFparser import PdfLinkExtractor
# 导入 urlchecker 的接口
from urlchecker.main import check_url_is_dataset, check_url_likely_dataset

# 设置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- (可选) 初步过滤的辅助函数 ---
# 定义一些可能需要保留的域（除了 skip_domains 之外）
# 可以根据需要扩展这个列表
PRELIMINARY_KEEP_DOMAINS = [
    "github.com",
    "gitlab.com",
    "bitbucket.org",
    "hf.co", # huggingface.co 已经被替换为 hf-mirror.com, 但保留以防万一
    "huggingface.co",
    "hf-mirror.com",
    "google.com/drive", # Google Drive
    "dropbox.com",
    "zenodo.org",
    "figshare.com",
    "paperswithcode.com/dataset",
    "kaggle.com/datasets"
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
    keywords = ["dataset", "code", "repo", "github", "data", "download", "model", "pretrained"]
    if any(keyword in url.lower() for keyword in keywords):
         return True
    # 4. 其他情况，暂时跳过（可以调整此逻辑）
    # logger.debug(f"初步过滤跳过 URL: {url}")
    return False

# --- 修改 MiningPipeline --- 
class MiningPipeline:
    """
    挖掘流程：(可选抓取PDF) -> 提取链接 -> 调用 Agent 检查链接 -> 输出结果
    """
    def __init__(self, config_path: str):
        cfg = load_config(config_path)
        scraper_cfg = cfg.get("scraper", {})
        parser_cfg = cfg.get("PDFparser", {})

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
        # 第一步：抓取 PDF (可选, 当前注释掉了)
        # logger.info("[Pipeline] 开始抓取 PDF")
        # self.scraper.run(urls)

        # 第二步：提取链接
        logger.info("[Pipeline] 开始从 PDF 提取链接...")
        extracted_urls = self.extractor.run() # 现在会返回列表
        logger.info(f"[Pipeline] 从 PDF 共提取到 {len(extracted_urls)} 个唯一链接。")

        if not extracted_urls:
            logger.info("[Pipeline] 未提取到任何链接，流程结束。")
            return

        # 第三步：初步过滤链接 (可选但推荐)
        logger.info("[Pipeline] 开始初步过滤链接...")
        candidate_urls = [url for url in extracted_urls if preliminary_filter(url, self.skip_domains)]
        logger.info(f"[Pipeline] 初步过滤后剩余 {len(candidate_urls)} 个候选链接需要 Agent 检查。")
        
        if not candidate_urls:
             logger.info("[Pipeline] 初步过滤后无候选链接，流程结束。")
             return
        
        # 第3.5步: 使用LLM粗选链接(应该返回url对应三种状态yes, no, maybe)
        # 使用网站链接测试来判断是否为国外网站,如果为国外网站算作maybe,其余算作yes或者no
        urls_maybe = []
        urls_yes_no = []
        for url in candidate_urls:
            logger.info(f"正在检测网址 {url}")
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    urls_yes_no.append(url)
                else:
                    urls_maybe.append(url)
            except requests.RequestException as e:
                print(f"连接 {url} 时出现错误: {e}")
        # 使用agent判断网址是否为数据集的网站
        logger.info(f"[Pipeline] 开始顺序调用 Agent 检查 {len(candidate_urls)} 个链接... (这可能需要一些时间)")
        urls_yes = []
        urls_no = []
        for url in urls_yes_no:
            logger.info(f"[Pipeline] 正在检查 URL: {url}")
            try:
                result = await check_url_is_dataset(url)
                if result == "YES":
                    urls_yes.append(url)
                elif result == "NO":
                    urls_no.append(url)
            except Exception as e:
                logger.error(f"[Agent检查严重错误] URL: {url} 在调用 check_url_is_dataset 时发生异常: {e}")
                urls_maybe.append(url)
        # 国内访问不了的url存放在urls_maybe, 判断是数据库网站的url存放在urls_yes, 判断不是数据库网址的url存放在urls_no

        # 第四步：调用 urlchecker Agent 进行检查 (改为顺序执行)
        logger.info(f"[Pipeline] 开始顺序调用 Agent 检查 {len(candidate_urls)} 个链接... (这可能需要一些时间)")
        
        results_map = {} # 用于存储 URL 和其结果的映射

        for url in candidate_urls:
            logger.info(f"[Pipeline] 正在检查 URL: {url}")
            try:
                result = await check_url_is_dataset(url)
                results_map[url] = result
            except Exception as e:
                logger.error(f"[Agent检查严重错误] URL: {url} 在调用 check_url_is_dataset 时发生异常: {e}")
                results_map[url] = e # 将异常本身存起来，以便后续识别
            # 可以在每个 URL 检查后稍作停顿，如果需要避免过于频繁的请求
            # await asyncio.sleep(1) # 例如，暂停1秒

        # 第五步：处理结果并输出
        dataset_urls = []
        error_count = 0
        no_count = 0
        # 现在遍历 results_map 来获取结果
        for url, result in results_map.items():
            if isinstance(result, Exception):
                # 之前已经在循环中记录过错误日志，这里只计数
                error_count += 1
            elif result == "YES":
                logger.info(f"[Agent确认✅] URL: {url} -> YES")
                dataset_urls.append(url)
            elif result == "NO":
                 logger.info(f"[Agent确认❌] URL: {url} -> NO")
                 no_count += 1
            else: # 处理 check_url_is_dataset 返回的 "Error: ..." 字符串
                logger.warning(f"[Agent检查警告/错误] URL: {url}, 返回: {result}")
                error_count += 1 # 将非 YES/NO 的明确返回也视为错误

        end_time = time.time()
        logger.info(f"[Pipeline] Agent 检查完成。耗时: {end_time - start_time:.2f} 秒。")
        logger.info(f"--- 最终结果 --- ({len(dataset_urls)} 个确认的链接)")
        logger.info(f"确认 YES: {len(dataset_urls)}, 确认 NO: {no_count}, 出错/未明确: {error_count}")
        
        if dataset_urls:
            print("\n确认的数据集/代码链接:")
            for url in dataset_urls:
                print(f"- {url}")
            # TODO: 可以选择将 dataset_urls 保存到文件，例如使用 utils.save_json
            from utils import save_json
            output_json_path = "final_dataset_links.json"
            save_json(output_json_path, dataset_urls)
            logger.info(f"已将确认的链接保存到: {output_json_path}")
        else:
            print("\n未找到确认的数据集/代码链接。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="论文挖掘 Pipeline：提取 PDF 链接 -> Agent 检查 -> 输出确认的链接"
    )
    parser.add_argument(
        "urls",
        nargs="*",
        default=[
            "https://openreview.net/group?id=ICLR.cc/2025/Conference#tab-accept-oral",
            "https://openreview.net/group?id=ICLR.cc/2025/Conference#tab-accept-spotlight",
            #"https://openreview.net/group?id=ICLR.cc/2025/Conference#tab-accept-poster"
        ],
        help="要抓取的 OpenReview 页面 URL 列表 (当前抓取功能未启用)"
    )
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
