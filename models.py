from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import random

db = SQLAlchemy()

# 任务等级定义（按难度升序）
TASK_LEVELS = ['E', 'D', 'C', 'B', 'A', 'S', 'SS', 'SSS']
LEVEL_RANK = {lv: i for i, lv in enumerate(TASK_LEVELS)}

# 任务状态
TASK_STATUS_PENDING = 'pending'          # 等待接取
TASK_STATUS_REVIEWING = 'reviewing'      # B级以上审核中
TASK_STATUS_REJECTED = 'rejected'        # 审核拒绝
TASK_STATUS_IN_PROGRESS = 'in_progress'  # 进行中
TASK_STATUS_COMPLETED = 'completed'      # 已完成
TASK_STATUS_CANCELLED = 'cancelled'      # 已取消
TASK_STATUS_DISPUTED = 'disputed'        # 争议中


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    nickname = db.Column(db.String(64), nullable=False)
    gender = db.Column(db.String(10), default='保密')
    avatar = db.Column(db.String(256), default='default_avatar.png')
    register_time = db.Column(db.DateTime, default=datetime.utcnow)
    balance = db.Column(db.Float, default=100.0)  # 新手礼包100虚拟货币
    credit_score = db.Column(db.Integer, default=100)  # 信誉分
    mission_count = db.Column(db.Integer, default=0)    # 完成低等级任务计数
    phone = db.Column(db.String(20), nullable=True)
    location_enabled = db.Column(db.Boolean, default=False)
    last_lat = db.Column(db.Float, nullable=True)
    last_lng = db.Column(db.Float, nullable=True)

    # 关系
    published_tasks = db.relationship('Task', foreign_keys='Task.publisher_id', backref='publisher', lazy='dynamic')
    assigned_tasks = db.relationship('Task', foreign_keys='Task.assignee_id', backref='assignee', lazy='dynamic')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic', foreign_keys='Notification.user_id')
    sent_messages = db.relationship('Message', foreign_keys='Message.from_user_id', backref='sender', lazy='dynamic')
    received_messages = db.relationship('Message', foreign_keys='Message.to_user_id', backref='receiver', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_unlocked_level_rank(self):
        """根据完成的任务数计算已解锁的最高等级"""
        if self.mission_count >= 10:
            return 7  # 全部解锁，包括SSS
        elif self.mission_count >= 8:
            return 6  # 解锁到SS
        elif self.mission_count >= 5:
            return 5  # 解锁到S
        elif self.mission_count >= 3:
            return 4  # 解锁到A
        elif self.mission_count >= 1:
            return 3  # 解锁到B
        else:
            return 2  # 默认解锁到C（E、D、C）

    def can_accept_level(self, level_str):
        """判断是否可以接取某个等级的任务"""
        task_rank = LEVEL_RANK.get(level_str, 0)
        unlocked_rank = self.get_unlocked_level_rank()
        return task_rank <= unlocked_rank

    @property
    def level_badge(self):
        """用户等级徽章"""
        rank = self.get_unlocked_level_rank()
        if rank >= 7:
            return 'SSS级冒险者'
        elif rank >= 6:
            return 'SS级冒险者'
        elif rank >= 5:
            return 'S级冒险者'
        elif rank >= 4:
            return 'A级冒险者'
        elif rank >= 3:
            return 'B级冒险者'
        elif rank >= 2:
            return 'C级冒险者'
        elif rank >= 1:
            return 'D级冒险者'
        else:
            return 'E级冒险者（新手）'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'nickname': self.nickname,
            'gender': self.gender,
            'avatar': self.avatar,
            'credit_score': self.credit_score,
            'mission_count': self.mission_count,
            'level_badge': self.level_badge,
            'register_time': self.register_time.strftime('%Y-%m-%d'),
        }


