import streamlit as st
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pandas as pd
import requests
import json

st.set_page_config(page_title="ระบบเช็คชื่อออนไลน์", page_icon="📋", layout="centered")
st.title("📋 ระบบเช็คชื่อและนับวันขาดสะสมรายสัปดาห์ (Online)")

# 🔗 ท่อส่งข้อมูลผ่าน Web App หลังบ้านของ Google Sheets (ของบอสที่ใช้งานได้จริง)
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyrj_wUbQ_yVfDkYZBI2gAmo10Jkhm712lif7Z_PNQ6r66xKtyNH86pGu8tCzSfjKLi/exec"

# ลิงก์ดึงข้อมูลรายชื่อตั้งต้นมาแสดงผล
sheet_url = "https://docs.google.com/spreadsheets/d/174ayeuwSmC4xqZRj5PC_q0nMuinwkcHEpINmmoCyhH0/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# ฟังก์ชันโหลดข้อมูลตอนเปิดเว็บ
def load_data():
    try:
        df = conn.read(spreadsheet=sheet_url, ttl=0)
        for col in ["id", "name", "status", "absent_days", "last_checked_date"]:
            if col not in df.columns:
                df[col] = ""
        return df.to_dict(orient="records")
    except:
        return []

# ฟังก์ชันเซฟข้อมูลใหม่ (แก้จุดตายจากที่ใช้ conn.update เปลี่ยนมาส่งผ่านท่อแทน)
def save_data_to_sheets(data_list):
    try:
        headers = {"Content-Type": "application/json"}
        payload = json.dumps(data_list)
        response = requests.post(SCRIPT_URL, data=payload, headers=headers)
        if response.status_code == 200:
            return True
        return False
    except:
        return False

# ตรวจสอบค่าภายใน Session
if "students" not in st.session_state:
    raw_data = load_data()
    for s in raw_data:
        if not s.get("status"): s["status"] = "ขาด"
        if not s.get("absent_days"): s["absent_days"] = 0
        if not s.get("last_checked_date"): s["last_checked_date"] = ""
    st.session_state.students = raw_data

current_date = datetime.now().strftime("%Y-%m-%d")
current_week = datetime.now().strftime("%U")

if "last_date" not in st.session_state: st.session_state.last_date = current_date
if "last_week" not in st.session_state: st.session_state.last_week = current_week

# ตรวจสอบการรีเซ็ตวัน / สัปดาห์
if st.session_state.last_date != current_date:
    for student in st.session_state.students:
        if student["status"] == "ขาด" and student.get("last_checked_date") != st.session_state.last_date:
            student["absent_days"] = int(student.get("absent_days", 0)) + 1
            student["last_checked_date"] = st.session_state.last_date
        student["status"] = "ขาด"
    st.session_state.last_date = current_date
    st.toast("🔄 เริ่มต้นวันใหม่! รีเซ็ตสถานะประจำวันแล้ว", icon="ℹ️")

if st.session_state.last_week != current_week:
    for student in st.session_state.students:
        student["absent_days"] = 0
    st.session_state.last_week = current_week
    st.toast("📅 เริ่มต้นสัปดาห์ใหม่! รีเซ็ตยอดขาดสะสมเป็น 0 แล้ว", icon="ℹ️")

st.info(f"📅 วันที่เช็คชื่อปัจจุบัน: **{datetime.now().strftime('%d/%m/%Y')}** (สัปดาห์ที่ {current_week})")

# --- 💾 ปุ่มบันทึกข้อมูลแบบใหม่ (ไม่มีระเบิดหน้าจอแดงแน่นอน) ---
if st.button("💾 บันทึกข้อมูลลง Google Sheets (เซฟถาวร)", type="primary", use_container_width=True):
    with st.spinner("กำลังส่งข้อมูลอัปเดตลง Google Sheets..."):
        if save_data_to_sheets(st.session_state.students):
            st.success("✅ บันทึกสถิติข้อมูลลง Google Sheets สำเร็จแล้วครับบอส!")
        else:
            st.error("❌ บันทึกไม่สำเร็จ กรุณาตรวจสอบสิทธิ์การตั้งค่า Web App ใน Google Sheets")

