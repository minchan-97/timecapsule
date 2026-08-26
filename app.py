"""
타임캡슐 — 교실용 편지 앱
편지를 팻말에 걸어두면 나무가 자라고, 마지막 수업에 하나씩 열립니다.
반마다 날짜·코드·편지가 완전히 따로 굴러갑니다.
"""
import base64
import json
import random
from datetime import date, datetime
from pathlib import Path

import streamlit as st

# ─────────────────────────────────────────────────────────────
# 반 설정 — 여기만 바꾸면 됩니다
#
#   code  : 아이들이 입력하는 코드. 이 코드가 반을 알아서 찾아갑니다.
#           8개가 서로 겹치지 않게 하세요.
#   start : 편지 쓰는 날 (0주차)
#   open  : 마지막 수업 (개봉일)
#   cuts  : 그림이 바뀌는 주차. 생략하면 DEFAULT_CUTS 를 씁니다.
#           예) "6-1": {..., "cuts": (2, 4, 7)}
# ─────────────────────────────────────────────────────────────
DEFAULT_CUTS = (2, 5, 9)   # 0~1주 팻말만 / 2~4주 묘목 / 5~8주 자라는 중 / 9주~ 큰 나무

CLASSES = {
    "5-1": {"name": "5학년 1반", "code": "namu51", "start": date(2026, 9, 1), "open": date(2026, 12, 15)},
    "5-2": {"name": "5학년 2반", "code": "namu52", "start": date(2026, 9, 1), "open": date(2026, 12, 16)},
    "5-3": {"name": "5학년 3반", "code": "namu53", "start": date(2026, 9, 2), "open": date(2026, 12, 17)},
    "5-4": {"name": "5학년 4반", "code": "namu54", "start": date(2026, 9, 2), "open": date(2026, 12, 18)},
    "6-1": {"name": "6학년 1반", "code": "namu61", "start": date(2026, 9, 3), "open": date(2026, 12, 15)},
    "6-2": {"name": "6학년 2반", "code": "namu62", "start": date(2026, 9, 3), "open": date(2026, 12, 16)},
    "6-3": {"name": "6학년 3반", "code": "namu63", "start": date(2026, 9, 4), "open": date(2026, 12, 17)},
    "6-4": {"name": "6학년 4반", "code": "namu64", "start": date(2026, 9, 4), "open": date(2026, 12, 18)},
}

TEACHER_PIN = "0000"   # 배포 전에 반드시 바꾸세요. 이 코드로 들어가면 개봉 화면입니다.
MUSIC_FILE  = "music.mp3"

DATA_DIR = Path("data")
ASSETS   = Path("assets")

STAGES      = ["stage1.jpg", "stage2.jpg", "stage3.jpg", "stage4.jpg"]
STAGE_LABEL = ["아직 아무것도", "묘목", "자라는 중", "큰 나무"]


# ─────────────────────────────────────────────────────────────
# 반 조회
# ─────────────────────────────────────────────────────────────
def find_class_by_code(code):
    code = code.strip()
    for key, c in CLASSES.items():
        if code and code == c["code"]:
            return key
    return None


def cfg(key):
    return CLASSES[key]


def cuts(key):
    return cfg(key).get("cuts", DEFAULT_CUTS)


# ─────────────────────────────────────────────────────────────
# 저장소 — 반마다 별도 파일. 한 줄에 편지 하나씩 append.
# ─────────────────────────────────────────────────────────────
def data_file(key):
    return DATA_DIR / f"letters_{key}.jsonl"


def load_letters(key):
    path = data_file(key)
    if not path.exists():
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return out


