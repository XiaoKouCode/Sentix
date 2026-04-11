"""
Flask应用主入口
基于Python的商品评论情感分析系统
"""
import os
import io
import base64
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, session, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False
from wordcloud import WordCloud

from config import Config
from models import db, User, Product, Comment, AnalysisLog
from utils.sentiment import analyze_sentiment, batch_analyze, get_sentiment_statistics, extract_keywords, clean_text
from utils.data_processor import load_data, clean_data, standardize_columns, preview_data, allowed_file, generate_sample_data
from utils.ml_model import classifier, SentimentClassifier


app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def admin_required(f):
    """管理员权限装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('需要管理员权限', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def active_required(f):
    """检查用户是否被禁用"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated and not current_user.is_active:
            flash('您的账号已被禁用，请联系管理员', 'danger')
            logout_user()
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# ==================== 初始化数据库 ====================
def init_db():
    """初始化数据库和默认管理员"""
    with app.app_context():
        db.create_all()

        # 创建默认管理员
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', role='admin', email='admin@sentix.com')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print('默认管理员已创建: admin / admin123')


# ==================== 认证路由 ====================
@app.route('/register', methods=['GET', 'POST'])
def register():
    """用户注册"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')

        if not username or not password:
            flash('用户名和密码不能为空', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('用户名已存在', 'danger')
            return redirect(url_for('register'))

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('注册成功，请登录', 'success')
        return redirect(url_for('login'))

    return render_template('auth/register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            if not user.is_active:
                flash('您的账号已被禁用，请联系管理员', 'danger')
                return redirect(url_for('login'))

            login_user(user)

            if user.is_admin():
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('index'))
        else:
            flash('用户名或密码错误', 'danger')

    return render_template('auth/login.html')


@app.route('/logout')
@login_required
def logout():
    """用户登出"""
    logout_user()
    flash('已退出登录', 'success')
    return redirect(url_for('login'))


# ==================== 前台路由（普通用户） ====================
@app.route('/')
@login_required
@active_required
def index():
    """前台首页"""
    # 获取用户最近的分析记录
    recent_logs = AnalysisLog.query.filter_by(user_id=current_user.id).order_by(AnalysisLog.analysis_time.desc()).limit(5).all()

    # 获取评论统计
    total_comments = Comment.query.count()
    analyzed_comments = Comment.query.filter(Comment.sentiment_label.isnot(None)).count()

    return render_template('frontend/index.html',
                           recent_logs=recent_logs,
                           total_comments=total_comments,
                           analyzed_comments=analyzed_comments)


@app.route('/import', methods=['GET', 'POST'])
@login_required
@active_required
def import_data():
    """数据导入"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('请选择文件', 'danger')
            return redirect(url_for('import_data'))

        file = request.files['file']
        if file.filename == '':
            flash('请选择文件', 'danger')
            return redirect(url_for('import_data'))

        if allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            try:
                df = load_data(filepath)
                df = standardize_columns(df)
                df = clean_data(df)

                # 保存到数据库
                save_to_database(df)

                flash(f'成功导入 {len(df)} 条评论', 'success')
                return redirect(url_for('preview'))

            except Exception as e:
                flash(f'导入失败: {str(e)}', 'danger')
                return redirect(url_for('import_data'))
        else:
            flash('不支持的文件格式，请上传CSV、JSON或Excel文件', 'danger')

    return render_template('frontend/import.html')


@app.route('/preview')
@login_required
@active_required
def preview():
    """数据预览"""
    page = request.args.get('page', 1, type=int)
    per_page = 20

    comments = Comment.query.order_by(Comment.id.desc()).paginate(page=page, per_page=per_page)

    return render_template('frontend/preview.html', comments=comments)


