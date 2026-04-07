"""
情感分析核心模块
使用SnowNLP进行中文文本情感分析
"""
import jieba
from snownlp import SnowNLP
import re


# 停用词列表
STOPWORDS = set([
    '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
    '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
    '自己', '这', '那', '里', '吧', '啊', '呢', '吗', '哦', '嗯', '哈', '呵', '吃',
    '买', '买来', '之后', '觉得', '但是', '还是', '用', '这个', '那个', '因为',
    '所以', '如果', '虽然', '而且', '或者', '可以', '可能', '应该', '需要',
    '已经', '正在', '将要', '曾经', '一直', '一直', '才', '再', '又', '也',
    '很', '太', '非常', '特别', '相当', '比较', '稍微', '有点', '一些',
    '什么', '怎么', '为什么', '哪', '哪里', '何时', '多少', '几', '怎样'
])


def clean_text(text):
    """文本清洗"""
    if not text:
        return ''
    # 移除HTML标签
    text = re.sub(r'<[^>]+>', '', text)
    # 移除特殊字符，保留中文、英文、数字
    text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s]', '', text)
    # 移除多余空格
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def tokenize(text):
    """jieba分词"""
    if not text:
        return []
    words = jieba.lcut(text)
    # 过滤停用词
    words = [w for w in words if w not in STOPWORDS and len(w) > 1]
    return words


def analyze_sentiment(text):
    """
    分析单条文本的情感
    返回: (label, score)
    - label: 'positive', 'negative', 'neutral'
    - score: 0-1的情感得分
    """
    if not text:
        return 'neutral', 0.5

    text = clean_text(text)
    if not text:
        return 'neutral', 0.5

    try:
        s = SnowNLP(text)
        score = s.sentiments

        # 根据得分判断情感标签
        if score >= 0.6:
            label = 'positive'
        elif score <= 0.4:
            label = 'negative'
        else:
            label = 'neutral'

        return label, round(score, 4)
    except Exception as e:
        return 'neutral', 0.5


def batch_analyze(texts):
    """
    批量情感分析
    texts: 文本列表
    返回: [(label, score), ...]
    """
    results = []
    for text in texts:
        label, score = analyze_sentiment(text)
        results.append((label, score))
    return results


def get_sentiment_statistics(results):
    """
    统计情感分析结果
    results: [(label, score), ...]
    返回: 统计字典
    """
    positive_count = sum(1 for r in results if r[0] == 'positive')
    negative_count = sum(1 for r in results if r[0] == 'negative')
    neutral_count = sum(1 for r in results if r[0] == 'neutral')
    total = len(results)

    avg_score = sum(r[1] for r in results) / total if total > 0 else 0

    return {
        'total': total,
        'positive': positive_count,
        'negative': negative_count,
        'neutral': neutral_count,
        'avg_score': round(avg_score, 4),
        'positive_ratio': round(positive_count / total * 100, 2) if total > 0 else 0,
        'negative_ratio': round(negative_count / total * 100, 2) if total > 0 else 0,
        'neutral_ratio': round(neutral_count / total * 100, 2) if total > 0 else 0
    }


def extract_keywords(texts, top_n=20):
    """
    提取高频关键词
    texts: 文本列表
    top_n: 返回前N个关键词
    返回: [(word, count), ...]
    """
    from collections import Counter

    all_words = []
    for text in texts:
        words = tokenize(clean_text(text))
        all_words.extend(words)

    word_counts = Counter(all_words)
    return word_counts.most_common(top_n)