class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    level = db.Column(db.String(10), nullable=False, default='E')  # SSS/SS/S/A/B/C/D/E
    description = db.Column(db.Text, nullable=False)
    reward = db.Column(db.Float, nullable=False, default=0)
    location = db.Column(db.String(200), nullable=True)
    location_lat = db.Column(db.Float, nullable=True)
    location_lng = db.Column(db.Float, nullable=True)
    expected_time = db.Column(db.String(100), nullable=True)  # 预期完成时间
    status = db.Column(db.String(20), default=TASK_STATUS_PENDING)
    publisher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assignee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    create_time = db.Column(db.DateTime, default=datetime.utcnow)
    complete_time = db.Column(db.DateTime, nullable=True)
    review_comment = db.Column(db.Text, nullable=True)  # 审核意见
    fee_rate = db.Column(db.Float, default=0.05)  # 手续费率

    # 关系
    transactions = db.relationship('Transaction', backref='task', lazy='dynamic')
    reviews = db.relationship('Review', backref='task', lazy='dynamic')
    location_records = db.relationship('LocationRecord', backref='task', lazy='dynamic')

    @property
    def level_rank(self):
        return LEVEL_RANK.get(self.level, 0)

    @property
    def status_cn(self):
        status_map = {
            TASK_STATUS_PENDING: '等待接取',
            TASK_STATUS_REVIEWING: '审核中',
            TASK_STATUS_REJECTED: '审核未通过',
            TASK_STATUS_IN_PROGRESS: '进行中',
            TASK_STATUS_COMPLETED: '已完成',
            TASK_STATUS_CANCELLED: '已取消',
            TASK_STATUS_DISPUTED: '争议中',
        }
        return status_map.get(self.status, self.status)

    @property
    def color_class(self):
        """任务等级对应的颜色"""
        colors = {
            'E': 'success',    # 绿色
            'D': 'info',       # 蓝色
            'C': 'primary',    # 靛蓝
            'B': 'warning',    # 黄色
            'A': 'orange',     # 橙色
            'S': 'danger',     # 红色
            'SS': 'dark',      # 黑色
            'SSS': 'gold',     # 金色
        }
        return colors.get(self.level, 'secondary')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'level': self.level,
            'description': self.description[:200] if self.description else '',
            'reward': self.reward,
            'location': self.location,
            'expected_time': self.expected_time,
            'status': self.status,
            'status_cn': self.status_cn,
            'publisher_name': self.publisher.nickname if self.publisher else '未知',
            'assignee_name': self.assignee.nickname if self.assignee else None,
            'create_time': self.create_time.strftime('%Y-%m-%d %H:%M'),
        }


class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    publisher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assignee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    fee = db.Column(db.Float, default=0)
    status = db.Column(db.String(20), default='frozen')  # frozen/released/refunded
    create_time = db.Column(db.DateTime, default=datetime.utcnow)
    release_time = db.Column(db.DateTime, nullable=True)

    # 关系
    publisher = db.relationship('User', foreign_keys=[publisher_id])
    assignee = db.relationship('User', foreign_keys=[assignee_id])


class Review(db.Model):
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    from_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    to_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.Text, nullable=True)
    role = db.Column(db.String(20), nullable=False)  # 'publisher' 或 'assignee'
    create_time = db.Column(db.DateTime, default=datetime.utcnow)

    from_user = db.relationship('User', foreign_keys=[from_user_id])
    to_user = db.relationship('User', foreign_keys=[to_user_id])


class LocationRecord(db.Model):
    __tablename__ = 'location_records'

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    update_time = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[user_id])


class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    from_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    to_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    create_time = db.Column(db.DateTime, default=datetime.utcnow)

    from_user = db.relationship('User', foreign_keys=[from_user_id])
    to_user = db.relationship('User', foreign_keys=[to_user_id])


class Follow(db.Model):
    __tablename__ = 'follows'

    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    create_time = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('follower_id', 'followed_id'),)


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), default='system')  # system/task/review/message
    related_link = db.Column(db.String(200), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    create_time = db.Column(db.DateTime, default=datetime.utcnow)