st.markdown("---")

# --- ส่วนที่ 1: เพิ่มรายชื่อ ---
st.subheader("➕ เพิ่มรายชื่อใหม่")
col1, col2 = st.columns([3, 1])
with col1:
    new_name = st.text_input("ชื่อ-นามสกุล", placeholder="พิมพ์ชื่อที่ต้องการเพิ่มที่นี่...", label_visibility="collapsed")
with col2:
    if st.button("เพิ่มรายชื่อ", use_container_width=True):
        if new_name.strip() != "":
            student_id = str(datetime.now().timestamp())
            st.session_state.students.append({
                "id": student_id, "name": new_name, "status": "ขาด", "absent_days": 0, "last_checked_date": ""
            })
            # บันทึกข้อมูลลงชีตให้อัตโนมัติทันทีที่มีการเพิ่มชื่อใหม่
            save_data_to_sheets(st.session_state.students)
            st.rerun()

st.markdown("---")

# --- ส่วนที่ 2: ตารางแสดงข้อมูลและการเช็คชื่อ ---
st.subheader("🧑‍💻 รายชื่อ การเช็คชื่อ และยอดขาดสะสมอาทิตย์นี้")
if len(st.session_state.students) == 0:
    st.info("ยังไม่มีข้อมูลรายชื่อในระบบ ลองเพิ่มชื่อด้านบนได้เลยครับ")
else:
    total_students = len(st.session_state.students)
    present_count = sum(1 for s in st.session_state.students if s["status"] == "มา")
    absent_count = sum(1 for s in st.session_state.students if s["status"] == "ขาด")
    leave_count = sum(1 for s in st.session_state.students if s["status"] == "ลา")

    def sort_by_status(student):
        if student["status"] == "ขาด": return 1
        elif student["status"] == "ลา": return 2
        else: return 3

    sorted_students = sorted(st.session_state.students, key=sort_by_status)

    for display_index, student in enumerate(sorted_students):
        c_num, c_name, c_history, c_status, c_delete = st.columns([0.5, 3.5, 1.2, 2, 0.6])
        with c_num:
            st.write(f"**{display_index + 1}**")
        with c_name:
            if student["status"] == "ขาด": st.write(f"🔴 **{student['name']}**")
            elif student["status"] == "ลา": st.write(f"🟡 *{student['name']}*")
            else: st.write(f"🟢 {student['name']}")
        with c_history:
            st.markdown(f"⚠️ ขาด **{int(student.get('absent_days', 0))}** วัน")
        with c_status:
            if student["status"] == "ขาด": button_type = "type"; display_text = "🔴 ขาด"
            elif student["status"] == "มา": button_type = "primary"; display_text = "🟢 มา"
            else: button_type = "secondary"; display_text = "🟡 ลา"
            
            if st.button(display_text, key=f"btn_{student['id']}", type="secondary" if button_type=="type" else button_type, use_container_width=True):
                for original_student in st.session_state.students:
                    if original_student["id"] == student["id"]:
                        if original_student["status"] == "ขาด": original_student["status"] = "มา"
                        elif original_student["status"] == "มา": original_student["status"] = "ลา"
                        else: original_student["status"] = "ขาด"
                st.rerun()
                
            if student["status"] == "ขาด":
                st.markdown(f"""<style>div.stButton > button[key="btn_{student['id']}"] {{background-color: #ff4b4b !important; color: white !important; border: none !important;}}</style>""", unsafe_allow_html=True)
        with c_delete:
            if st.button("❌", key=f"del_{student['id']}"):
                st.session_state.students = [s for s in st.session_state.students if s["id"] != student["id"]]
                save_data_to_sheets(st.session_state.students)
                st.rerun()

    st.markdown("---")
    st.subheader("📊 สรุปยอดรวมวันนี้")
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric(label="จำนวนทั้งหมด", value=f"{total_students} คน")
    with m2: st.metric(label="🟢 มา", value=f"{present_count} คน")
    with m3: st.metric(label="🔴 ขาด", value=f"{absent_count} คน")
    with m4: st.metric(label="🟡 ลา", value=f"{leave_count} คน")