@app.route('/analysis', methods=['GET', 'POST'])
@login_required
@active_required
def analysis():
    """情感分析"""
    if request.method == 'POST':
        # 获取分析方法选择
        method = request.form.get('method', 'snownlp')  # snownlp 或 ml

        # 获取待分析的评论
        comment_ids = request.form.getlist('comment_ids')

        if not comment_ids:
            # 分析所有未分析的评论
            comments = Comment.query.filter(Comment.sentiment_label.isnot(None)).all()
            if not comments:
                comments = Comment.query.limit(100).all()
        else:
            comments = Comment.query.filter(Comment.id.in_(comment_ids)).all()

        if not comments:
            flash('没有可分析的评论', 'warning')
            return redirect(url_for('preview'))

        # 执行批量分析
        texts = [c.content for c in comments]

        if method == 'ml':
            # 使用机器学习模型（朴素贝叶斯）
            # 尝试加载模型，如果没有则先训练
            if not classifier.load_model():
                flash('机器学习模型未训练，正在自动训练...', 'info')
                # 使用部分数据训练模型
                train_comments = Comment.query.filter(
                    Comment.rating.isnot(None),
                    Comment.content.isnot(None)
                ).limit(5000).all()
                if train_comments:
                    train_df = pd.DataFrame([{
                        'content': c.content,
                        'rating': c.rating
                    } for c in train_comments])
                    classifier.train(train_df)

            results = classifier.batch_predict(texts)
        else:
            # 使用SnowNLP
            results = batch_analyze(texts)

        # 更新评论的情感标签
        for comment, (label, score) in zip(comments, results):
            comment.sentiment_label = label
            comment.sentiment_score = score

        db.session.commit()

        # 记录分析日志
        stats = get_sentiment_statistics(results)
        log = AnalysisLog(
            user_id=current_user.id,
            total_comments=stats['total'],
            positive_count=stats['positive'],
            negative_count=stats['negative'],
            neutral_count=stats['neutral'],
            avg_score=stats['avg_score']
        )
        db.session.add(log)
        db.session.commit()

        flash(f'分析完成，共处理 {len(comments)} 条评论 (使用{method == "ml" and "朴素贝叶斯模型" or "SnowNLP"})', 'success')
        return redirect(url_for('visualization', log_id=log.id))

    # GET请求显示分析页面
    comments = Comment.query.filter(Comment.sentiment_label.isnot(None)).limit(100).all()

    # 检查ML模型状态
    ml_model_ready = classifier.load_model()

    return render_template('frontend/analysis.html', comments=comments, ml_model_ready=ml_model_ready)


@app.route('/visualization')
@login_required
@active_required
def visualization():
    """可视化展示"""
    log_id = request.args.get('log_id', type=int)

    if log_id:
        log = AnalysisLog.query.get(log_id)
    else:
        log = AnalysisLog.query.filter_by(user_id=current_user.id).order_by(AnalysisLog.analysis_time.desc()).first()

    if not log:
        flash('请先进行情感分析', 'warning')
        return redirect(url_for('analysis'))

    # 获取所有已分析的评论
    comments = Comment.query.filter(Comment.sentiment_label.isnot(None)).all()

    # 情感分布数据
    sentiment_data = {
        'positive': Comment.query.filter_by(sentiment_label='positive').count(),
        'negative': Comment.query.filter_by(sentiment_label='negative').count(),
        'neutral': Comment.query.filter_by(sentiment_label='neutral').count()
    }

    # 关键词数据
    texts = [c.content for c in comments]
    keywords = extract_keywords(texts, top_n=30)

    # 商品对比数据 - 只获取有已分析评论的商品
    # 使用子查询获取有评论的商品ID
    analyzed_product_ids = db.session.query(Comment.product_id).filter(
        Comment.sentiment_label.isnot(None)
    ).distinct().limit(20).all()
    analyzed_product_ids = [p[0] for p in analyzed_product_ids]

    product_sentiment = []
    for pid in analyzed_product_ids:
        product = Product.query.filter_by(product_id=pid).first()
        pos = Comment.query.filter_by(product_id=pid, sentiment_label='positive').count()
        neg = Comment.query.filter_by(product_id=pid, sentiment_label='negative').count()
        neu = Comment.query.filter_by(product_id=pid, sentiment_label='neutral').count()
        if pos + neg + neu > 0:
            product_sentiment.append({
                'name': product.product_name[:30] if product else pid,
                'positive': pos,
                'negative': neg,
                'neutral': neu
            })

    return render_template('frontend/visualization.html',
                           log=log,
                           sentiment_data=sentiment_data,
                           keywords=keywords,
                           product_sentiment=product_sentiment)


