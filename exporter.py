# =============================================================================
# exporter.py — Génération du bulletin Excel Marine (Sème)
# Structure : 4 feuilles
#   Feuille 1 (Paysage) : En-tête + Warning + Met Situation + Weather + Tableau
#   Feuille 2 (Portrait): Figure 1 (Graphique Wind/MSLP) + Tableau marées
#   Feuille 3 (Portrait): Figure 2 (ENSgram — zone image)
#   Feuille 4 (Portrait): Figure 3 (4 images probabilistes — zones images)
# =============================================================================

import io
import math
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.drawing.image import Image as XLImage
from openpyxl.worksheet.datavalidation import DataValidation
from datetime import datetime, timedelta
from pathlib import Path
import config

# ---------------------------------------------------------------------------
# Constantes de style
# ---------------------------------------------------------------------------
BLUE_DARK  = "1F4E79"
BLUE_MED   = "2E75B6"
BLUE_LIGHT = "BDD7EE"
WHITE      = "FFFFFF"
BLACK      = "000000"
YELLOW     = "FFCC00"
RED        = "FF0000"

DAY_COLORS = {0:"EBF5FB",1:"EBF5EB",2:"FEF9E7",3:"FDEDEC",
              4:"F4F6F7",5:"FFF3E0",6:"F3E5F5"}
ENG_DAYS   = {0:"Mon.",1:"Tue.",2:"Wed.",3:"Thu.",4:"Fri.",5:"Sat.",6:"Sun."}
ENG_MONTHS = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
              7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
ENG_MONTHS_FULL = {1:"January",2:"February",3:"March",4:"April",
                   5:"May",6:"June",7:"July",8:"August",
                   9:"September",10:"October",11:"November",12:"December"}
ENG_DAYS_FULL = {0:"Monday",1:"Tuesday",2:"Wednesday",3:"Thursday",
                 4:"Friday",5:"Saturday",6:"Sunday"}

def thin():
    s = Side(style="thin", color="BBBBBB")
    return Border(left=s, right=s, top=s, bottom=s)

def fill(hex_col):
    return PatternFill("solid", fgColor=hex_col)

def hfont(size=9, bold=True, color=WHITE):
    return Font(name="Arial", size=size, bold=bold, color=color)

def dfont(size=8, bold=False, color=BLACK):
    return Font(name="Arial", size=size, bold=bold, color=color)

def center(wrap=False):
    return Alignment(horizontal="center", vertical="center", wrap_text=wrap)

def left(wrap=True):
    return Alignment(horizontal="left", vertical="center", wrap_text=wrap)

def fmt(val, dec=1):
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "—"
    return f"{val:.{dec}f}" if dec > 0 else str(int(round(val)))

def ordinal(n):
    if 11 <= n <= 13: return f"{n}th"
    return f"{n}" + {1:"st",2:"nd",3:"rd"}.get(n%10,"th")

def fmt_period(dt):
    return (f"{ENG_DAYS_FULL[dt.weekday()]}, {ordinal(dt.day)} "
            f"{ENG_MONTHS_FULL[dt.month]} {dt.year} at 07:00 pm")

def add_yellow_line(ws, row, n_cols=24):
    ws.row_dimensions[row].height = 4
    ws.merge_cells(f"A{row}:{get_column_letter(n_cols)}{row}")
    ws[f"A{row}"].fill = fill("FFD700")

def set_page_landscape(ws):
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize   = 9
    ws.page_setup.fitToPage   = True
    ws.page_setup.fitToWidth  = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_view.showGridLines = False

def set_page_portrait(ws):
    ws.page_setup.orientation = "portrait"
    ws.page_setup.paperSize   = 9
    ws.page_setup.fitToPage   = True
    ws.page_setup.fitToWidth  = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_view.showGridLines = False


# ---------------------------------------------------------------------------
# FEUILLE 1 — En-tête + données (Paysage)
# ---------------------------------------------------------------------------

