# Sentix - 商品评论情感分析系统

基于Python的商品评论情感分析系统，使用SnowNLP进行中文文本情感分析。

## 功能特性

- 用户注册/登录，区分普通用户与管理员
- 普通用户：数据导入、情感分析、可视化展示
- 管理员后台：用户管理、评论管理、商品管理、分析日志
- 支持京东商品评论数据集（70000条真实评论）

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置MySQL数据库

创建数据库：
```sql
CREATE DATABASE sentix CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

修改 `config.py` 配置数据库连接：
```python
MYSQL_USER = 'root'        # MySQL用户名
MYSQL_PASSWORD = 'root'    # MySQL密码
MYSQL_HOST = 'localhost'   # MySQL主机
MYSQL_PORT = '3306'        # MySQL端口
MYSQL_DB = 'sentix'        # 数据库名
```

### 3. 导入数据集

将京东数据集文件放入 `data/` 目录（已包含）：
- 商品信息.csv
- 商品类别列表.csv
- 训练集.csv

运行导入脚本：
```bash
python utils/import_dataset.py
```

### 4. 运行系统

```bash
python app.py
```

### 5. 访问系统

- 前台地址: http://localhost:5000
- 后台地址: http://localhost:5000/admin

默认管理员账号: `admin` / `admin123`

## 数据集说明

使用京东商品评论数据集（约70000条评论），包含：
- 商品信息：商品ID、商品名称、所属类别
- 商品类别：类别ID、类别名称
- 训练集：评论ID、用户ID、商品ID、评论时间戳、评论标题、评论内容、评分

## 技术架构

- 后端: Flask + SQLAlchemy + SnowNLP + jieba
- 前端: Bootstrap + ECharts + AdminLTE
- 数据库: MySQL
- 可视化: ECharts + matplotlib + wordcloud

## 项目结构

```
Sentix/
├── app.py              # Flask应用入口
├── config.py           # 配置文件（MySQL配置）
├── models.py           # 数据库模型（4张表）
├── requirements.txt    # 依赖列表
├── data/               # 数据目录
│   ├── 商品信息.csv
│   ├── 商品类别列表.csv
│   ├── 训练集.csv       # 70000条评论
│   └── 测试集.csv
├── static/             # 静态资源
│   ├── css/style.css
│   ├── js/main.js
│   └── js/charts.js
├── templates/          # HTML模板
│   ├── auth/           # 登录/注册
│   ├── frontend/       # 前台页面
│   └── admin/          # 后台管理
└── utils/
    ├── sentiment.py    # 情感分析核心
    ├── data_processor.py # 数据处理
    └── import_dataset.py # 数据导入脚本
```

## 系统截图

### 前台界面
- 首页：数据概览、快速入口
- 数据导入：支持CSV/JSON/Excel格式
- 情感分析：批量分析评论情感
- 可视化：情感分布饼图、柱状图、词云图、商品对比图

### 后台管理
- 仪表盘：系统统计、今日分析次数
- 用户管理：新增/禁用/删除用户、重置密码
- 评论管理：查看/筛选/删除评论
- 商品管理：编辑/删除商品
- 分析日志：查看所有分析记录