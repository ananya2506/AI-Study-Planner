import streamlit as st
import pandas as pd

# --------------------------------------------------------
#                   PAGE TITLE
# --------------------------------------------------------
st.set_page_config(page_title="AI Study Planner", layout="centered")
st.title("📘 AI Study Planner – Smart Exam Preparation Assistant")

st.write(
    "This AI-powered tool generates an optimized, personalized study plan "
    "based on workload, topic difficulty, and your available study hours."
)

# --------------------------------------------------------
#                  TIME FORMAT FUNCTION
# --------------------------------------------------------
def format_time(hours):
    """Convert decimal hours to 'X hrs Y mins'."""
    total_minutes = int(hours * 60)
    hrs = total_minutes // 60
    mins = total_minutes % 60

    if hrs > 0 and mins > 0:
        return f"{hrs} hrs {mins} mins"
    elif hrs > 0:
        return f"{hrs} hrs"
    else:
        return f"{mins} mins"


# --------------------------------------------------------
#                   INPUT SECTION
# --------------------------------------------------------
st.header("➤ Enter Subjects, Topics & Difficulty")

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
#                  PROCESSING LOGIC
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
                    tasks.append((subject.strip(), chapter, diff, weight))

    total_weight = sum([t[3] for t in tasks])
    total_hours = days * daily_hours

    # Assign time based on difficulty weight
    for i in range(len(tasks)):
        allocated = (tasks[i][3] / total_weight) * total_hours
        tasks[i] += (allocated,)


   # --------------------------------------------------------
#         TOPIC-WISE TIME ALLOCATION TABLE
# --------------------------------------------------------
st.header("📘 Topic-wise Time Allocation")

topic_data = []
for idx, t in enumerate(tasks, start=1):   # numbering starts from 1
    subject, chapter, diff, weight, hrs = t
    topic_data.append([
        idx,                                  # row number
        subject,
        chapter,
        diff.capitalize(),
        format_time(hrs)
    ])

df_topics = pd.DataFrame(
    topic_data,
    columns=["No.", "Subject", "Topic", "Difficulty", "Allocated Time"]
)

# Reset index (optional)
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

# Reset index to start from 1
df_summary.index = df_summary.index + 1

st.dataframe(df_summary, use_container_width=True)



    # --------------------------------------------------------
    #             AI INSIGHTS SECTION
    # --------------------------------------------------------
    st.header("🧠 AI Insights & Recommendations")

    insights = []

    # Top workload subject
    max_sub = df_summary.loc[df_summary["Allocated Hours"].idxmax(), "Subject"]
    insights.append(f"• Focus more on **{max_sub}**, it has the highest workload.")

    # Many hard topics
    hard_topics = [t for t in tasks if t[2] == "hard"]
    if len(hard_topics) >= 3:
        insights.append(f"• You have **{len(hard_topics)} hard topics** — start them earlier.")

    # Low daily hours
    if daily_hours <= 2:
        insights.append("• Your daily study hours are low. Increase them for better preparation.")

    # Even distribution
    if df_summary["Allocated Hours"].max() - df_summary["Allocated Hours"].min() < 1.5:
        insights.append("• Your subjects are evenly balanced — great job!")

    for ins in insights:
        st.write(ins)


    # --------------------------------------------------------
    #           DAY-BY-DAY DETAILED STUDY PLAN
    # --------------------------------------------------------
    st.header("📅 Day-by-Day Study Plan")

    plan = {}
    day = 1
    hours_left = daily_hours

    for task in tasks:
        sub, chap, diff, weight, hrs = task
        remaining = hrs

        while remaining > 0:
            if day not in plan:
                plan[day] = []

            if hours_left <= 0:
                day += 1
                hours_left = daily_hours
                plan[day] = []

            allocate = min(remaining, hours_left)
            plan[day].append(
                f"{sub} – {chap} ({diff}) → {format_time(allocate)}"
            )
            hours_left -= allocate
            remaining -= allocate

    # Display the plan
    for d in plan:
        st.subheader(f"Day {d}")
        for item in plan[d]:
            st.write("• " + item)


    # --------------------------------------------------------
    #                 DOWNLOAD BUTTON
    # --------------------------------------------------------
    output_text = "AI Study Plan\n\n"
    for d in plan:
        output_text += f"Day {d}\n"
        for item in plan[d]:
            output_text += "- " + item + "\n"
        output_text += "\n"

    st.download_button("📥 Download Plan as Text", output_text)