def build_sheet1(ws, df, run_datetime, warning_text, df_sorted):
    set_page_landscape(ws)
    ws.title = "Marine Forecast"

    N = 24
    last_col = get_column_letter(N)

    logo_rep = Path("D:/pipeline/logo_republique.png")
    logo_met = Path("D:/pipeline/logo_meteo_oval.png")

    col_widths = [10,7, 5,6,6, 5,6, 7,6,6, 10,6,6, 5,5,6, 5,5,6, 6, 5,6, 9,7]
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # ── En-tête lignes 1-5 ────────────────────────────────────────────────
    for r in range(1, 6):
        ws.row_dimensions[r].height = 16

    if logo_rep.exists():
        img = XLImage(str(logo_rep))
        img.width = 160; img.height = 72
        ws.add_image(img, "A1")

    ws.merge_cells("E1:P2")
    ws["E1"] = "DIRECTION DE LA PREVISION ET DU RESEAU D'OBSERVATION METEOROLOGIQUE"
    ws["E1"].font = Font(name="Arial", size=9, bold=True)
    ws["E1"].alignment = center(wrap=True)

    ws.merge_cells("E3:P4")
    ws["E3"] = "SERVICE DE LA PREVISION ET DE L'ASSISTANCE METEOROLOGIQUE"
    ws["E3"].font = Font(name="Arial", size=9, bold=True)
    ws["E3"].alignment = center(wrap=True)

    ws.merge_cells("E5:P5")
    ws["E5"] = "MARINE FORECAST FOR SEME"
    ws["E5"].font = Font(name="Arial", size=12, bold=True)
    ws["E5"].alignment = center()

    ws.merge_cells("Q1:W1")
    ws["Q1"] = "AGENCE NATIONALE DE LA METEOROLOGIE"
    ws["Q1"].font = Font(name="Arial", size=8, bold=True, color=BLUE_MED)
    ws["Q1"].alignment = Alignment(horizontal="right", vertical="center")

    for rng, txt in [("Q2:W2","TEL : 00 229 01 94 17 41 57"),
                     ("Q3:W3","01 BP : 379 COTONOU"),
                     ("Q4:W4","Site : www.meteobenin.bj"),
                     ("Q5:W5","E-mail : meteobenin@meteobenin.bj")]:
        ws.merge_cells(rng)
        c = ws[rng.split(":")[0]]
        c.value = txt
        c.font = Font(name="Arial", size=7, color=BLACK)
        c.alignment = Alignment(horizontal="right", vertical="center")

    if logo_met.exists():
        img2 = XLImage(str(logo_met))
        img2.width = 65; img2.height = 65
        ws.add_image(img2, "X1")

    # ── Ligne jaune + période + warning + Met Sit + Weather ───────────────
    add_yellow_line(ws, 6, N)

    ws.row_dimensions[7].height = 16
    dt_start = pd.to_datetime(df_sorted["valid_local"].iloc[0])
    dt_end   = dt_start + timedelta(days=3)
    ws.merge_cells(f"A7:{last_col}7")
    ws["A7"] = f"From {fmt_period(dt_start)} to {fmt_period(dt_end)} (local time)"
    ws["A7"].font = Font(name="Arial", size=9, bold=True)
    ws["A7"].alignment = left(wrap=False)

    add_yellow_line(ws, 8, N)

    ws.row_dimensions[9].height = 22
    ws.merge_cells(f"A9:{last_col}9")
    warning_display = warning_text or "Warning: None."
    ws["A9"] = warning_display
    ws["A9"].alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    if "ALERT" in warning_display.upper():
        ws["A9"].fill = fill(RED)
        ws["A9"].font = Font(name="Arial", size=9, bold=True, color=WHITE)
    elif "Warning: None" in warning_display:
        ws["A9"].fill = fill("E2EFDA")
        ws["A9"].font = Font(name="Arial", size=9, bold=True, color="1E6B3C")
    else:
        ws["A9"].fill = fill("FFCC00")
        ws["A9"].font = Font(name="Arial", size=9, bold=True, color="7F4E00")

    ws.row_dimensions[10].height = 13
    ws.merge_cells(f"A10:{last_col}10")
    ws["A10"] = "Met Situation:"
    ws["A10"].font = Font(name="Arial", size=9, bold=True)
    ws["A10"].alignment = left(wrap=False)

    for r in [11, 12]:
        ws.row_dimensions[r].height = 22
        ws.merge_cells(f"A{r}:{last_col}{r}")
        ws[f"A{r}"].fill = fill("FFFDE7")
        ws[f"A{r}"].font = Font(name="Arial", size=9, italic=True, color="999999")
        ws[f"A{r}"].alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    ws["A11"] = "[ Met situation — enter text here ]"

    ws.row_dimensions[13].height = 13
    ws.merge_cells(f"A13:{last_col}13")
    ws["A13"] = "Weather:"
    ws["A13"].font = Font(name="Arial", size=9, bold=True)
    ws["A13"].alignment = left(wrap=False)

    for r in [14, 15]:
        ws.row_dimensions[r].height = 22
        ws.merge_cells(f"A{r}:{last_col}{r}")
        ws[f"A{r}"].fill = fill("FFFDE7")
        ws[f"A{r}"].font = Font(name="Arial", size=9, italic=True, color="999999")
        ws[f"A{r}"].alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    ws["A14"] = "[ Weather description — enter text here ]"

    ws.row_dimensions[16].height = 13
    ws.merge_cells(f"A16:{last_col}16")
    ws["A16"] = "Table 1: Weather and Ocean parameters"
    ws["A16"].font = Font(name="Arial", size=9, bold=True)
    ws["A16"].alignment = left(wrap=False)

    # ── En-têtes tableau 3 niveaux ────────────────────────────────────────
    ws.row_dimensions[17].height = 14

    # Niveau 1
    ws.merge_cells("A17:B17")
    ws["A17"].fill = fill(BLUE_MED)

    ws.merge_cells("C17:M17")
    ws["C17"] = "Weather parameters"
    ws["C17"].font = hfont(size=9); ws["C17"].fill = fill(BLUE_MED)
    ws["C17"].alignment = center(); ws["C17"].border = thin()

    ws.merge_cells("N17:X17")
    ws["N17"] = "Ocean parameters"
    ws["N17"].font = hfont(size=9); ws["N17"].fill = fill(BLUE_MED)
    ws["N17"].alignment = center(); ws["N17"].border = thin()

    # Niveau 2
    ws.row_dimensions[18].height = 20
    groups = [
        ("A18","B18","Date & Time"),("C18","E18","Wind at 10m"),
        ("F18","G18","Wind at 100m"),("H18","H18","MSLP\n(hPa)"),
        ("I18","I18","Vis.\n(km)"),("J18","J18","T\n(°C)"),
        ("K18","K18","Weather\ncondition"),("L18","L18","Chance\nof rain"),
        ("M18","M18","SST\n(°C)"),("N18","P18","Swell 1"),
        ("Q18","S18","Swell 2"),("T18","T18","S.W\n(m)"),
        ("U18","V18","Currents"),("W18","W18","Confidence\nof forecast"),
        ("X18","X18","SWH\nSource"),
    ]
    for start, end, label in groups:
        if start != end: ws.merge_cells(f"{start}:{end}")
        c = ws[start]
        c.value = label; c.font = hfont(size=8)
        c.fill = fill(BLUE_MED); c.alignment = center(wrap=True); c.border = thin()

    # Niveau 3
    ws.row_dimensions[19].height = 22
    sub = ["Date","Time","Dir.","Spd.\n(kts)","Gust\n(kts)","Dir.","Spd.\n(kts)",
           "MSLP","Vis.","T(°C)","Weather\ncondition","Rain\n(%)","SST\n(°C)",
           "Dir.","Per.\n(s)","Ht.\n(m)","Dir.","Per.\n(s)","Ht.\n(m)",
           "S.W\n(m)","Dir.","Spd.\n(kts)","Conf.","Src"]
    for i, sh in enumerate(sub, 1):
        c = ws.cell(row=19, column=i, value=sh)
        c.font = Font(name="Arial", size=7, bold=True, color=BLUE_DARK)
        c.fill = fill(BLUE_LIGHT); c.alignment = center(wrap=True); c.border = thin()

    # ── Données ───────────────────────────────────────────────────────────
    ws.freeze_panes = "A20"
    current_day = None
    row_idx = 20
    named_range = "'Weather Conditions'!$A$3:$A$21"

    for _, row_data in df_sorted.iterrows():
        dt      = pd.to_datetime(row_data.get("valid_local"))
        day_key = f"{ENG_DAYS[dt.weekday()]} {dt.day:02d} {ENG_MONTHS[dt.month]}"
        day_bg  = DAY_COLORS[dt.weekday()]
        date_disp = day_key if day_key != current_day else ""
        if day_key != current_day: current_day = day_key

        swh      = row_data.get("swh_m")
        wind_spd = row_data.get("wind10_spd_kt")

        values = [
            date_disp, dt.strftime("%H:%M"),
            str(row_data.get("wind10_dir") or "—"), fmt(wind_spd,0),
            fmt(row_data.get("wind10_gust_kt"),0),
            str(row_data.get("wind100_dir") or "—"), fmt(row_data.get("wind100_spd_kt"),0),
            fmt(row_data.get("mslp_hpa"),0), fmt(row_data.get("vis_km"),0),
            fmt(row_data.get("t2m_c"),0), "",
            str(row_data.get("rain_pct","—")), fmt(row_data.get("sst_c"),0),
            str(row_data.get("sw1_dir") or "—"), fmt(row_data.get("sw1_period_s"),0),
            fmt(row_data.get("sw1_ht_m"),1),
            str(row_data.get("sw2_dir") or "—"), fmt(row_data.get("sw2_period_s"),0),
            fmt(row_data.get("sw2_ht_m"),1), fmt(swh,1),
            str(row_data.get("cur_dir") or "—"), fmt(row_data.get("cur_spd_kt"),1),
            "", str(row_data.get("swh_source") or "—"),
        ]

        ws.row_dimensions[row_idx].height = 13
        for col_i, val in enumerate(values, 1):
            bg = day_bg
            try:
                if col_i == 20 and swh and not math.isnan(float(swh)):
                    if swh >= config.ALERT_SWH_DANGER: bg = RED
                    elif swh >= config.ALERT_SWH_WARNING: bg = YELLOW
                if col_i == 4 and wind_spd and not math.isnan(float(wind_spd)):
                    if wind_spd >= config.ALERT_WIND_DANGER: bg = RED
                    elif wind_spd >= config.ALERT_WIND_WARNING: bg = YELLOW
            except: pass
            c = ws.cell(row=row_idx, column=col_i, value=val)
            c.fill = fill(bg); c.font = dfont(size=8)
            c.alignment = center(); c.border = thin()
            if bg == RED: c.font = Font(name="Arial", size=8, bold=True, color=WHITE)

        ws.cell(row=row_idx, column=11).fill = fill("FFFACD")
        ws.cell(row=row_idx, column=23).fill = fill("E8F5E9")

        dv = DataValidation(type="list", formula1=named_range,
                            allow_blank=True, showDropDown=False)
        ws.add_data_validation(dv)
        dv.add(ws.cell(row=row_idx, column=11))
        row_idx += 1

    # Légende
    row_idx += 1
    ws.merge_cells(f"A{row_idx}:{last_col}{row_idx}")
    ws[f"A{row_idx}"] = ("Dir=Direction | Spd=Speed(kts) | MSLP=Mean Sea Level Pressure | "
                          "Vis=Visibility(km) | T=Air Temp(°C) | SST=Sea Surface Temp(°C) | "
                          "Ht=Height(m) | S.W=Significant Wave Height | "
                          "Sources: ECMWF Open Data + Copernicus Marine")
    ws[f"A{row_idx}"].font = Font(name="Arial", size=6, italic=True, color="666666")
    ws[f"A{row_idx}"].alignment = left(wrap=True)
    ws.row_dimensions[row_idx].height = 10


