import os
import pdfkit
import re
import sqlite3
import json
import time
from datetime import datetime
from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin

# PDF 存储路径
PDF_DIR = "/home/yy/project/Gewechat/vxbot/data/articles/pdfs"
DB_PATH = "/home/yy/project/Gewechat/vxbot/data/message_monitor.db"

# 确保PDF目录存在
os.makedirs(PDF_DIR, exist_ok=True)


def clean_html(html_content):
    """
    清理HTML内容，修复图片链接等
    """
    # 使用BeautifulSoup解析HTML
    soup = BeautifulSoup(html_content, 'html.parser')

    # 处理图片链接
    for img in soup.find_all('img'):
        src = img.get('src', '')
        if src and not src.startswith(('http://', 'https://')):
            # 如果是相对路径，可能需要转换为绝对路径
            # 这里假设所有图片都来自微信，使用一个通用的前缀
            img['src'] = src.replace(
                '//mmbiz.qpic.cn', 'https://mmbiz.qpic.cn')

    # 添加基本样式以改善PDF渲染
    style = soup.new_tag('style')
    style.string = """
        @font-face {
            font-family: 'SimSun';
            src: local('SimSun');
        }
        @font-face {
            font-family: 'Microsoft YaHei';
            src: local('Microsoft YaHei');
        }
        body { 
            font-family: 'Microsoft YaHei', 'SimSun', Arial, sans-serif; 
            margin: 20px;
            font-size: 16px;
            line-height: 1.8;
            text-align: justify;
            word-wrap: break-word;
            word-break: normal;
        }
        img { max-width: 100%; height: auto; }
        p { 
            line-height: 1.8; 
            margin-bottom: 15px; 
            text-align: justify;
            word-wrap: break-word;
            word-break: normal;
        }
        h1, h2, h3 { margin-top: 20px; }
        * {
            max-width: 100%;
            box-sizing: border-box;
        }
    """

    # 添加meta标签确保正确的字符编码
    meta = soup.new_tag('meta')
    meta['charset'] = 'UTF-8'

    # 添加viewport标签
    viewport = soup.new_tag('meta')
    viewport['name'] = 'viewport'
    viewport['content'] = 'width=device-width, initial-scale=1.0'

    if soup.head:
        soup.head.insert(0, meta)
        soup.head.insert(1, viewport)
        soup.head.append(style)
    else:
        head = soup.new_tag('head')
        head.insert(0, meta)
        head.insert(1, viewport)
        head.append(style)
        if soup.html:
            soup.html.insert(0, head)
        else:
            html = soup.new_tag('html')
            html.append(head)
            html.append(soup.body if soup.body else soup)
            soup = html

    # 修复文本内容的布局问题
    for p in soup.find_all(['p', 'div', 'span']):
        # 添加样式确保文本不会被截断
        if not p.get('style'):
            p['style'] = 'word-wrap: break-word; word-break: normal; text-align: justify;'
        else:
            p['style'] += '; word-wrap: break-word; word-break: normal; text-align: justify;'

    return str(soup)


