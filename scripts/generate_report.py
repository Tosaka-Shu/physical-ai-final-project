from pathlib import Path
import re
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, Image, KeepTogether
import argparse
parser=argparse.ArgumentParser(description="日本語説明資料PDFの生成")
parser.add_argument('--source',default='docs/report_outline.md')
parser.add_argument('--output',default='submission/report.pdf')
args=parser.parse_args()
source=Path(args.source).read_text(encoding='utf-8')
out=Path(args.output)
out.parent.mkdir(parents=True,exist_ok=True)
font="HeiseiKakuGo-W5"
pdfmetrics.registerFont(UnicodeCIDFont(font))
st=getSampleStyleSheet()
st.add(ParagraphStyle(name="JPTitle",parent=st["Title"],fontName=font,fontSize=19,leading=27,alignment=TA_CENTER,textColor=colors.HexColor("#17324d"),spaceAfter=17*mm))
st.add(ParagraphStyle(name="JPSection",parent=st["Heading2"],fontName=font,fontSize=13,leading=19,textColor=colors.HexColor("#174a6e"),spaceBefore=5*mm,spaceAfter=2*mm,keepWithNext=True))
st.add(ParagraphStyle(name="JPBody",parent=st["BodyText"],fontName=font,fontSize=9.5,leading=15,alignment=TA_JUSTIFY,wordWrap="CJK",spaceAfter=3*mm))
st.add(ParagraphStyle(name="JPBullet",parent=st["BodyText"],fontName=font,fontSize=9.5,leading=15,alignment=TA_LEFT,wordWrap="CJK",leftIndent=5*mm,firstLineIndent=-3*mm,spaceAfter=1.5*mm))
def inline(text):
 text=re.sub(r"\[([^\]]+)\]\([^)]+\)",r"\1",text)
 text=re.sub(r"`([^`]+)`",r"\1",text)
 return re.sub(r"\*\*(.+?)\*\*",r"<b>\1</b>",escape(text))
flow=[]; lines=source.splitlines(); i=0
while i<len(lines):
 line=lines[i].strip()
 if not line: i+=1; continue
 if line.startswith("!["):
  match=re.match(r"!\[([^\]]*)\]\(([^)]+)\)",line)
  if match:
   image_path=Path(match[2])
   if not image_path.is_absolute():image_path=Path(args.source).parent/image_path
   pic=Image(str(image_path)); ratio=min(1,160*mm/pic.imageWidth,95*mm/pic.imageHeight)
   pic.drawWidth=pic.imageWidth*ratio;pic.drawHeight=pic.imageHeight*ratio
   flow.append(KeepTogether([pic,Paragraph(inline(match[1]),st["JPBody"])]))
   i+=1;continue
 if line.startswith("# "):
  flow.extend([Spacer(1,22*mm),Paragraph(inline(line[2:]),st["JPTitle"]),Spacer(1,3*mm)]); i+=1; continue
 if line.startswith("## "):
  flow.append(Paragraph(inline(line[3:]),st["JPSection"])); i+=1; continue
 if line.startswith("- "):
  items=[]
  while i<len(lines) and lines[i].strip().startswith("- "):
   items.append(ListItem(Paragraph(inline(lines[i].strip()[2:]),st["JPBullet"]),leftIndent=5*mm)); i+=1
  flow.append(ListFlowable(items,bulletType="bullet",leftIndent=5*mm,bulletFontName=font,bulletFontSize=7,bulletColor=colors.HexColor("#174a6e"),spaceAfter=2*mm)); continue
 para=[line]; i+=1
 while i<len(lines) and lines[i].strip() and not lines[i].lstrip().startswith(("#","- ")):
  para.append(lines[i].strip()); i+=1
 flow.append(Paragraph(inline(" ".join(para)),st["JPBody"]))
def page(canvas,doc):
 canvas.saveState(); canvas.setStrokeColor(colors.HexColor("#d5e0e8")); canvas.line(22*mm,14*mm,A4[0]-22*mm,14*mm); canvas.setFont(font,8); canvas.setFillColor(colors.HexColor("#596b78")); canvas.drawRightString(A4[0]-22*mm,9*mm,str(doc.page)); canvas.restoreState()
doc=SimpleDocTemplate(str(out),pagesize=A4,rightMargin=22*mm,leftMargin=22*mm,topMargin=20*mm,bottomMargin=19*mm,title="AI危険度予測による災害救援物資の自律配送ロボット",author="",subject="シミュレーション設計、危険度予測、比較実験")
doc.build(flow,onFirstPage=page,onLaterPages=page)
print(out,out.stat().st_size)
