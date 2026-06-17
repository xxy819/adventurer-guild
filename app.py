import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uuid
from datetime import datetime

from flask import (Flask, render_template, redirect, url_for, flash, request,
                   jsonify, abort)
from flask_login import (LoginManager, login_user, logout_user, login_required,
                         current_user)
from werkzeug.utils import secure_filename

from models import (db, User, Task, Transaction, Review, LocationRecord,
                    Message, Follow, Notification, TASK_LEVELS, LEVEL_RANK,
                    TASK_STATUS_PENDING, TASK_STATUS_REVIEWING,
                    TASK_STATUS_REJECTED, TASK_STATUS_IN_PROGRESS,
                    TASK_STATUS_COMPLETED, TASK_STATUS_CANCELLED,
                    TASK_STATUS_DISPUTED)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'adventurer-guild-secret-key-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///guild.db')
# Render 上 PostgreSQL 连接需要以 postgresql:// 开头
if app.config['SQLALCHEMY_DATABASE_URI'] and app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = '请先登录冒险者公会'


@app.context_processor
def inject_notifications():
    if current_user.is_authenticated:
        unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        recent_notifs = Notification.query.filter_by(user_id=current_user.id, is_read=False)\
            .order_by(Notification.create_time.desc()).limit(5).all()
        return dict(unread_count=unread_count, recent_notifications=recent_notifs)
    return dict(unread_count=0, recent_notifications=[])


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ─── 辅助函数 ─────────────────────────────────────────────

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def add_notification(user_id, content, type='system', link=None):
    notif = Notification(user_id=user_id, content=content, type=type, related_link=link)
    db.session.add(notif)
    db.session.commit()


def get_level_color(level):
    colors = {
        'E': '#28a745', 'D': '#17a2b8', 'C': '#007bff',
        'B': '#ffc107', 'A': '#fd7e14', 'S': '#dc3545',
        'SS': '#343a40', 'SSS': '#b8860b',
    }
    return colors.get(level, '#6c757d')


def get_level_badge_html(level):
    color = get_level_color(level)
    return f'<span class="badge" style="background-color:{color};color:{"#fff" if level in ["B","A","S","SS","SSS"] else "#000"}">{level}</span>'


# ─── 首页 ──────────────────────────────────────────────────

@app.route('/')
def index():
    hot_tasks = Task.query.filter_by(status=TASK_STATUS_PENDING).order_by(Task.reward.desc()).limit(6).all()
    completed_tasks = Task.query.filter_by(status=TASK_STATUS_COMPLETED).order_by(Task.complete_time.desc()).limit(4).all()
    top_adventurers = User.query.order_by(User.credit_score.desc()).limit(5).all()
    return render_template('index.html', hot_tasks=hot_tasks, completed_tasks=completed_tasks,
                           top_adventurers=top_adventurers)


