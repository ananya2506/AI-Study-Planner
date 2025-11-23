import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px

# ------------------------------
#           CONFIG
# ------------------------------
st.set_page_config(page_title="AI Study Planner • Pro", layout="wide")

# Optional logo from uploaded file (local path)
logo_path = "/mnt/data/63613500-6316-4b0d-bf04-48e5de9075fb.png"
try:
    st.image(logo_path, width=120)
except Exception:
    # image might not exist in some environments
    pass

st.title("📘 AI Study Planner – Professional Edition")
st.markdown(
    "Generate an optimized study schedule with AI-assisted difficulty detection, "
    "smart alerts, a productivity score, and a Gantt timeline for visualization."
)


# ------------------------------
#      HELPER / UTILITY FUNCS
# ------------------------------
def format_time(hours):
    """Convert decimal hours to 'X hrs Y mins'."""
    total_minutes = int(round(hours * 60))
    hrs = total_minutes // 60
    mins = total_minutes % 60
    if hrs > 0 and mins > 0:
        return f"{hrs} hrs {mins} mins"
    elif hrs > 0:
        return f"{hrs} hrs"
    else:
        return f"{mins} mins"


def predict_difficulty(topic):
    """
    Simple rule-based difficulty predictor.
    Returns 'easy', 'medium', or 'hard'.
    """
    t = topic.lower()
    # hard keywords
    hard_kw = [
        "neural", "deep", "derivative", "proof", "theorem", "optimization",
        "convergence", "matrix", "bayes", "laplace", "transform", "complex",
        "differential", "gradient", "regression", "backpropagation", "entropy"
    ]
    easy_kw = ["basics", "intro", "foundation", "overview", "introduction", "getting started", "simple"]
    medium_kw = ["application", "concept", "practice", "example", "intermediate"]

    if any(k in t for k in hard_kw):
        return "hard"
    if any(k in t for k in easy_kw):
        return "easy"
    if any(k in t for k in medium_kw):
        return "medium"

    # fallback: length-based heuristic
    words = len(t.split())
    if words >= 3:
        return "medium"
    return "easy"


# ------------------------------
#            INPUTS
# ------------------------------
st.header("➤ Enter Subjects, Topics & Difficulty")

st.markdown(
    "Enter each subject on a new line in this format:\n\n"
    "`Subject: Topic1 (difficulty), Topic2 (difficulty), ...`\n\n"
    "You can also tick **Auto-detect difficulty** and skip the `(difficulty)` for topics."
)

subjects_input = st.text_area(
    "Example:\nMath: Algebra (hard), Calculus (medium), Trigonometry (easy)\nPython: Basics, OOP (medium), ML (hard)",
    height=160,
)

col_left, col_right = st.columns(2)
with col_left:
    days = st.number_input("Days left for exam", min_value=1, value=10)
    start_date = st.date_input("Plan start date (for timeline)", value=datetime.today().date())
with col_right:
    daily_hours = st.number_input("Study hours per day", min_value=1, value=3)
    auto_detect = st.checkbox("🔍 Auto-detect topic difficulty (recommended)", value=True)

generate = st.button("✨ Generate Study Plan")

