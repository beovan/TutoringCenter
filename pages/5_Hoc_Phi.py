"""Học phí – Phase 2"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import streamlit as st
import pandas as pd
from datetime import date, datetime
import plotly.graph_objects as go
from utils.database import (
    init_db, get_all_classes, get_all_students,
    get_fees, save_fee, get_fee_summary_by_month
)
from utils.auth import check_auth, render_sidebar, get_teacher_id
from utils.helpers import fmt_currency, FEE_STATUS_LABEL, MONTHS_VI

init_db()
st.set_page_config(page_title="Học phí", page_icon="💰", layout="wide")
user = check_auth(); render_sidebar()
teacher_id = get_teacher_id()

st.title("💰 Quản Lý Học Phí")
classes  = get_all_classes(teacher_id=teacher_id)
if not classes:
    st.warning("⚠️ Chưa có lớp."); st.stop()

cls_opts = {f"{c['name']} ({c['subject']})": c["id"] for c in classes}
cls_map  = {c["id"]: c for c in classes}
now      = datetime.now()

tab_nhap, tab_theo_doi, tab_bieu_do = st.tabs([
    "📝 Nhập / Cập nhật", "📋 Theo dõi", "📊 Biểu đồ"
])

with tab_nhap:
    c1, c2, c3 = st.columns(3)
    sel_cls  = c1.selectbox("📖 Lớp", list(cls_opts.keys()), key="fee_cls")
    sel_month= c2.selectbox("Tháng", range(1,13), index=now.month-1,
                             format_func=lambda m: MONTHS_VI[m])
    sel_year = c3.selectbox("Năm", list(range(now.year, now.year-4, -1)))
    cid = cls_opts[sel_cls]; cls_info = cls_map[cid]
    students = get_all_students(class_id=cid)
    if not students:
        st.info("Lớp chưa có học sinh.")
    else:
        existing = {f["student_id"]: f for f in get_fees(class_id=cid, month=sel_month, year=sel_year)}
        st.info(f"💡 Học phí mặc định: **{fmt_currency(cls_info['tuition_fee'])}**")
        st.markdown("---")
        with st.form("fee_form"):
            hdr = st.columns([3,2,2,2,2])
            for h, t in zip(hdr, ["**Học sinh**","**Học phí (₫)**","**Đã nộp (₫)**","**Trạng thái**","**Ghi chú**"]):
                h.markdown(t)
            rows_data = []
            for stu in students:
                sid  = stu["id"]; prev = existing.get(sid,{})
                cols = st.columns([3,2,2,2,2])
                cols[0].markdown(f"**{stu['full_name']}**")
                amount = cols[1].number_input(f"a{sid}", label_visibility="collapsed",
                    value=float(prev.get("amount", cls_info["tuition_fee"])),
                    min_value=0.0, step=100000.0, format="%.0f", key=f"fa{sid}")
                paid = cols[2].number_input(f"p{sid}", label_visibility="collapsed",
                    value=float(prev.get("paid_amount",0)),
                    min_value=0.0, step=100000.0, format="%.0f", key=f"fp{sid}")
                status = cols[3].selectbox(f"s{sid}", list(FEE_STATUS_LABEL.keys()),
                    format_func=lambda x: FEE_STATUS_LABEL[x],
                    index=list(FEE_STATUS_LABEL.keys()).index(prev.get("status","unpaid")),
                    label_visibility="collapsed", key=f"fs{sid}")
                note = cols[4].text_input(f"n{sid}", value=prev.get("note",""),
                    label_visibility="collapsed", key=f"fn{sid}")
                rows_data.append((sid, amount, paid, status, note))
            st.markdown("---")
            submitted = st.form_submit_button("💾 Lưu học phí", type="primary", use_container_width=True)
        if submitted:
            for sid, amount, paid, status, note in rows_data:
                if paid >= amount: status = "paid"
                elif paid > 0:     status = "partial"
                else:              status = "unpaid"
                save_fee(sid, cid, sel_month, sel_year, amount, paid,
                         str(date.today()) if paid > 0 else "", status, note)
            st.success(f"✅ Đã lưu học phí {MONTHS_VI[sel_month]}/{sel_year}!"); st.rerun()

with tab_theo_doi:
    c1, c2, c3 = st.columns(3)
    td_cls   = c1.selectbox("📖 Lớp", ["-- Tất cả --"]+list(cls_opts.keys()), key="td_cls")
    td_month = c2.selectbox("Tháng", range(1,13), index=now.month-1,
                             format_func=lambda m: MONTHS_VI[m], key="td_month")
    td_year  = c3.selectbox("Năm", list(range(now.year, now.year-4, -1)), key="td_year")
    cid_f = cls_opts.get(td_cls)
    fees  = get_fees(class_id=cid_f, month=td_month, year=td_year, teacher_id=teacher_id)
    if not fees:
        st.info("Không có dữ liệu.")
    else:
        df = pd.DataFrame(fees)
        total_a = df["amount"].sum(); total_p = df["paid_amount"].sum()
        total_d = (df["amount"]-df["paid_amount"]).sum()
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("💰 Tổng", fmt_currency(total_a))
        m2.metric("✅ Đã thu", fmt_currency(total_p))
        m3.metric("❌ Còn nợ", fmt_currency(total_d))
        m4.metric("📊 Đóng đủ", f"{(df['status']=='paid').sum()}/{len(df)}")
        st.markdown("---")
        df_s = df[["full_name","class_name","amount","paid_amount","status","paid_date","note"]].copy()
        df_s["amount"]      = df_s["amount"].apply(fmt_currency)
        df_s["paid_amount"] = df_s["paid_amount"].apply(fmt_currency)
        df_s["status"]      = df_s["status"].map(FEE_STATUS_LABEL)
        df_s["paid_date"]   = df_s["paid_date"].apply(lambda d: d[:10] if d else "—")
        df_s.columns = ["Học sinh","Lớp","Học phí","Đã nộp","Trạng thái","Ngày nộp","Ghi chú"]
        def color_s(val):
            if "Đã" in str(val): return "background-color:#E8F5E9"
            if "thiếu" in str(val): return "background-color:#FFF8E1"
            if "Chưa" in str(val): return "background-color:#FFEBEE"
            return ""
        st.dataframe(df_s.style.map(color_s, subset=["Trạng thái"]),
                     use_container_width=True, hide_index=True)
        st.download_button("📥 Xuất CSV",
                           data=df_s.to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"hoc_phi_{td_month}_{td_year}.csv", mime="text/csv")

with tab_bieu_do:
    chart_year = st.selectbox("Năm", list(range(now.year, now.year-4, -1)), key="chart_year")
    fee_summary = get_fee_summary_by_month(chart_year, teacher_id=teacher_id)
    if not fee_summary:
        st.info("Chưa có dữ liệu.")
    else:
        df_c = pd.DataFrame(fee_summary)
        df_c["month_label"] = df_c["month"].apply(lambda m: MONTHS_VI[m])
        fig = go.Figure()
        fig.add_trace(go.Bar(name="✅ Đã thu", x=df_c["month_label"], y=df_c["total_paid"],
                              marker_color="#4CAF50",
                              text=df_c["total_paid"].apply(lambda v: f"{v/1e6:.1f}M"),
                              textposition="auto"))
        fig.add_trace(go.Bar(name="❌ Còn nợ", x=df_c["month_label"], y=df_c["total_debt"],
                              marker_color="#F44336",
                              text=df_c["total_debt"].apply(lambda v: f"{v/1e6:.1f}M"),
                              textposition="auto"))
        fig.update_layout(barmode="group", title=f"📊 Học phí năm {chart_year}",
                          plot_bgcolor="white", paper_bgcolor="white", height=420,
                          yaxis=dict(tickformat=",.0f", title="VNĐ"),
                          legend=dict(orientation="h", yanchor="bottom", y=1.02),
                          margin=dict(t=60, b=40))
        st.plotly_chart(fig, use_container_width=True)
        tp = df_c["total_paid"].sum(); td = df_c["total_debt"].sum()
        fig2 = go.Figure(go.Pie(labels=["✅ Đã thu","❌ Còn nợ"], values=[tp,td],
                                 marker_colors=["#4CAF50","#F44336"], hole=0.5))
        fig2.update_layout(title=f"Tỷ lệ thu phí năm {chart_year}", height=320)
        st.plotly_chart(fig2, use_container_width=True)
