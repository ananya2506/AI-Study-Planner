import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px

# ------------------------------
#           CONFIG
# ------------------------------
st.set_page_config(page_title="AI Study Planner • Final", layout="wide")

# Use uploaded image file as logo (local path included)
logo_path = "/mnt/data/63613500-6316-4b0d-bf04-48e5de9075fb.png"
try:
    st.image(logo_path, width=110)
except Exception:
    pass

st.title("📘 AI Study Planner — Final Pro Edition")
st.markdown(
    "Optimized, AI-assisted study planner with difficulty detection, priority boosting, "
    "what-if simulation, smart balancing and an interactive Gantt timeline."
)

# ------------------------------
#        HELPER FUNCTIONS
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
    """Simple rule-based difficulty predictor (fallback if user doesn't provide)."""
    t = topic.lower()
    hard_kw = ["neural", "deep", "derivative", "proof", "theorem", "optimization", "matrix", "bayes", "differential", "gradient", "regression", "entropy", "convergence"]
    easy_kw = ["basics", "intro", "introduction", "foundation", "overview", "getting started", "simple"]
    medium_kw = ["application", "concept", "practice", "example", "intermediate"]
    if any(k in t for k in hard_kw):
        return "hard"
    if any(k in t for k in easy_kw):
        return "easy"
    if any(k in t for k in medium_kw):
        return "medium"
    # fallback
    return "medium" if len(t.split()) >= 2 else "easy"

def allocate_hours(tasks, days, daily_hours):
    """
    Allocate hours to tasks proportionally using their (possibly boosted) weight.
    tasks: list of [subject, topic, diff, base_weight, boost, hours_placeholder]
    returns tasks with updated hours (float)
    """
    # compute combined weight per task = base_weight * boost
    total_weight = sum([t[3] * t[4] for t in tasks])
    total_available = days * daily_hours
    if total_weight == 0:
        # avoid division by zero
        for t in tasks:
            t[5] = 0.0
        return tasks
    for t in tasks:
        t[5] = (t[3] * t[4] / total_weight) * total_available
    return tasks

def build_day_alloc(tasks, days, daily_hours):
    """
    Create day-by-day allocation list (list length == days) of allocated hours.
    This is a sequential filler that fills each day up to daily_hours before moving forward.
    Returns day_alloc list and plan dict (day -> list of (subject, topic, diff, allocated_chunk))
    """
    plan = {}
    day_alloc = [0.0 for _ in range(days)]
    day_index = 0
    remaining_in_day = daily_hours
    # iterate tasks in order; prefer scheduling hard topics earlier by sorting externally if needed
    for sub, topic, diff, base_w, boost, hrs in tasks:
        remain = hrs
        while remain > 1e-6:
            if day_index >= days:
                # if overflow, append remaining hours to last day
                day_index = days - 1
            can_take = min(remain, remaining_in_day)
            plan.setdefault(day_index + 1, []).append((sub, topic, diff, can_take))
            day_alloc[day_index] += can_take
            remaining_in_day -= can_take
            remain -= can_take
            if remaining_in_day <= 1e-6:
                day_index += 1
                if day_index < days:
                    remaining_in_day = daily_hours
    return day_alloc, plan

