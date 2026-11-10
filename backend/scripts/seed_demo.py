"""BE-008 演示种子（Issue #48）。可重复执行，不重复插数据。

    cd backend
    uv run python scripts/seed_demo.py            # 两个演示账号都灌
    uv run python scripts/seed_demo.py student01  # 只灌一个

账号：`student01 / password123`、`student02 / password123`。
第二个账号不是凑数——同组查重、用户隔离、越权 403 这些都得有两个账号才验得出来。

不调用真实 LLM：analysis 与生成题都是手写的固定内容，所以跑这个脚本不花钱、也不会
因为模型抖动导致两次演示的数据不一样。

三处刻意的"不做"，都是踩过的坑：
1. **不写 `questions.difficulty`**。这一列现在没有任何代码读写（正式难度在
   `analysis.difficulty`），种子去填它等于凭空造第二个真源。
2. **不伪造 `image_path`**。指向不存在的文件会让详情页取图 404，比 NULL 更糟；
   演示图片走真实上传。
3. **不给软删行**。种子数据全部是活跃题，避免统计口径里"总数和对不上"的怀疑。
"""
from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/

# Windows 控制台默认 GBK，中文汇总会打成乱码（和 scripts/spike_llm.py 同一个坑）
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy import func, select  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.db.base import utcnow  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    GeneratedQuestion,
    GenerationTask,
    PracticeRecord,
    Question,
    Tag,
    User,
)
from app.schemas.question import count_blanks, validate_type_payload  # noqa: E402

PASSWORD = "password123"
DEMO_USERS = ("student01", "student02")

# (题干, 题型, 学科, 章节, 答案, 解析, 掌握状态, [知识点])
QUESTIONS = [
    ("求函数 $f(x)=x^3-3x+1$ 的极值。", "solve", "高等数学", "导数与极值",
     "极大值 $f(-1)=3$，极小值 $f(1)=-1$", "$f'(x)=3x^2-3$，令其为 0 得 $x=\\pm1$，列表判号得极值。",
     "reviewing", ["导数", "极值", "单调性"]),
    ("设 $f(x)=x^2-2x+3$，则 $f(x)$ 的最小值为（ ）。", "choice", "高等数学", "函数与极限",
     "选 B", "配方 $f(x)=(x-1)^2+2$，最小值 2。", "unmastered",
     ["二次函数", "配方法"]),
    ("计算极限 $\\lim_{x\\to 0}\\dfrac{\\sin 3x}{x}= $ ___。", "blank", "高等数学", "函数与极限",
     "$3$", "等价无穷小 $\\sin 3x\\sim 3x$，故极限为 3。", "mastered",
     ["极限", "等价无穷小"]),
    ("在直角三角形 $ABC$ 中，$\\angle C=90^\\circ$，$AC=4$，$BC=3$，$CD$ 是斜边 $AB$ 上的高，求 $CD$。",
     "solve", "高等数学", "几何应用",
     "$AB=5$，由等面积 $CD=\\dfrac{AC\\cdot BC}{AB}=\\dfrac{12}{5}$。",
     "先用勾股定理求斜边，再用面积法求斜边上的高。", "unmastered", ["三角形", "勾股定理"]),
    ("设向量组 $a_1=(1,2,1)$，$a_2=(2,5,3)$，$a_3=(1,1,0)$，判断其线性相关性。", "solve",
     "线性代数", "向量空间", "行列式为 0，故线性相关。", "把三个向量排成矩阵求秩，秩小于 3 即相关。",
     "reviewing", ["线性相关", "矩阵的秩"]),
    ("矩阵 $A=\\begin{pmatrix}2&1\\\\1&2\\end{pmatrix}$ 的特征值为 ___ 和 ___。", "blank",
     "线性代数", "特征值", None, "解 $|A-\\lambda I|=0$ 得 $\\lambda_1=3$、$\\lambda_2=1$。",
     "unmastered", ["特征值", "行列式"]),
    ("设随机变量 $X,Y$ 都服从标准正态分布，则（ ）。", "choice", "概率论与数理统计", "多维随机变量",
     "选 C", "$X^2+Y^2$ 服从 $\\chi^2(2)$，选项里只有 C 成立。", "reviewing",
     ["正态分布", "$\\chi^2$ 分布"]),
    ("设总体 $X$ 的方差为 1，容量 $n=100$，样本均值为 5，求均值的 0.95 置信区间。", "solve",
     "概率论与数理统计", "参数估计", "$[4.804, 5.196]$。",
     "$\\bar x\\pm z_{0.025}\\dfrac{\\sigma}{\\sqrt n}=5\\pm1.96\\times0.1$。", "unmastered",
     ["置信区间", "样本均值"]),
    ("曲线 $y=\\ln x$ 在点 $(1,0)$ 处的切线方程为 ___。", "blank", "高等数学", "导数与极值",
     None, "$y'=1/x$，斜率 1，切线 $y=x-1$。", "mastered", ["切线方程", "导数"]),
    ("从总体 $X\\sim N(60,15^2)$ 中抽取容量为 100 的样本，求样本均值与总体均值之差的绝对值大于 3 的概率。",
     "solve", "概率论与数理统计", "参数估计", "约 $0.046$。",
     "$\\bar X\\sim N(60, 15^2/100)$，标准化后查表。", "reviewing", ["正态分布", "标准化"]),
    ("计算定积分 $\\int_0^1 x\\,e^{x}\\,dx$。", "solve", "高等数学", "不定积分与定积分",
     "$1$。", "分部积分：$\\int x e^x dx = (x-1)e^x + C$，代限得 1。", "mastered",
     ["分部积分", "定积分"]),
    ("设 $X_1,\\dots,X_n$ 是来自总体 $X\\sim N(\\mu,2^2)$ 的样本，下列变量中（ ）不是统计量。",
     "choice", "概率论与数理统计", "基本概念", "选 B",
     "统计量不能含未知参数，B 里出现了 $\\mu$。", "unmastered", ["统计量", "样本"]),
]

