import os
import time
import requests
from urllib.parse import urlparse, parse_qs
from typing_extensions import Tuple
import json

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException


class OpenReviewScraper:
    BASE_URL = "https://openreview.net"
    PDF_URL_TMPL = BASE_URL + "/pdf?id={paper_id}"

    def __init__(self, pdf_dir: str, json_dir: str, headless: bool = True):
        self.pdf_dir = pdf_dir
        self.json_dir = json_dir
        self.headless = headless
        os.makedirs(self.pdf_dir, exist_ok=True)
        os.makedirs(self.json_dir, exist_ok=True)

    def get_paper_links_via_api(self, page_url: str, limit: int = 1000) -> list:
        """
        使用 OpenReview API2 拉取指定 group 页面（如 ICLR 2025 Oral、NeurIPS 2024 Poster 等）的所有 note。
        对于分区名称（Oral/Spotlight/Poster）同时尝试 Title-case 和 lower-case，
        并将两次结果合并去重后返回。
        """
        # 1. 解析 URL
        parsed = urlparse(page_url)
        qs = parse_qs(parsed.query)
        group_id = qs.get("id", [""])[0]             # e.g. "ICLR.cc/2025/Conference"
        fragment = parsed.fragment                   # e.g. "tab-accept-oral"

        # 2. 拆出 conf、year
        parts = group_id.split('/')
        conf = parts[0].split('.')[0]                # "ICLR"
        year = parts[1] if len(parts) > 1 else ""     # "2025"

        # 3. 分区关键词
        suffix = fragment.split('-')[-1] if fragment else ""
        section_title = suffix.title()               # "Oral"
        section_lower = suffix.lower()               # "oral"

        # 4. 两种 venue 组合
        venue_options = [
            f"{conf} {year} {section_title}",
            f"{conf} {year} {section_lower}"
        ]

        api_url = "https://api2.openreview.net/notes"
        base_params = {
            "domain": group_id,
            "details": "replyCount,presentation,writable",
            "limit": limit
        }

        merged_links = []
        # 5. 对每个 venue 都分页拉取、累积
        for venue in venue_options:
            params = {**base_params, "content.venue": venue, "offset": 0}
            while True:
                resp = requests.get(api_url, params=params)
                resp.raise_for_status()
                data = resp.json()
                notes = data.get("notes", [])
                if not notes:
                    break
                for note in notes:
                    pid = note.get("id") or note.get("forum")
                    if pid:
                        merged_links.append(f"{self.BASE_URL}/forum?id={pid}")
                params["offset"] += limit

        # 6. 去重并保持原顺序
        return list(dict.fromkeys(merged_links))
    
    def download_pdf_bytes(self, paper_url: str) -> Tuple[str, bytes]:
        parsed = urlparse(paper_url)
        qs = parse_qs(parsed.query)
        paper_id = qs.get("id", [None])[0]
        if not paper_id:
            raise ValueError(f"无法从 URL 中解析出 paper id：{paper_url}")
        pdf_url = self.PDF_URL_TMPL.format(paper_id=paper_id)
        resp = requests.get(pdf_url)
        resp.raise_for_status()
        return paper_id, resp.content

    def download_pdf(self, url: str,save_subdir:str) -> str:
        paper_id, pdf_bytes = self.download_pdf_bytes(url)
        filename = os.path.join(self.pdf_dir,save_subdir ,f"{paper_id}.pdf")
        with open(filename, "wb") as f:
            f.write(pdf_bytes)
        return paper_id

    def setup_driver(self) -> webdriver.Chrome:
        opts = Options()
        if self.headless:
            opts.add_argument("--headless")
            opts.add_argument("--disable-gpu")
        return webdriver.Chrome(options=opts)

    def get_paper_links_via_selenium(self, page_url: str, timeout: int = 20, max_scrolls: int = 5) -> list:
        driver = self.setup_driver()
        try:
            driver.get(page_url)
            wait = WebDriverWait(driver, timeout)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/forum?id=']")))

            fragment = urlparse(page_url).fragment
            container_id = fragment.replace("tab-", "") if fragment.startswith("tab-") else fragment
            link_selector = f"#{container_id} a[href*='/forum?id=']"
            pagination_sel = f"#{container_id} > div > div > nav > ul"

            found_pagination = False
            for _ in range(max_scrolls):
                if driver.find_elements(By.CSS_SELECTOR, pagination_sel):
                    found_pagination = True
                    break
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(0.3)

            if not found_pagination:
                elems = driver.find_elements(By.CSS_SELECTOR, link_selector)
                all_links = [e.get_attribute("href") for e in elems if e.get_attribute("href")]
                print(f"[Info] 未检测到分页控件，仅抓取单页，共 {len(all_links)} 篇论文")
                return list(dict.fromkeys(all_links))

            all_links = []
            page_index = 1
            while True:
                elems = driver.find_elements(By.CSS_SELECTOR, link_selector)
                for e in elems:
                    href = e.get_attribute("href")
                    if href:
                        all_links.append(href)
                print(f"[Info] 第 {page_index} 页（#{container_id}）抓到 {len(elems)} 篇论文")

                try:
                    arrow = driver.find_element(
                        By.CSS_SELECTOR,
                        f"{pagination_sel} > li.right-arrow > a"
                    )
                except NoSuchElementException:
                    break

                for attempt in (1, 2):
                    try:
                        old_first = elems[0].get_attribute("href") if elems else None
                        driver.execute_script("arguments[0].scrollIntoView(true);", arrow)
                        time.sleep(0.3)
                        arrow.click()
                        time.sleep(1)
                        if old_first:
                            wait.until(lambda d: d.find_element(By.CSS_SELECTOR, link_selector)
                                             .get_attribute("href") != old_first)
                        else:
                            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, link_selector)))
                        break
                    except StaleElementReferenceException as e:
                        if attempt == 1:
                            time.sleep(0.5)
                            arrow = driver.find_element(
                                By.CSS_SELECTOR,
                                f"{pagination_sel} > li.right-arrow > a"
                            )
                            continue
                        else:
                            return list(dict.fromkeys(all_links))
                    except Exception:
                        return list(dict.fromkeys(all_links))

                page_index += 1
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)

            return list(dict.fromkeys(all_links))
        finally:
            driver.quit()

    def run(self, urls: list):
        for page_url in urls:
            print(f"\n▶ 处理页面：{page_url}")
            parsed = urlparse(page_url)
            group_id = parse_qs(parsed.query).get("id", ["unknown"])[0]
            fragment = parsed.fragment or ""
            subdir = group_id.replace("/", "_") + (f"_{fragment}" if fragment else "")
            target_dir = os.path.join(self.pdf_dir, subdir)
            os.makedirs(target_dir, exist_ok=True)

            links_file = os.path.join(self.json_dir, f"{subdir}.json")
            try:
                links = self.get_paper_links_via_api(page_url)
                if not links:
                    raise ValueError("API 返回空列表，尝试回退到 Selenium")
                print(f"[Info] API 获取到 {len(links)} 篇论文链接")
            except Exception as api_err:
                print(f"[Warn] API 方法失败：{api_err}\n[Info] 改用 Selenium 动态爬虫")
                try:
                    links = self.get_paper_links_via_selenium(page_url)
                    print(f"[Info] Selenium 获取到 {len(links)} 篇论文链接（已跳过失败页）。")
                except Exception as sel_err:
                    print(f"[✗] Selenium 方法也失败：{sel_err}，跳过该页面")
                    continue

            # 保存链接到 JSON
            with open(links_file, "w", encoding="utf-8") as f:
                json.dump(links, f, ensure_ascii=False, indent=2)
            print(f"已将链接保存至：{links_file}")

            if not os.path.exists(links_file):
                print(f"[!] 未找到链接文件: {links_file}, 跳过")
                continue

            with open(links_file, "r", encoding="utf-8") as f:
                links = json.load(f)
            # print(links)
            # 默认不下载 PDF，如需下载，可取消下面代码注释
            for link in links:
                try:
                    paper_id = self.download_pdf(link,save_subdir=subdir)
                    print(f"[✓] 已保存 {subdir}/{paper_id}.pdf")
                except Exception as e:
                    print(f"[✗] 下载失败 {link} ：{e}")
                    continue            


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Selenium 抓取任意 OpenReview group 页面中的所有论文 PDF（跳过抓取失败的页）"
    )
    parser.add_argument(
        "urls",
        nargs="*",
        default=[
            "https://openreview.net/group?id=ICLR.cc/2025/Conference#tab-accept-oral",
            "https://openreview.net/group?id=ICLR.cc/2025/Conference#tab-accept-spotlight",
            "https://openreview.net/group?id=ICLR.cc/2025/Conference#tab-accept-poster",
            "https://openreview.net/group?id=NeurIPS.cc/2024/Conference#tab-accept-oral",
            "https://openreview.net/group?id=NeurIPS.cc/2024/Conference#tab-accept-spotlight",
            "https://openreview.net/group?id=NeurIPS.cc/2024/Conference#tab-accept-poster",
            "https://openreview.net/group?id=ICML.cc/2024/Conference#tab-accept-oral",
            "https://openreview.net/group?id=ICML.cc/2024/Conference#tab-accept-spotlight",
            "https://openreview.net/group?id=ICML.cc/2024/Conference#tab-accept-poster"
        ],
        help=(
            "一个或多个 OpenReview group 页面 URL，"
            "如果不提供则使用默认 ICLR2025 accept-oral 页面"
        )
    )
    from utils import load_config
    config = load_config("config.yaml")
    args = parser.parse_args()

    scraper = OpenReviewScraper(config['scraper']['pdf_dir'], config['scraper']['json_dir'])
    scraper.run(args.urls)
