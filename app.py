import streamlit as st
import pandas as pd

# ------------------------------
#        PAGE TITLE
# ------------------------------
st.set_page_config(page_title="AI Study Planner", layout="centered")
st.title("📘 AI Study Planner – Smart Exam Preparation")
st.write(
    "This AI-powered planner creates a personalized, optimized study schedule "
    "based on subject difficulty, workload, and your available study hours."
)

# ------------------------------
#        INPUT SECTION
# ------------------------------
st.header("➤ Enter Your Subjects, Chapters & Difficulty")

subjects_input = st.text_area(
    "Format: Subject: Topic (easy/medium/hard), Topic (difficulty)...",
    """Example:
Math: Algebra (hard), Calculus (medium), Trigonometry (easy)
Python: Basics (easy), OOP (medium), ML (hard)
""",
    height=150
)

col1, col2 = st.columns(2)
days = col1.number_input("Days left for exam", min_value=1, value=10)
daily_hours = col2.number_input("Study hours per day", min_value=1, value=3)

generate = st.button("✨ Generate Study Plan")

# ------------------------------
#         HELPER FUNCTION
# ------------------------------
def format_time(hours):
    h = int(hours)
    m = round((hours - h) * 60)
    if m == 0:
        return f"{h} hr"
    if h == 0:
        return f"{m} min"
    return f"{h} hr {m} min"

# ------------------------------
#         PROCESSING LOGIC
# ------------------------------
if generate:

    lines = subjects_input.strip().split("\n")
    tasks = []

    diff_weight = {"easy": 1, "medium": 2, "hard": 3}

    # Parse subjects & topics
    for line in lines:
        if ":" in line:
            subject, topics = line.split(":")
            topics_list = topics.split(",")

            for t in topics_list:
                t = t.strip()
                if "(" in t:
                    chapter = t.split("(")[0].strip()
                    diff = t.split("(")[1].replace(")", "").strip().lower()
                    weight = diff_weight.get(diff, 1)
                    tasks.append((subject.strip(), chapter, diff, weight))

    total_weight = sum([t[3] for t in tasks])
    total_hours = days * daily_hours

    # Allocate proportional hours
    for i in range(len(tasks)):
        allocated = round((tasks[i][3] / total_weight) * total_hours, 2)
        tasks[i] += (allocated,)

    # --------------------------------------------------------
    #         TOPIC-WISE TIME ALLOCATION TABLE
    # --------------------------------------------------------
    st.header("📘 Topic-wise Time Allocation")

    topic_data = []
    for idx, t in enumerate(tasks, start=1):
        subject, chapter, diff, weight, hrs = t
        topic_data.append([
            idx,
            subject,
            chapter,
            diff.capitalize(),
            format_time(hrs)
        ])

    df_topics = pd.DataFrame(
        topic_data,
        columns=["No.", "Subject", "Topic", "Difficulty", "Allocated Time"]
    )

    df_topics.index = df_topics.index + 1
    st.dataframe(df_topics, use_container_width=True)

    # --------------------------------------------------------
    #          SUBJECT-WISE SUMMARY TABLE
    # --------------------------------------------------------
    st.header("📊 Subject-wise Study Hour Breakdown")

    subject_summary = {}
    for t in tasks:
        sub, chap, diff, weight, hrs = t
        subject_summary[sub] = subject_summary.get(sub, 0) + hrs

    summary_data = []
    for idx, (sub, hrs) in enumerate(subject_summary.items(), start=1):
        summary_data.append([
            idx,
            sub,
            hrs,
            format_time(hrs),
            round((hrs / sum(subject_summary.values())) * 100, 2)
        ])

    df_summary = pd.DataFrame(
        summary_data,
        columns=["No.", "Subject", "Allocated Hours", "Readable Time", "% Weight"]
    )

    df_summary.index = df_summary.index + 1
    st.dataframe(df_summary, use_container_width=True)

    # ------------------------------
    #     AI INSIGHTS
    # ------------------------------
    st.header("🧠 AI Insights & Recommendations")

    insights = []

    # 1. Heaviest subject
    max_sub = df_summary.loc[df_summary["Allocated Hours"].idxmax(), "Subject"]
    insights.append(f"• You must focus more on **{max_sub}**, it has the highest workload.")

    # 2. Suggest more hours if load extremely high
    avg_load = total_weight / len(df_summary)
    if daily_hours < 3 and avg_load > 2.2:
        insights.append(
            "• Your study hours per day seem low for the difficulty load. "
            "Try increasing daily hours for better results."
        )

    # 3. Balanced check
    if df_summary["Allocated Hours"].max() - df_summary["Allocated Hours"].min() < 2:
        insights.append("• Your workload is evenly distributed — great balance!")

    # 4. Hard topics
    hard_topics_count = len([t for t in tasks if t[2] == "hard"])
    if hard_topics_count >= 3:
        insights.append(
            f"• You have **{hard_topics_count} hard topics**. Focus on them first."
        )

    for ins in insights:
        st.write(ins)

    # ------------------------------
    #      DAY-BY-DAY PLAN
    # ------------------------------
    st.header("📅 Detailed Day-by-Day Study Plan")

    plan = {}
    day = 1
    hours_left = daily_hours

    for task in tasks:
        sub, chap, diff, w, hrs = task
        remaining = hrs

        while remaining > 0:
            if day not in plan:
                plan[day] = []

            if hours_left == 0:
                day += 1
                hours_left = daily_hours
                plan[day] = []

            allocate = min(remaining, hours_left)
            plan[day].append(f"{sub} – {chap} ({diff}) → {format_time(allocate)}")
            hours_left -= allocate
            remaining -= allocate

    for d in plan:
        st.subheader(f"Day {d}")
        for item in plan[d]:
            st.write("• " + item)

    # ------------------------------
    #     DOWNLOAD PLAN BUTTON
    # ------------------------------
    output_text = "AI Study Plan\n\n"
    for d in plan:
        output_text += f"Day {d}\n"
        for item in plan[d]:
            output_text += "- " + item + "\n"
        output_text += "\n"

    st.download_button("📥 Download Plan as Text", output_text)
