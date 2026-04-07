"""
数据处理模块
支持CSV/JSON/Excel文件导入和数据清洗
"""
import pandas as pd
import os
from datetime import datetime
import re


def allowed_file(filename, allowed_extensions={'csv', 'json', 'xlsx'}):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


def load_data(filepath):
    """
    加载数据文件
    支持: CSV, JSON, Excel
    返回: pandas DataFrame
    """
    ext = filepath.rsplit('.', 1)[1].lower()

    try:
        if ext == 'csv':
            df = pd.read_csv(filepath, encoding='utf-8')
        elif ext == 'json':
            df = pd.read_json(filepath, encoding='utf-8')
        elif ext == 'xlsx':
            df = pd.read_excel(filepath)
        else:
            raise ValueError(f'不支持的文件格式: {ext}')
        return df
    except Exception as e:
        raise ValueError(f'文件读取失败: {str(e)}')


def clean_data(df):
    """
    数据清洗
    - 移除空值
    - 统一列名
    - 处理时间格式
    """
    # 确保必需列存在
    required_cols = ['content']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f'缺少必需列: {col}')

    # 移除评论内容为空的行
    df = df.dropna(subset=['content'])

    # 清洗评论内容
    df['content'] = df['content'].apply(clean_content)

    # 处理时间列
    if 'comment_time' in df.columns or 'time' in df.columns:
        time_col = 'comment_time' if 'comment_time' in df.columns else 'time'
        df['comment_time'] = pd.to_datetime(df[time_col], errors='coerce')

    # 处理评分列
    if 'rating' in df.columns or 'score' in df.columns:
        rating_col = 'rating' if 'rating' in df.columns else 'score'
        df['rating'] = pd.to_numeric(df[rating_col], errors='coerce')

    # 确保product_id列
    if 'product_id' not in df.columns:
        if 'product_id' in df.columns:
            pass
        else:
            df['product_id'] = 'unknown'

    return df


def clean_content(content):
    """清洗评论内容"""
    if pd.isna(content) or not content:
        return ''

    content = str(content)
    # 移除HTML标签
    content = re.sub(r'<[^>]+>', '', content)
    # 移除表情符号编码
    content = re.sub(r'\\[uU][0-9a-fA-F]{4,6}', '', content)
    # 移除特殊字符
    content = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s，。！？、；：""''（）【】…～]', '', content)
    # 移除多余空格
    content = re.sub(r'\s+', ' ', content).strip()

    return content


def standardize_columns(df, column_mapping=None):
    """
    标准化列名
    column_mapping: 自定义列名映射
    """
    default_mapping = {
        '评论内容': 'content',
        '评论': 'content',
        'comment': 'content',
        '商品ID': 'product_id',
        '商品名称': 'product_name',
        'product': 'product_name',
        '评分': 'rating',
        'score': 'rating',
        '评论时间': 'comment_time',
        'time': 'comment_time',
        '用户ID': 'user_id',
        'user': 'user_id'
    }

    if column_mapping:
        default_mapping.update(column_mapping)

    df = df.rename(columns=default_mapping)
    return df


def preview_data(df, n=10):
    """
    数据预览
    返回前n条数据
    """
    preview = df.head(n).to_dict('records')
    stats = {
        'total_rows': len(df),
        'columns': list(df.columns),
        'null_counts': df.isnull().sum().to_dict()
    }
    return preview, stats


def load_jd_dataset(data_dir):
    """
    加载京东商品评论数据集
    包含: 商品信息.csv, 商品类别列表.csv, 训练集.csv
    """
    import os

    # 加载商品信息
    products_file = os.path.join(data_dir, '商品信息.csv')
    if os.path.exists(products_file):
        products_df = pd.read_csv(products_file)
        products_df = products_df.rename(columns={
            '商品ID': 'product_id',
            '商品名称': 'product_name',
            '所属类别': 'category'
        })
    else:
        products_df = None

    # 加载类别信息
    categories_file = os.path.join(data_dir, '商品类别列表.csv')
    if os.path.exists(categories_file):
        categories_df = pd.read_csv(categories_file)
        categories_df = categories_df.rename(columns={
            '类别ID': 'category_id',
            '类别名称': 'category_name'
        })
    else:
        categories_df = None

    # 加载训练集评论
    train_file = os.path.join(data_dir, '训练集.csv')
    if os.path.exists(train_file):
        comments_df = pd.read_csv(train_file)
        comments_df = comments_df.rename(columns={
            '数据ID': 'data_id',
            '用户ID': 'user_id',
            '商品ID': 'product_id',
            '评论时间戳': 'comment_timestamp',
            '评论标题': 'comment_title',
            '评论内容': 'content',
            '评分': 'rating'
        })
    else:
        comments_df = None

    # 合并数据
    if comments_df is not None and products_df is not None:
        # 合并商品名称
        comments_df = comments_df.merge(
            products_df[['product_id', 'product_name', 'category']],
            on='product_id',
            how='left'
        )

    # 处理时间戳
    if comments_df is not None and 'comment_timestamp' in comments_df.columns:
        comments_df['comment_time'] = pd.to_datetime(
            comments_df['comment_timestamp'],
            unit='s',
            errors='coerce'
        )

    # 清洗评论内容
    if comments_df is not None and 'content' in comments_df.columns:
        comments_df['content'] = comments_df['content'].apply(clean_content)
        # 移除空评论
        comments_df = comments_df.dropna(subset=['content'])

    return {
        'products': products_df,
        'categories': categories_df,
        'comments': comments_df
    }


def generate_sample_data(n=100):
    """
    生成示例数据（用于测试）
    """
    import random

    sample_comments = [
        '这个商品非常好，质量很棒，推荐购买！',
        '东西收到了，包装很好，物流很快，满意。',
        '非常失望，质量太差了，和描述不符。',
        '还可以吧，一般般，没有想象中那么好。',
        '用了几天，感觉不错，性价比高。',
        '客服态度很好，解决问题很及时。',
        '太垃圾了，完全不推荐，浪费钱。',
        '质量不错，但是物流太慢了，等了好久。',
        '好评，值得购买，下次还会来的。',
        '差评，商品有问题，客服也不理人。',
        '还行，没什么特别的，凑合用吧。',
        '非常满意，超出预期，五星好评！',
        '太差劲了，退货了，不想再买。',
        '包装有点破损，但商品本身没问题。',
        '性价比很高，值得推荐给大家。',
    ]

    products = [
        {'product_id': 'P001', 'product_name': '华为手机', 'category': '手机'},
        {'product_id': 'P002', 'product_name': '小米电视', 'category': '电视'},
        {'product_id': 'P003', 'product_name': '联想笔记本', 'category': '电脑'},
        {'product_id': 'P004', 'product_name': '苹果耳机', 'category': '耳机'},
        {'product_id': 'P005', 'product_name': '戴森吸尘器', 'category': '家电'},
    ]

    data = []
    for i in range(n):
        product = random.choice(products)
        comment = random.choice(sample_comments)
        rating = random.randint(1, 5)
        user_id = f'user_{random.randint(1000, 9999)}'

        # 根据评论内容推断时间
        base_time = datetime(2023, 1, 1)
        random_days = random.randint(0, 365)
        comment_time = base_time + pd.Timedelta(days=random_days)

        data.append({
            'product_id': product['product_id'],
            'product_name': product['product_name'],
            'category': product['category'],
            'user_id': user_id,
            'content': comment,
            'rating': rating,
            'comment_time': comment_time
        })

    return pd.DataFrame(data)