# ---------------------------------------------------------------------------
# FEUILLE Weather Conditions
# ---------------------------------------------------------------------------

def build_weather_sheet(wb):
    ws = wb.create_sheet(title="Weather Conditions")
    ws.sheet_view.showGridLines = False
    ws["A1"] = "Weather Conditions — Reference List"
    ws["A1"].font = Font(name="Arial", size=11, bold=True, color=BLUE_DARK)
    for cell, label in [(ws["A2"],"Code"),(ws["B2"],"Description")]:
        cell.value = label
        cell.font = Font(name="Arial", size=9, bold=True, color=WHITE)
        cell.fill = fill(BLUE_MED); cell.alignment = center()
    ws.column_dimensions["A"].width = 24
    ws.column_dimensions["B"].width = 38
    items = [
        ("Sunny","☀️  Clear sky, sunny"),
        ("Mostly sunny","🌤️  Mostly sunny, few clouds"),
        ("Partly cloudy","⛅  Partly cloudy"),
        ("Mostly cloudy","🌥️  Mostly cloudy"),
        ("Overcast","☁️  Overcast / Cloudy"),
        ("Mostly sunny (night)","🌙  Mostly clear, night"),
        ("Partly cloudy (night)","🌑  Partly cloudy, night"),
        ("Mostly cloudy (night)","🌑  Mostly cloudy, night"),
        ("Thunderstorm","⛈️  Thunderstorm with rain"),
        ("Thunderstorm (moderate)","⛈️  Moderate thunderstorm"),
        ("Thunderstorm (heavy)","⛈️  Heavy thunderstorm"),
        ("Heavy rain showers","🌧️  Heavy rain showers"),
        ("Light rain showers","🌦️  Light rain showers (day)"),
        ("Light rain showers (night)","🌧️  Light rain showers (night)"),
        ("Dust","🌫️  Dust in suspension"),
        ("Dust storm","💨  Dust storm / Harmattan"),
        ("Dry haze","🌅  Dry haze"),
        ("Dry haze (night)","🌙  Dry haze, night"),
        ("Fog / Mist","🌫️  Fog or mist"),
    ]
    for i, (code, desc) in enumerate(items, 3):
        ca = ws.cell(row=i, column=1, value=code)
        cb = ws.cell(row=i, column=2, value=desc)
        bg = "F2F2F2" if i%2==0 else "FFFFFF"
        for c in [ca, cb]:
            c.fill = fill(bg); c.font = Font(name="Arial", size=9); c.border = thin()
        ca.alignment = center(); cb.alignment = left()


