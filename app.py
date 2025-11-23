import streamlit as st
import math

st.title("📘 SmartStudy AI – Intelligent Study Planner")
st.write("Get a personalized study plan based on difficulty, priorities, and available time.")

st.header("Enter Your Subjects and Topics")

subjects_input = st.text_area(
    "List subjects with chapters and difficulty (easy/medium/hard):",
    """Example:
Math: Algebra (hard), Calculus (medium), Trigonometry (easy)
Python: Basics (easy), OOP (medium), ML (hard)
"""
)

days = st.number_input("Total days left for exam", min_value=1, value=10)
daily_hours = st.number_input("Available study hours per day", min_value=1, value=3)

if st.button("Generate Study Plan"):
    st.header("📅 Your AI-Generated Study Plan")

    lines = subjects_input.strip().split("\n")
    tasks = []

    diff_weight = {"easy":1, "medium":2, "hard":3}

    for line in lines:
        if ":" in line:
            subject, topics = line.split(":")
            topics_list = topics.split(",")
            for t in topics_list:
                t = t.strip()
                if "(" in t:
                    chapter = t.split("(")[0].strip()
                    diff = t.split("(")[1].replace(")", "").strip().lower()
                    weight = diff_weight.get(diff,1)
                    tasks.append((subject.strip(), chapter, diff, weight))

    total_weight = sum([t[3] for t in tasks])
    total_hours = days * daily_hours

    # hours for each topic
    for i in range(len(tasks)):
        tasks[i] += (round((tasks[i][3] / total_weight) * total_hours, 2),)

    # Generate day-wise plan
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
            plan[day].append(f"{sub} - {chap} ({diff}) → {allocate} hrs")
            hours_left -= allocate
            remaining -= allocate

    # Show plan
    for d in plan:
        st.subheader(f"Day {d}")
        for item in plan[d]:
            st.write("- " + item)

    # Download option
    output_text = ""
    for d in plan:
        output_text += f"\nDay {d}\n"
        for item in plan[d]:
            output_text += "- " + item + "\n"

    st.download_button("📥 Download Study Plan", output_text)
