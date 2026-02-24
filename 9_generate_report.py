from docxtpl import DocxTemplate, InlineImage
from docx.shared import Mm
import os

# =========================
# 1) เตรียมโฟลเดอร์ปลายทาง
# =========================
output_dir = "report_output"
os.makedirs(output_dir, exist_ok=True)

# =========================
# 2) โหลด template
# =========================
doc = DocxTemplate("template.docx")

# =========================
# 3) ระบุ path รูปที่มีอยู่แล้ว
# =========================
graph_path = os.path.join(output_dir, "load_profile.png")

# ตรวจสอบว่ามีไฟล์จริงไหม
if not os.path.exists(graph_path):
    raise FileNotFoundError(f"ไม่พบไฟล์รูป: {graph_path}")

load_graph = InlineImage(doc, graph_path, width=Mm(120))

# =========================
# 4) ข้อมูลทดสอบ
# =========================
context = {
    "project_name": "Solar Rooftop โรงงาน A",
    "pv_capacity": 500,
    "annual_energy": 720000,
    "irr": 14.2,
    "payback": 6.8,
    "load_graph": load_graph
}

# =========================
# 5) Render และ Save
# =========================
doc.render(context)

output_path = os.path.join(output_dir, "output_test.docx")
doc.save(output_path)

print(f"Generate report success! -> {output_path}")