# ---------------------------------------------------------------------------
# FEUILLE 2 — Figure 1 + Marées (Portrait)
# ---------------------------------------------------------------------------

def build_sheet2(wb, ws, df_sorted, run_datetime):
    set_page_portrait(ws)
    ws.title = "Fig1 + Tides"
    ws.sheet_view.showGridLines = False

    dt_start = pd.to_datetime(df_sorted["valid_local"].iloc[0])
    dt_end   = dt_start + timedelta(days=3)
    fig1_title = (f"Figure 1: Trends of winds and Mean Sea Level Pressure "
                  f"from {ordinal(dt_start.day)} to {ordinal(dt_end.day)} "
                  f"{ENG_MONTHS_FULL[dt_start.month]} {dt_start.year}")

    ws.row_dimensions[1].height = 16
    ws.merge_cells("A1:N1")
    ws["A1"] = fig1_title
    ws["A1"].font = Font(name="Arial", size=10, bold=True, underline="single")
    ws["A1"].alignment = center()

    # Graphique matplotlib
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    times  = pd.to_datetime(df_sorted["valid_local"])
    speed  = df_sorted["wind10_spd_kt"].tolist()
    gust   = df_sorted["wind10_gust_kt"].tolist()
    mslp   = df_sorted["mslp_hpa"].tolist()
    x      = range(len(times))
    labels = [t.strftime("%H:%M") for t in times]
    tick_dates = {}
    prev_day = None
    for i, t in enumerate(times):
        if t.date() != prev_day:
            tick_dates[i] = f"{ENG_DAYS[t.weekday()]}\n{t.day}\n{ENG_MONTHS[t.month]}\n{t.strftime('%H:%M')}"
            prev_day = t.date()

    fig, ax1 = plt.subplots(figsize=(13, 4.5))
    fig.patch.set_facecolor("white")
    ax2 = ax1.twinx()
    ax2.bar(x, mslp, color="#FFC000", alpha=0.8, label="MSLP", zorder=2)
    ax2.set_ylabel("Pressure (hPa)", fontsize=9)
    ax2.tick_params(axis="y", labelsize=8)
    mslp_clean = [v for v in mslp if v and not math.isnan(v)]
    if mslp_clean: ax2.set_ylim(min(mslp_clean)-3, max(mslp_clean)+3)

    ax1.set_zorder(ax2.get_zorder()+1)
    ax1.patch.set_visible(False)
    ax1.plot(x, speed, color="#4472C4", linewidth=2.5, label="Speed", zorder=5)
    ax1.plot(x, gust,  color="#ED7D31", linewidth=2.5, label="Gust",  zorder=5)
    ax1.set_ylabel("Wind (Kts)", fontsize=9)
    ax1.set_xlabel("Times", fontsize=9)
    ax1.tick_params(axis="y", labelsize=8)
    ax1.set_xlim(-0.5, len(x)-0.5)
    gust_clean = [v for v in gust if v and not math.isnan(v)]
    ax1.set_ylim(0, (max(gust_clean) if gust_clean else 20)+4)
    ax1.grid(True, linestyle="--", alpha=0.4, zorder=1)
    ax1.set_facecolor("white")
    ax1.set_xticks(list(x))
    ax1.set_xticklabels([tick_dates.get(i, labels[i]) for i in list(x)], fontsize=6.5, ha="center")
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines2+lines1, labels2+labels1, loc="lower center", ncol=3,
               fontsize=8, bbox_to_anchor=(0.5,-0.28), frameon=True)
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)

    xl_img = XLImage(buf)
    xl_img.width = 860; xl_img.height = 310
    ws.add_image(xl_img, "A2")
    print("  ✅ Figure 1 insérée.")

    # Tableau marées
    tide_row = 22
    ws.row_dimensions[tide_row].height = 14
    ws.merge_cells(f"A{tide_row}:I{tide_row}")
    ws[f"A{tide_row}"] = "❖  Table 2: Tides predictions for SEME"
    ws[f"A{tide_row}"].font = Font(name="Arial", size=9, bold=True)
    ws[f"A{tide_row}"].alignment = left(wrap=False)

    tide_row += 1
    ws.row_dimensions[tide_row].height = 16
    ws.merge_cells(f"B{tide_row}:E{tide_row}")
    ws[f"B{tide_row}"] = "HIGH TIDES"
    ws[f"B{tide_row}"].font = hfont(size=8); ws[f"B{tide_row}"].fill = fill(BLUE_MED)
    ws[f"B{tide_row}"].alignment = center()
    ws.merge_cells(f"F{tide_row}:I{tide_row}")
    ws[f"F{tide_row}"] = "LOW TIDES"
    ws[f"F{tide_row}"].font = hfont(size=8); ws[f"F{tide_row}"].fill = fill(BLUE_MED)
    ws[f"F{tide_row}"].alignment = center()
    ws[f"A{tide_row}"].fill = fill(BLUE_MED); ws[f"A{tide_row}"].font = hfont(size=8)

    tide_row += 1
    ws.row_dimensions[tide_row].height = 14
    for col_i, label in enumerate(["Dates","Time","Height","Time","Height","Time","Height","Time","Height"],1):
        c = ws.cell(row=tide_row, column=col_i, value=label)
        c.fill = fill(BLUE_LIGHT); c.font = Font(name="Arial", size=8, bold=True, color=BLUE_DARK)
        c.alignment = center(); c.border = thin()

    for i in range(4):
        tide_row += 1
        ws.row_dimensions[tide_row].height = 14
        for col_i in range(1, 10):
            c = ws.cell(row=tide_row, column=col_i, value="")
            c.fill = fill(list(DAY_COLORS.values())[i])
            c.font = dfont(); c.alignment = center(); c.border = thin()

    print("  ✅ Tableau marées ajouté.")


