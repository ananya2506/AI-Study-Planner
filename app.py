import streamlit as st
import pandas as pd
import math
import numpy as np

# --------------------------------------------------------
#                PAGE SETUP
# --------------------------------------------------------
st.set_page_config(page_title="AI Study Planner", layout="centered")
st.image("logo.png", width=120)
st.title("📘 AI Study Planner – Smart Exam Preparation")

st.write(
    "This AI-powered planner creates a personalized, optimized study schedule "
    "based on subject difficulty, workload, and your available study hours."
)

# --------------------------------------------------------
# Convert hours to readable format
# --------------------------------------------------------
def format_time(hours):
    h = int(hours)
    m = int((hours - h) * 60)
    if h == 0:
        return f"{m} min"
    elif m == 0:
        return f"{h} hr"
    else:
        return f"{h} hr {m} min"

# --------------------------------------------------------
#                USER INPUT SECTION
# --------------------------------------------------------
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

# --------------------------------------------------------
#                PROCESSING
# --------------------------------------------------------
if generate:

    lines = subjects_input.strip().split("\n")
    tasks = []

    diff_weight = {"easy": 1, "medium": 2, "hard": 3}

    # Parse input
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
                    tasks.append([subject.strip(), chapter, diff, weight])

    total_weight = sum([t[3] for t in tasks])
    total_hours = days * daily_hours

    # Allocate hours proportionally
    for t in tasks:
        allocated = round((t[3] / total_weight) * total_hours, 2)
        t.append(allocated)

    # --------------------------------------------------------
    #          TOPIC-WISE TIME ALLOCATION TABLE
    # --------------------------------------------------------
    st.header("📘 Topic-wise Time Allocation")

    topic_data = []
    for t in tasks:
        subject, chapter, diff, weight, hrs = t
        topic_data.append([
            subject,
            chapter,
            diff.capitalize(),
            format_time(hrs)
        ])

    df_topics = pd.DataFrame(topic_data, columns=["Subject", "Topic", "Difficulty", "Allocated Time"])
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

    df_summary = pd.DataFrame(
        {
            "Subject": list(subject_summary.keys()),
            "Allocated Hours": list(subject_summary.values()),
        }
    )

    df_summary["Readable Time"] = df_summary["Allocated Hours"].apply(format_time)
    df_summary["% Weight"] = (
        df_summary["Allocated Hours"] / df_summary["Allocated Hours"].sum() * 100
    ).round(2)

    df_summary.index = df_summary.index + 1
    st.dataframe(df_summary, use_container_width=True)


    # --------------------------------------------------------
    #          AI INSIGHTS
    # --------------------------------------------------------
    st.header("🧠 AI Insights & Recommendations")

    insights = []

    max_sub = df_summary.loc[df_summary["Allocated Hours"].idxmax(), "Subject"]
    insights.append(f"• Focus more on **{max_sub}**, it has the highest study load.")

    hard_topics = [t for t in tasks if t[2] == "hard"]
    if len(hard_topics) >= 3:
        insights.append(f"• You have **{len(hard_topics)} hard topics**. Start them early.")

    if daily_hours < 3:
        insights.append("• Daily hours are quite low. Try increasing for better results.")

    for i in insights:
        st.write(i)


    # --------------------------------------------------------
    #          DAY-BY-DAY PLAN
    # --------------------------------------------------------
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

    # Display plan
    for d in plan:
        st.subheader(f"Day {d}")
        for item in plan[d]:
            st.write("• " + item)


    # --------------------------------------------------------
    #          DOWNLOAD BUTTON
    # --------------------------------------------------------
    output_text = "AI Study Plan\n\n"
    for d in plan:
        output_text += f"\nDay {d}\n"
        for item in plan[d]:
            output_text += "- " + item + "\n"

    st.download_button("📥 Download Study Plan", output_text)

