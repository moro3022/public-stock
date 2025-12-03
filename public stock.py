import streamlit as st
import pandas as pd
import numpy as np
import calendar
import holidays
import datetime
from streamlit_gsheets import GSheetsConnection

# 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# 데이터 로드 (ttl은 캐시 시간 - 5분마다 갱신)
df_schedule = conn.read(worksheet="일정", ttl="5m")
df_trade = conn.read(worksheet="매매", ttl="5m")

# 2️⃣ 날짜/숫자 타입 변환
df_schedule["청약일"] = pd.to_datetime(df_schedule["청약일"], errors="coerce")
df_schedule["상장일"] = pd.to_datetime(df_schedule["상장일"], errors="coerce")
df_schedule["공모가"] = pd.to_numeric(df_schedule["공모가"], errors="coerce")
df_schedule["최소증거금"] = pd.to_numeric(df_schedule["최소증거금"], errors="coerce")
df_schedule["균등"] = pd.to_numeric(df_schedule["균등"], errors="coerce")
df_schedule["비례"] = pd.to_numeric(df_schedule["비례"], errors="coerce")

df_trade["매도일"] = pd.to_datetime(df_trade["매도일"], errors="coerce")
df_trade["실제이익"] = pd.to_numeric(df_trade["실제이익"], errors="coerce")

# 세션 상태 초기화
if "calendar_year" not in st.session_state:
    st.session_state.calendar_year = pd.Timestamp.today().year
if "calendar_month" not in st.session_state:
    st.session_state.calendar_month = pd.Timestamp.today().month

selected_year = st.session_state.calendar_year
selected_month = st.session_state.calendar_month

# ----------------------------
# 0) Streamlit 출력 시작
# ----------------------------

st.markdown("""
<link href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
html, body, .stApp, * {
    font-family: 'Pretendard', sans-serif !important;
}
.font-mono {
    font-family: 'Roboto Mono', monospace !important;
}
</style>
""", unsafe_allow_html=True)


# ----------------------------
# 1) 이번주 청약 종목 카드 출력
# ----------------------------
today = pd.Timestamp.today().normalize()
start_of_week = today.normalize() - pd.Timedelta(days=today.weekday())
end_of_week = start_of_week + pd.Timedelta(days=4)

청약일_정규 = df_schedule["청약일"].dt.normalize()
상장일_정규 = df_schedule["상장일"].dt.normalize()

df_this_week = df_schedule[
    (청약일_정규.between(today, end_of_week)) | (상장일_정규.between(today, end_of_week))
].copy()

df_this_week["기준일"] = df_this_week.apply(
    lambda x: x["청약일"] if (pd.notna(x["청약일"]) and start_of_week <= x["청약일"].normalize() <= end_of_week)
    else x["상장일"],
    axis=1
)

df_this_week = df_this_week.sort_values(by=["기준일"], ascending=True)


icon_check = "https://cdn-icons-png.flaticon.com/128/18624/18624451.png"