# ---------------------------------------------------------------------------
# FEUILLE 3 — Figure 2 ENSgram (Portrait)
# ---------------------------------------------------------------------------

def build_sheet3(ws, run_datetime):
    set_page_portrait(ws)
    ws.title = "Fig2 ENSgram"
    ws.sheet_view.showGridLines = False

    dt = run_datetime
    ws.row_dimensions[1].height = 16
    ws.merge_cells("A1:N1")
    ws["A1"] = (f"Figure 2: Wave ensemblegram issued by ECMWF "
                f"from {ordinal(dt.day)} to {ordinal((dt+timedelta(days=3)).day)} "
                f"{ENG_MONTHS_FULL[dt.month]} {dt.year}")
    ws["A1"].font = Font(name="Arial", size=10, bold=True, underline="single")
    ws["A1"].alignment = center()

    for r in range(2, 30):
        ws.row_dimensions[r].height = 16
    ws.merge_cells("A2:N29")
    ws["A2"] = "[ Insert ENSgram image here — copy/paste from ECMWF website ]"
    ws["A2"].fill = fill("F0F8FF")
    ws["A2"].alignment = center(wrap=True)
    ws["A2"].font = Font(name="Arial", size=11, italic=True, color="AAAAAA")

    ws.row_dimensions[30].height = 14
    ws.merge_cells("A30:N30")
    ws["A30"] = "❖  Significant wave heights are forecast to..."
    ws["A30"].font = Font(name="Arial", size=9, bold=True)
    ws["A30"].alignment = left(wrap=False)

    for r in [31, 32]:
        ws.row_dimensions[r].height = 20
        ws.merge_cells(f"A{r}:N{r}")
        ws[f"A{r}"].fill = fill("FFFDE7")
        ws[f"A{r}"].font = Font(name="Arial", size=9, italic=True, color="999999")
        ws[f"A{r}"].alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    ws["A31"] = "[ Commentary on ENSgram — enter text here ]"
    print("  ✅ Feuille ENSgram créée.")


