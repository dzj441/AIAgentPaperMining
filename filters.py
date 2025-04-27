# filter_links.py
import re
# Optional: import LLM chain if available
try:
    from langchain import OpenAI
    from langchain.chains import LLMChain
    from langchain.prompts import PromptTemplate

    llm = OpenAI(model_name="gpt-3.5-turbo", temperature=0)
    prompt = PromptTemplate(
        input_variables=["url"],
        template=(
            "The following URL comes from a research paper. "
            "Does it point to a dataset download page or an official code repository? "
            "Answer YES or NO.\nURL: {url}\nAnswer:"
        )
    )
    chain = LLMChain(llm=llm, prompt=prompt)
except Exception:
    chain = None

skip_domains = ["openreview.net/pdf", "arxiv.org", "doi.org", "ieee.org", 
                "aclweb.org", "springer.com", "dblp.org"]
keep_domains = ["github.com", "gitlab.com", "bitbucket.org",
                "kaggle.com", "huggingface.co", "zenodo.org",
                "figshare.com", "drive.google.com", "dropbox.com",
                "paperswithcode.com"]
keywords = ["dataset", "data", "benchmarks", "download"]
file_exts = [".zip", ".tar", ".gz", ".tgz"]

def is_dataset_or_code_link(url: str) -> bool:
    """Determine if URL likely points to a dataset or code repository."""
    low = url.lower()
    for dom in skip_domains:
        if dom in low:
            return False
    for dom in keep_domains:
        if dom in low:
            return True
    if chain:
        try:
            res = chain.run(url=url).strip().lower()
            return res.startswith("yes")
        except Exception:
            pass
    if any(ext in low for ext in file_exts):
        return True
    if any(kw in low for kw in keywords):
        return True
    return False
