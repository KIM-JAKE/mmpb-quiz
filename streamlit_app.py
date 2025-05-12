# streamlit_app.py
import streamlit as st
import pandas as pd
from PIL import Image
import os

def resolve_path(raw_path: str, data_dir="data"):
    """
    Resolve an image path relative to data_dir using the CSV path.
    Only valid if the file exists exactly at data_dir/raw_path.
    """
    # Normalize path separators
    rel = raw_path.replace("\\", "/").lstrip("/")
    candidate = os.path.join(data_dir, rel)
    return candidate

@st.cache_data
def load_questions(csv_path: str, data_dir: str = "data"):
    # 1) Read everything
    df = pd.read_csv(csv_path, encoding="utf-8").fillna("")
    records = df.to_dict(orient="records")

    # 2) Resolve each path and only keep rows whose image actually exists
    valid = []
    for r in records:
        img = resolve_path(r["image_path"], data_dir)
        # skip any image not located inside data_dir
        abs_data = os.path.abspath(data_dir)
        abs_img = os.path.abspath(img)
        if not abs_img.startswith(abs_data + os.sep):
            continue
        # skip any image not under the "test" subdirectory
        if os.sep + "test" + os.sep not in abs_img:
            continue
        if os.path.exists(img):
            r["_img"] = img
            valid.append(r)

    # Rename specific categories for display
    mapping = {"overconcept": "appropriateness", "inconsistency": "coherency"}
    for r in valid:
        if r.get("l2-category") in mapping:
            r["l2-category"] = mapping[r["l2-category"]]
        if r.get("attribute") in mapping:
            r["attribute"] = mapping[r["attribute"]]
    return valid

def main():
    st.set_page_config(page_title="Beat the VLMs: MMPB Quiz", layout="centered")
    st.title("Beat the VLMs: MMPB Quiz")

    # Load all valid questions from data directory
    qs = load_questions("dataset5.csv", data_dir="data")[:]
    st.caption(f"🔍 Loaded {len(qs)} questions")

    # Initialize state
    if "idx" not in st.session_state:
        st.session_state.idx = 0
        st.session_state.score = 0
        st.session_state.responses = []  # to store per-question results

    idx = st.session_state.idx

    # ────────────────────────────────────────────────────────
    # Quiz in progress
    # ────────────────────────────────────────────────────────
    if idx < len(qs):
        q = qs[idx]

        col_q, col_score = st.columns([4, 1])
        with col_score:
            st.markdown(
                f"""
                <div style="text-align:center; line-height:1.2;">
                  <div style="font-size:14px; font-weight:600; color:#666;">Score</div>
                  <div style="font-size:18px; font-weight:700;">{st.session_state.score} / {len(qs)}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col_q:
            st.markdown(f"**{q['description_moderate']}**\n\n**{q['preference']}**")
            try:
                img = Image.open(q["_img"])
                st.image(img, use_container_width=True)
            except Exception as e:
                st.error(f"Couldn’t load image:\n{q['_img']}\n{e}")
            st.markdown(f"**Q{idx+1}. {q['question']}**")

            # Prepare option mapping (letter->text) or Yes/No
            opt_keys = [k for k in ("A","B","C","D") if q.get(k)]
            if opt_keys:
                opts_dict = {k: q[k] for k in opt_keys}
            else:
                opts_dict = {"Yes": "Yes", "No": "No"}

            with st.form(key=f"quiz_form_{idx}"):
                choice_key = st.radio("Select an option:", list(opts_dict.keys()), format_func=lambda x: opts_dict[x])
                submitted = st.form_submit_button("Next", use_container_width=True)

                if submitted:
                    # Determine correctness: if answer is a letter key, compare keys; else compare text
                    ans = q["answer"]
                    selected_letter = choice_key
                    selected_text = opts_dict[choice_key]
                    if ans in opts_dict:
                        correct = (selected_letter == ans)
                    else:
                        correct = (selected_text == ans)

                    st.session_state.responses.append({
                        "category":  q.get("category",""),
                        "attribute": q.get("attribute",""),
                        "l2":        q.get("l2-category",""),
                        "correct":   correct
                    })
                    if correct:
                        st.session_state.score += 1
                    st.session_state.idx += 1

    # ────────────────────────────────────────────────────────
    # Quiz complete → show breakdown
    # ────────────────────────────────────────────────────────
    else:
        st.markdown("## 🎉 Quiz Complete!")
        st.markdown(f"**Your total score: {st.session_state.score} / {len(qs)}**")

        # Convert to DataFrame
        df = pd.DataFrame(st.session_state.responses)

        # 1) by category
        df_cat = df.groupby("category")["correct"].agg(correct="sum", total="count")
        st.markdown("### Score by Category")
        st.table(df_cat)

        # 2) by attribute
        df_attr = df.groupby("attribute")["correct"].agg(correct="sum", total="count")
        st.markdown("### Score by Attribute")
        st.table(df_attr)

        # 3) by l2-category
        df_l2 = df.groupby("l2")["correct"].agg(correct="sum", total="count")
        st.markdown("### Score by L2 Category")
        st.table(df_l2)

        # Restart button
        if st.button("Restart Quiz"):
            for k in ("idx","score","responses"):
                del st.session_state[k]
            st.experimental_rerun()

if __name__ == "__main__":
    main()