# word_exporter.py — Bulletin Marine Word complet
import io, math
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.section import WD_ORIENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import config

# =============================================================================
# ECMWF OpenCharts — téléchargement automatique des images
# =============================================================================

ECMWF_BASE = "https://charts.ecmwf.int/opencharts-api/v1/products"

def _ecmwf_base_time(run_datetime: datetime) -> str:
    """Formate run_datetime en base_time ISO8601 pour l'API ECMWF."""
    # On utilise toujours 00Z ou 12Z — aligner sur la run 00Z du jour du run
    run_00z = run_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
    return run_00z.strftime("%Y-%m-%dT%H:%M:%SZ")

def _ecmwf_valid_time(run_datetime: datetime) -> str:
    """J+1 à 12UTC = valid_time pour Figure 3."""
    vt = run_datetime.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1, hours=12)
    return vt.strftime("%Y-%m-%dT%H:%M:%SZ")

def fetch_ecmwf_image(url: str, label: str = "") -> io.BytesIO | None:
    """
    Télécharge une image depuis l'API ECMWF OpenCharts.
    L'API retourne d'abord un JSON contenant data.link.href → URL de l'image PNG.
    Retourne un BytesIO prêt à être inséré dans python-docx, ou None si échec.
    """
    try:
        import requests
        headers = {"User-Agent": "Mozilla/5.0 (METEO-BENIN pipeline)"}

        # Étape 1 : appel API → JSON avec l'URL de l'image
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "")

        if "image" in content_type:
            # Cas direct (rare) — déjà une image
            img_url = None
            img_data = resp.content
        elif "json" in content_type or "text" in content_type:
            # Cas normal — extraire l'URL depuis le JSON
            data = resp.json()
            img_url = data.get("data", {}).get("link", {}).get("href")
            if not img_url:
                print(f"  ⚠️  {label} : champ data.link.href absent dans la réponse JSON")
                return None
            # Étape 2 : téléchargement de l'image
            resp2 = requests.get(img_url, headers=headers, timeout=60)
            resp2.raise_for_status()
            img_data = resp2.content
        else:
            print(f"  ⚠️  {label} : Content-Type inattendu ({content_type})")
            return None

        buf = io.BytesIO(img_data)
        buf.seek(0)
        print(f"  ✅ Image téléchargée : {label}")
        return buf

    except Exception as e:
        print(f"  ⚠️  Échec téléchargement {label} : {e}")
        return None

def build_ecmwf_urls(run_datetime: datetime) -> dict:
    """
    Construit les 5 URLs ECMWF en fonction du run_datetime.
    Retourne un dict avec les clés : ensgram, swh_dir, swh_prob, mwp_8s, mwp_15s
    """
    from urllib.parse import quote
    bt = _ecmwf_base_time(run_datetime)   # base_time = 00Z du jour du run
    vt = _ecmwf_valid_time(run_datetime)  # valid_time = J+1 12UTC
    proj = "opencharts_northern_africa"

    def enc(s): return quote(s, safe="")

    # station_name : encoder en ASCII pur (enlever accents)
    import unicodedata
    station_name = unicodedata.normalize("NFKD", config.POINT["name"])
    station_name = station_name.encode("ascii", "ignore").decode("ascii")

    return {
        "ensgram": (
            f"{ECMWF_BASE}/opencharts_meteogram/"
            f"?base_time={enc(bt)}"
            f"&epsgram=classical_wave"
            f"&lat={config.POINT['lat']}"
            f"&lon={config.POINT['lon']}"
            f"&station_name={enc(station_name)}"
        ),
        "swh_dir": (
            f"{ECMWF_BASE}/medium-swh-mwd/"
            f"?base_time={enc(bt)}"
            f"&valid_time={enc(bt)}"
            f"&projection={proj}"
        ),
        "swh_prob": (
            f"{ECMWF_BASE}/medium-swh-probability/"
            f"?base_time={enc(bt)}"
            f"&valid_time={enc(vt)}"
            f"&projection={proj}"
        ),
        "mwp_8s": (
            f"{ECMWF_BASE}/medium-mwp-probability/"
            f"?base_time={enc(bt)}"
            f"&valid_time={enc(vt)}"
            f"&projection={proj}"
            f"&threshold=8"
        ),
        "mwp_15s": (
            f"{ECMWF_BASE}/medium-mwp-probability/"
            f"?base_time={enc(bt)}"
            f"&valid_time={enc(vt)}"
            f"&projection={proj}"
            f"&threshold=15"
        ),
    }

LOGO_REP = Path("D:/pipeline/logo_republique.png")
LOGO_MET = Path("D:/pipeline/logo_meteo_oval.png")   # logo oval seul (col droite en-tête)
BLUE_MED = RGBColor(0x2E,0x75,0xB6); WHITE = RGBColor(0xFF,0xFF,0xFF); BLACK = RGBColor(0,0,0)
ENG_DS = {0:"Mon.",1:"Tue.",2:"Wed.",3:"Thu.",4:"Fri.",5:"Sat.",6:"Sun."}
ENG_MS = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
ENG_DF = {0:"Monday",1:"Tuesday",2:"Wednesday",3:"Thursday",4:"Friday",5:"Saturday",6:"Sunday"}
ENG_MF = {1:"January",2:"February",3:"March",4:"April",5:"May",6:"June",7:"July",8:"August",9:"September",10:"October",11:"November",12:"December"}
DAY_BG = {0:"DBE5F1",1:"D8E4BC",2:"FFF2CC",3:"F2DCDB",4:"E5E0EC",5:"FDEADA",6:"EAD1DC"}
WX_LIST = ["Sunny","Mostly sunny","Partly cloudy","Mostly cloudy","Overcast","Mostly sunny (night)","Partly cloudy (night)","Mostly cloudy (night)","Thunderstorm","Thunderstorm (moderate)","Thunderstorm (heavy)","Heavy rain showers","Light rain showers","Light rain showers (night)","Dust","Dust storm","Dry haze","Dry haze (night)","Fog / Mist"]

