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

    def get_paper_links_via_api(self, limit: int = 1000) -> list:
        """
        使用 OpenReview API2 拉取 ICLR 2025 Oral Presentation 的所有 note，
        返回对应的 /forum?id=… 链接列表。
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
                paper_id = note.get("id") or note.get("forum")
                if paper_id:
                    links.append(f"{self.BASE_URL}/forum?id={paper_id}")

            params["offset"] += limit

        return links

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

    def download_pdf(self, url: str) -> str:
        paper_id, pdf_bytes = self.download_pdf_bytes(url)
        filename = os.path.join(self.pdf_dir, f"{paper_id}.pdf")
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
                links = self.get_paper_links_via_selenium(page_url)
                print(f"共找到 {len(links)} 篇论文链接（已跳过失败页）。")

                with open(links_file, "w", encoding="utf-8") as f:
                    json.dump(links, f, ensure_ascii=False, indent=2)
                print(f"已将链接保存至：{links_file}")

            except Exception as e:
                print(f"[✗] 抓取链接失败：{e}")
                continue

            if not os.path.exists(links_file):
                print(f"[!] 未找到链接文件: {links_file}, 跳过")
                continue

            with open(links_file, "r", encoding="utf-8") as f:
                links = json.load(f)
            print(links)
            # 默认不下载 PDF，如需下载，可取消下面代码注释
            for link in links:
                try:
                    paper_id = self.download_pdf(link)
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
            "https://openreview.net/group?id=ICLR.cc/2025/Conference#tab-accept-poster"
        ],
        help=(
            "一个或多个 OpenReview group 页面 URL，"
            "如果不提供则使用默认 ICLR2025 accept-oral 页面"
        )
    )
    parser.add_argument(
        "--json-dir",
        type=str,
        default="./openreview_paper_links",
        help="json 保存挖掘到的 links"
    )
    parser.add_argument(
        "--pdf-dir",
        type=str,
        default="./openreview_papers",
        help="PDF 保存根目录"
    )
    args = parser.parse_args()

    scraper = OpenReviewScraper(args.pdf_dir, args.json_dir)
    scraper.run(args.urls)