# ---------------------------------------------------------------------------
# FEUILLE 4 — Figure 3 (4 images probabilistes, Portrait)
# ---------------------------------------------------------------------------

def build_sheet4(ws, run_datetime):
    set_page_portrait(ws)
    ws.title = "Fig3 Probability"
    ws.sheet_view.showGridLines = False

    fig3_date = run_datetime + timedelta(days=1)
    ws.row_dimensions[1].height = 20
    ws.row_dimensions[2].height = 4
    ws.merge_cells("A1:P1")
    ws["A1"] = (f"Figure 3: Probability forecast for "
                f"{ENG_DAYS_FULL[fig3_date.weekday()]}, {ordinal(fig3_date.day)} "
                f"{ENG_MONTHS_FULL[fig3_date.month]} {fig3_date.year} at 01:00 pm local time.")
    ws["A1"].font = Font(name="Arial", size=10, bold=True, underline="single")
    ws["A1"].alignment = center(wrap=True)

    subtitles = [
        "Significant wave height and mean direction",
        "Probabilities: significant wave height",
        "Probabilities: mean wave period (≥8s)",
        "Probabilities: mean wave period (≥15s)",
    ]
    positions = [
        ("A3","H3","A4","H19"),
        ("I3","P3","I4","P19"),
        ("A21","H21","A22","H37"),
        ("I21","P21","I22","P37"),
    ]
    for r in range(3, 40):
        ws.row_dimensions[r].height = 15

    for i, (ts, te, is_, ie) in enumerate(positions):
        ws.merge_cells(f"{ts}:{te}")
        c = ws[ts]
        c.value = subtitles[i]
        c.font = Font(name="Arial", size=8, bold=True, italic=True)
        c.alignment = center(); c.fill = fill(BLUE_LIGHT)

        ws.merge_cells(f"{is_}:{ie}")
        c2 = ws[is_]
        c2.value = f"[ Image {i+1} — {subtitles[i]} ]"
        c2.fill = fill("F0F8FF")
        c2.alignment = center(wrap=True)
        c2.font = Font(name="Arial", size=9, italic=True, color="AAAAAA")

    print("  ✅ Feuille probabilités créée.")