# Nombre de pas de temps par jour (8 pas de 3h sur 24h)
STEPS_PER_DAY = 8

def ordinal(n):
    if 11<=n<=13: return f"{n}th"
    return f"{n}"+{1:"st",2:"nd",3:"rd"}.get(n%10,"th")

def fmt_period(dt):
    return f"{ENG_DF[dt.weekday()]}, {ordinal(dt.day)} {ENG_MF[dt.month]} {dt.year} at 07:00 pm"

def fmt(v,d=1):
    if v is None or (isinstance(v,float) and math.isnan(v)): return "—"
    return f"{v:.{d}f}" if d>0 else str(int(round(v)))

def sbg(cell,col):
    tc=cell._tc; p=tc.get_or_add_tcPr()
    for o in p.findall(qn('w:shd')): p.remove(o)
    s=OxmlElement('w:shd'); s.set(qn('w:val'),'clear'); s.set(qn('w:color'),'auto'); s.set(qn('w:fill'),col); p.append(s)

def smg(cell,t=20,b=20,l=25,r=25):
    tc=cell._tc; p=tc.get_or_add_tcPr(); m=OxmlElement('w:tcMar')
    for sd,v in [('top',t),('bottom',b),('left',l),('right',r)]:
        el=OxmlElement(f'w:{sd}'); el.set(qn('w:w'),str(v)); el.set(qn('w:type'),'dxa'); m.append(el)
    p.append(m)

def sbo(cell):
    tc=cell._tc; p=tc.get_or_add_tcPr(); b=OxmlElement('w:tcBorders')
    for sd in ['top','bottom','left','right']:
        el=OxmlElement(f'w:{sd}'); el.set(qn('w:val'),'single'); el.set(qn('w:sz'),'4'); el.set(qn('w:color'),'BBBBBB'); b.append(el)
    p.append(b)

def snb(cell):
    tc=cell._tc; p=tc.get_or_add_tcPr(); b=OxmlElement('w:tcBorders')
    for sd in ['top','bottom','left','right','insideH','insideV']:
        el=OxmlElement(f'w:{sd}'); el.set(qn('w:val'),'none'); el.set(qn('w:sz'),'0'); el.set(qn('w:color'),'FFFFFF'); b.append(el)
    p.append(b)

