from app import db
from models import User, Task, TASK_STATUS_PENDING


def seed_data():
    """初始化演示数据，返回结果说明"""
    from models import User, Task, TASK_STATUS_PENDING

    # ─── 创建用户（已有则跳过） ───
    new_users = 0
    if not User.query.filter_by(username='demo').first():
        demo = User(
            username='demo', email='demo@adventurer.com',
            nickname='冒险者小游', gender='男',
            balance=1000, credit_score=120, mission_count=5
        )
        demo.set_password('demo123')
        db.session.add(demo)
        new_users += 1

    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin', email='admin@guild.com',
            nickname='公会会长', gender='保密',
            balance=99999, credit_score=200, mission_count=99
        )
        admin.set_password('admin123')
        db.session.add(admin)
        new_users += 1

    db.session.commit()

    demo_user = User.query.filter_by(username='demo').first()
    admin_user = User.query.filter_by(username='admin').first()

    # ─── 任务列表 ───
    all_tasks = [
        {'title': '帮我取快递', 'level': 'E', 'description': '帮我去小区快递柜取快递，送到3栋502室。快递数量大概3件，都不重。', 'reward': 30, 'location': '阳光小区'},
        {'title': '上门喂猫', 'level': 'D', 'description': '出差3天，需要人每天上门喂一次猫、换水。猫咪很温顺，有自动猫砂盆。', 'reward': 80, 'location': '幸福花园'},
        {'title': '整理书房', 'level': 'C', 'description': '需要将书房200多本书按类别整理到书架上，并打扫卫生。预计工作4小时。', 'reward': 150, 'location': '书香苑'},
        {'title': '翻译技术文档', 'level': 'B', 'description': '一份20页的英文技术文档需要翻译成中文，内容涉及Python API开发。要求有技术翻译经验。', 'reward': 500, 'location': '线上'},
        {'title': '网站安全检测', 'level': 'A', 'description': '对公司官网进行全面安全渗透测试，发现漏洞并提供修复方案。需要提交详细报告。需持相关资质证书。', 'reward': 2000, 'location': '线上'},
        {'title': '开发自动交易系统', 'level': 'S', 'description': '开发一套基于量化策略的自动交易系统，对接主流交易所API。包含风控模块、回测系统、实盘监控。', 'reward': 10000, 'location': '线上'},
        {'title': '探索失落古城遗迹', 'level': 'SS', 'description': '前往南部雨林深处探索传说中失落的古城遗迹，带回古物和测绘数据。需组队前往，风险极高。', 'reward': 50000, 'location': '南部雨林'},
        {'title': '屠龙任务', 'level': 'SSS', 'description': '北方山脉有恶龙出没，严重威胁周边村落。需要讨伐恶龙，带回龙晶作为凭证。此任务极其危险，建议SSS级冒险者组队前往。', 'reward': 200000, 'location': '北方山脉'},
        # --- E级：生活小事 ---
        {'title': '帮取快递', 'level': 'E', 'description': '丰巢快递柜取件码XXXX，帮我取出送到楼下即可。大概一个鞋盒大小。', 'reward': 20, 'location': '翡翠城'},
        {'title': '代买早餐', 'level': 'E', 'description': '周末想睡懒觉，帮我买一份早餐。豆浆油条加一个茶叶蛋，7点半放门口就行。', 'reward': 15, 'location': '翠苑小区'},
        {'title': '帮遛狗', 'level': 'E', 'description': '我家柯基需要每天早晚各溜一次，每次20分钟。温顺不咬人，就在小区里走走。周末两天。', 'reward': 50, 'location': '龙湖花园'},
        {'title': '超市代购', 'level': 'E', 'description': '帮我从楼下超市买一箱矿泉水和两提纸巾，送到3楼。东西不重就是搬着累。', 'reward': 25, 'location': '华联超市'},
        {'title': '帮打卡', 'level': 'E', 'description': '公司要求每周三去社区服务站打卡签到，我这周出差，帮我代去一次。只需签个到即可。', 'reward': 30, 'location': '花园社区服务站'},
        # --- D级：简单技能 ---
        {'title': '修笔记本电脑', 'level': 'D', 'description': '笔记本开机黑屏但风扇在转，怀疑内存条松了。需要帮忙拆机排查，不复杂但需要动手能力。', 'reward': 80, 'location': '科技园'},
        {'title': '拍摄产品照片', 'level': 'D', 'description': '开淘宝店需要给20件小商品拍白底产品图。手机拍就行，会用修图软件简单调色。提供拍摄台。', 'reward': 100, 'location': '电商产业园'},
        {'title': '组装书柜', 'level': 'D', 'description': '宜家买的毕利书柜，一个人装太费劲，需要搭把手。工具都有，预计1小时搞定。', 'reward': 70, 'location': '书香苑'},
        {'title': '剪辑短视频', 'level': 'D', 'description': '有一段3分钟的探店视频需要剪辑，加字幕和背景音乐。剪映简单操作，提供素材。', 'reward': 90, 'location': '线上'},
        {'title': '照顾宠物仓鼠', 'level': 'D', 'description': '寒假回老家一周，需要人每两天来换一次水、加饲料和垫料。仓鼠很好养，不费事。', 'reward': 60, 'location': '阳光公寓'},
        # --- C级：专业入门 ---
        {'title': '设计海报', 'level': 'C', 'description': '为公司年会设计一张活动海报，尺寸60x90cm。要求有设计感，提供素材和文案。需要会用PS或Canva。', 'reward': 200, 'location': '线上'},
        {'title': '数据录入', 'level': 'C', 'description': '500份纸质问卷需要录入Excel，要求准确率98%以上。预计工作时长6-8小时，可远程做。', 'reward': 180, 'location': '线上'},
        {'title': '布置求婚现场', 'level': 'C', 'description': '周末要求婚，需要帮忙布置餐厅露台。气球、花束、灯带已经买好，需要3-4人帮忙搭起来。预计2小时。', 'reward': 200, 'location': '星空西餐厅'},
        {'title': '家庭网络布线', 'level': 'C', 'description': '新房装修需要从弱电箱拉网线到三个房间，穿管走线。六类线已买好，需要工具和穿线经验。', 'reward': 250, 'location': '滨江新苑'},
        {'title': '代写活动策划方案', 'level': 'C', 'description': '公司团建需要一份完整的策划方案。含活动流程、预算表、物料清单。有模板参考，需要润色和落地细化。', 'reward': 300, 'location': '线上'},
        # --- B级：专业进阶 ---
        {'title': '开发微信小程序', 'level': 'B', 'description': '需要开发一个简单的点餐小程序，包含菜单展示、购物车、下单功能。前后端都要做。提供UI设计稿。', 'reward': 1500, 'location': '线上'},
        {'title': '做全屋深度保洁', 'level': 'B', 'description': '150平新房开荒保洁，含擦窗、厨房除油、卫生间除胶。需要自带工具（吸尘器、玻璃刮等）。预计一整天。', 'reward': 600, 'location': '滨江大宅'},
        {'title': '搭建企业官网', 'level': 'B', 'description': '用WordPress给一家咖啡店搭建品牌官网。包含首页、菜单页、门店地图、在线预订功能。提供服务器和域名。', 'reward': 2000, 'location': '线上'},
        {'title': '同城带货跑腿', 'level': 'B', 'description': '需要从城东取一份合同文件送到城西的公司，限2小时内送达。加急件，需要用电动车。', 'reward': 120, 'location': '全城'},
        {'title': '整理财务报表', 'level': 'B', 'description': '小公司年末需要整理全年收支流水，做成规范的财务报表。有Excel数据，需要归类、核对、出报表。需会计基础。', 'reward': 800, 'location': '线上'},
        # --- A级：精英任务 ---
        {'title': '制作企业宣传片', 'level': 'A', 'description': '为科技公司拍摄制作一段3分钟的企业宣传片。含脚本、拍摄、后期剪辑。要求有专业设备。提供参考样片。', 'reward': 5000, 'location': '市中心'},
        {'title': '全栈开发电商后台', 'level': 'A', 'description': '开发一套电商后台管理系统，含商品管理、订单管理、数据看板。使用Vue+Python技术栈。需提供部署文档。', 'reward': 8000, 'location': '线上'},
        {'title': '室内设计效果图', 'level': 'A', 'description': '130平住宅需要出全套室内设计效果图。含客厅、主卧、儿童房、厨房四个空间。需3DMax或SketchUp出图。', 'reward': 4000, 'location': '线上'},
        {'title': '英语同声传译', 'level': 'A', 'description': '为期3天的国际商务会议需要英语同声传译。涉及人工智能和金融科技领域。需提供相关资质和经验证明。', 'reward': 6000, 'location': '国际会议中心'},
        {'title': '无人机航拍测绘', 'level': 'A', 'description': '建筑工地需要每周一次无人机航拍测绘，生成正射影像和三维模型。需持无人机驾驶证。提供设备。', 'reward': 3500, 'location': '建筑工地'},
        # --- S级：噩梦难度 ---
        {'title': '开发AI客服机器人', 'level': 'S', 'description': '基于大语言模型开发一个智能客服机器人，能回答产品咨询、处理退款、转接人工。需对接企业微信。需NLP经验。', 'reward': 20000, 'location': '线上'},
        {'title': '企业信息安全整改', 'level': 'S', 'description': '对公司现有IT系统进行全面安全评估和整改。含网络架构改造、权限体系重建、等保合规。需团队作业。', 'reward': 30000, 'location': '企业总部'},
        {'title': '开发AR营销应用', 'level': 'S', 'description': '为品牌开发一款AR营销互动应用（微信小程序端），用户扫码后可看到3D产品叠加在现实场景。需Unity3D经验。', 'reward': 25000, 'location': '线上'},
        {'title': '城市级物联网部署', 'level': 'S', 'description': '在智慧城市项目中部署2000+物联网传感器节点。含调试、组网、数据接入平台。需团队和工程资质。', 'reward': 40000, 'location': '全市范围'},
        # --- SS级：传说难度 ---
        {'title': '开发自动驾驶感知系统', 'level': 'SS', 'description': '为无人配送车开发多传感器融合感知系统。融合激光雷达、视觉、毫米波雷达数据。需博士级CV专家带队。', 'reward': 80000, 'location': '线下实验室'},
        {'title': '构建量化对冲基金系统', 'level': 'SS', 'description': '从零搭建一套量化对冲基金交易系统。含行情接入、策略引擎、风控系统、清算系统。需金融工程团队。', 'reward': 120000, 'location': '线上+线下'},
        {'title': '智慧城市大脑架构设计', 'level': 'SS', 'description': '为某省级智慧城市项目设计整体技术架构。含数据中台、AI中台、IoT平台、数字孪生。需提供完整方案。', 'reward': 100000, 'location': '甲方总部'},
        # --- SSS级：神话难度 ---
        {'title': '研发下一代芯片架构', 'level': 'SSS', 'description': '领导研发下一代RISC-V架构AI芯片。含指令集设计、微架构实现、EDA验证。需组建20+人顶尖团队。', 'reward': 500000, 'location': '芯片设计中心'},
        {'title': '发射商业气象卫星', 'level': 'SSS', 'description': '负责商业气象卫星项目全流程：卫星设计、发射、在轨测试、数据运营。需航天领域资深团队。', 'reward': 1000000, 'location': '发射基地'},
        {'title': '破解全球气候模型', 'level': 'SSS', 'description': '构建下一代全球气候预测模型，精度提升一个数量级。需气象学、流体力学、高性能计算顶尖专家联合攻关。', 'reward': 800000, 'location': '超算中心'},
    ]

    existing_titles = set(t.title for t in Task.query.all())
    new_count = 0
    for data in all_tasks:
        if data['title'] in existing_titles:
            continue
        pub = admin_user if data['level'] in ['B', 'A', 'S', 'SS', 'SSS'] else demo_user
        task = Task(
            title=data['title'], level=data['level'],
            description=data['description'], reward=data['reward'],
            location=data['location'], publisher_id=pub.id,
            status=TASK_STATUS_PENDING
        )
        db.session.add(task)
        new_count += 1

    db.session.commit()
    total = Task.query.count()
    return f'新增 {new_count} 个任务，当前共 {total} 个任务。用户: {new_users} 个新用户'


if __name__ == '__main__':
    from app import app
    with app.app_context():
        seed_data()
        print('Seed 完成')