def rebalance_tasks(tasks, days, daily_hours):
    """
    Simple rebalance algorithm:
    - Sort tasks by difficulty weight descending (hard first)
    - Re-allocate hours across days greedily to minimize overloaded days
    """
    # Create a flattened list of (subject, topic, diff, hours)
    flat = []
    for sub, topic, diff, base_w, boost, hrs in tasks:
        flat.append([sub, topic, diff, base_w * boost, hrs])
    # sort by weight descending (hardest first)
    flat.sort(key=lambda x: x[3], reverse=True)
    # Create new empty day buckets
    day_buckets = [[] for _ in range(days)]
    day_loads = [0.0 for _ in range(days)]
    # greedy: for each topic, try to place chunks across days where they fit, starting earliest
    for sub, topic, diff, weight, hrs in flat:
        remaining = hrs
        day_idx = 0
        while remaining > 1e-6:
            # find earliest day with enough space
            placed = False
            for d in range(days):
                space = daily_hours - day_loads[d]
                if space > 1e-6:
                    take = min(space, remaining)
                    day_buckets[d].append((sub, topic, diff, take))
                    day_loads[d] += take
                    remaining -= take
                    placed = True
                    if remaining <= 1e-6:
                        break
            if not placed:
                # all days full; append to last day as overflow
                day_buckets[-1].append((sub, topic, diff, remaining))
                day_loads[-1] += remaining
                remaining = 0
    # rebuild plan dict
    plan = {}
    for i, bucket in enumerate(day_buckets, start=1):
        if bucket:
            plan[i] = bucket
    return day_loads, plan

# ------------------------------
#            INPUTS
# ------------------------------
st.header("➤ Enter Subjects, Topics & Difficulty")
st.markdown(
    "Format per line: `Subject: Topic1 (optional_difficulty), Topic2 (optional_difficulty), ...`\n\n"
    "e.g. `Math: Algebra (hard), Calculus (medium)` or `Python: Basics, OOP (medium)`."
)

subjects_input = st.text_area("Subjects & topics", height=160)

left_col, right_col = st.columns(2)
with left_col:
    days = st.number_input("Days left for exam", min_value=1, value=10)
    start_date = st.date_input("Start date", value=datetime.today().date())
with right_col:
    daily_hours = st.number_input("Study hours per day", min_value=1.0, value=3.0, step=0.5)
    auto_detect = st.checkbox("Auto-detect difficulty (if difficulty not provided)", value=True)

# Generate / simulate controls
col_gen, col_sim = st.columns([2, 1])
with col_gen:
    generate = st.button("✨ Generate Plan")
with col_sim:
    st.write("What-if Simulator")
    sim_days = st.number_input("Simulate days (what-if)", min_value=1, value=days)
    sim_hours = st.number_input("Simulate hours/day (what-if)", min_value=1.0, value=daily_hours, step=0.5)
    simulate = st.button("🔁 Simulate What-If")

