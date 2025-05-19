# main.py
import argparse
import asyncio
import logging
from pipeline import MiningPipeline

# 设置日志记录 (与 pipeline.py 保持一致)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# follow maybe follow such steps: 1. download into a dir; 2. open dir and get candidates 3. validate candidates via LLM and Heuristic rules 4. save to json
def main(args):
    # download_pdf(args)   
    logger.info("初始化 MiningPipeline...")
    pipeline = MiningPipeline(config_path=args.config)

    logger.info(f"开始运行挖掘流程，目标URL: {args.urls if args.urls else '将使用配置文件中的默认或不抓取新PDF'}")
    try:
        asyncio.run(pipeline.run(args.urls))
        logger.info("挖掘流程成功完成。")
    except Exception as e:
        logger.exception(f"Pipeline 运行时发生未处理的异常: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="论文挖掘 Pipeline：提取 PDF 链接 -> Agent 检查 -> 输出确认的链接")
    # parser.add_argument('--conference_url',default=" ",help='URL of the OpenReview conference')
    # parser.add_argument('--output_path',default='testresults/result.json' ,help='Path to save the JSON results')
    # parser.add_argument('--pdf_dir',default='toyPDFset',help='Path to save the downloaded PDFs')
    
    # 更新命令行参数以适应 Pipeline 的需求
    parser.add_argument(
        "urls",
        nargs="*", # 0个或多个URL
        default=[], # 默认不传递URL，pipeline将根据配置决定是否抓取
        help="可选：要抓取的 OpenReview 页面 URL 列表。如果未提供，将依赖配置文件中的设置或跳过抓取步骤。"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml", # 默认配置文件名
        help="YAML 配置文件路径 (默认: config.yaml)"
    )
    
    args = parser.parse_args()

    # 这条信息来自原 pipeline.py, 放在这里作为启动提示
    logger.info("确保 urlchecker 依赖和 Playwright 浏览器已准备就绪...")
    
    main(args)