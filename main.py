
# main.py
# 어제의 박스오피스를 보여 주는 Streamlit 앱
# 초보자도 이해하기 쉽도록 주요 기능마다 주석을 달았습니다.

import datetime
import json
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import requests
import streamlit as st


# --------------------------------------------------
# 1. 기본 화면 설정
# --------------------------------------------------

st.set_page_config(
    page_title="어제의 박스오피스",
    page_icon="🎬",
    layout="wide",
)

# KOBIS 일별 박스오피스 API 주소
API_URL = (
    "https://www.kobis.or.kr/kobisopenapi/webservice/rest/"
    "boxoffice/searchDailyBoxOfficeList.json"
)

# 한국 시간 기준으로 어제 날짜를 계산합니다.
# 서버가 외국 시간대를 사용하더라도 한국 날짜를 기준으로 합니다.
KST = ZoneInfo("Asia/Seoul")
today_kst = datetime.datetime.now(KST).date()
yesterday = today_kst - datetime.timedelta(days=1)

# API가 요구하는 날짜 형식: YYYYMMDD
target_date = yesterday.strftime("%Y%m%d")

# 화면에 표시할 날짜 형식
display_date = yesterday.strftime("%Y년 %m월 %d일")


# --------------------------------------------------
# 2. KOBIS API에서 데이터 가져오기
# --------------------------------------------------

@st.cache_data(ttl=3600)
def fetch_boxoffice(date_str, api_key):
    """API에 요청을 보내고 JSON 응답을 반환합니다."""

    response = requests.get(
        API_URL,
        params={
            "key": api_key,
            "targetDt": date_str,
        },
        timeout=15,
    )

    # HTTP 상태 코드가 오류라면 예외를 발생시킵니다.
    response.raise_for_status()

    # 응답 본문이 올바른 JSON인지 확인합니다.
    return response.json()


# --------------------------------------------------
# 3. 앱 제목과 조회 날짜 표시
# --------------------------------------------------

st.title("🎬 어제의 박스오피스")
st.caption(f"조회 날짜: {display_date} (한국 시간 기준)")

st.markdown(
    "영화진흥위원회(KOBIS)의 일별 박스오피스 데이터를 "
    "바탕으로 어제의 영화 순위와 관객 현황을 보여 줍니다."
)

st.divider()


# --------------------------------------------------
# 4. 비밀 금고에서 인증키 읽기
# --------------------------------------------------

# 인증키를 코드에 직접 작성하지 않습니다.
# Streamlit Cloud의 앱 설정에서 KOBIS_KEY를 등록해야 합니다.
try:
    api_key = st.secrets["KOBIS_KEY"]

    if not str(api_key).strip():
        st.error("인증키가 비어 있습니다.")
        st.info(
            "Streamlit Cloud의 앱 설정에서 Secrets를 열고 "
            "KOBIS_KEY에 올바른 인증키를 입력해 주세요."
        )
        st.stop()

except (KeyError, FileNotFoundError):
    st.error("KOBIS API 인증키를 찾을 수 없습니다.")
    st.info(
        "Streamlit Cloud의 앱 설정에서 Secrets를 열고 "
        "아래 내용을 등록해 주세요."
    )
    st.code('KOBIS_KEY = "발급받은_인증키"')
    st.caption(
        "위 예시는 Secrets 설정란에 입력할 형식입니다. "
        "인증키를 main.py 코드에 직접 넣지 마세요."
    )
    st.stop()


# --------------------------------------------------
# 5. API 요청 및 오류 확인
# --------------------------------------------------

try:
    data = fetch_boxoffice(target_date, api_key)

except requests.exceptions.Timeout:
    st.error("KOBIS 서버의 응답 시간이 초과되었습니다.")
    st.info(
        "인터넷 연결을 확인하고 잠시 후 다시 시도해 주세요."
    )
    st.stop()

except requests.exceptions.HTTPError as error:
    st.error("KOBIS 서버에서 HTTP 오류가 발생했습니다.")
    st.info(
        f"상태 코드: {error.response.status_code}\n\n"
        "API 주소와 서버 상태를 확인한 후 다시 시도해 주세요."
    )
    st.stop()

except requests.exceptions.RequestException:
    st.error("KOBIS 서버에 연결하지 못했습니다.")
    st.info(
        "인터넷 연결, API 주소, 서버 상태를 확인한 후 "
        "다시 시도해 주세요."
    )
    st.stop()

except (json.JSONDecodeError, ValueError):
    st.error("KOBIS 서버의 응답을 JSON으로 읽을 수 없습니다.")
    st.info(
        "서버 응답이 올바른지 확인하고 잠시 후 다시 시도해 주세요."
    )
    st.stop()


# --------------------------------------------------
# 6. API 내부 오류와 데이터 확인
# --------------------------------------------------

# 인증키가 잘못된 경우 HTTP 상태 코드가 200이어도
# 응답 안에 faultInfo가 포함될 수 있습니다.
if not isinstance(data, dict):
    st.error("API 응답 형식이 예상과 다릅니다.")
    st.info("KOBIS API 응답 형식과 서버 상태를 확인해 주세요.")
    st.stop()

if "faultInfo" in data:
    fault = data["faultInfo"]

    if isinstance(fault, dict):
        error_code = fault.get("errorCode", "알 수 없음")
        error_message = fault.get("message", "오류 메시지 없음")
    else:
        error_code = "알 수 없음"
        error_message = str(fault)

    st.error("KOBIS API에서 오류를 반환했습니다.")
    st.write(f"오류 코드: {error_code}")
    st.write(f"오류 내용: {error_message}")
    st.info(
        "Secrets에 등록한 KOBIS_KEY가 정확한지 확인해 주세요. "
        "인증키가 유효한데도 문제가 지속된다면 API 이용 한도와 "
        "KOBIS 서버 상태도 확인해 주세요."
    )
    st.stop()