@app.route('/model/train', methods=['GET', 'POST'])
@login_required
@active_required
def model_train():
    """模型训练页面"""
    if request.method == 'POST':
        # 获取训练参数
        sample_size = request.form.get('sample_size', 10000, type=int)

        # 获取有评分的训练数据
        train_comments = Comment.query.filter(
            Comment.rating.isnot(None),
            Comment.content.isnot(None)
        ).limit(sample_size).all()

        if not train_comments:
            flash('没有可用的训练数据（需要有评分的评论）', 'danger')
            return redirect(url_for('model_train'))

        # 构建训练数据
        train_df = pd.DataFrame([{
            'content': c.content,
            'rating': c.rating
        } for c in train_comments])

        # 训练模型
        results = classifier.train(train_df)

        flash(f'模型训练完成！准确率: {results["accuracy"]}, F1值: {results["f1_score"]}', 'success')
        return render_template('frontend/model_result.html', results=results, sample_size=len(train_df))

    # GET请求显示训练页面
    # 统计可训练数据量
    train_count = Comment.query.filter(
        Comment.rating.isnot(None),
        Comment.content.isnot(None)
    ).count()

    # 检查模型状态
    model_ready = classifier.load_model()

    return render_template('frontend/model_train.html', train_count=train_count, model_ready=model_ready)


@app.route('/model/evaluate')
@login_required
@active_required
def model_evaluate():
    """模型评估页面"""
    # 尝试加载模型
    if not classifier.load_model():
        flash('请先训练模型', 'warning')
        return redirect(url_for('model_train'))

    # 获取特征词
    feature_words = classifier.get_feature_words(top_n=20)

    return render_template('frontend/model_evaluate.html', feature_words=feature_words)


@app.route('/history')
@login_required
@active_required
def history():
    """历史记录"""
    page = request.args.get('page', 1, type=int)
    per_page = 10

    logs = AnalysisLog.query.filter_by(user_id=current_user.id).order_by(AnalysisLog.analysis_time.desc()).paginate(page=page, per_page=per_page)

    return render_template('frontend/history.html', logs=logs)


# ==================== 后台管理路由（管理员） ====================
@app.route('/admin/')
@login_required
@admin_required
def admin_dashboard():
    """管理员仪表盘"""
    # 统计数据
    total_users = User.query.count()
    total_comments = Comment.query.count()
    total_products = Product.query.count()
    total_logs = AnalysisLog.query.count()

    # 今日分析次数
    today = datetime.utcnow().date()
    today_logs = AnalysisLog.query.filter(AnalysisLog.analysis_time >= today).count()

    # 最近7天的分析趋势
    week_ago = datetime.utcnow() - timedelta(days=7)
    week_logs = AnalysisLog.query.filter(AnalysisLog.analysis_time >= week_ago).all()

    # 情感分布
    positive_count = Comment.query.filter_by(sentiment_label='positive').count()
    negative_count = Comment.query.filter_by(sentiment_label='negative').count()
    neutral_count = Comment.query.filter_by(sentiment_label='neutral').count()

    return render_template('admin/dashboard.html',
                           total_users=total_users,
                           total_comments=total_comments,
                           total_products=total_products,
                           total_logs=total_logs,
                           today_logs=today_logs,
                           positive_count=positive_count,
                           negative_count=negative_count,
                           neutral_count=neutral_count)


