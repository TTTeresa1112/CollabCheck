"""全局配置：环境变量与常量。"""
import os
import datetime
from dotenv import load_dotenv

load_dotenv()

# 通过 .env 或环境变量配置
USER_EMAIL = os.getenv("USER_EMAIL", "teresa.l@explorationpub.com")
NCBI_API_KEY = os.getenv("NCBI_API_KEY", None)  # 提升 PubMed 请求限额
S2_API_KEY = os.getenv("S2_API_KEY", None)      # 缩短 Semantic Scholar 请求间隔

CURRENT_YEAR = datetime.datetime.now().year
START_YEAR = CURRENT_YEAR - 5

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'
}