# ------------------------------
#       MAIN LOGIC
# ------------------------------
if generate:
    # Parse lines and topics
    lines = [ln.strip() for ln in subjects_input.splitlines() if ln.strip()]
    tasks = []  # tuples: (subject, topic, difficulty, weight, hours_allocated_future)

    diff_weight = {"easy": 1.0, "medium": 2.0, "hard": 3.0}

    for line in lines:
        if ":" not in line:
            continue
        subject, topics_blob = line.split(":", 1)
        subjects_topics = [t.strip() for t in topics_blob.split(",") if t.strip()]
        for raw in subjects_topics:
            # if user provided difficulty in parentheses, use it
            if "(" in raw and ")" in raw:
                topic_name = raw.split("(")[0].strip()
                diff = raw.split("(")[1].split(")")[0].strip().lower()
                if diff not in diff_weight:
                    diff = "medium"
            else:
                topic_name = raw
                if auto_detect:
                    diff = predict_difficulty(topic_name)
                else:
                    diff = "medium"
            weight = diff_weight.get(diff, 1.0)
            tasks.append([subject.strip(), topic_name.strip(), diff, weight, 0.0])

    if len(tasks) == 0:
        st.error("No topics found. Please follow the input format and try again.")
        st.stop()

    total_weight = sum([t[3] for t in tasks])
    total_available_hours = days * daily_hours

    # Allocate time proportionally to weights (float hours)
    for row in tasks:
        allocated = (row[3] / total_weight) * total_available_hours
        row[4] = allocated  # set hours

    # ------------------------------
    #  Topic-wise table (numbered from 1)
    # ------------------------------
    st.subheader("📘 Topic-wise Time Allocation")
    topic_rows = []
    for i, (sub, topic, diff, weight, hrs) in enumerate(tasks, start=1):
        topic_rows.append([i, sub, topic, diff.capitalize(), format_time(hrs), round(hrs, 2)])
    df_topics = pd.DataFrame(topic_rows, columns=["No.", "Subject", "Topic", "Difficulty", "Allocated Time", "Hours (decimal)"])
    df_topics.index = df_topics.index + 1
    st.dataframe(df_topics[["No.", "Subject", "Topic", "Difficulty", "Allocated Time"]], use_container_width=True)

    # ------------------------------
    #  Subject-wise summary (numbered from 1)
    # ------------------------------
    st.subheader("📊 Subject-wise Study Hour Breakdown")
    subject_summary = {}
    for sub, topic, diff, weight, hrs in tasks:
        subject_summary[sub] = subject_summary.get(sub, 0) + hrs

    summary_rows = []
    total_allocated = sum(subject_summary.values())
    for i, (sub, hrs) in enumerate(subject_summary.items(), start=1):
        pct = 0.0
        if total_allocated > 0:
            pct = (hrs / total_allocated) * 100
        summary_rows.append([i, sub, hrs, format_time(hrs), round(pct, 2)])
    df_summary = pd.DataFrame(summary_rows, columns=["No.", "Subject", "Allocated Hours", "Readable Time", "% Weight"])
    df_summary.index = df_summary.index + 1
    st.dataframe(df_summary, use_container_width=True)

    # ------------------------------
    # Progress / Productivity score
    # ------------------------------
    st.subheader("📈 Productivity Score & Quick Stats")

    # Productivity metric (simple but explainable)
    # score base: normalized weighted-hours-per-day -> scaled 0..100
    weighted_score = total_weight  # sum of difficulty weights
    # expected_effort = weighted_score * 1.5  # arbitrary normalization constant
    # we'll compute score from ratio: total_available_hours vs weighted_score * days
    effort_need = weighted_score  # proxy
    # compute an index: (available hours per day) * sqrt(days) * scaling
    raw_score = (daily_hours * np.sqrt(days)) / (1 + (weighted_score / 3.0))
    # scale to 0..100
    prod_score = int(np.clip((raw_score / 2.5) * 100, 0, 100))
    # small heuristics for labels
    if prod_score >= 75:
        label = "Excellent ✅"
    elif prod_score >= 50:
        label = "Good 👍"
    elif prod_score >= 30:
        label = "Fair 🔶"
    else:
        label = "Needs work 🔴"

    col_a, col_b, col_c = st.columns([2, 2, 2])
    col_a.metric("Productivity Score", f"{prod_score} / 100", label)
    col_b.metric("Total Topics", len(tasks))
    col_c.metric("Total Allocated Hours", f"{round(total_allocated,2)} hrs")

    # ------------------------------
    #    Smart Alerts & Recommendations
    # ------------------------------
    st.subheader("🧠 Smart Alerts & Recommendations")
    alerts = []

    # 1. If allocated hours > available hours (should be equal but rounding may differ)
    if round(total_allocated, 2) > round(total_available_hours, 2) + 0.01:
        alerts.append("⚠️ Allocated time exceeds available time. Reduce topics or increase daily hours.")

    # 2. If many hard topics
    hard_count = sum(1 for t in tasks if t[2] == "hard")
    if hard_count >= 3:
        alerts.append(f"🔔 You have {hard_count} hard topics — schedule them earlier in the plan.")

    # 3. If daily hours low relative to weighted load
    avg_weight_per_topic = (total_weight / len(tasks)) if tasks else 0
    if daily_hours <= 2 and avg_weight_per_topic > 2:
        alerts.append("⚠️ Daily study hours are low for the difficulty level — consider increasing daily hours.")

    # 4. Check last-day crowding (many hours on final day)
    # build a quick day allocation to evaluate crowding
    day_alloc = [0.0 for _ in range(days)]
    d_idx = 0
    remaining_in_day = daily_hours
    for sub, topic, diff, weight, hrs in tasks:
        remain = hrs
        while remain > 0 and d_idx < days:
            take = min(remain, remaining_in_day)
            day_alloc[d_idx] += take
            remaining_in_day -= take
            remain -= take
            if remaining_in_day <= 1e-6:
                d_idx += 1
                if d_idx < days:
                    remaining_in_day = daily_hours
    if day_alloc[-1] > daily_hours * 0.6:
        alerts.append("⚠️ Final day looks crowded. Move some tasks earlier or increase days/hours.")

    # 5. If any single day > daily_hours (overflow due to rounding), warn
    if max(day_alloc) > daily_hours + 0.01:
        alerts.append("⚠️ Some days exceed daily available hours after allocation — check distribution.")

    if not alerts:
        st.success("No critical alerts — your plan looks feasible ✅")
    else:
        for a in alerts:
            st.warning(a)

    # Provide friendly suggestions (ranked)
    st.markdown("**Suggested actions:**")
    suggestions = []
    suggestions.append("• Start with hard topics in the first 40% of your schedule.")
    suggestions.append("• Use active recall + spaced repetition for hard topics.")
    suggestions.append("• If overloaded, remove or postpone low-weight topics.")
    for s in suggestions:
        st.write(s)

    # ------------------------------
    #     Build Detailed Day-by-Day Plan & Gantt items
    # ------------------------------
    st.subheader("📅 Day-by-Day Plan (detailed) & Gantt Timeline")

    plan = {}  # day -> list of human lines
    gantt_rows = []  # for Plotly: dicts with Task, Start, Finish, Topic
    day = 0
    hours_left = daily_hours
    # We'll use start_date as the day-0 baseline; within-day we track hours as timestamps
    baseline = datetime.combine(start_date, datetime.min.time())

    # track time cursor per day as hours from midnight
    day_cursor_hours = 9.0  # study start hour (9:00 AM) - aesthetic choice
    for sub, topic, diff, weight, hrs in tasks:
        remaining = hrs
        while remaining > 0:
            if day >= days:
                # overflow beyond available days — append to last day
                day = days - 1
            # how many hours we can allocate in the current day
            possible = min(remaining, daily_hours - (day_cursor_hours - 9.0))
            if possible <= 0.0:
                # move to next day
                day += 1
                day_cursor_hours = 9.0
                continue

            # record plan text
            hh = possible
            text = f"{sub} – {topic} ({diff}) → {format_time(hh)}"
            plan.setdefault(day + 1, []).append(text)

            # Gantt: start = baseline + day days + day_cursor_hours hours
            start_dt = baseline + timedelta(days=day, hours=day_cursor_hours)
            end_dt = start_dt + timedelta(hours=hh)
            gantt_rows.append({
                "Subject": sub,
                "Task": f"{topic} ({diff})",
                "Start": start_dt,
                "Finish": end_dt,
                "Hours": hh,
            })

            # advance cursor
            day_cursor_hours += hh
            # if day_cursor_hours reaches study window, move to next day
            if (day_cursor_hours - 9.0) >= daily_hours - 1e-6:
                day += 1
                day_cursor_hours = 9.0

            remaining -= possible

    # Display day-by-day
    for d in sorted(plan.keys()):
        st.markdown(f"**Day {d} — { (baseline + timedelta(days=d-1)).strftime('%Y-%m-%d')}**")
        for item in plan[d]:
            st.write("• " + item)

    # ------------------------------
    #    GANTT / TIMELINE PLOT
    # ------------------------------
    if len(gantt_rows) > 0:
        df_gantt = pd.DataFrame(gantt_rows)
        # Plotly timeline
        fig = px.timeline(
            df_gantt,
            x_start="Start",
            x_end="Finish",
            y="Subject",
            color="Subject",
            hover_data=["Task", "Hours"]
        )
        fig.update_yaxes(autorange="reversed")  # show top-down
        fig.update_layout(height=400, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)

    # ------------------------------
    #    DOWNLOAD / EXPORT
    # ------------------------------
    st.subheader("⬇️ Export Plan")
    # CSV of topics
    export_topics = df_topics.copy()
    export_topics = export_topics.drop(columns=["Hours (decimal)"])
    csv = export_topics.to_csv(index=False)
    st.download_button("Download topic allocation CSV", csv, file_name="study_topics.csv", mime="text/csv")

    # CSV of gantt rows
    if len(gantt_rows) > 0:
        df_gantt_export = df_gantt.copy()
        # convert datetimes to ISO strings
        df_gantt_export["Start"] = df_gantt_export["Start"].apply(lambda x: x.isoformat())
        df_gantt_export["Finish"] = df_gantt_export["Finish"].apply(lambda x: x.isoformat())
        st.download_button("Download timeline CSV", df_gantt_export.to_csv(index=False), file_name="study_timeline.csv", mime="text/csv")

    # quick resume text to copy-paste
    st.subheader("📝 Short Project Summary (for resume/interview)")
    st.code(
        "AI Study Planner — Generates an optimized study schedule using difficulty-weighted "
        "time allocation, AI-based topic difficulty prediction, smart alerts, productivity scoring, "
        "and an interactive Gantt timeline. Built with Streamlit, pandas and Plotly."
    )

    st.success("Plan generated. Use the exported CSV or the Gantt timeline for a polished demo in interviews.")
