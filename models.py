from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
import hashlib
import bcrypt

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """用户表"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user')
    email = db.Column(db.String(100))
    create_time = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    analysis_logs = db.relationship('AnalysisLog', backref='user', lazy='dynamic')

    def set_password(self, password):
        # 使用bcrypt进行密码哈希
        salt = bcrypt.gensalt()
        self.password = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password.encode('utf-8'))

    def is_admin(self):
        return self.role == 'admin'


class Product(db.Model):
    """商品表"""
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.String(50), unique=True, nullable=False)
    product_name = db.Column(db.Text)  # 使用Text支持长商品名
    category = db.Column(db.String(50))
    create_time = db.Column(db.DateTime, default=datetime.utcnow)

    comments = db.relationship('Comment', backref='product', lazy='dynamic')


class Comment(db.Model):
    """评论表"""
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.String(50), db.ForeignKey('products.product_id'))
    user_id = db.Column(db.String(50))
    content = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer)
    comment_time = db.Column(db.DateTime)
    sentiment_label = db.Column(db.String(10))
    sentiment_score = db.Column(db.Float)


class AnalysisLog(db.Model):
    """分析记录表"""
    __tablename__ = 'analysis_logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    analysis_time = db.Column(db.DateTime, default=datetime.utcnow)
    total_comments = db.Column(db.Integer)
    positive_count = db.Column(db.Integer)
    negative_count = db.Column(db.Integer)
    neutral_count = db.Column(db.Integer)
    avg_score = db.Column(db.Float)