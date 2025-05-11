# streamlit_app.py
import streamlit as st
import pandas as pd
from PIL import Image
import os

def resolve_path(raw_path: str, data_dir="data"):
    """
    Turn the CSV's image_path into a real file, trying:
      1) the raw path as-is,
      2) stripping any leading prefix and prefixing with data_dir,
      3) walking data_dir for any file matching the basename under the right name.
    """
    raw = raw_path.replace("\\", "/")
    basename = os.path.basename(raw)

    # 1) raw
    if os.path.exists(raw):
        return raw

    # 2) strip up to NAME and prefix with data_dir
    parts = raw.split("/")
    if len(parts) >= 3:
        tail = "/".join(parts[2:])  # NAME/.../file.png
        attempt2 = os.path.join(data_dir, tail)
        if os.path.exists(attempt2):
            return attempt2

    # 3) walk data_dir matching basename + containing the name folder
    name = parts[2] if len(parts) >= 3 else ""
    for root, _, files in os.walk(data_dir):
        if basename in files:
            if not name or name in root:
                return os.path.join(root, basename)

    # fallback: show what we’d tried
    return attempt2 if 'attempt2' in locals() else raw

@st.cache_data
def load_questions(csv_path: str, data_dir: str = "data"):
    # 1) Read everything
    df = pd.read_csv(csv_path, encoding="utf-8").fillna("")
    records = df.to_dict(orient="records")

    # 2) Resolve each path and only keep rows whose image actually exists
    valid = []
    for r in records:
        img = resolve_path(r["image_path"], data_dir)
        if os.path.exists(img):
            r["_img"] = img
            valid.append(r)

    return valid

def main():
    st.set_page_config(page_title="Beat the VLMs: MMPB Quiz", layout="centered")
    st.title("Beat the VLMs: MMPB Quiz")

    # Load and keep only the first 10 for a quick test
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

        # two columns: left=question, right=current score
        col_q, col_score = st.columns([4, 1])
        with col_score:
            # 작게 조절한 Score 표시
            st.markdown(
                f"""
                <div style="text-align:center; line-height:1.2;">
                  <div style="font-size:14px; font-weight:600; color:#aaa;">Score</div>
                  <div style="font-size:18px; font-weight:700;">{st.session_state.score} / {len(qs)}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col_q:
            # 1) description + preference
            st.markdown(f"**{q['description_moderate']}**\n\n**{q['preference']}**")

            # 2) image
            try:
                img = Image.open(q["_img"])
                st.image(img, use_container_width=True)
            except Exception as e:
                st.error(f"Couldn’t load image:\n{q['_img']}\n{e}")

            # 3) question text
            st.markdown(f"**Q{idx+1}. {q['question']}**")

            # 4) options
            opts = [q.get(k) for k in ("A","B","C","D") if q.get(k)]
            if not opts:
                opts = ["Yes", "No"]
            choice = st.radio("Select an option:", opts, key=f"choice_{idx}")

            # 5) Next
            if st.button("Next", use_container_width=True):
                correct = (choice == q["answer"])
                # record response
                st.session_state.responses.append({
                    "category":    q.get("category", ""),
                    "attribute":   q.get("attribute", ""),
                    "l2":          q.get("l2-category", ""),
                    "correct":     correct
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