def cp(cell,text,sz=7,bold=False,color=None,italic=False):
    p=cell.paragraphs[0]; p.clear(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    r=p.add_run(str(text)); r.font.size=Pt(sz); r.font.bold=bold; r.font.italic=italic
    if color: r.font.color.rgb=color
    return p

def ar(para,text,sz=9,bold=False,color=None,italic=False):
    r=para.add_run(str(text)); r.font.size=Pt(sz); r.font.bold=bold; r.font.italic=italic
    if color: r.font.color.rgb=color
    return r

def ybar(doc):
    p=doc.add_paragraph(); p.paragraph_format.space_before=Pt(0); p.paragraph_format.space_after=Pt(0)
    pp=p._p.get_or_add_pPr(); s=OxmlElement('w:shd'); s.set(qn('w:val'),'clear'); s.set(qn('w:color'),'auto'); s.set(qn('w:fill'),'FFD700'); pp.append(s)
    sp=OxmlElement('w:spacing'); sp.set(qn('w:before'),'0'); sp.set(qn('w:after'),'0'); sp.set(qn('w:line'),'100'); sp.set(qn('w:lineRule'),'exact'); pp.append(sp)
    r=p.add_run(" "); r.font.size=Pt(5)
    rp=OxmlElement('w:rPr'); rs=OxmlElement('w:shd'); rs.set(qn('w:val'),'clear'); rs.set(qn('w:color'),'auto'); rs.set(qn('w:fill'),'FFD700'); rp.append(rs); r._r.append(rp)

def tzone(doc,ph,sz=9):
    p=doc.add_paragraph(); p.paragraph_format.space_before=Pt(2); p.paragraph_format.space_after=Pt(2)
    pp=p._p.get_or_add_pPr(); s=OxmlElement('w:shd'); s.set(qn('w:val'),'clear'); s.set(qn('w:color'),'auto'); s.set(qn('w:fill'),'FFFDE7'); pp.append(s)
    r=p.add_run(ph); r.font.size=Pt(sz); r.font.italic=True; r.font.color.rgb=RGBColor(0x99,0x99,0x99)

def izone(doc,ph,hcm=10):
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before=Pt(4); p.paragraph_format.space_after=Pt(2)
    pp=p._p.get_or_add_pPr(); s=OxmlElement('w:shd'); s.set(qn('w:val'),'clear'); s.set(qn('w:color'),'auto'); s.set(qn('w:fill'),'F0F8FF'); pp.append(s)
    sp=OxmlElement('w:spacing'); sp.set(qn('w:before'),str(int(hcm*567))); sp.set(qn('w:after'),str(int(hcm*567))); pp.append(sp)
    r=p.add_run(ph); r.font.size=Pt(10); r.font.italic=True; r.font.color.rgb=RGBColor(0xAA,0xAA,0xAA)

def add_dropdown(cell):
    """Liste déroulante Weather condition — 7pt fixe."""
    sdt=OxmlElement('w:sdt')
    sp=OxmlElement('w:sdtPr')
    a=OxmlElement('w:alias'); a.set(qn('w:val'),'Weather Condition'); sp.append(a)
    t=OxmlElement('w:tag'); t.set(qn('w:val'),'wx'); sp.append(t)
    # Forcer la police via rPr dans sdtPr
    rpr=OxmlElement('w:rPr')
    sz_pr=OxmlElement('w:sz'); sz_pr.set(qn('w:val'),'14')   # 7pt = 14 demi-points
    szcs=OxmlElement('w:szCs'); szcs.set(qn('w:val'),'14')
    rpr.append(sz_pr); rpr.append(szcs); sp.append(rpr)
    dd=OxmlElement('w:dropDownList')
    i0=OxmlElement('w:listItem'); i0.set(qn('w:displayText'),'— Select —'); i0.set(qn('w:value'),''); dd.append(i0)
    for w in WX_LIST:
        it=OxmlElement('w:listItem'); it.set(qn('w:displayText'),w); it.set(qn('w:value'),w); dd.append(it)
    sp.append(dd); sdt.append(sp)
    sc=OxmlElement('w:sdtContent')
    p=OxmlElement('w:p'); pp2=OxmlElement('w:pPr'); jc=OxmlElement('w:jc'); jc.set(qn('w:val'),'center'); pp2.append(jc); p.append(pp2)
    r=OxmlElement('w:r')
    rp=OxmlElement('w:rPr')
    sz2=OxmlElement('w:sz'); sz2.set(qn('w:val'),'14')
    szcs2=OxmlElement('w:szCs'); szcs2.set(qn('w:val'),'14')
    rp.append(sz2); rp.append(szcs2); r.append(rp)
    tx=OxmlElement('w:t'); tx.text='— Select —'; r.append(tx); p.append(r); sc.append(p); sdt.append(sc)
    tc=cell._tc
    for ch in list(tc): tc.remove(ch)
    tc.append(sdt)


def add_confidence_dropdown(cell):
    """
    Liste déroulante Confidence : Low / Medium / High — 7pt.
    Préserve la fusion de cellule existante (ne supprime pas le vMerge).
    """
    tc = cell._tc
    # Supprimer uniquement les paragraphes existants, pas les attributs de fusion
    for child in list(tc):
        if child.tag in [qn('w:p'), qn('w:sdt')]:
            tc.remove(child)

    sdt = OxmlElement('w:sdt')
    sp  = OxmlElement('w:sdtPr')
    a   = OxmlElement('w:alias'); a.set(qn('w:val'),'Confidence'); sp.append(a)
    t   = OxmlElement('w:tag');   t.set(qn('w:val'),'conf');       sp.append(t)
    rpr = OxmlElement('w:rPr')
    sz_pr = OxmlElement('w:sz');   sz_pr.set(qn('w:val'),'14'); rpr.append(sz_pr)
    szcs  = OxmlElement('w:szCs'); szcs.set(qn('w:val'),'14');  rpr.append(szcs)
    sp.append(rpr)
    dd = OxmlElement('w:dropDownList')
    i0 = OxmlElement('w:listItem'); i0.set(qn('w:displayText'),'— Select —'); i0.set(qn('w:value'),''); dd.append(i0)
    for val in ["Low","Medium","High"]:
        it = OxmlElement('w:listItem'); it.set(qn('w:displayText'),val); it.set(qn('w:value'),val); dd.append(it)
    sp.append(dd); sdt.append(sp)
    sc = OxmlElement('w:sdtContent')
    p  = OxmlElement('w:p')
    pp2 = OxmlElement('w:pPr')
    jc  = OxmlElement('w:jc'); jc.set(qn('w:val'),'center'); pp2.append(jc)
    p.append(pp2)
    r  = OxmlElement('w:r')
    rp = OxmlElement('w:rPr')
    sz2  = OxmlElement('w:sz');   sz2.set(qn('w:val'),'14'); rp.append(sz2)
    szcs2= OxmlElement('w:szCs'); szcs2.set(qn('w:val'),'14'); rp.append(szcs2)
    r.append(rp)
    tx = OxmlElement('w:t'); tx.text = '— Select —'; r.append(tx)
    p.append(r); sc.append(p); sdt.append(sc)
    tc.append(sdt)

def add_header(doc):
    # Tableau principal 3 colonnes
    t=doc.add_table(rows=1,cols=3); t.alignment=WD_TABLE_ALIGNMENT.CENTER; t.style='Table Grid'
    for i,c in enumerate(t.rows[0].cells):
        c.width=[Cm(5.5),Cm(15),Cm(5)][i]; snb(c)

    # Col 0 — Logo République
    cl=t.rows[0].cells[0]; cl.vertical_alignment=WD_ALIGN_VERTICAL.CENTER
    p=cl.paragraphs[0]; p.alignment=WD_ALIGN_PARAGRAPH.LEFT
    if LOGO_REP.exists(): p.add_run().add_picture(str(LOGO_REP),width=Cm(5))
    else: p.add_run("[Logo Rép.]")

    # Col 1 — Titre central
    cc=t.rows[0].cells[1]; cc.vertical_alignment=WD_ALIGN_VERTICAL.CENTER
    for txt,sz,bd in [
        ("DIRECTION DE LA PREVISION ET DU RESEAU D'OBSERVATION METEOROLOGIQUE",8.5,True),
        ("SERVICE DE LA PREVISION ET DE L'ASSISTANCE METEOROLOGIQUE",8.5,True),
        ("MARINE FORECAST FOR SEME",12,True)
    ]:
        p=cc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before=Pt(1); p.paragraph_format.space_after=Pt(1)
        r=p.add_run(txt); r.bold=bd; r.font.size=Pt(sz)
    cc.paragraphs[0]._p.getparent().remove(cc.paragraphs[0]._p)

    # Col 2 — Logo Météo Bénin avec coordonnées intégrées
    cr=t.rows[0].cells[2]; cr.vertical_alignment=WD_ALIGN_VERTICAL.CENTER
    p=cr.paragraphs[0]; p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    if LOGO_MET.exists():
        p.add_run().add_picture(str(LOGO_MET), width=Cm(4.8))
    else:
        p.add_run("[Logo Météo Bénin]")

def make_full_table(doc, df_sorted):
    """
    Tableau complet toutes colonnes — 3 niveaux d'en-têtes.
    - Colonne Date (col 0) : fusionnée par jour + 2 cellules vides en en-tête
    - Colonne Confidence (col 22) : fusionnée par jour
    - Pagination : jours 1-2 sur page 1, jours 3-4 sur page 2
    """
    COLS = [
        ("Date",1.7),("Time",0.85),
        ("Dir.",0.65),("Spd\n(kts)",0.65),("Gust\n(kts)",0.65),
        ("Dir.",0.65),("Spd\n(kts)",0.65),
        ("MSLP\n(hPa)",0.8),("Vis.\n(km)",0.6),("T\n(°C)",0.6),
        ("Weather\ncond.",1.9),("Rain\n(%)",0.6),("SST\n(°C)",0.6),
        ("Dir.",0.6),("Per.\n(s)",0.6),("Ht.\n(m)",0.6),
        ("Dir.",0.6),("Per.\n(s)",0.6),("Ht.\n(m)",0.6),
        ("S.W\n(m)",0.65),
        ("Dir.",0.6),("Spd.\n(m/s)",0.65),
        ("Conf.",1.5),
    ]
    NC = len(COLS)
    GRP = [
        (0,1,"Date & Time"),(2,4,"Wind at 10m"),(5,6,"Wind at 100m"),
        (7,7,"MSLP (hPa)"),(8,8,"Vis. (km)"),(9,9,"T (°C)"),
        (10,10,"Weather condition"),(11,11,"Rain (%)"),(12,12,"SST (°C)"),
        (13,15,"Swell 1"),(16,18,"Swell 2"),(19,19,"S.W (m)"),
        (20,21,"Currents"),(22,22,"Confidence")
    ]

    # Regrouper les lignes par jour
    df_sorted = df_sorted.copy()
    df_sorted["_dt"] = pd.to_datetime(df_sorted["valid_local"])
    df_sorted["_day"] = df_sorted["_dt"].dt.date
    days = list(df_sorted["_day"].unique())

    # Nombre total de lignes de données
    N = len(df_sorted)

    # Créer le tableau : 3 lignes d'en-têtes + N lignes données
    tbl = doc.add_table(rows=3 + N, cols=NC)
    tbl.style = 'Table Grid'
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER

    # ── Ligne 0 : Weather / Ocean parameters ──────────────────────────────
    r0 = tbl.rows[0]
    # Col 0-1 (Date & Time) : vides mais bleu
    for j in range(2):
        sbg(r0.cells[j], "2E75B6"); sbo(r0.cells[j])
    cw = r0.cells[2].merge(r0.cells[12])
    sbg(cw,"2E75B6"); sbo(cw)
    cp(cw,"Weather parameters",sz=9,bold=True,color=WHITE)
    cw.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    co = r0.cells[13].merge(r0.cells[22])
    sbg(co,"2E75B6"); sbo(co)
    cp(co,"Ocean parameters",sz=9,bold=True,color=WHITE)
    co.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    # ── Ligne 1 : groupes ─────────────────────────────────────────────────
    r1 = tbl.rows[1]; done = set()
    for gs, ge, lbl in GRP:
        if gs in done: continue
        c = r1.cells[gs].merge(r1.cells[ge]) if gs != ge else r1.cells[gs]
        sbg(c,"2E75B6"); sbo(c); smg(c,15,15,20,20)
        cp(c, lbl, sz=7, bold=True, color=WHITE)
        c.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        for i in range(gs, ge+1): done.add(i)

    # ── Ligne 2 : sous-en-têtes ───────────────────────────────────────────
    # Col 0 (Date) : afficher "Date & Time" sur cette ligne seulement
    r2 = tbl.rows[2]
    for j, (lbl, w) in enumerate(COLS):
        c = r2.cells[j]
        sbg(c,"BDD7EE"); sbo(c); smg(c,15,15,20,20)
        # Col 0 : "Date & Time" centré verticalement sur 3 lignes
        display_lbl = lbl if j != 0 else "Date & Time"
        cp(c, display_lbl, sz=6.5, bold=True,
           color=RGBColor(0x1F,0x4E,0x79))
        c.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        c.width = Cm(w)

    # ── Données : par jour avec fusions ───────────────────────────────────
    row_offset = 0  # décalage dans le tableau (après 3 lignes d'en-têtes)

    for day_idx, day in enumerate(days):
        day_rows = df_sorted[df_sorted["_day"] == day]
        n_day = len(day_rows)
        bg = DAY_BG[list(day_rows["_dt"])[0].weekday()]

        # Saut de page après le 2ème jour (entre jour 2 et jour 3)
        if day_idx == 2 and row_offset > 0:
            # Ajouter saut de page sur la première ligne du 3ème jour
            first_data_row = tbl.rows[3 + row_offset]
            first_cell = first_data_row.cells[1]
            fc_p = first_cell.paragraphs[0]._p
            fc_pPr = fc_p.get_or_add_pPr()
            pb = OxmlElement('w:pageBreakBefore')
            pb.set(qn('w:val'), '1')
            fc_pPr.append(pb)

        for k, (_, rd) in enumerate(day_rows.iterrows()):
            dt = pd.to_datetime(rd.get("valid_local"))
            swh = rd.get("swh_m")
            ws  = rd.get("wind10_spd_kt")
            i   = row_offset + k
            tr  = tbl.rows[3 + i]

            # Valeurs pour chaque colonne
            vals = [
                "",  # Date — sera fusionnée (col 0)
                dt.strftime("%H:%M"),  # Time (24h)
                str(rd.get("wind10_dir") or "—"), fmt(ws,0),
                fmt(rd.get("wind10_gust_kt"),0),
                str(rd.get("wind100_dir") or "—"),
                fmt(rd.get("wind100_spd_kt"),0),
                fmt(rd.get("mslp_hpa"),0), fmt(rd.get("vis_km"),0),
                fmt(rd.get("t2m_c"),0),
                None,  # Weather condition — liste déroulante (col 10)
                str(rd.get("rain_pct","—")), fmt(rd.get("sst_c"),0),
                str(rd.get("sw1_dir") or "—"),
                fmt(rd.get("sw1_period_s"),0), fmt(rd.get("sw1_ht_m"),1),
                str(rd.get("sw2_dir") or "—"),
                fmt(rd.get("sw2_period_s"),0), fmt(rd.get("sw2_ht_m"),1),
                fmt(swh,1),
                str(rd.get("cur_dir") or "—"),
                fmt(rd.get("cur_spd_ms"),2),
                "",  # Confidence — sera fusionnée (col 22)
            ]

            for j, v in enumerate(vals):
                c = tr.cells[j]; cb = bg
                try:
                    if j==19 and swh and not math.isnan(float(swh)):
                        if swh>=config.ALERT_SWH_DANGER: cb="FF0000"
                        elif swh>=config.ALERT_SWH_WARNING: cb="FFCC00"
                    if j==3 and ws and not math.isnan(float(ws)):
                        if ws>=config.ALERT_WIND_DANGER: cb="FF0000"
                        elif ws>=config.ALERT_WIND_WARNING: cb="FFCC00"
                except: pass

                sbg(c,cb); sbo(c); smg(c,12,12,18,18)
                c.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

                if j == 10:   # Weather condition
                    sbg(c,"FFFACD"); add_dropdown(c)
                elif j == 22: # Confidence — liste déroulante
                    sbg(c,"E8F5E9"); add_confidence_dropdown(c)
                elif j == 0:  # Date — vide (sera fusionnée)
                    cp(c,"",sz=9)
                else:
                    fc = WHITE if cb=="FF0000" else None
                    cp(c, str(v) if v is not None else "—", sz=9, color=fc)

        # ── Fusionner colonne Date (col 0) sur tout le jour ───────────────
        if n_day > 1:
            first_row_idx = 3 + row_offset
            last_row_idx  = 3 + row_offset + n_day - 1
            merged_date = tbl.rows[first_row_idx].cells[0].merge(
                          tbl.rows[last_row_idx].cells[0])
            day_label = f"{ENG_DS[list(day_rows['_dt'])[0].weekday()]} {list(day_rows['_dt'])[0].day:02d} {ENG_MS[list(day_rows['_dt'])[0].month]}"
            sbg(merged_date, bg)
            sbo(merged_date)
            smg(merged_date,12,12,18,18)
            cp(merged_date, day_label, sz=7, bold=True)
            merged_date.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

        # ── Fusionner colonne Confidence (col 22) sur tout le jour ────────
        if n_day > 1:
            first_row_idx = 3 + row_offset
            last_row_idx  = 3 + row_offset + n_day - 1
            merged_conf = tbl.rows[first_row_idx].cells[22].merge(
                          tbl.rows[last_row_idx].cells[22])
            sbg(merged_conf,"E8F5E9")
            sbo(merged_conf)
            smg(merged_conf,12,12,18,18)
            merged_conf.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            add_confidence_dropdown(merged_conf)

        row_offset += n_day

    # Col 0 en-tête : laisser les 2 lignes séparées mais bleues
    for row_i in range(2):
        c = tbl.rows[row_i].cells[0]
        sbg(c,"2E75B6"); sbo(c)
        cp(c,"",sz=9,color=WHITE)

def _safe(lst):
    """Remplace None/NaN par 0 pour matplotlib."""
    return [v if (v is not None and not (isinstance(v, float) and math.isnan(v))) else 0 for v in lst]

def gen_chart(df_sorted):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    times = pd.to_datetime(df_sorted["valid_local"])
    speed = _safe(df_sorted["wind10_spd_kt"].tolist())
    gust  = _safe(df_sorted["wind10_gust_kt"].tolist())
    mslp  = _safe(df_sorted["mslp_hpa"].tolist())
    x = range(len(times))
    lbl=[t.strftime("%H:%M") for t in times]; td={}; prev=None
    for i,t in enumerate(times):
        if t.date()!=prev: td[i]=f"{ENG_DS[t.weekday()]}\n{t.day}\n{ENG_MS[t.month]}\n{t.strftime('%H:%M')}"; prev=t.date()
    fig,ax1=plt.subplots(figsize=(13,6.5)); fig.patch.set_facecolor("white")
    ax2=ax1.twinx(); ax2.bar(x,mslp,color="#FFC000",alpha=0.8,label="MSLP",zorder=2); ax2.set_ylabel("Pressure (hPa)",fontsize=9); ax2.tick_params(axis="y",labelsize=8)
    mc=[v for v in mslp if v]; 
    if mc: ax2.set_ylim(min(mc)-3,max(mc)+3)
    ax1.set_zorder(ax2.get_zorder()+1); ax1.patch.set_visible(False)
    ax1.plot(x,speed,color="#4472C4",linewidth=2.5,label="Speed",zorder=5); ax1.plot(x,gust,color="#ED7D31",linewidth=2.5,label="Gust",zorder=5)
    ax1.set_ylabel("Wind (Kts)",fontsize=9); ax1.set_xlabel("Times",fontsize=9); ax1.tick_params(axis="y",labelsize=8); ax1.set_xlim(-0.5,len(x)-0.5)
    gc=[v for v in gust if v]; ax1.set_ylim(0,(max(gc) if gc else 20)+4); ax1.grid(True,linestyle="--",alpha=0.4,zorder=1)
    ax1.set_xticks(list(x)); ax1.set_xticklabels([td.get(i,lbl[i]) for i in list(x)],fontsize=6.5,ha="center")
    l1,lb1=ax1.get_legend_handles_labels(); l2,lb2=ax2.get_legend_handles_labels()
    ax1.legend(l2+l1,lb2+lb1,loc="lower center",ncol=3,fontsize=8,bbox_to_anchor=(0.5,-0.28),frameon=True)
    plt.tight_layout(); buf=io.BytesIO(); fig.savefig(buf,format="png",dpi=140,bbox_inches="tight"); plt.close(fig); buf.seek(0); return buf

def sec_land(doc):
    s=doc.add_section(); s.orientation=WD_ORIENT.LANDSCAPE; s.page_width=Cm(29.7); s.page_height=Cm(21); s.left_margin=Cm(1.2); s.right_margin=Cm(1.2); s.top_margin=Cm(1.2); s.bottom_margin=Cm(1.2); return s

def sec_port(doc):
    s=doc.add_section(); s.orientation=WD_ORIENT.PORTRAIT; s.page_width=Cm(21); s.page_height=Cm(29.7); s.left_margin=Cm(1.5); s.right_margin=Cm(1.5); s.top_margin=Cm(1.5); s.bottom_margin=Cm(1.5); return s

def generate_word_bulletin(df, run_datetime, warning_text=None, output_path=None):
    # Nom du fichier avec date et run — identique à l'Excel
    date_str = run_datetime.strftime("%d%m%Y")
    run_str  = f"{run_datetime.hour:02d}Z"
    if output_path is None:
        output_path = f"D:/pipeline/Marine_forecast_{date_str}_{run_str}.docx"
    else:
        base = output_path.replace(".docx", "").replace(".xlsx", "")
        output_path = f"{base}_{date_str}_{run_str}.docx"

    df_sorted = df.sort_values("valid_local").reset_index(drop=True)
    dt_start  = pd.to_datetime(df_sorted["valid_local"].iloc[0])
    dt_end    = dt_start + timedelta(days=3)

    doc = Document()
    # Section 1 — Paysage
    s1=doc.sections[0]; s1.orientation=WD_ORIENT.LANDSCAPE; s1.page_width=Cm(29.7); s1.page_height=Cm(21); s1.left_margin=Cm(1.2); s1.right_margin=Cm(1.2); s1.top_margin=Cm(1.2); s1.bottom_margin=Cm(1.2)

    # En-tête
    add_header(doc); ybar(doc)

    # Période — 12pt
    p=doc.add_paragraph(); p.paragraph_format.space_before=Pt(3); p.paragraph_format.space_after=Pt(2)
    ar(p,f"From {fmt_period(dt_start)} to {fmt_period(dt_end)} (local time)",sz=12,bold=True)
    ybar(doc)

    # Warning — 12pt
    pw=doc.add_paragraph(); pw.paragraph_format.space_before=Pt(3); pw.paragraph_format.space_after=Pt(3)
    pp=pw._p.get_or_add_pPr(); wd=warning_text or "Warning: None."
    bg="FF0000" if "ALERT" in wd.upper() else ("E2EFDA" if "Warning: None" in wd else "FFCC00")
    s=OxmlElement('w:shd'); s.set(qn('w:val'),'clear'); s.set(qn('w:color'),'auto'); s.set(qn('w:fill'),bg); pp.append(s)
    r=pw.add_run(wd); r.font.size=Pt(12); r.font.bold=True
    if bg=="FF0000": r.font.color.rgb=WHITE
    elif bg=="E2EFDA": r.font.color.rgb=RGBColor(0x1E,0x6B,0x3C)
    else: r.font.color.rgb=RGBColor(0x7F,0x4E,0x00)

    # Met Situation — 12pt
    pm=doc.add_paragraph(); pm.paragraph_format.space_before=Pt(3); pm.paragraph_format.space_after=Pt(1)
    ar(pm,"Met Situation:",sz=12,bold=True); tzone(doc,"[ Met situation — enter text here ]",sz=12)

    # Weather — 12pt
    pw2=doc.add_paragraph(); pw2.paragraph_format.space_before=Pt(3); pw2.paragraph_format.space_after=Pt(1)
    ar(pw2,"Weather:",sz=12,bold=True); tzone(doc,"[ Weather description — enter text here ]",sz=12)

    # Titre Table 1 — 12pt
    pt=doc.add_paragraph(); pt.paragraph_format.space_before=Pt(4); pt.paragraph_format.space_after=Pt(2)
    ar(pt,"Table 1: Weather and Ocean parameters",sz=12,bold=True)

    # Tableau complet
    make_full_table(doc,df_sorted)

    # Légende
    pl=doc.add_paragraph(); pl.paragraph_format.space_before=Pt(2)
    ar(pl,"🟨 Weather condition: select from dropdown  |  🟩 Confidence: enter manually  |  Dir=Direction | Spd=Speed (kts for wind, m/s for currents) | Per=Period(s) | Ht=Height(m) | S.W=Significant Wave Height",sz=8,italic=True,color=RGBColor(0x66,0x66,0x66))

    # ── Page portrait : Figure 1 + Marées ────────────────────────────────
    sec_port(doc)
    print("  🖼️  Figure 1...")
    buf=gen_chart(df_sorted)
    pc=doc.add_paragraph(); pc.alignment=WD_ALIGN_PARAGRAPH.CENTER; pc.paragraph_format.space_before=Pt(4); pc.paragraph_format.space_after=Pt(2)
    pc.add_run().add_picture(buf,width=Cm(17))
    # Titre sous le graphique — 12pt
    pf1=doc.add_paragraph(); pf1.alignment=WD_ALIGN_PARAGRAPH.CENTER; pf1.paragraph_format.space_before=Pt(2); pf1.paragraph_format.space_after=Pt(6)
    ar(pf1,f"Figure 1: Trends of winds and Mean Sea Level Pressure from {ordinal(dt_start.day)} to {ordinal(dt_end.day)} {ENG_MF[dt_start.month]} {dt_start.year}",sz=12,bold=True)

    # Titre Table 2 — 12pt
    pt2=doc.add_paragraph(); pt2.paragraph_format.space_before=Pt(4); pt2.paragraph_format.space_after=Pt(2)
    ar(pt2,"❖  Table 2: Tides predictions for SEME",sz=12,bold=True)

    # ── Récupérer les marées via WorldTides API ───────────────────────────
    try:
        import tides as tides_module
        tide_data  = tides_module.get_tides(dt_start, days=4)
        tide_rows  = tides_module.format_tide_table(tide_data, dt_start, days=4)
    except Exception as e:
        print(f"  ⚠️  Marées non disponibles : {e}")
        tide_rows = []

    n_data = max(len(tide_rows), 4)
    tide=doc.add_table(rows=2+n_data, cols=9)
    tide.style='Table Grid'; tide.alignment=WD_TABLE_ALIGNMENT.CENTER

    # En-tête ligne 1
    r0=tide.rows[0]
    sbg(r0.cells[0],"2E75B6"); sbo(r0.cells[0]); cp(r0.cells[0],"Dates",sz=9,bold=True,color=WHITE)
    ch=r0.cells[1].merge(r0.cells[4]); sbg(ch,"2E75B6"); sbo(ch); cp(ch,"HIGH TIDES",sz=9,bold=True,color=WHITE)
    cl2=r0.cells[5].merge(r0.cells[8]); sbg(cl2,"2E75B6"); sbo(cl2); cp(cl2,"LOW TIDES",sz=9,bold=True,color=WHITE)

    # En-tête ligne 2
    r1=tide.rows[1]
    for j,lbl in enumerate(["Dates","Time","Height","Time","Height","Time","Height","Time","Height"]):
        c=r1.cells[j]; sbg(c,"BDD7EE"); sbo(c)
        cp(c,lbl,sz=9,bold=True,color=RGBColor(0x1F,0x4E,0x79))

    # Données : remplies automatiquement si WorldTides disponible, sinon vides
    DAY_BGS = ["DBE5F1","D8E4BC","FFF2CC","F2DCDB"]
    for i in range(n_data):
        row=tide.rows[2+i]; bg=DAY_BGS[i%4]
        if i < len(tide_rows):
            tr = tide_rows[i]
            vals=[tr["date"],
                  tr["high1"]["time"],tr["high1"]["height"],
                  tr["high2"]["time"],tr["high2"]["height"],
                  tr["low1"]["time"], tr["low1"]["height"],
                  tr["low2"]["time"], tr["low2"]["height"]]
        else:
            vals=[""] * 9
        for j,v in enumerate(vals):
            c=row.cells[j]; sbg(c,bg); sbo(c); cp(c,str(v),sz=9)

    # ── Page portrait : Figure 2 ENSgram ─────────────────────────────────
    sec_port(doc)
    print("  🌐 Téléchargement Figure 2 (ENSgram ECMWF)...")
    ecmwf_urls = build_ecmwf_urls(run_datetime)
    img_ensgram = fetch_ecmwf_image(ecmwf_urls["ensgram"], "ENSgram")

    if img_ensgram:
        pe=doc.add_paragraph(); pe.alignment=WD_ALIGN_PARAGRAPH.CENTER
        pe.paragraph_format.space_before=Pt(4); pe.paragraph_format.space_after=Pt(2)
        pe.add_run().add_picture(img_ensgram, width=Cm(17))
    else:
        izone(doc,"[ ENSgram ECMWF — image non disponible (vérifier connexion) ]",hcm=8)

    pf2=doc.add_paragraph(); pf2.alignment=WD_ALIGN_PARAGRAPH.CENTER; pf2.paragraph_format.space_before=Pt(2); pf2.paragraph_format.space_after=Pt(4)
    ar(pf2,f"Figure 2: Wave ensemblegram issued by ECMWF from {ordinal(dt_start.day)} to {ordinal(dt_end.day)} {ENG_MF[dt_start.month]} {dt_start.year}",sz=12,bold=True)
    pc2=doc.add_paragraph(); ar(pc2,"❖  Significant wave heights are forecast to...",sz=12,bold=True)
    tzone(doc,"[ Commentary on ENSgram — enter text here ]",sz=9)

    # ── Page portrait : Figure 3 (4 cartes ECMWF) ────────────────────────
    sec_port(doc)
    fig3d=run_datetime+timedelta(days=1)
    print("  🌐 Téléchargement Figure 3 (4 cartes ECMWF)...")

    FIG3_KEYS   = ["swh_dir", "swh_prob", "mwp_8s", "mwp_15s"]
    FIG3_LABELS = [
        "SWH & mean direction",
        "Prob. SWH ≥2m",
        "Prob. mean wave period ≥8s",
        "Prob. mean wave period ≥15s",
    ]
    fig3_imgs = [fetch_ecmwf_image(ecmwf_urls[k], FIG3_LABELS[i])
                 for i, k in enumerate(FIG3_KEYS)]

    it=doc.add_table(rows=2,cols=2); it.style='Table Grid'; it.alignment=WD_TABLE_ALIGNMENT.CENTER
    cells=[it.rows[0].cells[0],it.rows[0].cells[1],it.rows[1].cells[0],it.rows[1].cells[1]]

    for idx, cell in enumerate(cells):
        snb(cell); cell.width=Cm(8.5)
        # Supprimer paragraphe vide initial
        if cell.paragraphs:
            cell.paragraphs[0]._p.getparent().remove(cell.paragraphs[0]._p)

        # Sous-titre de la carte
        pt_sub = cell.add_paragraph()
        pt_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pt_sub.paragraph_format.space_before = Pt(2)
        pt_sub.paragraph_format.space_after  = Pt(1)
        r_sub = pt_sub.add_run(FIG3_LABELS[idx])
        r_sub.font.size  = Pt(7)
        r_sub.font.bold  = True
        r_sub.font.color.rgb = RGBColor(0x1F,0x4E,0x79)

        # Image ou placeholder
        pi = cell.add_paragraph()
        pi.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pi.paragraph_format.space_before = Pt(1)
        pi.paragraph_format.space_after  = Pt(2)

        if fig3_imgs[idx]:
            pi.add_run().add_picture(fig3_imgs[idx], width=Cm(8.0))
        else:
            pp2 = pi._p.get_or_add_pPr()
            s2  = OxmlElement('w:shd'); s2.set(qn('w:val'),'clear'); s2.set(qn('w:color'),'auto'); s2.set(qn('w:fill'),'F0F8FF'); pp2.append(s2)
            sp2 = OxmlElement('w:spacing'); sp2.set(qn('w:before'),'800'); sp2.set(qn('w:after'),'800'); pp2.append(sp2)
            ri  = pi.add_run(f"[ Image {idx+1} — non disponible ]")
            ri.font.size = Pt(8); ri.font.italic = True; ri.font.color.rgb = RGBColor(0xAA,0xAA,0xAA)

    # Titre Figure 3 — sous le tableau d'images
    pf3=doc.add_paragraph(); pf3.alignment=WD_ALIGN_PARAGRAPH.CENTER; pf3.paragraph_format.space_before=Pt(4); pf3.paragraph_format.space_after=Pt(2)
    ar(pf3,f"Figure 3: Probability forecast for {ENG_DF[fig3d.weekday()]}, {ordinal(fig3d.day)} {ENG_MF[fig3d.month]} {fig3d.year} at 01:00 pm local time.",sz=12,bold=True)

    doc.save(output_path)
    print(f"  ✅ Bulletin Word : {output_path}")
    return output_path