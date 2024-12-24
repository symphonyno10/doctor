import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.express as px

def main():
    st.title("처방의사 비율 분석 앱 (상위 10명 + 기타)")

    st.write("""
    **기능 요약**  
    1) CSV 업로드  
    2) 첫 행을 건너뛰고(`skiprows=1`), 두 번째 행을 헤더로 사용  
    3) '처방의사' 열 기준으로 조제 건수 집계 → 건수 내림차순 정렬  
    4) 상위 10명만 표시, 나머지는 '기타'로 합산  
    5) 점유율(%) 표 및 기둥그래프, 원그래프 출력  
    6) 결과 테이블 CSV로 저장  
    """)

    # 1) CSV 업로드
    uploaded_file = st.file_uploader("CSV 파일을 업로드하세요", type=["csv"])
    
    if uploaded_file is not None:
        st.write(f"**업로드된 파일**: {uploaded_file.name}")

        # 2) 첫 행(0번째)을 건너뛰고 1번째를 헤더로 사용
        try:
            df = pd.read_csv(uploaded_file, skiprows=1, encoding="utf-8-sig")
        except UnicodeDecodeError:
            # 만약 utf-8-sig가 아니면 euc-kr로 시도
            df = pd.read_csv(uploaded_file, skiprows=1, encoding="euc-kr")

        # (디버깅용) 원본 컬럼명 표시
        st.subheader("CSV 컬럼명 (정리 전)")
        st.write(df.columns.tolist())

        # 열 이름 정리 (개행, 공백 제거)
        df.columns = (
            df.columns
            .str.replace('\n', '', regex=True)
            .str.replace('\r', '', regex=True)
            .str.replace('\t', '', regex=True)
            .str.strip()
            .str.replace(' ', '')
        )

        st.subheader("CSV 컬럼명 (정리 후)")
        st.write(df.columns.tolist())

        # 필요시, '합계' 행 제거 (예: '조제일' 열이 '합계'인 경우)
        if '조제일' in df.columns:
            df = df[df['조제일'] != '합계']

        # 3) 처방의사별 건수, 비율 계산
        if '처방의사' not in df.columns:
            st.error("'처방의사' 열이 존재하지 않습니다. CSV 파일 구조를 확인하세요.")
            return

        # groupby 후 건수 계산
        df_counts = df.groupby('처방의사')['처방의사'].count().rename("조제건수")
        df_counts = df_counts.reset_index()

        # 건수가 많은 순으로 내림차순 정렬
        df_counts = df_counts.sort_values(by='조제건수', ascending=False)

        # 전체 조제 건수
        total_count = df_counts["조제건수"].sum()

        # 점유율(%) 계산
        df_counts["점유율(%)"] = df_counts["조제건수"] / total_count * 100

        # 4) 상위 10명 + 나머지(기타)로 합치기
        if len(df_counts) > 10:
            # 상위 10명
            df_top10 = df_counts.iloc[:10].copy()
            # 나머지
            df_rest = df_counts.iloc[10:].copy()

            rest_count = df_rest["조제건수"].sum()
            rest_ratio = df_rest["점유율(%)"].sum()

            # "기타" 행을 만들어 df_top10에 추가
            df_etc = pd.DataFrame({
                "처방의사": ["기타"],
                "조제건수": [rest_count],
                "점유율(%)": [rest_ratio]
            })

            df_counts_final = pd.concat([df_top10, df_etc], ignore_index=True)
        else:
            # 처방의사가 10명 이하라면 그대로
            df_counts_final = df_counts.copy()

        st.subheader("처방의사별 조제 건수 및 점유율 (상위 10명 + 기타)")
        st.dataframe(df_counts_final)

        # 5) 시각화
        st.subheader("기둥그래프 (Bar Chart) - 점유율(%) 기준")
        fig_bar = px.bar(
            df_counts_final,
            x='처방의사', 
            y='점유율(%)', 
            text='점유율(%)',
            color='처방의사',  # 색상 구분(옵션)
            title="처방의사별 점유율(%) (Bar Chart)"
        )
        fig_bar.update_layout(yaxis=dict(range=[0, 100]))  # y축 0~100 범위
        fig_bar.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        st.plotly_chart(fig_bar)

        st.subheader("원그래프 (Pie Chart) - 조제건수 기준")
        fig_pie = px.pie(
            df_counts_final,
            values='조제건수',
            names='처방의사',
            title="처방의사별 조제 건수 (Pie Chart)",
            hole=0.3  # 도넛 모양
        )
        # hover 시 점유율(%) 표시
        fig_pie.update_traces(hovertemplate='처방의사=%{label}<br>조제건수=%{value}건<br>비율=%{percent:.1%}')
        st.plotly_chart(fig_pie)

        # 6) 결과 CSV 저장
        st.write("---")
        st.write("#### 결과 테이블 저장하기")

        save_path = st.text_input("결과를 저장할 파일 경로 (예: C:/temp/result.csv)")

        if st.button("저장하기"):
            if save_path.strip() == "":
                st.error("저장할 경로를 입력하세요.")
            else:
                # 경로에 폴더가 없다면 생성
                dir_name = os.path.dirname(save_path)
                if dir_name and not os.path.exists(dir_name):
                    os.makedirs(dir_name, exist_ok=True)

                df_counts_final.to_csv(save_path, index=False, encoding="utf-8-sig")
                st.success(f"결과가 저장되었습니다: {save_path}")

if __name__ == "__main__":
    main()
