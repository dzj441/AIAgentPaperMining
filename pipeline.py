import argparse

from utils import load_config
from scraper import OpenReviewScraper
from PDFparser import PdfLinkExtractor


class MiningPipeline:
    """
    挖掘流程：先使用 OpenReviewScraper 抓取指定会议页面的论文 PDF，
    然后使用 PdfLinkExtractor 对下载好的 PDF 进行链接提取。
    """
    def __init__(self, config_path: str):
        # 加载 YAML 配置
        cfg = load_config(config_path)
        scraper_cfg = cfg.get("scraper", {})
        parser_cfg = cfg.get("PDFparser", {})

        # 初始化抓取器
        self.scraper = OpenReviewScraper(
            pdf_dir=scraper_cfg.get("pdf_dir"),
            json_dir=scraper_cfg.get("json_dir"),
            headless=scraper_cfg.get("headless", True)
        )

        # 初始化链接提取器
        self.extractor = PdfLinkExtractor(
            pdf_root_dir=scraper_cfg.get("pdf_dir"),
            output_file=parser_cfg.get("output_path"),
            flatten=parser_cfg.get("flatten", True),
            skip_domains=parser_cfg.get("skip_domains",None),
            replacements=parser_cfg.get("replacements",None)
        )

    def run(self, urls: list):
        # 第一步：抓取 PDF
        print("[Pipeline] 开始抓取 PDF")
        # self.scraper.run(urls)

        # 第二步：提取链接
        print("[Pipeline] 开始提取链接")
        self.extractor.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="mining pipeline：先抓 PDF，再提取 PDF 中的链接"
    )
    parser.add_argument(
        "urls",
        nargs="*",
        default=[
            "https://openreview.net/group?id=ICLR.cc/2025/Conference#tab-accept-oral",
            "https://openreview.net/group?id=ICLR.cc/2025/Conference#tab-accept-spotlight",
            "https://openreview.net/group?id=ICLR.cc/2025/Conference#tab-accept-poster"
        ],
        help="要抓取的 OpenReview 页面 URL 列表"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="YAML 配置文件路径"
    )
    args = parser.parse_args()

    pipeline = MiningPipeline(config_path=args.config)
    pipeline.run(args.urls)