if not df_this_week.empty:

    st.markdown(
        f"""
        <h4 style='display:flex; align-items:center; gap:8px; margin:0;'>
            <img src="{icon_check}" alt="calendar" width="24" height="24" style="vertical-align:middle;" />
            이번주 공모주
        </h4>
        """,
        unsafe_allow_html=True
    )
    card_list = []
    for _, row in df_this_week.iterrows():
        청약일 = pd.to_datetime(row["청약일"])
        상장일 = pd.to_datetime(row["상장일"])
        종목명 = str(row["종목명"])
        증권사 = str(row["증권사"])
        테마 = str(row["테마"])
        공모가 = f"{int(row['공모가']):,}원" if not pd.isna(row["공모가"]) else "-"
        최소증거금 = f"{int(row['최소증거금']):,}원" if not pd.isna(row["최소증거금"]) else "-"
        균등 = int(row["균등"]) if not pd.isna(row["균등"]) else 0
        비례 = int(row["비례"]) if not pd.isna(row["비례"]) else 0
        배정주식수 = f"{균등 + 비례:,}주" if (균등 + 비례) > 0 else "-"
        예측값 = str(row["예측"]) if not pd.isna(row["예측"]) else "-"
        청약일표시 = f"{청약일.strftime('%m-%d')} ({['월','화','수','목','금','토','일'][청약일.weekday()]})" if pd.notna(청약일) else "-"
        상장일표시 = f"{상장일.strftime('%m-%d')} ({['월','화','수','목','금','토','일'][상장일.weekday()]})" if pd.notna(상장일) else "-"

        is_today_청약 = pd.notna(청약일) and 청약일.normalize() == today
        is_today_상장 = pd.notna(상장일) and 상장일.normalize() == today

        border_color = "#6A5ACD" if is_today_청약 else "#f4ca16" if is_today_상장 else "#ddd"
        border_width = "2px" if is_today_청약 or is_today_상장 else "1px"

        예측색 = {"매우좋음": "#EAA600", "좋음": "#F8CEB9", "보통": "#D6C6B4"}.get(예측값, "#EEE")
        예측글자색 = {"매우좋음": "#fff", "좋음": "#6B3F1D", "보통": "#5A4632"}.get(예측값, "#666")

        예측뱃지 = f"<span style='background:{예측색};color:{예측글자색};padding:2px 8px;border-radius:4px;font-size:12px;font-weight:500;'>{예측값}</span>"
        
        # 뱃지 스타일 및 텍스트 결정 "#6A5ACD", "상장": "#f4ca16"}
        badges = []
        if pd.notna(청약일) and start_of_week <= 청약일.normalize() <= end_of_week:
            badge_color = "#6A5ACD" if 청약일.normalize() == today else "#6A5ACD"
            badges.append(f"<span style='background:{badge_color}; color:#fff; padding:2px 6px; border-radius:6px; font-size:12px; font-weight:600; margin-left:8px;'>청약</span>")
        if pd.notna(상장일) and start_of_week <= 상장일.normalize() <= end_of_week:
            badge_color = "#f4ca16" if 상장일.normalize() == today else "#f4ca16"
            badges.append(f"<span style='background:{badge_color}; color:#fff; padding:2px 6px; border-radius:6px; font-size:12px; font-weight:600; margin-left:8px;'>상장</span>")

        badges_html = "".join(badges)

        card_body = (
            f"<div style='display:flex;gap:8px;justify-content:flex-start;'>"
            f"<div style='color:#666;width:64px;'>청약일</div><div style='color:#333;'>{청약일표시}</div></div>"
            f"<div style='display:flex;gap:8px;justify-content:flex-start;'>"
            f"<div style='color:#666;width:64px;'>상장일</div><div style='color:#333;'>{상장일표시}</div></div>"
            f"<div style='display:flex;gap:8px;justify-content:flex-start;'>"
            f"<div style='color:#666;width:64px;'>증권사</div><div style='color:#333;'>{증권사}</div></div>"
            f"<div style='display:flex;gap:8px;justify-content:flex-start;'>"
            f"<div style='color:#666;width:64px;'>테마</div><div style='color:#333;'>{테마}</div></div>"
            f"<div style='display:flex;gap:8px;justify-content:flex-start;'>"
            f"<div style='color:#666;width:64px;'>공모가</div><div style='color:#333;'>{공모가}</div></div>"
        )
        if (상장일 >= start_of_week and 상장일 <= end_of_week) or (is_today_상장):
            card_body += (
                f"<div style='display:flex;gap:8px;justify-content:flex-start;'>"
                f"<div style='color:#666;width:64px;'>주식수</div><div style='color:#333;'>{배정주식수}</div></div>"
            )
        else:
            card_body += (
                f"<div style='display:flex;gap:8px;justify-content:flex-start;'>"
                f"<div style='color:#666;width:64px;'>증거금</div><div style='color:#333;'>{최소증거금}</div></div>"
            )
        card_body += (
            f"<div style='display:flex;gap:8px;justify-content:flex-start;'>"
            f"<div style='color:#666;width:64px;'>예측</div><div>{예측뱃지}</div></div>"
        )
        
        card_header = (
            f"<div style='display:flex; align-items:center; font-size:16px; font-weight:600; margin-bottom:8px; text-align:left;'>"
            f"<div>{종목명}</div>"
            f"{badges_html}"
            f"</div>"
        )
        card = (
            f"<div style='border:{border_width} solid {border_color}; border-radius:12px; padding:12px 16px; width:220px; box-shadow:1px 1px 4px rgba(0,0,0,0.05);'>"
            f"{card_header}"
            f"<div style='display:flex; flex-direction:column; gap:4px; text-align:left; font-size:14px;'>"
            f"{card_body}</div></div>"
        )
        card_list.append(card.strip())
    card_html = f"<div style='display:flex;flex-wrap:wrap;gap:12px;margin-bottom:32px;'>{''.join(card_list)}</div>"
    st.markdown(card_html, unsafe_allow_html=True)


# ----------------------------
# 2) 상단 버튼 + 달력 제목
# ----------------------------

icon_calendar = "https://cdn-icons-png.flaticon.com/128/7602/7602624.png"
col1, col2, col3, col4, col5 = st.columns([12, 0.5, 2, 2, 0.1])
with col1:
    st.markdown(
        f"""
        <h4 style='display:flex; align-items:center; gap:8px; margin:0;'>
        <img src="{icon_calendar}" alt="calendar" width="24" height="24" style="vertical-align:middle;" />
            {selected_year}년 {selected_month}월 공모주 일정
        </h4>
        """,
        unsafe_allow_html=True
    )
with col3:
    prev_clicked = st.button("이전달", key="prev_btn")
with col4:
    next_clicked = st.button("다음달", key="next_btn")

if prev_clicked:
    if st.session_state.calendar_month == 1:
        st.session_state.calendar_month = 12
        st.session_state.calendar_year -= 1
    else:
        st.session_state.calendar_month -= 1
    st.rerun()

