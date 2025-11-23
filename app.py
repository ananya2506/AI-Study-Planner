import streamlit as st
import pandas as pd

# ------------------------------
#         PAGE TITLE
# ------------------------------
st.set_page_config(page_title="AI Study Planner", layout="centered")
st.title("📘 AI Study Planner – Smart Exam Preparation")
st.write(
    "This AI-powered planner creates a personalized, optimized study schedule "
    "based on subject difficulty, workload, and your available study hours."
)

# ------------------------------
#         INPUT SECTION
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
#         PROCESSING LOGIC
# ------------------------------
if generate:

    lines = subjects_input.strip().split("\n")
    tasks = []

    diff_weight = {"easy": 1, "medium": 2, "hard": 3}

    # Parse the user input
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

    # Assign hours proportionally to difficulty
    for i in range(len(tasks)):
        allocated = round((tasks[i][3] / total_weight) * total_hours, 2)
        tasks[i] += (allocated,)

    # ------------------------------
    #     SUBJECT-WISE SUMMARY
    # ------------------------------
    st.header("📊 Subject-wise Study Hour Distribution")

    subject_summary = {}
    for t in tasks:
        sub, chap, diff, weight, hrs = t
        subject_summary[sub] = subject_summary.get(sub, 0) + hrs

    df_summary = pd.DataFrame(
        {
            "Subject": subject_summary.keys(),
            "Allocated Hours": subject_summary.values(),
        }
    )

    df_summary["% Weight"] = (
        df_summary["Allocated Hours"] / df_summary["Allocated Hours"].sum() * 100
    ).round(2)

    st.dataframe(df_summary, use_container_width=True)

    # ------------------------------
    #     AI INSIGHTS SECTION
    # ------------------------------
    st.header("🧠 AI Insights & Recommendations")

    insights = []

    # 1. Identify heaviest subject
    max_sub = df_summary.loc[df_summary["Allocated Hours"].idxmax(), "Subject"]
    insights.append(f"• You must focus more on **{max_sub}**, it has the highest workload.")

    # 2. Suggest increasing hours if load > available
    avg_load = total_weight / len(df_summary)
    if daily_hours < 3 and avg_load > 2.2:
        insights.append(
            "• Your study hours per day seem low for the difficulty load. "
            "Try increasing daily hours for better results."
        )

    # 3. Balanced distribution check
    if df_summary["Allocated Hours"].max() - df_summary["Allocated Hours"].min() < 2:
        insights.append("• Your workload is evenly distributed across subjects — great balance!")

    # 4. Hard topics warning
    hard_topics = [t for t in tasks if t[2] == "hard"]
    if len(hard_topics) >= 3:
        insights.append(
            f"• You have **{len(hard_topics)} hard topics**. "
            "Focus on them earlier for better productivity."
        )

    # Display insights
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
            plan[day].append(f"{sub} – {chap} ({diff}) → {allocate} hrs")
            hours_left -= allocate
            remaining -= allocate

    # Output display
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
