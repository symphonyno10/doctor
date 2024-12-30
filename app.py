import streamlit as st
import pandas as pd
import os
import plotly.express as px

def main():
    st.title("처방의사 분석 앱 (PDF/콘솔 출력 제거 버전)")

    st.write("""
    **기능 요약**  
    1) CSV 업로드 (첫 행 skiprows=1로 건너뛰고, 두 번째 행을 헤더로 사용)  
    2) '처방의사' 기준 조제 건수 → 상위 10 + '기타' 합산  
    3) Plotly Bar/Pie 차트 표시  
    4) 최종 CSV 저장  
    """)

    # 1) CSV 업로드
    uploaded_file = st.file_uploader("CSV 파일을 업로드하세요", type=["csv"])
    if uploaded_file is not None:
        st.write(f"**업로드된 파일**: {uploaded_file.name}")

        # CSV 읽기 (첫 행 건너뛰고, 두 번째 행을 헤더로 사용)
        try:
            df = pd.read_csv(uploaded_file, skiprows=1, encoding="utf-8-sig")
        except UnicodeDecodeError:
            df = pd.read_csv(uploaded_file, skiprows=1, encoding="euc-kr")

        # 열 이름 정리 (개행, 공백 제거)
        df.columns = (
            df.columns
            .str.replace('\n', '', regex=True)
            .str.replace('\r', '', regex=True)
            .str.replace('\t', '', regex=True)
            .str.strip()
            .str.replace(' ', '')
        )

        # (옵션) '합계' 행 제거 (예: '조제일' 열이 '합계'인 경우)
        if '조제일' in df.columns:
            df = df[df['조제일'] != '합계']

        # '처방의사' 기준 조제 건수 집계
        if '처방의사' not in df.columns:
            st.error("'처방의사' 열이 없습니다. CSV 구조를 확인하세요.")
            return

        df_counts = (
            df.groupby('처방의사')['처방의사']
            .count()
            .rename("조제건수")
            .reset_index()
            .sort_values(by='조제건수', ascending=False)
        )

        # 전체 조제건수 합계
        total_count = df_counts["조제건수"].sum()
        df_counts["점유율(%)"] = df_counts["조제건수"] / total_count * 100

        # 상위 10 + '기타' 처리
        if len(df_counts) > 10:
            df_top10 = df_counts.iloc[:10].copy()
            df_rest = df_counts.iloc[10:].copy()

            rest_count = df_rest["조제건수"].sum()
            rest_ratio = df_rest["점유율(%)"].sum()

            df_etc = pd.DataFrame({
                "처방의사": ["기타"],
                "조제건수": [rest_count],
                "점유율(%)": [rest_ratio]
            })
            df_counts_final = pd.concat([df_top10, df_etc], ignore_index=True)
        else:
            df_counts_final = df_counts.copy()

        st.subheader("처방의사별 조제 건수 및 점유율 (상위 10명 + 기타)")
        st.dataframe(df_counts_final)

        # Plotly Bar Chart
        st.subheader("Bar Chart - 점유율(%)")
        fig_bar = px.bar(
            df_counts_final,
            x='처방의사',
            y='점유율(%)',
            text='점유율(%)',
            color='처방의사',
            title="처방의사별 점유율(%)"
        )
        fig_bar.update_layout(yaxis=dict(range=[0, 100]))
        fig_bar.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        st.plotly_chart(fig_bar)

        # Plotly Pie Chart
        st.subheader("Pie Chart - 조제건수")
        fig_pie = px.pie(
            df_counts_final,
            values='조제건수',
            names='처방의사',
            title="처방의사별 조제 건수",
            hole=0.3
        )
        fig_pie.update_traces(
            hovertemplate='처방의사=%{label}<br>조제건수=%{value}건<br>비율=%{percent:.1%}'
        )
        st.plotly_chart(fig_pie)

        # 결과 CSV 저장
        st.write("---")
        st.write("#### 결과 테이블 CSV 저장하기")
        save_path = st.text_input("결과를 저장할 파일 경로 (예: C:/temp/result.csv)")

        if st.button("CSV 저장"):
            if save_path.strip() == "":
                st.error("저장할 경로를 입력하세요.")
            else:
                dir_name = os.path.dirname(save_path)
                if dir_name and not os.path.exists(dir_name):
                    os.makedirs(dir_name, exist_ok=True)

                df_counts_final.to_csv(save_path, index=False, encoding="utf-8-sig")
                st.success(f"결과가 저장되었습니다: {save_path}")

if __name__ == "__main__":
    main()