# 选择题的选项按题给，不共用一套：演示时人一眼就能看出"$0$/$2$/$3$/$4$ 和正态分布题不搭"。
CHOICE_OPTIONS = {
    "设 $f(x)=x^2-2x+3$，则 $f(x)$ 的最小值为（ ）。":
        ["$0$", "$2$", "$3$", "$4$"],
    "设随机变量 $X,Y$ 都服从标准正态分布，则（ ）。":
        ["$X+Y$ 服从 $N(0,1)$", "$X^2+Y^2$ 服从 $\\chi^2(1)$",
         "$X^2+Y^2$ 服从 $\\chi^2(2)$", "$X/Y$ 服从 $N(0,1)$"],
    "设 $X_1,\\dots,X_n$ 是来自总体 $X\\sim N(\\mu,2^2)$ 的样本，下列变量中（ ）不是统计量。":
        ["$\\sum_{i=1}^{n}(X_i-3)^2$", "$\\sum_{i=1}^{n}\\dfrac{(X_i-\\mu)^2}{4}$",
         "$\\min\\{X_1,\\dots,X_n\\}$", "$\\sum_{i=1}^{n}(X_i-\\bar X)^2$"],
}

# 填空题的空位答案。种子必须自带答案：`blanks` 里留空会被 `validate_type_payload` 判死
# （"每个空位都要有答案"），那样灌出来的行在编辑器里一保存就 400。
# 识图阶段留空是另一回事——那是"图上确实没印答案"的如实交付，不该由种子来模仿。
BLANK_ANSWERS = {
    "计算极限 $\\lim_{x\\to 0}\\dfrac{\\sin 3x}{x}= $ ___。": ["$3$"],
    "矩阵 $A=\\begin{pmatrix}2&1\\\\1&2\\end{pmatrix}$ 的特征值为 ___ 和 ___。": ["$3$", "$1$"],
    "曲线 $y=\\ln x$ 在点 $(1,0)$ 处的切线方程为 ___。": ["$y=x-1$"],
}

# 每个账号的练习记录数（issue 要求 20+）
PRACTICE_PLAN = {"student01": 24, "student02": 21}


def _tags(session, names: list[str]) -> list[Tag]:
    out = []
    for name in names:
        tag = session.scalar(select(Tag).where(Tag.name == name))
        if tag is None:
            tag = Tag(name=name, type="knowledge_point")
            session.add(tag)
            session.flush()
        out.append(tag)
    return out


def _analysis(topic: str, difficulty: str, points: list[str], reason: str, summary: str) -> dict:
    """正式难度写在这里，不写 `questions.difficulty`（见模块 docstring 第 1 条）。"""
    return {
        "topic_type": topic,
        "difficulty": difficulty,
        "knowledge_points": points,
        "error_reasons": [reason],
        "solution_summary": summary,
    }