if next_clicked:
    if st.session_state.calendar_month == 12:
        st.session_state.calendar_month = 1
        st.session_state.calendar_year += 1
    else:
        st.session_state.calendar_month += 1
    st.rerun()

# ----------------------------
# 3) 날짜 매핑
# ----------------------------
num_days = calendar.monthrange(selected_year, selected_month)[1]
kr_holidays = holidays.KR(years=[selected_year])

data_map = {}
for _, row in df_schedule.iterrows():
    종목명 = str(row["종목명"])
    증권사 = str(row["증권사"])
    종목표시 = f"{종목명} <span style='color:#999; font-size:12px;'>({증권사})</span>"
    if pd.notna(row["청약일"]) and row["청약일"].year == selected_year and row["청약일"].month == selected_month:
        day = row["청약일"].day
        data_map.setdefault(day, []).append(("청약", 종목표시))
    if pd.notna(row["상장일"]) and row["상장일"].year == selected_year and row["상장일"].month == selected_month:
        day = row["상장일"].day
        data_map.setdefault(day, []).append(("상장", 종목표시))


# ----------------------------
# 4) 달력 셀 생성
# ----------------------------

days, weekdays, week_numbers, texts = [], [], [], []
first_day_weekday = pd.Timestamp(selected_year, selected_month, 1).weekday()
badge_colors = {"청약": "#6A5ACD", "상장": "#f4ca16"}

for day in range(1, num_days + 1):
    weekday = pd.Timestamp(selected_year, selected_month, day).weekday()
    if weekday > 4:
        continue
    week = ((day + first_day_weekday - 1) // 7)
    일정목록 = data_map.get(day, [])

    day_color = "#D32F2F" if pd.Timestamp(selected_year, selected_month, day).date() in kr_holidays else "black"

    if not 일정목록:
        content_html = ""
    else:
        content_html = ""
        for 구분, 종목표시 in 일정목록:
            color = badge_colors.get(구분, "#ccc")
            content_html += f"<div style='margin-top:4px;'><span style='background:{color}; color:white; padding:4px 10px; border-radius:6px; font-size:13px; font-weight:600;'>{구분}</span></div>"
            content_html += f"<div style='margin-top:2px; font-size:14px; font-weight:500;'>{종목표시}</div>"

    cell_date = pd.Timestamp(selected_year, selected_month, day).date()
    is_today = cell_date == pd.Timestamp.today().date()
    background_color = "#EEF1FA" if is_today else "transparent"

    cell_html = (
        f"<div style='text-align:center; background:{background_color}; border-radius:8px; padding:3px;'>"
        f"<div style='font-size:18px; font-weight:bold; color:{day_color};'>{day}</div>"
        f"{content_html}"
        f"</div>"
    )
    days.append(day)
    weekdays.append(weekday)
    week_numbers.append(week)
    texts.append(cell_html)

# ----------------------------
# 5) 달력 테이블 렌더링
# ----------------------------
week_count = ((num_days + first_day_weekday - 1) // 7) + 1
text_grid = np.full((week_count, 5), "", dtype=object)
for d, w, wk, t in zip(days, weekdays, week_numbers, texts):
    text_grid[wk, w] = t

calendar_rows = []
for wk in range(text_grid.shape[0]):
    row = text_grid[wk, :]
    if not any(cell.strip() for cell in row):
        continue
    calendar_rows.append(row)

weekday_labels = ["월", "화", "수", "목", "금"]
calendar_df = pd.DataFrame(calendar_rows, columns=weekday_labels)
calendar_df.columns = [f"<div style='text-align:center'><b>{day}</b></div>" for day in weekday_labels]

st.markdown(
    f"""
    <div style='overflow-x:auto; width:100%;'>
        <table style="width:100%; table-layout:fixed;">
            {calendar_df.to_html(escape=False, index=False, border=0).split('>', 1)[1]}
        </table>
    </div>
    """,
    unsafe_allow_html=True
)

# ----------------------------
# 6) 수익 합계 출력
# ----------------------------

# 매매 시트 불러오기
df_trade = pd.read_excel("C:/Users/woori/Desktop/Invest/공모주 관리.xlsx", sheet_name="매매")

# 전체 실제이익 합계
total_profit = df_trade["실제이익"].sum()

# 이번년도 실제이익 합계
current_year = datetime.datetime.today().year
df_trade["매도일"] = pd.to_datetime(df_trade["매도일"], errors="coerce")
df_trade_current_year = df_trade[df_trade["매도일"].dt.year == current_year]
year_profit = df_trade_current_year["실제이익"].sum()

summary_html = f"""
<div style=' padding:12px 16px; margin-top:12px; background:#f5f5f5; border-radius:12px; font-weight:500; font-size:16px; '>
    # {current_year}년 공모주 수익: {year_profit:,.0f} 원
</div>
"""

st.markdown(summary_html, unsafe_allow_html=True)