def save_letter(key, record):
    DATA_DIR.mkdir(exist_ok=True)
    with open(data_file(key), "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def find_letter(key, number):
    for r in load_letters(key):
        if r["number"] == number:
            return r
    return None


# ─────────────────────────────────────────────────────────────
# 성장 — 시작일로부터 몇 주가 지났는지로만 결정
# ─────────────────────────────────────────────────────────────
def weeks_elapsed(key):
    return max(0, (date.today() - cfg(key)["start"]).days // 7)


def stage_index(key):
    w = weeks_elapsed(key)
    for i, cut in enumerate(cuts(key)):
        if w < cut:
            return i
    return 3


def days_left(key):
    return max(0, (cfg(key)["open"] - date.today()).days)


@st.cache_data
def img_b64(name):
    path = ASSETS / name
    return base64.b64encode(path.read_bytes()).decode() if path.exists() else None


# ─────────────────────────────────────────────────────────────
# 스타일
# ─────────────────────────────────────────────────────────────
def inject_css(stage_file, intro=False):
    """intro=True 면 아이콘이 먼저 뜨고 배경이 뒤따라 번집니다."""
    b64 = img_b64(stage_file)
    bg = f"url('data:image/jpeg;base64,{b64}')" if b64 else "none"
    bg_anim = "animation: veilOut 2.0s ease-out 1.15s both;" if intro else "opacity: 0; display: none;"
    css = f"""
@import url('https://fonts.googleapis.com/css2?family=Gaegu:wght@400;700&family=Gowun+Dodum&display=swap');
  #MainMenu, footer, header {{visibility: hidden;}}
  .stApp {{
    background-image: {bg};
    background-size: cover;
    background-position: center top;
    background-attachment: fixed;
    background-color: #f3ece2;
  }}
  [data-testid="stAppViewContainer"],
  [data-testid="stMain"],
  [data-testid="stHeader"],
  [data-testid="stBottomBlockContainer"],
  section.main,
  .main {{background: transparent !important;}}
  /* 시작 화면에서 배경을 잠시 덮었다가 걷히는 막 */
  .stApp::after {{
    content: "";
    position: fixed;
    inset: 0;
    background: #f3ece2;
    pointer-events: none;
    z-index: 0;
    {bg_anim}
  }}
  .block-container {{position: relative; z-index: 1;}}
  @keyframes veilOut {{from {{opacity: 1;}} to {{opacity: 0;}}}}

  /* 시작 화면 아이콘 */
  .icon-wrap {{text-align: center; margin: 0.4rem 0 1.2rem;}}
  .icon-wrap img {{
    width: 190px; max-width: 52vw; height: auto;
    filter: drop-shadow(0 10px 26px rgba(90,70,40,0.22));
    animation: iconIn 1.15s cubic-bezier(.2,.7,.3,1) both;
  }}
  @keyframes iconIn {{
    from {{opacity: 0; transform: scale(0.86) translateY(10px);}}
    to   {{opacity: 1; transform: scale(1) translateY(0);}}
  }}
  .intro-late {{animation: lateIn 1.4s ease-out 1.5s both;}}
  @keyframes lateIn {{from {{opacity: 0;}} to {{opacity: 1;}}}}

  @media (prefers-reduced-motion: reduce) {{
    .stApp::after {{animation: none !important; opacity: 0 !important;}}
    .icon-wrap img, .intro-late {{animation: none !important; opacity: 1 !important;}}
  }}

  .block-container {{max-width: 620px; padding-top: 2.2rem; padding-bottom: 4rem;}}

  html, body, [class*="css"], .stMarkdown, p, div, label, input, textarea {{
    font-family: 'Gowun Dodum', sans-serif;
  }}

  .sky-title {{
    font-family: 'Gaegu', cursive; font-size: 2.5rem; font-weight: 700;
    color: #4a6b3f; text-align: center; letter-spacing: 0.04em;
    text-shadow: 0 2px 12px rgba(255,255,255,0.9); margin-bottom: 0.1rem;
  }}
  .sky-sub {{
    text-align: center; color: #6e7f6a; font-size: 0.95rem;
    text-shadow: 0 1px 8px rgba(255,255,255,0.9); margin-bottom: 1.6rem;
  }}

  .paper {{
    background: rgba(253, 249, 240, 0.93);
    border: 1px solid rgba(139,111,78,0.28); border-radius: 3px;
    padding: 1.5rem 1.6rem; box-shadow: 0 8px 28px rgba(90,70,40,0.16);
    animation: rise 0.7s ease-out;
  }}
  @keyframes rise {{
    from {{opacity: 0; transform: translateY(14px);}}
    to   {{opacity: 1; transform: translateY(0);}}
  }}
  @media (prefers-reduced-motion: reduce) {{ .paper {{animation: none;}} }}

  .letter-body {{
    font-family: 'Gaegu', cursive; font-size: 1.35rem; line-height: 1.95;
    color: #3f3a33; white-space: pre-wrap; word-break: break-word;
  }}
  .letter-from {{
    font-family: 'Gaegu', cursive; font-size: 1.15rem;
    color: #8b6f4e; text-align: right; margin-top: 1.2rem;
  }}
  .meta {{
    font-size: 0.82rem; color: #9a9184;
    border-top: 1px dashed rgba(139,111,78,0.3);
    padding-top: 0.7rem; margin-top: 1.1rem;
  }}
  .badge {{
    display: inline-block; background: rgba(253,249,240,0.9);
    border: 1px solid rgba(139,111,78,0.25); border-radius: 999px;
    padding: 0.35rem 1rem; font-size: 0.9rem; color: #5c6b4f;
  }}
  .center {{text-align: center;}}

  .stButton > button {{
    background: #7d9b5e; color: #fff; border: none; border-radius: 4px;
    padding: 0.55rem 1.4rem; font-family: 'Gowun Dodum', sans-serif;
  }}
  .stButton > button:hover {{background: #6b8850; color: #fff;}}
  .stButton > button:focus-visible {{outline: 3px solid #f2c25c; outline-offset: 2px;}}

  .stTextInput input, .stTextArea textarea {{
    background: rgba(253,249,240,0.95); border: 1px solid rgba(139,111,78,0.3);
  }}
  .stTextArea textarea {{font-family: 'Gaegu', cursive; font-size: 1.25rem; line-height: 1.9;}}
"""
    # 빈 줄이 하나라도 있으면 Streamlit 마크다운이 HTML 블록을 끊어버려
    # 나머지 CSS가 화면에 글자로 찍힙니다. 반드시 전부 제거합니다.
    css = "".join(line.strip() + " " for line in css.splitlines() if line.strip())
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def play_music():
    """assets/music.mp3 가 있으면 재생기를 띄웁니다. 없으면 조용히 넘어갑니다.

    브라우저가 자동재생을 막는 경우가 많아 재생 버튼이 보이는 형태로 둡니다.
    수업 시작할 때 한 번 눌러 주세요.
    """
    music = ASSETS / MUSIC_FILE
    if not music.exists():
        return
    try:
        st.audio(str(music), loop=True, autoplay=True)
    except TypeError:
        st.audio(str(music))   # 구버전 Streamlit


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def printable_html(key, letters):
    """서버가 사라져도 남는 사본. 브라우저에서 열어 PDF로 인쇄하세요."""
    c = cfg(key)
    parts = []
    for r in sorted(letters, key=lambda x: int(x["number"])):
        w = datetime.fromisoformat(r["written_at"]).date()
        parts.append(
            f"<article><h2>{r['number']}번 {esc(r['nickname'])}</h2>"
            f"<p>{esc(r['body'])}</p>"
            f"<small>{w.year}. {w.month}. {w.day}</small></article>"
        )
    return f"""<!doctype html><html lang="ko"><meta charset="utf-8">
<title>타임캡슐 — {c['name']}</title>
<style>
 body{{font-family:sans-serif;max-width:640px;margin:3rem auto;padding:0 1.5rem;color:#333;}}
 h1{{font-size:1.6rem;border-bottom:2px solid #7d9b5e;padding-bottom:.6rem;}}
 article{{page-break-inside:avoid;margin:2.4rem 0;border-left:3px solid #d8ddc9;padding-left:1.2rem;}}
 h2{{font-size:1.1rem;color:#5c6b4f;margin-bottom:.6rem;}}
 p{{white-space:pre-wrap;line-height:1.9;}}
 small{{color:#999;}}
</style>
<h1>타임캡슐 — {c['name']}</h1>
<p>{c['start']} 에 맡기고 {c['open']} 에 열었습니다. 모두 {len(letters)}통.</p>
{''.join(parts)}
</html>"""


# ─────────────────────────────────────────────────────────────
# 화면 1 — 편지 쓰기
# ─────────────────────────────────────────────────────────────
def page_write(key):
    c = cfg(key)
    st.markdown('<div class="sky-title">타임캡슐</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="sky-sub">{c["name"]} · {c["open"].month}월 {c["open"].day}일에 열립니다</div>',
        unsafe_allow_html=True,
    )

    if date.today() > c["open"]:
        st.markdown('<div class="paper center">편지 쓰는 기간이 끝났어요.</div>', unsafe_allow_html=True)
        return

    number = st.text_input("번호", max_chars=2, placeholder="예: 7", key=f"w_num_{key}")
    nickname = st.text_input("이름 또는 별명", max_chars=12, placeholder="편지 아래에 적힐 이름", key=f"w_nick_{key}")
    body = st.text_area(
        "그날의 나에게",
        height=260, max_chars=1200,
        placeholder="지금 무슨 생각을 하고 있는지, 그때는 어떤 사람이 되어 있길 바라는지 써 보세요.",
        key=f"w_body_{key}",
    )

    st.caption("한 번 넣으면 개봉일까지 열 수 없어요. 선생님은 관리를 위해 내용을 볼 수 있습니다.")

    if st.button("팻말에 걸기", key=f"w_btn_{key}"):
        num = number.strip()
        if not num.isdigit():
            st.error("번호는 숫자로 적어 주세요.")
            return
        if not nickname.strip():
            st.error("이름 또는 별명을 적어 주세요.")
            return
        if len(body.strip()) < 20:
            st.error("편지가 너무 짧아요. 20자 이상 써 주세요.")
            return
        if find_letter(key, num):
            st.error(f"{num}번은 이미 편지를 넣었어요. '내 나무 보기'에서 확인할 수 있어요.")
            return

        save_letter(key, {
            "number": num,
            "nickname": nickname.strip(),
            "body": body.strip(),
            "written_at": datetime.now().isoformat(timespec="seconds"),
        })
        st.session_state.just_saved = num
        st.rerun()


# ─────────────────────────────────────────────────────────────
# 화면 2 — 내 나무 보기
# ─────────────────────────────────────────────────────────────
def page_tree(key):
    c = cfg(key)
    st.markdown('<div class="sky-title">내 나무</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="sky-sub">{weeks_elapsed(key)}주차 · {STAGE_LABEL[stage_index(key)]} · 개봉까지 {days_left(key)}일</div>',
        unsafe_allow_html=True,
    )

    number = st.text_input("번호", max_chars=2, placeholder="예: 7", key=f"t_num_{key}")
    if st.button("확인", key=f"t_btn_{key}"):
        rec = find_letter(key, number.strip())
        if not rec:
            st.warning("그 번호로 넣은 편지가 없어요.")
        else:
            written = datetime.fromisoformat(rec["written_at"]).date()
            st.markdown(
                f"""
<div class="paper">
  <div class="center" style="font-family:'Gaegu',cursive;font-size:1.5rem;color:#5c6b4f;">
    {esc(rec['nickname'])}의 편지는 잘 있어요
  </div>
  <div class="meta">
    맡긴 날 {written.year}. {written.month}. {written.day} · {(date.today()-written).days}일째 보관 중<br>
    {c['open'].month}월 {c['open'].day}일 마지막 수업에 열립니다.
  </div>
</div>
""",
                unsafe_allow_html=True,
            )

    st.markdown(
        f'<div class="center" style="margin-top:1.4rem;"><span class="badge">{c["name"]} 편지 {len(load_letters(key))}통</span></div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────
# 화면 3 — 개봉 (교사용)
# ─────────────────────────────────────────────────────────────
def page_open():
    keys = list(CLASSES.keys())
    labels = [CLASSES[k]["name"] for k in keys]
    picked = st.selectbox("반", labels, key="open_class")
    key = keys[labels.index(picked)]

    # 반을 바꾸면 진행 상태 초기화
    if st.session_state.get("open_key") != key:
        st.session_state.open_key = key
        st.session_state.pop("order", None)
        st.session_state.idx = -1

    c = cfg(key)
    letters = load_letters(key)
    if not letters:
        st.markdown(f'<div class="paper center">{c["name"]}은 아직 편지가 없어요.</div>', unsafe_allow_html=True)
        return

    if "order" not in st.session_state:
        order = list(range(len(letters)))
        random.shuffle(order)
        st.session_state.order = order

    order = st.session_state.order
    idx = st.session_state.get("idx", -1)

    play_music()

    if idx < 0:
        st.markdown('<div class="sky-title">타임캡슐이 열립니다</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="sky-sub">{c["name"]} · {len(letters)}통의 편지 · {weeks_elapsed(key)}주 만에</div>',
            unsafe_allow_html=True,
        )
        if st.button("첫 번째 편지 열기"):
            st.session_state.idx = 0
            st.rerun()
        st.download_button(
            "인쇄용으로 내려받기",
            data=printable_html(key, letters),
            file_name=f"타임캡슐_{c['name']}_{c['open']}.html",
            mime="text/html",
        )
        return

    if idx >= len(order):
        st.markdown('<div class="sky-title">여기까지</div>', unsafe_allow_html=True)
        st.markdown('<div class="paper center letter-body">모두 잘 자랐습니다.</div>', unsafe_allow_html=True)
        return

    rec = letters[order[idx]]
    written = datetime.fromisoformat(rec["written_at"]).date()
    st.markdown(f'<div class="sky-sub">{idx+1} / {len(order)}</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
<div class="paper">
  <div class="letter-body">{esc(rec['body'])}</div>
  <div class="letter-from">— {esc(rec['nickname'])}</div>
  <div class="meta">{written.year}. {written.month}. {written.day}에 쓴 편지</div>
</div>
""",
        unsafe_allow_html=True,
    )

    if st.button("다음 편지" if idx + 1 < len(order) else "마치기"):
        st.session_state.idx = idx + 1
        st.rerun()


# ─────────────────────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────────────────────
def main():
    st.set_page_config(page_title="타임캡슐", page_icon="🌳", layout="centered")

    key = st.session_state.get("cls")
    teacher = st.session_state.get("teacher", False)

    at_start = not key and not teacher

    if teacher:
        stage_file = STAGES[3]
    elif key:
        stage_file = STAGES[stage_index(key)]
    else:
        stage_file = STAGES[0]
    inject_css(stage_file, intro=at_start)

    # 시작 화면 — 아이콘이 먼저 뜨고 배경이 뒤따릅니다
    if at_start:
        icon = img_b64("icon.png")
        if icon:
            st.markdown(
                f'<div class="icon-wrap"><img src="data:image/png;base64,{icon}" alt=""></div>',
                unsafe_allow_html=True,
            )
        st.markdown('<div class="sky-title intro-late">타임캡슐</div>', unsafe_allow_html=True)
        st.markdown('<div class="sky-sub intro-late">선생님이 알려준 코드를 넣어 주세요</div>', unsafe_allow_html=True)
        play_music()
        code = st.text_input("반 코드", type="password")
        if st.button("들어가기"):
            found = find_class_by_code(code)
            if found:
                st.session_state.cls = found
                st.rerun()
            elif code.strip() == TEACHER_PIN:
                st.session_state.teacher = True
                st.rerun()
            else:
                st.error("코드가 맞지 않아요.")
        return

    if teacher:
        page_open()
        return

    if st.session_state.get("just_saved"):
        num = st.session_state.pop("just_saved")
        c = cfg(key)
        st.markdown('<div class="sky-title">잘 걸었어요</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
<div class="paper center">
  <div class="letter-body">{num}번의 편지를 팻말에 걸었습니다.<br>
  나무가 자라는 동안 가끔 보러 오세요.</div>
  <div class="meta">{c['open'].year}. {c['open'].month}. {c['open'].day}에 열립니다 · {days_left(key)}일 남음</div>
</div>
""",
            unsafe_allow_html=True,
        )
        return

    tab1, tab2 = st.tabs(["편지 쓰기", "내 나무 보기"])
    with tab1:
        page_write(key)
    with tab2:
        page_tree(key)


if __name__ == "__main__":
    main()
