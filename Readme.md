



# RSS 文章收集与 PDF 生成工具

这个工具集用于从 RSS 源获取文章，存储到数据库，并生成高质量的 PDF 文件。它特别适合用于归档和离线阅读微信公众号等平台的文章。

## 功能特点

- 从 RSS 源获取文章内容
- 将文章存储到 SQLite 数据库
- 自动生成格式美观的 PDF 文件
- 支持图片下载和嵌入
- 自动添加标题、作者和发布时间信息
- 优化的中文字体和排版
- 支持断点续传和错误重试
- 防止重复文章的存储

## 目录结构

```
rss_tools/
├── fetch_rss.py       # RSS 获取模块
├── store_rss_db.py    # 数据库存储模块
├── html_to_pdf.py     # HTML 转 PDF 模块
├── config.py          # 配置文件
└── README.md          # 使用说明
```

## 安装依赖

```bash
pip install requests beautifulsoup4 pdfkit sqlite3
```

此外，还需要安装 wkhtmltopdf：

```bash
# Ubuntu/Debian
sudo apt-get install wkhtmltopdf

# CentOS/RHEL
sudo yum install wkhtmltopdf

# macOS
brew install wkhtmltopdf
```

## 使用方法

### 1. 获取并存储 RSS 文章

```python
from rss_tools.store_rss_db import fetch_store_and_process_rss

# 获取文章并生成 PDF
stored_count, processed_count = fetch_store_and_process_rss(
    feed_id="all",  # 指定 feed ID，"all" 表示所有源
    page_size=5,    # 获取的页数
    process_pdf=True  # 是否生成 PDF
)

print(f"成功存储 {stored_count} 条 RSS 条目，处理 {processed_count} 条为 PDF")
```

### 2. 仅获取 RSS 文章

```python
from rss_tools.fetch_rss import get_all_items

# 获取 RSS 条目
items = get_all_items(
    feed_id="all",  # 指定 feed ID
    title_include="关键词",  # 标题包含的关键词（可选）
    title_exclude="排除词",  # 标题排除的关键词（可选）
    page_size=1     # 获取的页数
)

print(f"获取到 {len(items)} 条 RSS 条目")
```

### 3. 仅处理未处理的 RSS 条目为 PDF

```python
from rss_tools.html_to_pdf import process_rss_to_pdf

# 处理未处理的 RSS 条目为 PDF
processed_count = process_rss_to_pdf(limit=10)  # 每次处理的最大条目数
print(f"成功处理 {processed_count} 条 RSS 条目为 PDF")
```

### 4. 获取 RSS 统计信息

```python
from rss_tools.store_rss_db import get_rss_stats

# 获取 RSS 统计信息
stats = get_rss_stats()
print(f"总条目数: {stats['total_count']}")

# 按账号分组的统计
for account, count in list(stats['by_account'].items())[:5]:
    print(f"  {account}: {count}条")

# 最近添加的条目
for item in stats['recent_items'][:3]:
    print(f"  {item['title']} ({item['account_name']})")
```

## 数据库结构

工具使用 SQLite 数据库存储文章信息，主要表结构为 `wechat_articles`，包含以下字段：

- `id`: 自增主键
- `message_id`: 消息 ID
- `from_user`: 发送者
- `title`: 标题
- `url`: URL 链接
- `content`: 内容
- `cover_url`: 封面图片 URL
- `pdf_path`: PDF 文件路径
- `images`: 图片列表 (JSON 格式)
- `created_at`: 创建时间
- `raw_data`: 原始数据 (JSON 格式)
- `processed`: 是否已处理
- `process_time`: 处理时间
- `account_name`: 账号名称
- `article_type`: 文章类型 (RSS)

## 关于 RSS 源

本工具使用 [WeWe RSS](https://github.com/cooderl/wewe-rss) 作为上游 RSS 源。WeWe RSS 是一个优雅的微信公众号订阅工具，支持私有化部署、微信公众号 RSS 生成（基于微信读书）。如果您需要更多功能，可以考虑直接部署 WeWe RSS。

## 注意事项

1. 确保有足够的磁盘空间存储 PDF 文件和图片
2. 对于大量文章的处理，建议分批进行以避免内存问题
3. 如果遇到数据库锁定问题，工具会自动重试
4. 中文字体渲染依赖系统安装的字体，确保系统中有 SimSun 和 Microsoft YaHei 字体

## 许可证

MIT