def download_images(html_content, article_id):
    """
    下载HTML中的图片并替换为本地路径
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    img_dir = os.path.join(PDF_DIR, f"images_{article_id}")
    os.makedirs(img_dir, exist_ok=True)

    image_paths = []

    for i, img in enumerate(soup.find_all('img')):
        src = img.get('src', '')
        if not src:
            continue

        try:
            # 下载图片
            response = requests.get(src, timeout=10)
            if response.status_code == 200:
                # 确定图片扩展名
                content_type = response.headers.get('Content-Type', '')
                ext = '.jpg'  # 默认扩展名
                if 'png' in content_type:
                    ext = '.png'
                elif 'gif' in content_type:
                    ext = '.gif'
                elif 'jpeg' in content_type or 'jpg' in content_type:
                    ext = '.jpg'

                # 保存图片
                img_filename = f"img_{i}{ext}"
                img_path = os.path.join(img_dir, img_filename)
                with open(img_path, 'wb') as f:
                    f.write(response.content)

                # 替换HTML中的图片链接
                img['src'] = img_path

                # 记录图片路径
                image_paths.append(img_path)
        except Exception as e:
            print(f"下载图片失败: {src}, 错误: {e}")

    return str(soup), image_paths


def html_to_pdf(html_content, title, article_id, author="", date_modified=""):
    """
    将HTML内容转换为PDF

    参数:
    - html_content: HTML内容
    - title: 文章标题
    - article_id: 文章ID
    - author: 文章作者
    - date_modified: 文章修改时间

    返回:
    - PDF文件路径
    """
    # 清理文件名，移除不合法字符
    safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
    safe_title = safe_title[:50]  # 限制长度

    # 生成PDF文件名
    pdf_filename = f"{article_id}_{safe_title}.pdf"
    pdf_path = os.path.join(PDF_DIR, pdf_filename)

    # 清理和下载图片
    cleaned_html, image_paths = download_images(html_content, article_id)

    # 格式化日期
    formatted_date = ""
    if date_modified:
        try:
            # 尝试解析ISO格式的日期
            dt = datetime.fromisoformat(date_modified.replace('Z', '+00:00'))
            formatted_date = dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            formatted_date = date_modified

    # 添加标题、作者和日期到HTML内容的开头
    header_html = f"""
    <div style="text-align: center; margin-bottom: 30px; max-width: 100%; padding: 0 20px;">
        <h1 style="font-size: 24px; margin-bottom: 15px; word-wrap: break-word; line-height: 1.4;">{title}</h1>
        <div style="font-size: 16px; color: #666; margin-bottom: 8px; word-wrap: break-word;">
            {f'作者: {author}' if author else ''}
        </div>
        <div style="font-size: 14px; color: #999; word-wrap: break-word;">
            {f'发布时间: {formatted_date}' if formatted_date else ''}
        </div>
    </div>
    <hr style="margin-bottom: 25px; border: 0; border-top: 1px solid #ddd;">
    """

    # 在body标签后插入header_html
    if "<body>" in cleaned_html:
        cleaned_html = cleaned_html.replace("<body>", "<body>" + header_html)
    else:
        # 如果没有body标签，在开头添加header_html
        soup = BeautifulSoup(cleaned_html, 'html.parser')
        header_soup = BeautifulSoup(header_html, 'html.parser')
        if soup.body:
            soup.body.insert(0, header_soup)
        else:
            # 创建body标签
            body = soup.new_tag('body')
            body.append(header_soup)
            for tag in list(soup.contents):
                if tag.name != 'head' and tag.name != 'html':
                    body.append(tag)
            if soup.html:
                soup.html.append(body)
            else:
                html = soup.new_tag('html')
                html.append(body)
                soup = html
        cleaned_html = str(soup)

    # 确保HTML内容有正确的DOCTYPE和编码声明
    if not cleaned_html.startswith('<!DOCTYPE html>'):
        cleaned_html = '<!DOCTYPE html>\n<html>\n<head>\n<meta charset="UTF-8">\n</head>\n<body>\n' + \
            cleaned_html + '\n</body>\n</html>'

    # 将HTML内容保存到临时文件
    temp_html_path = os.path.join(PDF_DIR, f"temp_{article_id}.html")
    with open(temp_html_path, 'w', encoding='utf-8') as f:
        f.write(cleaned_html)

    # 配置pdfkit选项
    options = {
        'page-size': 'A4',
        'margin-top': '0.75in',
        'margin-right': '0.75in',
        'margin-bottom': '0.75in',
        'margin-left': '0.75in',
        'encoding': 'UTF-8',
        'no-outline': None,
        'enable-local-file-access': None,  # 允许访问本地文件
        '--enable-javascript': None,
        '--javascript-delay': '1000',
        '--no-stop-slow-scripts': None,
        '--zoom': '1.0',  # 设置缩放比例
        '--disable-smart-shrinking': None,  # 禁用智能缩小
        '--print-media-type': None,  # 使用打印媒体类型
        '--dpi': '300',  # 设置更高的DPI
        '--footer-right': '[page]/[topage]',  # 添加页码
        '--footer-font-size': '9'
    }

    try:
        # 从文件生成PDF而不是从字符串生成
        pdfkit.from_file(temp_html_path, pdf_path, options=options)
        print(f"PDF生成成功: {pdf_path}")

        # 清理临时文件
        os.remove(temp_html_path)

        return pdf_path, image_paths
    except Exception as e:
        print(f"生成PDF失败: {e}")
        # 清理临时文件
        if os.path.exists(temp_html_path):
            os.remove(temp_html_path)
        return None, []


def process_rss_to_pdf(db_path=DB_PATH, limit=10):
    """
    处理数据库中未处理的RSS条目，生成PDF

    参数:
    - db_path: 数据库路径
    - limit: 每次处理的最大条目数

    返回:
    - 成功处理的条目数
    """
    # 添加重试机制处理数据库锁定问题
    max_retries = 5
    retry_delay = 1  # 初始延迟1秒

    for attempt in range(max_retries):
        try:
            conn = sqlite3.connect(db_path, timeout=20)
            cursor = conn.cursor()

            # 查询未处理的RSS条目
            cursor.execute("""
                SELECT id, message_id, title, content, account_name, from_user, created_at, raw_data
                FROM wechat_articles
                WHERE article_type = 'RSS' AND processed = 0
                LIMIT ?
            """, (limit,))

            items = cursor.fetchall()
            processed_count = 0

            for item in items:
                article_id, message_id, title, content, account_name, from_user, created_at, raw_data = item

                if not content:
                    print(f"跳过无内容的文章: {title}")
                    # 标记为已处理，但不生成PDF
                    cursor.execute("""
                        UPDATE wechat_articles
                        SET processed = 1, process_time = ?
                        WHERE id = ?
                    """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), article_id))
                    processed_count += 1
                    continue

                print(f"处理文章: {title} ({account_name})")

                # 获取作者信息
                author = from_user or account_name

                # 获取日期信息
                date_modified = created_at

                # 尝试从raw_data中提取更多信息
                if raw_data:
                    try:
                        raw_data_json = json.loads(raw_data)
                        if not author and 'author' in raw_data_json:
                            if isinstance(raw_data_json['author'], dict) and 'name' in raw_data_json['author']:
                                author = raw_data_json['author']['name']
                            elif isinstance(raw_data_json['author'], str):
                                author = raw_data_json['author']

                        if not date_modified and 'date_modified' in raw_data_json:
                            date_modified = raw_data_json['date_modified']
                    except:
                        pass

                # 生成PDF
                pdf_path, image_paths = html_to_pdf(
                    content, title, article_id, author, date_modified)

                if pdf_path:
                    # 更新数据库
                    cursor.execute("""
                        UPDATE wechat_articles
                        SET processed = 1, process_time = ?, pdf_path = ?, images = ?
                        WHERE id = ?
                    """, (
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        pdf_path,
                        json.dumps(image_paths),
                        article_id
                    ))
                    processed_count += 1
                    print(f"已更新数据库: {title}")

                # 每处理一条提交一次，避免长事务
                conn.commit()

            conn.close()
            return processed_count

        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                print(f"数据库被锁定，尝试重试 ({attempt+1}/{max_retries})...")
                time.sleep(retry_delay)
                retry_delay *= 2  # 指数退避
                continue
            else:
                print(f"数据库错误: {e}")
                raise
        finally:
            # 确保连接被关闭
            if 'conn' in locals() and conn:
                try:
                    conn.close()
                except:
                    pass

    return 0  # 如果所有重试都失败


if __name__ == "__main__":
    # 处理未处理的RSS条目
    processed_count = process_rss_to_pdf(limit=5)
    print(f"成功处理 {processed_count} 条RSS条目")
