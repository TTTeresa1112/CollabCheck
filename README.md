# 🔍 CollabCheck

快速筛查两位作者之间是否存在共同发文，从而识别潜在的**利益冲突（Conflicts of Interest, COI）**。
基于 [Streamlit](https://streamlit.io) 构建的开源工具，自动检索多个学术数据库，聚合展示可能存在的合作论文。

> 本项目为开源版本，基于 MIT License 发布，欢迎使用、修改与贡献。

## 功能特性

- **多数据库检索**：自动查询 PubMed、OpenAlex、Crossref、Semantic Scholar、DOAJ 五个学术数据源
- **批量姓名比对**：支持一次输入多位作者，逐一交叉筛查
- **智能检索式生成**：为 Web of Science / Google Scholar 自动生成姓名检索式变体
- **结果聚合去重**：按 DOI / 标题合并重复结果，标注命中来源
- **模糊匹配**：基于 thefuzz 的作者名模糊匹配，降低拼写差异造成的漏检
- **会话历史**：保留本次会话的检索记录，可随时回看
- **并发保护**：内置搜索锁与冷却机制，避免高频请求被 API 限流

## 快速开始

需要 Python 3.9+。

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API 密钥（可选）

复制示例配置文件并填写你的密钥：

```bash
cp .env.example .env
```

各变量说明见 [配置说明](#配置说明)。不配置密钥也能运行，仅请求限额较低。

### 3. 启动应用

```bash
streamlit run web_app.py
```

浏览器访问 <http://localhost:8501> 即可使用。

## 配置说明

| 变量 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `USER_EMAIL` | 是 | - | 你的邮箱，NCBI / OpenAlex 等 API 要求提供联系方式 |
| `NCBI_API_KEY` | 否 | 无 | NCBI E-utilities 密钥，配置后 PubMed 请求限额提升至 10 次/秒 |
| `S2_API_KEY` | 否 | 无 | Semantic Scholar API 密钥，配置后请求间隔缩短至 1.1 秒 |

密钥获取方式：

- NCBI API Key：<https://www.ncbi.nlm.nih.gov/account/settings/>
- Semantic Scholar API Key：<https://www.semanticscholar.org/product/api>

## 使用方法

1. 在左侧 **Potential COI** 输入潜在利益相关方姓名，**Author(s)** 输入待查作者姓名，每行一位，格式：`名; 姓`（例如 `Nancy; Lane`）
2. 点击 **Start Search**
3. 在结果弹窗中查看命中的共同论文，可通过 DOI 跳转原文核验

## ⚠️ 免责声明

本工具基于多个学术数据库的**自动检索**，结果可能存在不精准、遗漏或误判，仅供初步筛查参考。
最终结论请以人工核查、论文原文及官方记录为准。

## 项目结构

```text
├── web_app.py            # 主应用（Streamlit）
├── requirements.txt      # Python 依赖
├── .env.example          # 环境变量配置示例
├── .gitignore            # 忽略 .env 等文件
├── LICENSE               # MIT 许可证
└── .devcontainer/        # 开发容器配置
```

## 许可证

[MIT License](LICENSE)
