import streamlit as st
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="ระบบเช็คชื่อออนไลน์", page_icon="📋", layout="centered")
st.title("📋 ระบบเช็คชื่อและนับวันขาดสะสม (Online)")

# ดึงลิงก์ Google Sheets จากระบบตั้งค่าของ Streamlit
sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]

# เชื่อมต่อ Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# ฟังก์ชันโหลดข้อมูล
def load_data():
    try:
        df = conn.read(spreadsheet=sheet_url, ttl=0)
        return df.to_dict(orient="records")
    except:
        return []

# ฟังก์ชันเซฟข้อมูล
def save_data(data):
    df = pd.DataFrame(data)
    conn.update(spreadsheet=sheet_url, data=df)
    st.cache_data.clear()

# โหลดข้อมูลเข้าเว็บ
if "students" not in st.session_state:
    st.session_state.students = load_data()

current_date = datetime.now().strftime("%Y-%m-%d")
if "last_date" not in st.session_state:
    st.session_state.last_date = current_date

# ระบบรีเซ็ตวันต่อวัน (ตัดคำว่า เรียน ออกในตรรกะเช็คสถานะ)
if st.session_state.last_date != current_date:
    for student in st.session_state.students:
        if student["status"] == "ขาด" and student.get("last_checked_date") != st.session_state.last_date:
            student["absent_days"] = int(student.get("absent_days", 0)) + 1
            student["last_checked_date"] = st.session_state.last_date
        student["status"] = "ขาด"
    st.session_state.last_date = current_date
    save_data(st.session_state.students)
    st.toast("🔄 เริ่มต้นวันใหม่! รีเซ็ตสถานะและอัปเดตยอดสะสมแล้ว", icon="ℹ️")

st.info(f"📅 วันที่เช็คชื่อปัจจุบัน: **{datetime.now().strftime('%d/%m/%Y')}**")

# --- ส่วนที่ 1: เพิ่มรายชื่อ ---
st.subheader("➕ เพิ่มรายชื่อนักเรียน")
col1, col2 = st.columns([3, 1])
with col1:
    new_name = st.text_input("ชื่อ-นามสกุล", placeholder="พิมพ์ชื่อนักเรียนที่นี่...", label_visibility="collapsed")
with col2:
    if st.button("เพิ่มรายชื่อ", use_container_width=True):
        if new_name.strip() != "":
            student_id = str(datetime.now().timestamp())
            st.session_state.students.append({
                "id": student_id, "name": new_name, "status": "ขาด", "absent_days": 0, "last_checked_date": ""
            })
            save_data(st.session_state.students)
            st.rerun()

st.markdown("---")

# --- ส่วนที่ 2: ตารางเช็คชื่อ ---
st.subheader("🧑‍🎓 รายชื่อ การเช็คชื่อ และยอดขาดสะสม")
if len(st.session_state.students) == 0:
    st.info("ยังไม่มีรายชื่อนักเรียนในระบบ ลองเพิ่มชื่อด้านบนได้เลยครับ")
else:
    total_students = len(st.session_state.students)
    present_count = sum(1 for s in st.session_state.students if s["status"] == "มา")
    absent_count = sum(1 for s in st.session_state.students if s["status"] == "ขาด")
    leave_count = sum(1 for s in st.session_state.students if s["status"] == "ลา")

    # จัดลำดับความสำคัญตามสถานะใหม่
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
            if student["status"] == "ขาด":
                button_type = "type"; display_text = "🔴 ขาด"
            elif student["status"] == "มา":
                button_type = "primary"; display_text = "🟢 มา"
            else:
                button_type = "secondary"; display_text = "🟡 ลา"
            
            # ปรับการลูปสถานะ: ขาด -> มา -> ลา -> ขาด
            if st.button(display_text, key=f"btn_{student['id']}", type="secondary" if button_type=="type" else button_type, use_container_width=True):
                for original_student in st.session_state.students:
                    if original_student["id"] == student["id"]:
                        if original_student["status"] == "ขาด": original_student["status"] = "มา"
                        elif original_student["status"] == "มา": original_student["status"] = "ลา"
                        else: original_student["status"] = "ขาด"
                save_data(st.session_state.students)
                st.rerun()
                
            if student["status"] == "ขาด":
                st.markdown(f"""<style>div.stButton > button[key="btn_{student['id']}"] {{background-color: #ff4b4b !important; color: white !important; border: none !important;}}</style>""", unsafe_allow_html=True)
        with c_delete:
            if st.button("❌", key=f"del_{student['id']}"):
                st.session_state.students = [s for s in st.session_state.students if s["id"] != student["id"]]
                save_data(st.session_state.students)
                st.rerun()

    st.markdown("---")
    st.subheader("📊 สรุปยอดรวมวันนี้")
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric(label="นักเรียนทั้งหมด", value=f"{total_students} คน")
    with m2: st.metric(label="🟢 มา", value=f"{present_count} คน")
    with m3: st.metric(label="🔴 ขาด", value=f"{absent_count} คน")
    with m4: st.metric(label="🟡 ลา", value=f"{leave_count} คน")