# ------------------------------
#         MAIN WORKFLOW
# ------------------------------
if generate or simulate:
    # parse input
    lines = [ln.strip() for ln in subjects_input.splitlines() if ln.strip()]
    tasks = []  # each element: [subject, topic, diff, base_weight, boost, allocated_hours]
    base_weights = {"easy": 1.0, "medium": 2.0, "hard": 3.0}

    for line in lines:
        if ":" not in line:
            continue
        subject, topics_blob = line.split(":", 1)
        topic_entries = [t.strip() for t in topics_blob.split(",") if t.strip()]
        for te in topic_entries:
            if "(" in te and ")" in te:
                topic_name = te.split("(")[0].strip()
                diff = te.split("(")[1].split(")")[0].strip().lower()
                if diff not in base_weights:
                    diff = "medium"
            else:
                topic_name = te
                diff = predict_difficulty(topic_name) if auto_detect else "medium"
            tasks.append([subject.strip(), topic_name.strip(), diff, base_weights.get(diff, 1.0), 1.0, 0.0])

    if not tasks:
        st.error("No topics parsed. Please enter at least one subject/topic following the format.")
        st.stop()

    # Build subject list and show priority sliders for each subject
    subjects = sorted(list({t[0] for t in tasks}))
    st.subheader("🔧 Subject Priority Boosts (optional)")
    st.markdown("Use these sliders to increase priority (and time) for subjects you want to prioritize.")
    subject_boosts = {}
    cols = st.columns(min(len(subjects), 4))
    for i, subject in enumerate(subjects):
        col = cols[i % len(cols)]
        # default 1.0; allow up to 2.0x boost
        subject_boosts[subject] = col.slider(f"{subject} priority", 0.5, 2.0, 1.0, 0.1, key=f"boost_{subject}")

    # apply boosts to each task entry
    for t in tasks:
        t[4] = subject_boosts.get(t[0], 1.0)

    # choose which (days/hours) to use: real or simulate
    use_days = sim_days if simulate else days
    use_daily_hours = sim_hours if simulate else daily_hours

    # allocate hours based on base weight * boost
    allocate_hours(tasks, use_days, use_daily_hours)

    # Optionally reorder tasks: Hard topics first for earlier scheduling
    # We'll create a scheduled_tasks list sorted by (weight desc, subject)
    scheduled_tasks = sorted(tasks, key=lambda x: (x[3] * x[4]), reverse=True)

    # Build topic table (numbered from 1)
    st.subheader("📘 Topic-wise Allocation")
    topic_rows = []
    for idx, (sub, topic, diff, base_w, boost, hrs) in enumerate(scheduled_tasks, start=1):
        topic_rows.append([idx, sub, topic, diff.capitalize(), format_time(hrs), round(hrs, 2)])
    df_topics = pd.DataFrame(topic_rows, columns=["No.", "Subject", "Topic", "Difficulty", "Allocated Time", "Hours(decimal)"])
    df_topics.index = df_topics.index + 1
    st.dataframe(df_topics[["No.", "Subject", "Topic", "Difficulty", "Allocated Time"]], use_container_width=True)

    # Build subject summary table
    st.subheader("📊 Subject-wise Breakdown")
    summary = {}
    for sub, topic, diff, base_w, boost, hrs in scheduled_tasks:
        summary[sub] = summary.get(sub, 0) + hrs
    summary_rows = []
    total_alloc = sum(summary.values())
    for i, (sub, hrs) in enumerate(summary.items(), start=1):
        pct = (hrs / total_alloc * 100) if total_alloc > 0 else 0
        summary_rows.append([i, sub, round(hrs, 2), format_time(hrs), round(pct, 2)])
    df_summary = pd.DataFrame(summary_rows, columns=["No.", "Subject", "Allocated Hours", "Readable Time", "% Weight"])
    df_summary.index = df_summary.index + 1
    st.dataframe(df_summary, use_container_width=True)

    # Productivity score & quick stats
    st.subheader("📈 Productivity Score & Stats")
    weighted_sum = sum([t[3] * t[4] for t in scheduled_tasks])
    raw_score = (use_daily_hours * np.sqrt(use_days)) / (1 + (weighted_sum / 4.0))
    prod_score = int(np.clip((raw_score / 2.5) * 100, 0, 100))
    label = "Excellent ✅" if prod_score >= 75 else ("Good 👍" if prod_score >= 50 else ("Fair 🔶" if prod_score >= 30 else "Needs work 🔴"))
    c1, c2, c3 = st.columns(3)
    c1.metric("Productivity Score", f"{prod_score} / 100", label)
    c2.metric("Total Topics", len(scheduled_tasks))
    c3.metric("Total Allocated Hours", f"{round(total_alloc,2)} hrs")

    # Smart alerts — improved: identify real overloaded days
    st.subheader("🧠 Smart Alerts & Recommendations")
    # compute day allocation and plan
    day_alloc, plan = build_day_alloc(scheduled_tasks, use_days, use_daily_hours)
    overloaded_days = [(i+1, hrs) for i, hrs in enumerate(day_alloc) if hrs > use_daily_hours + 1e-6]

    if overloaded_days:
        for d, hrs in overloaded_days:
            st.warning(f"⚠️ Day {d} is overloaded: {format_time(hrs)} (limit: {format_time(use_daily_hours)})")
        st.markdown("You can click **Auto-balance schedule** to try to distribute tasks more evenly across days.")
        if st.button("🔧 Auto-balance schedule"):
            # perform rebalance
            new_day_loads, new_plan = rebalance_tasks(scheduled_tasks, use_days, use_daily_hours)
            day_alloc = new_day_loads
            plan = new_plan
            overloaded_days = [(i+1, hrs) for i, hrs in enumerate(day_alloc) if hrs > use_daily_hours + 1e-6]
            if not overloaded_days:
                st.success("✅ Rebalance successful — no overloaded days.")
            else:
                for d, hrs in overloaded_days:
                    st.warning(f"⚠️ After rebalance Day {d} still overloaded: {format_time(hrs)}")
    else:
        st.success("✅ No overloaded days detected — schedule looks balanced.")

    # friendly suggestions
    st.markdown("**Suggested actions:**")
    suggestions = []
    if any(t[2] == "hard" for t in scheduled_tasks):
        suggestions.append("• Start hard topics early (first 30–40% of schedule).")
    suggestions.append("• Use active recall and spaced repetition for hard topics.")
    suggestions.append("• If overloaded, try increasing daily hours or extending days (use What-if).")
    for s in suggestions:
        st.write(s)

    # Build detailed day-by-day text plan and Gantt rows
    st.subheader("📅 Day-by-Day Plan & Timeline")
    baseline = datetime.combine(start_date, datetime.min.time())  # midnight of start date
    # We'll set study day start at 9:00 AM for timeline aesthetics
    day_start_hour = 9

    gantt_rows = []
    for day_num in sorted(plan.keys()):
        st.markdown(f"**Day {day_num} — {(baseline + timedelta(days=day_num-1)).strftime('%Y-%m-%d')}**")
        for (sub, topic, diff, hrs) in plan[day_num]:
            st.write(f"• {sub} — {topic} ({diff}) → {format_time(hrs)}")
            start_dt = baseline + timedelta(days=day_num-1, hours=day_start_hour)
            # compute start offset from previous tasks scheduled on same day
            # compute how many hours already scheduled earlier this day
            already = sum([r[3] for r in plan[day_num] if r is not None and r != (sub, topic, diff, hrs)])  # not ideal but used only for rough timeline
            # For better timeline ordering, we recreate with cumulative offsets:
    # Recreate gantt with cumulative offsets per day for correct start times
    gantt_rows = []
    for day_num in sorted(plan.keys()):
        cum = 0.0
        for (sub, topic, diff, hrs) in plan[day_num]:
            start_dt = baseline + timedelta(days=day_num-1, hours=day_start_hour + cum)
            end_dt = start_dt + timedelta(hours=hrs)
            gantt_rows.append({"Subject": sub, "Task": f"{topic} ({diff})", "Start": start_dt, "Finish": end_dt, "Hours": round(hrs,2)})
            cum += hrs

    # Plot Gantt timeline
    if gantt_rows:
        df_gantt = pd.DataFrame(gantt_rows)
        fig = px.timeline(df_gantt, x_start="Start", x_end="Finish", y="Subject", color="Subject", hover_data=["Task","Hours"])
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(height=420, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)

    # ------------------------------
    #    EXPORT / DOWNLOAD OPTIONS
    # ------------------------------
    st.subheader("⬇️ Export Plan & Data")
    export_topics = df_topics[["Subject", "Topic", "Difficulty", "Allocated Time", "Hours(decimal)"]].copy()
    st.download_button("Download topic allocation CSV", export_topics.to_csv(index=False), file_name="study_topics.csv", mime="text/csv")

    if gantt_rows:
        df_gantt_export = pd.DataFrame(gantt_rows)
        df_gantt_export["Start"] = df_gantt_export["Start"].apply(lambda x: x.isoformat())
        df_gantt_export["Finish"] = df_gantt_export["Finish"].apply(lambda x: x.isoformat())
        st.download_button("Download timeline CSV", df_gantt_export.to_csv(index=False), file_name="study_timeline.csv", mime="text/csv")

    # Resume-ready description
    st.subheader("📝 One-line Project Summary (for resume/interview)")
    st.code("AI Study Planner — Difficulty-weighted time allocation, AI topic difficulty detection, priority boosting, what-if simulation, auto-balance, and interactive Gantt timeline. Built with Streamlit, pandas, numpy and Plotly.")

    st.success("Plan ready — try What-If simulator, adjust priorities, or auto-balance to refine.")