# 응답에서 영화 목록을 가져옵니다.
box_office_result = data.get("boxOfficeResult")

if not isinstance(box_office_result, dict):
    st.error("박스오피스 결과를 찾을 수 없습니다.")
    st.info("KOBIS API 응답에 boxOfficeResult가 있는지 확인해 주세요.")
    st.stop()

movie_list = box_office_result.get("dailyBoxOfficeList")

if not isinstance(movie_list, list) or len(movie_list) == 0:
    st.warning(f"{display_date}의 박스오피스 데이터가 없습니다.")
    st.info(
        "KOBIS에 해당 날짜의 집계 결과가 등록되었는지 확인해 주세요. "
        "API 응답에 오류가 있는지도 살펴보세요."
    )
    st.stop()


# --------------------------------------------------
# 7. 영화 데이터를 표와 그래프에 사용할 수 있게 정리
# --------------------------------------------------

df = pd.DataFrame(movie_list)

# 화면에 필요한 항목이 응답에 있는지 확인합니다.
required_columns = [
    "rank",
    "movieNm",
    "openDt",
    "audiCnt",
    "audiAcc",
    "scrnCnt",
]

missing_columns = [
    column for column in required_columns
    if column not in df.columns
]

if missing_columns:
    st.error("API 응답에 필요한 영화 정보가 빠져 있습니다.")
    st.write("누락된 항목:", ", ".join(missing_columns))
    st.info("KOBIS API의 응답 구조를 확인해 주세요.")
    st.stop()

# 숫자 값은 문자열로 전달되므로 숫자로 변환합니다.
# 변환할 수 없는 값은 0으로 처리합니다.
number_columns = ["rank", "audiCnt", "audiAcc", "scrnCnt"]

for column in number_columns:
    df[column] = pd.to_numeric(
        df[column],
        errors="coerce",
    ).fillna(0).astype(int)

# 영화 이름과 개봉일이 비어 있을 때 표시할 값을 지정합니다.
df["movieNm"] = df["movieNm"].fillna("영화명 없음")
df["openDt"] = df["openDt"].fillna("").replace("", "정보 없음")

# 순위가 빠른 영화부터 정렬합니다.
df = df.sort_values("rank").reset_index(drop=True)


# --------------------------------------------------
# 8. 1위 영화의 주요 지표 카드 3개
# --------------------------------------------------

st.subheader("🏆 오늘의 1위 영화")
st.caption("아래 정보는 한국 시간 기준 어제의 집계 결과입니다.")

first_movie = df.iloc[0]

st.markdown(f"### {first_movie['movieNm']}")

# 화면을 세 칸으로 나누어 주요 수치를 크게 보여 줍니다.
card1, card2, card3 = st.columns(3)

with card1:
    st.metric(
        label="🥇 박스오피스 순위",
        value=f"{first_movie['rank']}위",
    )

with card2:
    st.metric(
        label="👥 일일 관객수",
        value=f"{first_movie['audiCnt']:,}명",
    )

with card3:
    st.metric(
        label="🎟️ 누적 관객수",
        value=f"{first_movie['audiAcc']:,}명",
    )


# --------------------------------------------------
# 9. 전체 박스오피스 표
# --------------------------------------------------

st.divider()
st.subheader("📋 일별 박스오피스 순위")

# 내부 API 필드명을 사용자가 읽기 쉬운 한국어로 바꿉니다.
table_df = df[
    [
        "rank",
        "movieNm",
        "openDt",
        "audiCnt",
        "audiAcc",
        "scrnCnt",
    ]
].rename(
    columns={
        "rank": "순위",
        "movieNm": "영화명",
        "openDt": "개봉일",
        "audiCnt": "관객수",
        "audiAcc": "누적관객",
        "scrnCnt": "스크린수",
    }
)

# 관객수와 스크린수에 천 단위 쉼표를 적용합니다.
st.dataframe(
    table_df.style.format(
        {
            "관객수": "{:,}",
            "누적관객": "{:,}",
            "스크린수": "{:,}",
        }
    ),
    use_container_width=True,
    hide_index=True,
)


# --------------------------------------------------
# 10. 관객수 상위 5편 막대그래프
# --------------------------------------------------

st.divider()
st.subheader("📊 관객수 상위 5편")

# 순위가 아니라 일일 관객수가 많은 영화부터 5편을 선택합니다.
top5 = (
    df.sort_values("audiCnt", ascending=False)
    .head(5)
    .copy()
)

# 그래프에서 영화 제목이 위에서 아래로 보이도록 정렬합니다.
top5 = top5.sort_values("audiCnt", ascending=True)

# 막대그래프를 만듭니다.
fig = px.bar(
    top5,
    x="audiCnt",
    y="movieNm",
    orientation="h",
    text="audiCnt",
    labels={
        "audiCnt": "일일 관객수 (명)",
        "movieNm": "영화명",
    },
    title="일일 관객수 비교",
)

# 막대 끝에 관객수를 쉼표와 함께 표시합니다.
fig.update_traces(
    texttemplate="%{text:,.0f}명",
    textposition="outside",
    cliponaxis=False,
)

fig.update_layout(
    xaxis_title="일일 관객수 (명)",
    yaxis_title="",
    yaxis=dict(categoryorder="total ascending"),
    margin=dict(l=20, r=100, t=60, b=30),
)

st.plotly_chart(fig, use_container_width=True)

# 화면 하단에 데이터 출처를 표시합니다.
st.caption(
    "데이터 출처: 영화진흥위원회(KOBIS) 오픈API · "
    f"조회일: {display_date}"
)
