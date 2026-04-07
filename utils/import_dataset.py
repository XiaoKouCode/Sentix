"""
京东数据集导入脚本
将京东商品评论数据导入MySQL数据库
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models import User, Product, Comment
from utils.data_processor import load_jd_dataset, clean_content
import pandas as pd
from datetime import datetime


def import_jd_dataset(data_dir, limit=None):
    """
    导入京东数据集到数据库
    limit: 限制导入的评论数量（用于测试）
    """
    print('开始加载京东数据集...')
    dataset = load_jd_dataset(data_dir)

    if dataset['comments'] is None:
        print('错误: 未找到训练集文件')
        return

    comments_df = dataset['comments']
    products_df = dataset['products']

    # 限制导入数量
    if limit:
        comments_df = comments_df.head(limit)
        print(f'限制导入 {limit} 条评论')

    print(f'加载了 {len(comments_df)} 条评论')

    with app.app_context():
        # 创建数据库表
        db.create_all()

        # 创建默认管理员
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', role='admin', email='admin@sentix.com')
            admin.set_password('admin123')
            db.session.add(admin)
            print('创建默认管理员: admin / admin123')

        # 导入商品数据
        print('导入商品数据...')
        imported_products = 0
        if products_df is not None:
            for _, row in products_df.iterrows():
                product_id = str(row.get('product_id', ''))
                if not product_id:
                    continue

                # 检查是否已存在
                existing = Product.query.filter_by(product_id=product_id).first()
                if not existing:
                    # 解析类别
                    category_str = str(row.get('category', ''))
                    category = category_str.split(',')[0].replace('CATE_', '') if category_str else ''

                    product = Product(
                        product_id=product_id,
                        product_name=str(row.get('product_name', '未知商品')),
                        category=category
                    )
                    db.session.add(product)
                    imported_products += 1

        db.session.commit()
        print(f'导入 {imported_products} 个商品')

        # 导入评论数据
        print('导入评论数据...')
        imported_comments = 0
        batch_size = 1000

        for idx, row in comments_df.iterrows():
            try:
                content = clean_content(row.get('content', ''))
                if not content:
                    continue

                comment = Comment(
                    product_id=str(row.get('product_id', 'unknown')),
                    user_id=str(row.get('user_id', '')),
                    content=content,
                    rating=int(row.get('rating', 0)) if row.get('rating') else None,
                    comment_time=row.get('comment_time')
                )
                db.session.add(comment)
                imported_comments += 1

                # 分批提交
                if imported_comments % batch_size == 0:
                    db.session.commit()
                    print(f'已导入 {imported_comments} 条评论...')

            except Exception as e:
                print(f'导入评论 {idx} 失败: {str(e)}')
                continue

        db.session.commit()
        print(f'完成！导入 {imported_comments} 条评论')

        # 统计
        print('\n数据库统计:')
        print(f'用户数: {User.query.count()}')
        print(f'商品数: {Product.query.count()}')
        print(f'评论数: {Comment.query.count()}')


def main():
    # 数据目录
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')

    # 可选：限制导入数量（用于测试）
    # 取消注释下面这行可以只导入10000条测试
    # import_jd_dataset(data_dir, limit=10000)

    # 导入全部数据
    import_jd_dataset(data_dir)


if __name__ == '__main__':
    main()