def _seed_user(session, username: str) -> dict:
    user = session.scalar(select(User).where(User.username == username))
    if user is None:
        user = User(username=username, email=f"{username}@demo.local",
                    password_hash=hash_password(PASSWORD))
        session.add(user)
        session.flush()
        created_user = True
    else:
        created_user = False

    existing = set(session.scalars(
        select(Question.content_md).where(
            Question.user_id == user.id, Question.deleted_at.is_(None))))
    new_questions: list[Question] = []
    # 时间锚点跟随父题（列表按 created_at 倒序，第 0 题必须排最前）：
    # 用 utcnow() 的话，部分重跑时补插的题会顶到父题前面，
    # 演示要点到列表底部才看得到挂着三格生成题的那道
    existing_parent = session.scalar(select(Question).where(
        Question.user_id == user.id, Question.content_md == QUESTIONS[0][0],
        Question.deleted_at.is_(None)))
    anchor = existing_parent.created_at if existing_parent else utcnow()
    # 全部题目都是纯文本可作答：含图题在种子阶段没有配图，写「如图」等于演示时答不出来，
    # 所以那道三角形的题已经改成自包含文本（斜边上的高）
    for position, (content, qtype, subject, chapter, answer, explanation, mastery, points) in enumerate(QUESTIONS):
        if content in existing:
            continue
        options = None
        blanks = None
        if qtype == "choice":
            labels = CHOICE_OPTIONS[content]
            options = [{"label": chr(ord("A") + i), "content_md": text}
                       for i, text in enumerate(labels)]
        elif qtype == "blank":
            answers = BLANK_ANSWERS[content]
            markers = count_blanks(content)
            if markers != len(answers):
                raise SystemExit(f"种子数据自相矛盾：{content[:30]} 空位 {markers} 个、答案 {len(answers)} 个")
            blanks = [{"index": i + 1, "answer_md": answers[i]} for i in range(markers)]
        # 每一行都先过一遍应用自己的判据：种子灌出非法行，等于把故障推迟到用户点开它那一刻
        validate_type_payload(qtype, content, options, blanks)
        question = Question(
            user_id=user.id, subject=subject, chapter=chapter, source_type="text",
            content_md=content, answer_md=answer, explanation_md=explanation,
            question_type=qtype, options=options, blanks=blanks,
            mastery_status=mastery, status="confirmed",
            analysis=_analysis(subject, {"solve": "medium", "choice": "easy", "blank": "medium"}[qtype],
                               points, "概念边界没分清，按定义再走一遍", explanation),
            tags=_tags(session, points),
            # 不伪造 image_path：见模块 docstring 第 2 条
            # 按题目定义顺序从锚点往前铺：父题（第 0 题）永远是列表首条
            created_at=anchor - timedelta(hours=position),
            updated_at=anchor - timedelta(hours=position),
        )
        session.add(question)
        new_questions.append(question)
    session.flush()

    # 生成题：给第一道活跃错题铺满三格（ADR-006 的 target_index/difficulty）
    # 父题按题干认，不按"最早/最新一条"认：位置会随用户后来新增的题漂移，
    # 一旦漂移，重复执行就会再插一组三格，"可重复执行"这条验收就废了
    parent = session.scalar(select(Question).where(
        Question.user_id == user.id, Question.content_md == QUESTIONS[0][0],
        Question.deleted_at.is_(None)))
    if parent is None:
        raise SystemExit("种子父题没找到，生成题无法挂靠——请检查库里 student 的错题是否被删过")
    made_generated = 0
    slots = [("easy", "求 $2x^3-6x+1$ 的极值点与极值。",
              "$x=-1$ 处极大值 $5$，$x=1$ 处极小值 $-3$。"),
             ("medium", "求 $g(x)=x^3-3x^2+2$ 的极值点与极值。", "$x=0$ 处极大值 2，$x=2$ 处极小值 $-2$。"),
             ("hard", "设 $h(x)=x^3-3ax+1$ 在 $x=1$ 处取极值，求 $a$ 与该点极值。",
              "$a=1$，极小值 $h(1)=-1$。")]
    for index, (difficulty, content, answer) in enumerate(slots, start=1):
        exists = session.scalar(select(GeneratedQuestion).where(
            GeneratedQuestion.parent_question_id == parent.id,
            GeneratedQuestion.target_index == index,
            GeneratedQuestion.deleted_at.is_(None)))
        if exists is not None:
            continue
        # 三格都按解答题给：seed 不去模仿"换题型"，那是真模型的行为，
        # 造出来只会让演示里出现一批库里没有的脏结构
        validate_type_payload("solve", content, None, None)
        session.add(GeneratedQuestion(
            parent_question_id=parent.id, user_id=user.id, content_md=content,
            answer_md=answer, explanation_md="按求导→驻点→判号的固定流程做。",
            question_type="solve", difficulty=difficulty, target_index=index,
            model="seed", prompt_version="generate_v2",
            validation_status="valid", validation_score=0.92))
        made_generated += 1
    session.flush()

    # 三段面板的数据源：前端详情页用 `detail.tasks.some(isSegmentTask)` 决定渲染三段面板，
    # 只插 generated_questions 不插 generation_task，演示会退回旧的 GenerationProgress，
    # 任务中心也没有「生题 3/3」分组——结果对了、过程区却是空的
    made_tasks = 0
    for index, (difficulty, _content, _answer) in enumerate(slots, start=1):
        exists_task = session.scalar(select(GenerationTask).where(
            GenerationTask.question_id == parent.id,
            GenerationTask.user_id == user.id,
            GenerationTask.stage == "quiz",
            GenerationTask.target_index == index))
        if exists_task is not None:
            continue
        started = anchor - timedelta(minutes=index)
        session.add(GenerationTask(
            question_id=parent.id, user_id=user.id, stage="quiz", status="done",
            target_index=index, difficulty=difficulty, retry_index=0,
            created_at=started, started_at=started,
            finished_at=started + timedelta(seconds=20)))
        made_tasks += 1

    # 练习流水：铺在最近 10 天，recent_trend 才有形状
    gen_rows = list(session.scalars(select(GeneratedQuestion).where(
        GeneratedQuestion.user_id == user.id,
        GeneratedQuestion.deleted_at.is_(None))))
    already = session.scalar(select(PracticeRecord.id).where(
        PracticeRecord.user_id == user.id).limit(1))
    made_practice = 0
    if already is None and gen_rows:
        plan = PRACTICE_PLAN.get(username, 20)
        base = utcnow()
        for i in range(plan):
            target = gen_rows[i % len(gen_rows)]
            correct = (i % 3) != 0          # 约 2/3 正确，看起来像真在进步
            session.add(PracticeRecord(
                user_id=user.id, generated_question_id=target.id,
                user_answer=None if i % 4 else "设 $f'(x)=0$ 得驻点，再判号。",
                is_correct=correct, duration_seconds=40 + (i * 17) % 220,
                created_at=base - timedelta(days=(i * 10) // plan, hours=i % 9),
                updated_at=base - timedelta(days=(i * 10) // plan, hours=i % 9)))
            made_practice += 1

    total_questions = session.scalar(
        select(func.count(Question.id)).where(
            Question.user_id == user.id, Question.deleted_at.is_(None))
    )
    total_practice = session.scalar(
        select(func.count(PracticeRecord.id)).where(PracticeRecord.user_id == user.id)
    )
    return {
        "user": username,
        "user_created": created_user,
        "questions_added": len(new_questions),
        "questions_total": total_questions,
        "generated_added": made_generated,
        "tasks_added": made_tasks,
        "practice_added": made_practice,
        "practice_total": total_practice,
    }


def main() -> None:
    wanted = sys.argv[1:] or list(DEMO_USERS)
    unknown = [u for u in wanted if u not in DEMO_USERS]
    if unknown:
        raise SystemExit(f"只允许演示账号 {DEMO_USERS}，收到 {unknown}——"
                         "种子不往真实账号上灌数据")
    with SessionLocal() as session:
        for username in wanted:
            summary = _seed_user(session, username)
            session.commit()
            print(f"[seed] {username}: 新建用户={summary['user_created']} "
                  f"新增错题={summary['questions_added']}（活跃共 {summary['questions_total']} 道）"
                  f" 新增生成题={summary['generated_added']} 新增任务={summary['tasks_added']}"
                  f" 新增练习={summary['practice_added']}")
        # 复核 issue 的验收项：三类掌握状态之和 == 活跃错题数（统计页那条断言）
        for username in wanted:
            counts = dict(session.execute(
                select(Question.mastery_status, func.count(Question.id))
                .join(User, User.id == Question.user_id)
                .where(User.username == username, Question.deleted_at.is_(None))
                .group_by(Question.mastery_status)
            ).all())
            total = sum(counts.values())
            print(f"[check] {username} 掌握度分布={counts} 合计={total} "
                  f"（{'OK' if total >= 10 else '题数不足 10'}）")
    print("[seed] 完成。重复执行本脚本不会重复插数据。")


if __name__ == "__main__":
    main()