@app.route('/admin/users', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_users():
    """用户管理"""
    if request.method == 'POST':
        action = request.form.get('action')
        user_id = request.form.get('user_id', type=int)

        user = User.query.get(user_id)
        if not user:
            flash('用户不存在', 'danger')
            return redirect(url_for('admin_users'))

        if action == 'toggle_active':
            user.is_active = not user.is_active
            db.session.commit()
            status = '启用' if user.is_active else '禁用'
            flash(f'用户 {user.username} 已{status}', 'success')

        elif action == 'reset_password':
            user.set_password('123456')
            db.session.commit()
            flash(f'用户 {user.username} 密码已重置为: 123456', 'success')

        elif action == 'change_role':
            new_role = request.form.get('new_role')
            if new_role in ['admin', 'user']:
                user.role = new_role
                db.session.commit()
                flash(f'用户 {user.username} 角色已更改为: {new_role}', 'success')

        elif action == 'delete':
            if user.id == current_user.id:
                flash('不能删除自己的账号', 'danger')
            else:
                db.session.delete(user)
                db.session.commit()
                flash(f'用户 {user.username} 已删除', 'success')

        return redirect(url_for('admin_users'))

    page = request.args.get('page', 1, type=int)
    per_page = 20
    users = User.query.order_by(User.id.desc()).paginate(page=page, per_page=per_page)

    return render_template('admin/users.html', users=users)


@app.route('/admin/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_add_user():
    """新增用户"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        role = request.form.get('role', 'user')

        if User.query.filter_by(username=username).first():
            flash('用户名已存在', 'danger')
            return redirect(url_for('admin_add_user'))

        user = User(username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash(f'用户 {username} 已创建', 'success')
        return redirect(url_for('admin_users'))

    return render_template('admin/add_user.html')


@app.route('/admin/comments')
@login_required
@admin_required
def admin_comments():
    """评论管理"""
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # 筛选条件
    product_id = request.args.get('product_id')
    sentiment = request.args.get('sentiment')

    query = Comment.query
    if product_id:
        query = query.filter_by(product_id=product_id)
    if sentiment:
        query = query.filter_by(sentiment_label=sentiment)

    comments = query.order_by(Comment.id.desc()).paginate(page=page, per_page=per_page)
    products = Product.query.all()

    return render_template('admin/comments.html', comments=comments, products=products)


@app.route('/admin/comments/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_comment(id):
    """删除评论"""
    comment = Comment.query.get(id)
    if comment:
        db.session.delete(comment)
        db.session.commit()
        flash('评论已删除', 'success')
    else:
        flash('评论不存在', 'danger')

    return redirect(url_for('admin_comments'))


@app.route('/admin/products', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_products():
    """商品管理"""
    if request.method == 'POST':
        action = request.form.get('action')
        product_id = request.form.get('product_id', type=int)

        product = Product.query.get(product_id)
        if not product:
            flash('商品不存在', 'danger')
            return redirect(url_for('admin_products'))

        if action == 'update':
            product.product_name = request.form.get('product_name')
            product.category = request.form.get('category')
            db.session.commit()
            flash(f'商品 {product.product_name} 已更新', 'success')

        elif action == 'delete':
            # 删除商品关联的评论
            Comment.query.filter_by(product_id=product.product_id).delete()
            db.session.delete(product)
            db.session.commit()
            flash(f'商品 {product.product_name} 及其评论已删除', 'success')

        return redirect(url_for('admin_products'))

    page = request.args.get('page', 1, type=int)
    per_page = 20
    products = Product.query.order_by(Product.id.desc()).paginate(page=page, per_page=per_page)

    return render_template('admin/products.html', products=products)


@app.route('/admin/logs')
@login_required
@admin_required
def admin_logs():
    """分析日志"""
    page = request.args.get('page', 1, type=int)
    per_page = 20

    logs = AnalysisLog.query.order_by(AnalysisLog.analysis_time.desc()).paginate(page=page, per_page=per_page)

    return render_template('admin/logs.html', logs=logs)


@app.route('/admin/import', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_import():
    """管理员数据导入"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('请选择文件', 'danger')
            return redirect(url_for('admin_import'))

        file = request.files['file']
        if file.filename == '':
            flash('请选择文件', 'danger')
            return redirect(url_for('admin_import'))

        if allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            try:
                df = load_data(filepath)
                df = standardize_columns(df)
                df = clean_data(df)

                save_to_database(df)

                flash(f'成功导入 {len(df)} 条评论', 'success')
                return redirect(url_for('admin_comments'))

            except Exception as e:
                flash(f'导入失败: {str(e)}', 'danger')
                return redirect(url_for('admin_import'))
        else:
            flash('不支持的文件格式', 'danger')

    return render_template('admin/import.html')


# ==================== API接口 ====================
@app.route('/api/analysis', methods=['POST'])
@login_required
@active_required
def api_analysis():
    """API: 执行情感分析"""
    data = request.get_json()
    texts = data.get('texts', [])

    if not texts:
        return jsonify({'error': '没有提供文本'}), 400

    results = batch_analyze(texts)
    stats = get_sentiment_statistics(results)

    return jsonify({
        'results': results,
        'statistics': stats
    })


@app.route('/api/visualization/sentiment')
@login_required
@active_required
def api_sentiment_data():
    """API: 获取情感分布数据"""
    positive = Comment.query.filter_by(sentiment_label='positive').count()
    negative = Comment.query.filter_by(sentiment_label='negative').count()
    neutral = Comment.query.filter_by(sentiment_label='neutral').count()

    return jsonify({
        'positive': positive,
        'negative': negative,
        'neutral': neutral
    })


@app.route('/api/visualization/keywords')
@login_required
@active_required
def api_keywords():
    """API: 获取关键词数据"""
    comments = Comment.query.filter(Comment.sentiment_label.isnot(None)).all()
    texts = [c.content for c in comments]
    keywords = extract_keywords(texts, top_n=30)

    return jsonify(keywords)


@app.route('/api/comments')
@login_required
def api_comments():
    """API: 获取评论列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    comments = Comment.query.order_by(Comment.id.desc()).paginate(page=page, per_page=per_page)

    data = [{
        'id': c.id,
        'product_id': c.product_id,
        'content': c.content,
        'rating': c.rating,
        'sentiment_label': c.sentiment_label,
        'sentiment_score': c.sentiment_score
    } for c in comments.items]

    return jsonify({
        'data': data,
        'total': comments.total,
        'page': page,
        'per_page': per_page
    })


@app.route('/api/users/<int:id>', methods=['PUT'])
@login_required
@admin_required
def api_update_user(id):
    """API: 更新用户状态"""
    user = User.query.get(id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404

    data = request.get_json()

    if 'is_active' in data:
        user.is_active = data['is_active']
    if 'role' in data:
        user.role = data['role']

    db.session.commit()

    return jsonify({'success': True})


# ==================== 图表生成 ====================
@app.route('/generate_wordcloud')
@login_required
@active_required
def generate_wordcloud():
    """生成词云图"""
    comments = Comment.query.filter(Comment.sentiment_label.isnot(None)).limit(1000).all()
    texts = [c.content for c in comments]

    if not texts:
        # 如果没有已分析的评论，返回提示图片
        plt.figure(figsize=(10, 5))
        plt.text(0.5, 0.5, '请先进行情感分析', fontsize=20, ha='center', va='center')
        plt.axis('off')
        img = io.BytesIO()
        plt.savefig(img, format='png', bbox_inches='tight')
        img.seek(0)
        plt.close()
        return send_file(img, mimetype='image/png')

    # 合并所有文本
    all_text = ' '.join(texts)

    # 生成词云
    wordcloud = WordCloud(
        font_path='/System/Library/Fonts/STHeiti Light.ttc',
        width=800,
        height=400,
        background_color='white',
        max_words=100
    ).generate(all_text)

    # 转换为图片
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')

    # 保存到内存
    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')
    img.seek(0)
    plt.close()

    return send_file(img, mimetype='image/png')


@app.route('/generate_sentiment_chart')
@login_required
@active_required
def generate_sentiment_chart():
    """生成情感分布图"""
    positive = Comment.query.filter_by(sentiment_label='positive').count()
    negative = Comment.query.filter_by(sentiment_label='negative').count()
    neutral = Comment.query.filter_by(sentiment_label='neutral').count()

    labels = ['积极', '消极', '中性']
    sizes = [positive, negative, neutral]
    colors = ['#28a745', '#dc3545', '#ffc107']

    plt.figure(figsize=(8, 6))
    plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
    plt.title('情感分布图')

    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')
    img.seek(0)
    plt.close()

    return send_file(img, mimetype='image/png')


# ==================== 辅助函数 ====================
def save_to_database(df):
    """保存数据到数据库"""
    for _, row in df.iterrows():
        # 检查/创建商品
        product_id = str(row.get('product_id', 'unknown'))
        product = Product.query.filter_by(product_id=product_id).first()

        if not product:
            product = Product(
                product_id=product_id,
                product_name=row.get('product_name', '未知商品'),
                category=row.get('category', '未分类')
            )
            db.session.add(product)
            db.session.flush()

        # 创建评论
        comment = Comment(
            product_id=product_id,
            user_id=str(row.get('user_id', '')),
            content=row.get('content', ''),
            rating=int(row.get('rating', 0)) if row.get('rating') else None,
            comment_time=row.get('comment_time')
        )
        db.session.add(comment)

    db.session.commit()


def generate_sample_dataset():
    """生成示例数据集"""
    df = generate_sample_data(5000)

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'jd_comments.csv')
    df.to_csv(filepath, index=False, encoding='utf-8')

    print(f'示例数据集已生成: {filepath}')
    return filepath


# ==================== 主程序 ====================
if __name__ == '__main__':
    # 确保目录存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # 初始化数据库表
    with app.app_context():
        db.create_all()

        # 创建默认管理员
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', role='admin', email='admin@sentix.com')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print('默认管理员已创建: admin / admin123')

    print('\n使用说明:')
    print('1. 请确保MySQL数据库已创建 (sentix)')
    print('2. 运行 python utils/import_dataset.py 导入京东数据集')
    print('3. 访问 http://localhost:5000 登录系统')
    print('\n启动服务...')

    app.run(debug=True, host='0.0.0.0', port=5001)