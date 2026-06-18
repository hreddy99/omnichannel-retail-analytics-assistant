"""
Renders the architecture diagram as a high-res PNG (Pillow) for the deck.
Run: python presentation/build_arch_diagram.py -> presentation/architecture.png
"""
from PIL import Image, ImageDraw, ImageFont

# ---- palette ----
RED=(196,18,48); INK=(15,23,42); GREY=(82,92,107); MIST=(138,147,163)
LINE=(214,221,230); WHITE=(255,255,255); SHADOW=(228,232,238)
BLUE=(37,99,235); INDIGO=(79,70,229); GREEN=(21,128,61); AMBER=(180,84,9); TEAL=(15,118,110)
BLUE_T=(230,238,255); INDIGO_T=(237,236,254); GREEN_T=(230,244,234)
AMBER_T=(252,240,225); RED_T=(252,231,235); TEAL_T=(226,242,240)

W, H = 2360, 1010
img = Image.new("RGB", (W, H), WHITE)
d = ImageDraw.Draw(img)

FREG = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
FBLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FIT  = "/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf"
def font(sz, bold=False, ital=False):
    return ImageFont.truetype(FBLD if bold else (FIT if ital else FREG), sz)

def text_center(cx, cy, s, f, fill):
    l,t,r,b = d.textbbox((0,0), s, font=f)
    d.text((cx-(r-l)/2, cy-(b-t)/2 - t), s, font=f, fill=fill)

def text_left(x, y, s, f, fill):
    d.text((x, y), s, font=f, fill=fill)

def rrect(box, rad, fill, outline=None, width=3, shadow=False):
    x0,y0,x1,y1 = box
    if shadow:
        d.rounded_rectangle((x0+5,y0+7,x1+5,y1+7), rad, fill=SHADOW)
    d.rounded_rectangle(box, rad, fill=fill, outline=outline, width=width)

def chip(x, y, label, tint, tc, fpx=23, padx=20, h=52):
    f = font(fpx, bold=True)
    l,t,r,b = d.textbbox((0,0), label, font=f)
    w = (r-l) + padx*2
    rrect((x, y, x+w, y+h), h//2, tint, outline=tc, width=2)
    text_center(x+w/2, y+h/2, label, f, tc)
    return w

def box(bx, title, sub, tint, tc, note=None):
    x0,y0,x1,y1 = bx
    rrect(bx, 22, tint, outline=tc, width=4, shadow=True)
    cx = (x0+x1)/2
    if note:
        text_center(cx, y0+ (y1-y0)*0.34, title, font(34, bold=True), tc)
        text_center(cx, y0+ (y1-y0)*0.60, sub, font(23), GREY)
        text_center(cx, y1-30, note, font(19, ital=True), GREEN)
    else:
        text_center(cx, y0+ (y1-y0)*0.40, title, font(34, bold=True), tc)
        text_center(cx, y0+ (y1-y0)*0.66, sub, font(23), GREY)

def arrow_right(x0, x1, y, color=MIST, w=7):
    d.line((x0, y, x1-16, y), fill=color, width=w)
    d.polygon([(x1, y), (x1-20, y-13), (x1-20, y+13)], fill=color)

def arrow_up(x, y0, y1, color=LINE, w=8):
    d.line((x, y0, x, y1+16), fill=color, width=w)
    d.polygon([(x, y1), (x-13, y1+20), (x+13, y1+20)], fill=color)

# ---- row 1: concept chips ----
concepts = [("ReAct orchestration",BLUE_T,BLUE),("RAG",INDIGO_T,INDIGO),
            ("Knowledge graph",TEAL_T,TEAL),("Multi-agent",BLUE_T,BLUE),
            ("Tree-of-Thoughts + beam",RED_T,RED),("Guardrails",AMBER_T,AMBER),
            ("LLM grounding",GREEN_T,GREEN)]
cx = 24
for label,tint,tc in concepts:
    cx += chip(cx, 8, label, tint, tc) + 16

# ---- row 2: guardrails wrapper band ----
rrect((24, 96, W-24, 188), 18, AMBER_T, outline=AMBER, width=3)
text_center(W/2, 142, "GUARDRAILS   ·   read-only SQL   ·   version / freshness gate   ·   "
            "write-refusal   ·   append-only audit trail", font(27, bold=True), AMBER)

# ---- row 3: the flow ----
flow = [("User question","natural language",BLUE_T,BLUE,None),
        ("Orchestrator","LangGraph ReAct loop",INDIGO_T,INDIGO,None),
        ("Multi-agent team","7 analysts · in parallel",BLUE_T,BLUE,None),
        ("Critic + beam","0–14 rubric → review",RED_T,RED,None),
        ("Governed answer","evidence · confidence · action",GREEN_T,GREEN,"LLM drafts wording only")]
n=len(flow); gap=66; m=24
bw=( (W-2*m) - gap*(n-1) )/n
y0,y1 = 232, 556
xs=[]
for i,(t1,t2,tint,tc,note) in enumerate(flow):
    x0 = m + i*(bw+gap); x1=x0+bw; xs.append((x0,x1))
    box((x0,y0,x1,y1), t1, t2, tint, tc, note=note)
for i in range(n-1):
    arrow_right(xs[i][1]+8, xs[i+1][0]-8, (y0+y1)/2)

# ---- row 4: governed foundation ----
text_left(24, 588, "GOVERNED FOUNDATION  (feeds the loop)", font(23, bold=True), GREY)
found=[("YAML catalog","source of truth",RED_T,RED),
       ("ChromaDB","RAG retrieval",INDIGO_T,INDIGO),
       ("NetworkX","knowledge graph",TEAL_T,TEAL),
       ("DuckDB","medallion data · read-only",GREEN_T,GREEN)]
fn=len(found); fgap=42
fbw=((W-2*m)-fgap*(fn-1))/fn
fy0,fy1=686,976
for i,(t1,t2,tint,tc) in enumerate(found):
    x0=m+i*(fbw+fgap); x1=x0+fbw
    arrow_up((x0+x1)/2, 680, 632)            # short arrow, sits in the gap
    box((x0,fy0,x1,fy1), t1, t2, tint, tc)

img.save("presentation/architecture.png")
print("saved presentation/architecture.png", img.size)
