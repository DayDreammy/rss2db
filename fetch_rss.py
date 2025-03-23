import os
import requests
import urllib.parse
import json
import xml.etree.ElementTree as ET

# 基础URL，替换为你的实际服务地址
BASE_URL = os.getenv("WEWERSS_URL", "http://localhost:9021")  # wewerss
print(BASE_URL)


def get_feed(feed_id=None, format="json", title_include=None, title_exclude=None, limit=None, update=False):
    """
    获取RSS feed

    参数:
    - feed_id: 特定feed的ID，如果为None则获取all
    - format: 返回格式，可选json、rss或atom
    - title_include: 标题包含的关键词，可以是单个词或用|分隔的多个词
    - title_exclude: 标题排除的关键词，可以是单个词或用|分隔的多个词
    - limit: 限制返回的条目数
    - update: 是否触发feed更新
    """
    # 构建URL
    if feed_id:
        url = f"{BASE_URL}/feeds/{feed_id}.{format}"
    else:
        url = f"{BASE_URL}/feeds/all.{format}"

    # 构建查询参数
    params = {}
    if title_include:
        params['title_include'] = title_include
    if title_exclude:
        params['title_exclude'] = title_exclude
    if limit:
        params['limit'] = limit
    if update:
        params['update'] = 'true'

    # 发送请求
    response = requests.get(url, params=params)

    # 检查请求是否成功
    if response.status_code == 200:
        if format == "json":
            return response.json()
        else:  # rss or atom
            return response.text
    else:
        print(f"请求失败: {response.status_code}")
        return None


def get_all_items(feed_id=None, title_include=None, title_exclude=None, batch_size=100, page_size=1):
    """
    获取所有RSS条目，通过分页方式获取全部内容

    参数:
    - feed_id: 特定feed的ID，如果为None则获取all
    - title_include: 标题包含的关键词，可以是单个词或用|分隔的多个词
    - title_exclude: 标题排除的关键词，可以是单个词或用|分隔的多个词
    - batch_size: 每次请求的条目数量
    - page_size: 获取的页数

    返回:
    - 包含所有条目的列表
    """
    all_items = []
    page = 1
    while True:
        # 获取当前批次的数据
        result = get_feed(
            feed_id=feed_id,
            format="json",
            title_include=title_include,
            title_exclude=title_exclude,
            limit=batch_size
        )

        # 检查请求是否成功
        if not result or 'items' not in result:
            break

        current_items = result.get('items', [])

        # 如果没有更多条目，退出循环
        if not current_items:
            break

        # 添加当前批次的条目到结果列表
        all_items.extend(current_items)

        # 如果返回的条目数小于请求的批次大小，说明已经获取完所有条目
        if len(current_items) < batch_size:
            break

        page += 1

        if page >= page_size:
            break

    return all_items


# 如果直接运行此脚本，则执行示例
if __name__ == "__main__":
    # 示例: 获取特定feed的所有条目
    all_items = get_all_items(feed_id="all", page_size=1)
    print("\n获取所有条目示例:")
    print(f"总共获取到 {len(all_items)} 条内容")

    # 打印第一条内容的详细信息(如果有)
    if all_items and len(all_items) > 0:
        first_item = all_items[0]
        print("\n第一条内容详细信息:")
        print(f"标题: {first_item.get('title')}")
        print(f"链接: {first_item.get('link')}")
        print(f"作者: {first_item.get('author')}")
        print(f"发布时间: {first_item.get('published')}")
        # 只显示前100个字符
        print(f"描述: {first_item.get('description', '')[:100]}...")