# ─── 注册 / 登录 ───────────────────────────────────────────

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        nickname = request.form.get('nickname', '').strip()
        gender = request.form.get('gender', '保密')

        # 验证
        if not all([username, email, password, nickname]):
            flash('请填写所有必填项', 'danger')
            return render_template('auth/register.html')
        if password != confirm:
            flash('两次密码不一致', 'danger')
            return render_template('auth/register.html')
        if User.query.filter_by(username=username).first():
            flash('用户名已被注册', 'danger')
            return render_template('auth/register.html')
        if User.query.filter_by(email=email).first():
            flash('邮箱已被注册', 'danger')
            return render_template('auth/register.html')

        user = User(username=username, email=email, nickname=nickname, gender=gender)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('注册成功！新手礼包（100虚拟货币）已发放到账户', 'success')
        login_user(user)
        return redirect(url_for('index'))

    return render_template('auth/register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        account = request.form.get('account', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter(
            (User.username == account) | (User.email == account)
        ).first()

        if not user or not user.check_password(password):
            flash('账号或密码错误', 'danger')
            return render_template('auth/login.html')

        login_user(user)
        next_page = request.args.get('next')
        flash(f'欢迎回来，{user.nickname}！', 'success')
        return redirect(next_page or url_for('index'))

    return render_template('auth/login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('已退出登录', 'info')
    return redirect(url_for('index'))


# ─── 任务发布 ──────────────────────────────────────────────

@app.route('/tasks/create', methods=['GET', 'POST'])
@login_required
def create_task():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        level = request.form.get('level', 'E')
        description = request.form.get('description', '').strip()
        reward = request.form.get('reward', 0, type=float)
        location = request.form.get('location', '').strip()
        expected_time = request.form.get('expected_time', '').strip()

        if not all([title, description]):
            flash('请填写任务标题和描述', 'danger')
            return render_template('tasks/create.html', levels=TASK_LEVELS)

        if reward <= 0:
            flash('报酬必须大于0', 'danger')
            return render_template('tasks/create.html', levels=TASK_LEVELS)

        if current_user.balance < reward:
            flash(f'余额不足！当前余额：{current_user.balance:.2f}，任务报酬：{reward:.2f}', 'danger')
            return render_template('tasks/create.html', levels=TASK_LEVELS)

        # 创建任务
        task = Task(
            title=title,
            level=level,
            description=description,
            reward=reward,
            location=location,
            expected_time=expected_time,
            publisher_id=current_user.id,
        )

        # B级以上需要审核
        if LEVEL_RANK.get(level, 0) >= 3:  # B级及以上
            task.status = TASK_STATUS_REVIEWING
            flash('B级以上任务已提交审核，请等待官方审核通过', 'info')
        else:
            task.status = TASK_STATUS_PENDING
            # 冻结资金
            current_user.balance -= reward
            trans = Transaction(
                task_id=0,  # 先创建任务拿到id后再更新
                publisher_id=current_user.id,
                amount=reward,
                fee=0,
                status='frozen'
            )
            db.session.add(trans)
            db.session.flush()
            flash('任务发布成功！报酬已冻结在官方平台', 'success')

        db.session.add(task)
        db.session.commit()

        # 更新交易的任务id
        if LEVEL_RANK.get(level, 0) < 3:
            trans.task_id = task.id
            db.session.commit()

        return redirect(url_for('task_detail', task_id=task.id))

    return render_template('tasks/create.html', levels=TASK_LEVELS)


# ─── 任务列表 ──────────────────────────────────────────────

@app.route('/tasks')
def task_list():
    page = request.args.get('page', 1, type=int)
    level_filter = request.args.get('level', '')
    status_filter = request.args.get('status', TASK_STATUS_PENDING)
    sort_by = request.args.get('sort', 'newest')

    query = Task.query

    if level_filter and level_filter in TASK_LEVELS:
        query = query.filter_by(level=level_filter)
    if status_filter:
        query = query.filter_by(status=status_filter)

    if sort_by == 'reward_desc':
        query = query.order_by(Task.reward.desc())
    elif sort_by == 'reward_asc':
        query = query.order_by(Task.reward.asc())
    else:
        query = query.order_by(Task.create_time.desc())

    tasks = query.paginate(page=page, per_page=12, error_out=False)
    return render_template('tasks/list.html', tasks=tasks, levels=TASK_LEVELS,
                           current_level=level_filter, current_sort=sort_by,
                           current_status=status_filter)


# ─── 任务详情 ──────────────────────────────────────────────

@app.route('/tasks/<int:task_id>')
def task_detail(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        abort(404)
    publisher = task.publisher
    assignee = task.assignee
    reviews = task.reviews.all()

    # 检查当前用户是否可以接取
    can_accept = False
    if current_user.is_authenticated:
        if (task.status == TASK_STATUS_PENDING
                and task.publisher_id != current_user.id
                and current_user.can_accept_level(task.level)):
            can_accept = True

    return render_template('tasks/detail.html', task=task, publisher=publisher,
                           assignee=assignee, reviews=reviews, can_accept=can_accept)


# ─── 承接任务 ──────────────────────────────────────────────

@app.route('/tasks/<int:task_id>/accept', methods=['POST'])
@login_required
def accept_task(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        abort(404)

    if task.status != TASK_STATUS_PENDING:
        flash('该任务已被承接或已结束', 'danger')
        return redirect(url_for('task_detail', task_id=task_id))

    if task.publisher_id == current_user.id:
        flash('不能承接自己发布的任务', 'danger')
        return redirect(url_for('task_detail', task_id=task_id))

    if not current_user.can_accept_level(task.level):
        flash(f'你需要先完成更多低等级任务才能接取{task.level}级任务', 'danger')
        return redirect(url_for('task_detail', task_id=task_id))

    # 承接任务
    task.assignee_id = current_user.id
    task.status = TASK_STATUS_IN_PROGRESS

    # 如果是B级以上且之前审核通过的任务，需要创建资金冻结
    existing_trans = Transaction.query.filter_by(task_id=task.id).first()
    if not existing_trans:
        # 从发布者账户冻结报酬（如果是审核通过的任务，之前可能没冻结）
        pub = task.publisher
        if pub.balance >= task.reward:
            pub.balance -= task.reward
            trans = Transaction(
                task_id=task.id,
                publisher_id=task.publisher_id,
                assignee_id=current_user.id,
                amount=task.reward,
                fee=task.reward * task.fee_rate,
                status='frozen'
            )
            db.session.add(trans)
        else:
            flash('发布者余额不足，无法承接该任务', 'danger')
            return redirect(url_for('task_detail', task_id=task_id))

    # 通知发布者
    add_notification(
        task.publisher_id,
        f'您的任务"{task.title}"已被{current_user.nickname}承接',
        'task',
        url_for('task_detail', task_id=task.id)
    )

    db.session.commit()
    flash('承接成功！请在任务详情页开启定位授权', 'success')
    return redirect(url_for('task_detail', task_id=task_id))


# ─── 完成任务 ──────────────────────────────────────────────

@app.route('/tasks/<int:task_id>/complete', methods=['POST'])
@login_required
def complete_task(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        abort(404)

    if task.assignee_id != current_user.id and task.publisher_id != current_user.id:
        flash('无权限操作', 'danger')
        return redirect(url_for('task_detail', task_id=task_id))

    if task.status != TASK_STATUS_IN_PROGRESS:
        flash('任务状态不正确', 'danger')
        return redirect(url_for('task_detail', task_id=task_id))

    if current_user.id == task.assignee_id:
        # 冒险者提交完成申请
        task.status = TASK_STATUS_COMPLETED
        task.complete_time = datetime.utcnow()

        # 发放报酬
        trans = Transaction.query.filter_by(task_id=task.id).first()
        if trans:
            trans.status = 'released'
            trans.release_time = datetime.utcnow()
            # 冒险者获得报酬（扣除手续费）
            assignee_pay = trans.amount - trans.fee
            task.assignee.balance += assignee_pay

        # 增加冒险者的任务计数
        task.assignee.mission_count += 1

        add_notification(
            task.publisher_id,
            f'您的任务"{task.title}"已被冒险者标记完成，请确认验收',
            'task',
            url_for('task_detail', task_id=task.id)
        )

        db.session.commit()
        flash('已提交完成申请，等待委托人验收', 'success')

    elif current_user.id == task.publisher_id:
        # 委托人确认完成
        task.status = TASK_STATUS_COMPLETED
        task.complete_time = datetime.utcnow()

        trans = Transaction.query.filter_by(task_id=task.id).first()
        if trans and trans.status == 'frozen':
            trans.status = 'released'
            trans.release_time = datetime.utcnow()
            assignee_pay = trans.amount - trans.fee
            task.assignee.balance += assignee_pay

        task.assignee.mission_count += 1

        add_notification(
            task.assignee_id,
            f'委托人已确认您的任务"{task.title}"完成，报酬已发放',
            'task',
            url_for('task_detail', task_id=task.id)
        )

        db.session.commit()
        flash('已确认任务完成，报酬已发放给冒险者', 'success')

    return redirect(url_for('task_detail', task_id=task_id))


# ─── 取消任务 ──────────────────────────────────────────────

@app.route('/tasks/<int:task_id>/cancel', methods=['POST'])
@login_required
def cancel_task(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        abort(404)

    if task.publisher_id != current_user.id:
        flash('只有发布者可以取消任务', 'danger')
        return redirect(url_for('task_detail', task_id=task_id))

    if task.status in [TASK_STATUS_COMPLETED, TASK_STATUS_CANCELLED]:
        flash('任务已结束', 'danger')
        return redirect(url_for('task_detail', task_id=task_id))

    # 退款
    trans = Transaction.query.filter_by(task_id=task.id, status='frozen').first()
    if trans:
        trans.status = 'refunded'
        task.publisher.balance += trans.amount

    task.status = TASK_STATUS_CANCELLED

    if task.assignee_id:
        add_notification(
            task.assignee_id,
            f'任务"{task.title}"已被发布者取消',
            'task',
            url_for('task_detail', task_id=task.id)
        )

    db.session.commit()
    flash('任务已取消，冻结资金已退还', 'success')
    return redirect(url_for('task_detail', task_id=task_id))


# ─── 个人中心 ──────────────────────────────────────────────

@app.route('/profile')
@login_required
def profile():
    page = request.args.get('page', 1, type=int)
    tab = request.args.get('tab', 'published')

    if tab == 'published':
        tasks = Task.query.filter_by(publisher_id=current_user.id)\
            .order_by(Task.create_time.desc())\
            .paginate(page=page, per_page=10, error_out=False)
    elif tab == 'assigned':
        tasks = Task.query.filter_by(assignee_id=current_user.id)\
            .order_by(Task.create_time.desc())\
            .paginate(page=page, per_page=10, error_out=False)
    else:
        tasks = []

    # 统计信息
    stats = {
        'published_count': Task.query.filter_by(publisher_id=current_user.id).count(),
        'assigned_count': Task.query.filter_by(assignee_id=current_user.id).count(),
        'completed_count': Task.query.filter(
            Task.assignee_id == current_user.id,
            Task.status == TASK_STATUS_COMPLETED
        ).count(),
        'balance': current_user.balance,
        'credit_score': current_user.credit_score,
    }

    # 通知
    notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False)\
        .order_by(Notification.create_time.desc()).limit(20).all()

    return render_template('profile.html', tasks=tasks, stats=stats,
                           notifications=notifications, tab=tab)


@app.route('/profile/edit', methods=['POST'])
@login_required
def edit_profile():
    nickname = request.form.get('nickname', '').strip()
    gender = request.form.get('gender', '保密')
    phone = request.form.get('phone', '').strip()

    if nickname:
        current_user.nickname = nickname
    current_user.gender = gender
    current_user.phone = phone
    db.session.commit()
    flash('个人信息已更新', 'success')
    return redirect(url_for('profile'))


# ─── 评价系统 ──────────────────────────────────────────────

@app.route('/tasks/<int:task_id>/review', methods=['GET', 'POST'])
@login_required
def review_task(task_id):
    task = db.session.get(Task, task_id)
    if not task or task.status != TASK_STATUS_COMPLETED:
        abort(404)

    if current_user.id not in [task.publisher_id, task.assignee_id]:
        abort(403)

    # 检查是否已评价
    existing = Review.query.filter_by(task_id=task_id, from_user_id=current_user.id).first()
    if existing:
        flash('你已评价过该任务', 'info')
        return redirect(url_for('task_detail', task_id=task_id))

    if request.method == 'POST':
        score = request.form.get('score', 5, type=int)
        comment = request.form.get('comment', '').strip()

        if score < 1 or score > 5:
            score = 5

        # 确定角色和评价对象
        if current_user.id == task.publisher_id:
            role = 'publisher'
            to_user_id = task.assignee_id
        else:
            role = 'assignee'
            to_user_id = task.publisher_id

        review = Review(
            task_id=task_id,
            from_user_id=current_user.id,
            to_user_id=to_user_id,
            score=score,
            comment=comment,
            role=role
        )
        db.session.add(review)

        # 更新被评价用户的信誉分
        to_user = db.session.get(User, to_user_id)
        if to_user:
            to_user.credit_score += (score - 3) * 2
            if to_user.credit_score < 0:
                to_user.credit_score = 0

        db.session.commit()
        flash('评价成功', 'success')
        return redirect(url_for('task_detail', task_id=task_id))

    return render_template('tasks/review.html', task=task)


# ─── 定位授权 ──────────────────────────────────────────────

@app.route('/location/update', methods=['POST'])
@login_required
def update_location():
    data = request.get_json()
    if not data:
        return jsonify({'error': '无效数据'}), 400

    lat = data.get('latitude')
    lng = data.get('longitude')
    task_id = data.get('task_id')

    if lat is None or lng is None:
        return jsonify({'error': '缺少坐标'}), 400

    current_user.last_lat = lat
    current_user.last_lng = lng
    current_user.location_enabled = True

    if task_id:
        record = LocationRecord(
            task_id=task_id,
            user_id=current_user.id,
            latitude=lat,
            longitude=lng
        )
        db.session.add(record)

    db.session.commit()
    return jsonify({'status': 'ok'})


@app.route('/location/task/<int:task_id>')
@login_required
def get_task_locations(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        return jsonify({'error': '任务不存在'}), 404

    if current_user.id not in [task.publisher_id, task.assignee_id]:
        return jsonify({'error': '无权限'}), 403

    records = LocationRecord.query.filter_by(task_id=task_id)\
        .order_by(LocationRecord.update_time.desc()).limit(50).all()

    locations = {}
    for r in records:
        username = r.user.nickname if r.user else '未知'
        if username not in locations:
            locations[username] = []
        locations[username].append({
            'lat': r.latitude,
            'lng': r.longitude,
            'time': r.update_time.strftime('%H:%M:%S')
        })

    return jsonify(locations)


# ─── 消息系统 ──────────────────────────────────────────────

@app.route('/messages')
@login_required
def messages():
    # 获取对话列表
    sent = db.session.query(Message.to_user_id).filter(Message.from_user_id == current_user.id).distinct().subquery()
    received = db.session.query(Message.from_user_id).filter(Message.to_user_id == current_user.id).distinct().subquery()

    # 简单实现：显示最近的私信
    recent = Message.query.filter(
        (Message.from_user_id == current_user.id) |
        (Message.to_user_id == current_user.id)
    ).order_by(Message.create_time.desc()).limit(50).all()

    # 获取对话用户
    contact_ids = set()
    for msg in recent:
        if msg.from_user_id == current_user.id:
            contact_ids.add(msg.to_user_id)
        else:
            contact_ids.add(msg.from_user_id)

    contacts = User.query.filter(User.id.in_(contact_ids)).all() if contact_ids else []

    return render_template('messages.html', recent_messages=recent, contacts=contacts)


@app.route('/messages/send', methods=['POST'])
@login_required
def send_message():
    to_user_id = request.form.get('to_user_id', type=int)
    content = request.form.get('content', '').strip()

    if not content:
        flash('消息不能为空', 'danger')
        return redirect(url_for('messages'))

    msg = Message(
        from_user_id=current_user.id,
        to_user_id=to_user_id,
        content=content
    )
    db.session.add(msg)

    add_notification(to_user_id, f'{current_user.nickname}给您发送了一条消息', 'message',
                     url_for('messages'))

    db.session.commit()
    return redirect(url_for('messages'))


@app.route('/messages/unread')
@login_required
def unread_messages():
    count = Message.query.filter_by(to_user_id=current_user.id, is_read=False).count()
    return jsonify({'count': count})


@app.route('/messages/read/<int:msg_id>')
@login_required
def read_message(msg_id):
    msg = db.session.get(Message, msg_id)
    if msg and msg.to_user_id == current_user.id:
        msg.is_read = True
        db.session.commit()
    return redirect(url_for('messages'))


# ─── 关注系统 ──────────────────────────────────────────────

@app.route('/user/<int:user_id>')
def user_profile(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)

    tasks = Task.query.filter_by(assignee_id=user_id, status=TASK_STATUS_COMPLETED)\
        .order_by(Task.complete_time.desc()).limit(10).all()

    is_following = False
    if current_user.is_authenticated:
        is_following = Follow.query.filter_by(
            follower_id=current_user.id, followed_id=user_id
        ).first() is not None

    # 收到的评价
    received_reviews = Review.query.filter_by(to_user_id=user_id).order_by(Review.create_time.desc()).limit(10).all()

    return render_template('user_profile.html', profile_user=user, tasks=tasks,
                           is_following=is_following, received_reviews=received_reviews)


@app.route('/follow/<int:user_id>', methods=['POST'])
@login_required
def toggle_follow(user_id):
    if user_id == current_user.id:
        flash('不能关注自己', 'warning')
        return redirect(url_for('user_profile', user_id=user_id))

    follow = Follow.query.filter_by(follower_id=current_user.id, followed_id=user_id).first()
    if follow:
        db.session.delete(follow)
        db.session.commit()
        flash('已取消关注', 'info')
    else:
        follow = Follow(follower_id=current_user.id, followed_id=user_id)
        db.session.add(follow)
        add_notification(user_id, f'{current_user.nickname}关注了您', 'system',
                         url_for('user_profile', user_id=current_user.id))
        db.session.commit()
        flash('关注成功', 'success')

    return redirect(url_for('user_profile', user_id=user_id))


# ─── 管理后台 ──────────────────────────────────────────────

@app.route('/admin')
@login_required
def admin_panel():
    # 简单的admin面板：查看待审核任务
    pending_reviews = Task.query.filter_by(status=TASK_STATUS_REVIEWING)\
        .order_by(Task.create_time.desc()).all()
    return render_template('admin.html', pending_reviews=pending_reviews)


@app.route('/admin/review/<int:task_id>/<action>', methods=['POST'])
@login_required
def admin_review_task(task_id, action):
    task = db.session.get(Task, task_id)
    if not task or task.status != TASK_STATUS_REVIEWING:
        abort(404)

    if action == 'approve':
        task.status = TASK_STATUS_PENDING
        # 冻结发布者资金
        pub = task.publisher
        if pub.balance >= task.reward:
            pub.balance -= task.reward
            trans = Transaction(
                task_id=task.id,
                publisher_id=task.publisher_id,
                amount=task.reward,
                fee=task.reward * task.fee_rate,
                status='frozen'
            )
            db.session.add(trans)
        add_notification(task.publisher_id, f'您的任务"{task.title}"已通过审核，报酬已冻结',
                         'task', url_for('task_detail', task_id=task.id))
        flash('任务审核通过，已上线', 'success')

    elif action == 'reject':
        task.status = TASK_STATUS_REJECTED
        task.review_comment = request.form.get('comment', '未通过审核')
        add_notification(task.publisher_id, f'您的任务"{task.title}"未通过审核，原因：{task.review_comment}',
                         'task', url_for('task_detail', task_id=task.id))
        flash('已拒绝该任务', 'warning')

    db.session.commit()
    return redirect(url_for('admin_panel'))


# ─── 通知 ──────────────────────────────────────────────────

@app.route('/notifications/read')
@login_required
def read_all_notifications():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    return redirect(url_for('profile'))


# ─── 404 ────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


# ─── 初始化种子数据 ──────────────────────────────────────

@app.route('/init-seed')
def init_seed():
    """访问此路由初始化演示数据（需要token验证）"""
    token = request.args.get('token', '')
    if token != 'guild2026':
        return jsonify({'error': 'token无效'}), 403

    with app.app_context():
        from models import TASK_STATUS_PENDING
        from seed import seed_data
        result = seed_data()
    return jsonify({'status': 'ok', 'message': result})


# ─── 启动入口 ──────────────────────────────────────────────

# gunicorn 启动时自动建表
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
