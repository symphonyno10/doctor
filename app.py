import streamlit as st
import pandas as pd
import plotly.express as px
from fpdf import FPDF
import traceback  # 에러 스택 추적용

def main():
    st.title("처방의사 분석 + PDF 생성 디버깅 예시")

    st.write("""
    **기능 요약**  
    1) CSV 업로드 (첫 행은 skiprows=1로 건너뛰고, 두 번째 행을 헤더로 사용)  
    2) '처방의사' 기준 조제 건수 → 상위 10 + '기타'로 합산  
    3) Plotly Bar/Pie 차트 표시  
    4) PDF 생성 과정에서 각 단계별 로그/에러메시지 표시  
    5) 최종 CSV 저장
    """)

    # 1) CSV 업로드
    uploaded_file = st.file_uploader("CSV 파일 업로드", type=["csv"])
    if uploaded_file is not None:
        st.write(f"**업로드된 파일**: {uploaded_file.name}")

        # CSV 읽기 (첫 행 건너뛰고, 두 번째 행을 헤더로 사용)
        try:
            df = pd.read_csv(uploaded_file, skiprows=1, encoding="utf-8-sig")
        except UnicodeDecodeError:
            df = pd.read_csv(uploaded_file, skiprows=1, encoding="euc-kr")
        except Exception as e:
            st.error(f"CSV 파일 읽기 실패: {e}")
            st.write(traceback.format_exc())
            return

        # 열 이름 정리 (개행/공백 제거)
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

        # 2) '처방의사' 기준 조제 건수 집계
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
        total_count = df_counts["조제건수"].sum()
        df_counts["점유율(%)"] = df_counts["조제건수"] / total_count * 100

        # 상위 10 + 기타
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

        # 3) Plotly Bar 차트
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

        # Plotly Pie 차트
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

        # 4) PDF 생성 과정 디버깅
        st.write("---")
        st.write("#### PDF 생성 (디버그 로그 및 에러 메시지 표시)")
        if st.button("PDF 생성"):
            st.write("버튼이 눌렸습니다. PDF 생성 과정을 시작합니다...")

            pdf_bytes = create_pdf_with_charts(fig_bar, fig_pie)
            if pdf_bytes is not None:
                st.download_button(
                    label="PDF 다운로드",
                    data=pdf_bytes,
                    file_name="charts.pdf",
                    mime="application/pdf"
                )
            else:
                st.error("PDF 생성에 실패했습니다. (위 로그 참조)")

        # 5) 최종 CSV 저장
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


def create_pdf_with_charts(fig_bar, fig_pie):
    """
    Plotly -> PNG -> PDF 과정 디버깅용:
    각 단계에서 st.write(...) 로그를 남기고,
    에러 발생 시 traceback 표시.
    """
    import traceback

    st.write("[디버그] PDF 생성 함수 진입")

    # 1) Bar 차트 -> PNG
    try:
        st.write("[디버그] Bar 차트 PNG 변환 시도...")
        bar_img = fig_bar.to_image(format="png")
        st.write("[디버그] Bar 차트 PNG 변환 성공!")
    except Exception as e:
        st.error(f"[에러] Bar 차트 PNG 변환 실패: {e}")
        st.write(traceback.format_exc())
        return None

    # 2) Pie 차트 -> PNG
    try:
        st.write("[디버그] Pie 차트 PNG 변환 시도...")
        pie_img = fig_pie.to_image(format="png")
        st.write("[디버그] Pie 차트 PNG 변환 성공!")
    except Exception as e:
        st.error(f"[에러] Pie 차트 PNG 변환 실패: {e}")
        st.write(traceback.format_exc())
        return None

    # 3) FPDF로 PDF 생성
    try:
        st.write("[디버그] FPDF 객체 생성...")
        pdf = FPDF()
        pdf.add_page()

        st.write("[디버그] 임시 파일에 Bar 차트 PNG 저장...")
        bar_img_path = "bar_tmp.png"
        with open(bar_img_path, "wb") as f:
            f.write(bar_img)

        st.write("[디버그] Bar 차트 이미지 PDF 삽입...")
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="Bar Chart - 점유율(%)", ln=1, align="C")
        pdf.image(bar_img_path, x=10, y=30, w=150)
        pdf.ln(85)

        # 다른 페이지에 Pie 차트 삽입
        pdf.add_page()
        st.write("[디버그] 임시 파일에 Pie 차트 PNG 저장...")
        pie_img_path = "pie_tmp.png"
        with open(pie_img_path, "wb") as f:
            f.write(pie_img)

        pdf.cell(200, 10, txt="Pie Chart - 조제건수", ln=1, align="C")
        pdf.image(pie_img_path, x=10, y=30, w=150)

        st.write("[디버그] PDF를 메모리에 저장...")
        pdf_bytes = pdf.output(dest="S").encode("latin-1")
        st.write("[디버그] PDF 생성 완료!")

        return pdf_bytes

    except Exception as e:
        st.error(f"[에러] PDF 생성 과정에서 실패: {e}")
        st.write(traceback.format_exc())
        return None

if __name__ == "__main__":
    main()
