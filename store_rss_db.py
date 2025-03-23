import sqlite3
import json
from datetime import datetime
import time
from rss_tools.fetch_rss import get_all_items
from html_to_pdf import process_rss_to_pdf

DB_PATH = "/home/yy/project/Gewechat/vxbot/data/message_monitor.db"


def store_rss_items_to_db(items, db_path=DB_PATH):
    """
    将RSS条目存储到数据库中

    参数:
    - items: RSS条目列表
    - db_path: 数据库文件路径

    返回:
    - 成功存储的条目数量
    """
    # 添加重试机制处理数据库锁定问题
    max_retries = 5
    retry_delay = 1  # 初始延迟1秒

    for attempt in range(max_retries):
        try:
            conn = sqlite3.connect(db_path, timeout=20)  # 增加超时时间
            cursor = conn.cursor()

            stored_count = 0

            for item in items:
                # 提取需要的字段
                item_id = item.get('id', '')
                title = item.get('title', '')
                url = item.get('url', '')
                content = item.get('content_html', '')
                cover_url = item.get('image', '')

                # 从author对象中提取name作为account_name
                author_obj = item.get('author', {})
                account_name = author_obj.get(
                    'name', '') if isinstance(author_obj, dict) else ''

                # 使用account_name作为from_user
                from_user = account_name

                # 处理日期
                date_modified = item.get('date_modified', '')

                # 生成一个唯一的message_id (使用RSS条目的id)
                message_id = f"rss_{item_id}" if item_id else f"rss_{hash(url)}"

                # 当前时间作为处理时间
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                # 将原始JSON数据存储为raw_data
                raw_data = json.dumps(item)

                # 设置文章类型为RSS
                article_type = "RSS"

                # 检查标题是否已存在 - 使用内联查询而不是单独函数调用
                cursor.execute(
                    "SELECT 1 FROM wechat_articles WHERE title = ? AND account_name = ?",
                    (title, account_name)
                )
                if cursor.fetchone():
                    print(f"标题已存在: {title} ({account_name})")
                    continue

                # 准备SQL语句，只插入我们有数据的字段
                try:
                    cursor.execute('''
                        INSERT OR IGNORE INTO wechat_articles 
                        (message_id, from_user, title, url, content, 
                         cover_url, raw_data, processed, process_time, 
                         account_name, article_type, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        message_id, from_user, title, url, content,
                        cover_url, raw_data, False, current_time,
                        account_name, article_type, date_modified
                    ))

                    if cursor.rowcount > 0:
                        stored_count += 1
                        print(f"已存储: {title} ({account_name})")
                    else:
                        print(f"已存在: {title} ({account_name})")

                except sqlite3.Error as e:
                    print(f"数据库错误: {e} - {title}")
                    continue

            # 提交事务并关闭连接
            conn.commit()
            conn.close()

            return stored_count

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


def fetch_and_store_rss(feed_id="all", title_include=None, title_exclude=None, page_size=5, db_path=DB_PATH):
    """
    获取RSS条目并存储到数据库

    参数:
    - feed_id: 特定feed的ID
    - title_include: 标题包含的关键词
    - title_exclude: 标题排除的关键词
    - page_size: 获取的页数
    - db_path: 数据库文件路径

    返回:
    - 存储的条目数量
    """
    # 获取RSS条目
    items = get_all_items(
        feed_id=feed_id,
        title_include=title_include,
        title_exclude=title_exclude,
        page_size=page_size
    )

    print(f"获取到 {len(items)} 条RSS条目")

    # 存储到数据库
    stored_count = store_rss_items_to_db(items, db_path)

    print(f"成功存储 {stored_count} 条RSS条目到数据库")
    return stored_count


def check_rss_item_exists(item_id=None, url=None, db_path=DB_PATH):
    """
    检查RSS条目是否已存在于数据库中

    参数:
    - item_id: RSS条目的ID
    - url: RSS条目的URL (如果没有提供item_id)
    - db_path: 数据库文件路径

    返回:
    - 如果存在返回True，否则返回False
    """
    if not item_id and not url:
        raise ValueError("必须提供item_id或url参数")

    message_id = f"rss_{item_id}" if item_id else f"rss_{hash(url)}"

    try:
        conn = sqlite3.connect(db_path, timeout=10)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT 1 FROM wechat_articles WHERE message_id = ?", (message_id,))
        result = cursor.fetchone() is not None

        conn.close()
        return result
    except sqlite3.Error as e:
        print(f"检查条目存在时出错: {e}")
        return False


def check_rss_item_exists_by_title(title, account_name=None, db_path=DB_PATH):
    """
    通过标题检查RSS条目是否已存在于数据库中

    参数:
    - title: RSS条目的标题
    - account_name: 可选的账号名称，用于进一步限定查询范围
    - db_path: 数据库文件路径

    返回:
    - 如果存在返回True，否则返回False
    """
    if not title:
        raise ValueError("必须提供title参数")

    try:
        conn = sqlite3.connect(db_path, timeout=10)
        cursor = conn.cursor()

        if account_name:
            cursor.execute(
                "SELECT 1 FROM wechat_articles WHERE title = ? AND account_name = ? AND article_type = 'RSS'",
                (title, account_name)
            )
        else:
            cursor.execute(
                "SELECT 1 FROM wechat_articles WHERE title = ? AND article_type = 'RSS'",
                (title,)
            )

        result = cursor.fetchone() is not None

        conn.close()
        return result
    except sqlite3.Error as e:
        print(f"通过标题检查条目存在时出错: {e}")
        return False


def get_rss_stats(db_path=DB_PATH):
    """
    获取数据库中RSS条目的统计信息

    参数:
    - db_path: 数据库文件路径

    返回:
    - 包含统计信息的字典
    """
    try:
        conn = sqlite3.connect(db_path, timeout=10)
        cursor = conn.cursor()

        stats = {}

        # 获取RSS条目总数
        cursor.execute(
            "SELECT COUNT(*) FROM wechat_articles WHERE article_type = 'RSS'")
        stats['total_count'] = cursor.fetchone()[0]

        # 获取按账号分组的条目数
        cursor.execute("""
            SELECT account_name, COUNT(*) 
            FROM wechat_articles 
            WHERE article_type = 'RSS' 
            GROUP BY account_name
            ORDER BY COUNT(*) DESC
        """)
        stats['by_account'] = {row[0]: row[1] for row in cursor.fetchall()}

        # 获取最近添加的条目
        cursor.execute("""
            SELECT title, url, account_name, created_at
            FROM wechat_articles
            WHERE article_type = 'RSS'
            ORDER BY created_at DESC
            LIMIT 10
        """)
        stats['recent_items'] = [
            {
                'title': row[0],
                'url': row[1],
                'account_name': row[2],
                'created_at': row[3]
            }
            for row in cursor.fetchall()
        ]

        conn.close()
        return stats
    except sqlite3.Error as e:
        print(f"获取RSS统计信息时出错: {e}")
        return {'total_count': 0, 'by_account': {}, 'recent_items': []}


def fetch_store_and_process_rss(feed_id="all", title_include=None, title_exclude=None, page_size=5, db_path=DB_PATH, process_pdf=True):
    """
    获取RSS条目，存储到数据库，并处理为PDF

    参数:
    - feed_id: 特定feed的ID
    - title_include: 标题包含的关键词
    - title_exclude: 标题排除的关键词
    - page_size: 获取的页数
    - db_path: 数据库文件路径
    - process_pdf: 是否处理PDF

    返回:
    - 存储的条目数量和处理的PDF数量
    """
    # 获取并存储RSS条目
    stored_count = fetch_and_store_rss(
        feed_id=feed_id,
        title_include=title_include,
        title_exclude=title_exclude,
        page_size=page_size,
        db_path=db_path
    )

    processed_count = 0
    if process_pdf and stored_count > 0:
        # 处理未处理的RSS条目为PDF
        print("开始处理RSS条目为PDF...")
        processed_count = process_rss_to_pdf(db_path=db_path)
        print(f"成功处理 {processed_count} 条RSS条目为PDF")

    return stored_count, processed_count


if __name__ == "__main__":
    # 示例: 获取RSS条目，存储到数据库，并处理为PDF
    stored_count, processed_count = fetch_store_and_process_rss(
        feed_id="all", page_size=1)
    print(f"成功存储 {stored_count} 条RSS条目，处理 {processed_count} 条为PDF")

    # 示例: 获取RSS统计信息
    stats = get_rss_stats()
    print("\nRSS统计信息:")
    print(f"总条目数: {stats['total_count']}")
    print("\n按账号分组:")
    for account, count in list(stats['by_account'].items())[:5]:  # 只显示前5个
        print(f"  {account}: {count}条")

    print("\n最近添加的条目:")
    for item in stats['recent_items'][:3]:  # 只显示前3个
        print(f"  {item['title']} ({item['account_name']})")