# ---------------------------------------------------------------------------
# EXPORT PRINCIPAL
# ---------------------------------------------------------------------------

def export_excel(df: pd.DataFrame,
                 run_datetime: datetime,
                 output_path: str = None,
                 warning_text: str = None) -> str:

    date_str = run_datetime.strftime("%d%m%Y")
    run_str  = f"{run_datetime.hour:02d}Z"
    if output_path is None:
        output_path = f"D:/pipeline/Marine_forecast_{date_str}_{run_str}.xlsx"
    else:
        base = output_path.replace(".xlsx", "")
        output_path = f"{base}_{date_str}_{run_str}.xlsx"

    wb = Workbook()
    df_sorted = df.sort_values("valid_local").reset_index(drop=True)

    print("  📄 Feuille 1 — Données principales...")
    build_sheet1(wb.active, df, run_datetime, warning_text, df_sorted)

    build_weather_sheet(wb)

    ws2 = wb.create_sheet()
    print("  📄 Feuille 2 — Figure 1 + Marées...")
    build_sheet2(wb, ws2, df_sorted, run_datetime)

    ws3 = wb.create_sheet()
    print("  📄 Feuille 3 — ENSgram...")
    build_sheet3(ws3, run_datetime)

    ws4 = wb.create_sheet()
    print("  📄 Feuille 4 — Probabilités...")
    build_sheet4(ws4, run_datetime)

    wb.save(output_path)
    print(f"  ✅ Fichier Excel généré : {output_path}")
    return output_path
