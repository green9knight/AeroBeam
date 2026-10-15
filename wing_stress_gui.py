"""
AeroBeam v1.2.3 — GUI
====================
Full Tkinter front-end for WingStressAnalyzer.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json, os, sys, traceback, math
import numpy as np
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import ctypes

if sys.platform == "win32":
    try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except: pass

from input_validation import ValidationError, validate_inputs
from wing_stress_analyzer import (
    WingStressAnalyzer, DEFAULT_INPUTS, dynamic_pressure_psi, parse_user_float,
)
from spar_sections import (
    MATERIAL_DB, STRUT_MATERIALS, ALUMINUM_ANGLES, ANGLE_DESCRIPTIONS,
    spar_type_names, aluminum_mat_names, wood_mat_names, all_mat_names, strut_mat_names,
)
from airfoil_database import AIRFOIL_DB, get_airfoil
from common_tube_spars import COMMON_TUBE_SIZES, get_tube_by_description

VERSION = "1.2.3"
APP_TITLE = f"AeroBeam v{VERSION}  —  Phil Ramer"

# Colour tags for summary panel
# ── Colour palette — Trendy Grey + Classic Blue ───────────────────────────────
#   Grey & Classic Blue:  #888A8E  #A7AAAF  #B9BCC2  #085097  #024084
#   Gold & Grey:          #D2B75F  #E5C87A  #F2EDE1  #CFC9BE  #A5A29B
#   Storm Clouds:         #4C535F  #5D646F  #6E7F87  #5F7379  #4D6469
C_BG        = "#41413F"   # dark charcoal (Grey & Cream base)
C_BG2       = "#4C535F"   # storm cloud dark — input fields
C_ACCENT    = "#085097"   # classic blue — primary action
C_ACCENT2   = "#D2B75F"   # gold — highlights, selected tabs, section headers
C_GREEN     = "#6E9B5A"   # muted engineering green — pass
C_YELLOW    = "#E5C87A"   # gold-yellow — warning
C_RED       = "#C0392B"   # deep red — fail
C_TEXT      = "#F2EDE1"   # warm cream — main text
C_TEXT_DIM  = "#B9BCC2"   # cool grey — subdued labels
C_PANEL     = "#555555"   # mid grey — panels and cards
C_BORDER    = "#6E7F87"   # storm cloud border
C_HEADER_BG = "#333333"   # near-black header

TAG_GREEN  = {"foreground": C_GREEN}
TAG_YELLOW = {"foreground": C_YELLOW}
TAG_RED    = {"foreground": C_RED}
TAG_HEAD   = {"font": ("Courier", 9, "bold"), "foreground": C_ACCENT2}
TAG_BOLD   = {"font": ("Courier", 9, "bold"), "foreground": C_TEXT}
TAG_FIX    = {"foreground": C_YELLOW, "font": ("Courier", 9, "italic")}

# ── Plot Styling Configuration ────────────────────────────────────────────────
PLOT_STYLE = {
    "dark_bg": "#252930",
    "label_color": "#e8eaf0",
    "tick_color": "#B9BCC2",
    "spine_color": "#6E7F87",
    "grid_alpha": 0.3,
    "pos_color": "#085097",      # Positive load case (blue)
    "neg_color": "#D2B75F",      # Negative load case (gold)
    "pos_lw": 2,
    "neg_lw": 1.5,
    "torsion_color": "orange",
    "torsion_lw": 1,
    "torsion_alpha": 0.8,
}

# Plot configuration for each subplot
PLOT_CONFIGS = [
    {
        "title": "Lift [lb/in]",
        "xlabel": "Span [in]",
        "plots": [
            {"key": "w", "load": "pos", "label_fn": lambda a: f"+{a.n:.0f}g"},
            {"key": "w", "load": "neg", "negate": True, "label_fn": lambda a: f"{a.n_neg:.0f}g"},
        ],
        "legend": True,
        "torsion_overlay": True,  # Show torsion on this plot
    },
    {
        "title": "Shear [lb]",
        "xlabel": "Span [in]",
        "plots": [
            {"key": "V", "load": "pos"},
            {"key": "V", "load": "neg"},
        ],
    },
    {
        "title": "Moment [lb·in]",
        "xlabel": "Span [in]",
        "plots": [
            {"key": "M", "load": "pos"},
            {"key": "M", "load": "neg"},
        ],
    },
    {
        "title": "Deflection [in]  (+up / -down)",
        "xlabel": "Span [in]",
        "plots": [
            {"key": "z_front", "load": "pos", "label": "Frt +g (up)"},
            {"key": "z_rear", "load": "pos", "color": "#B9BCC2", "lw": 1.5, "label": "Rr +g (up)"},
            {"key": "z_front", "load": "neg", "label": "Frt -g (down)"},
            {"key": "z_rear", "load": "neg", "color": "#E5C87A", "lw": 1, "label": "Rr -g (down)"},
        ],
        "legend": True,
        "zero_line": True,
    },
]

def naca_depth(x_over_c: float, t_over_c: float, chord: float) -> float:
    """
    NACA 4-digit thickness at chord position x_over_c.
    Returns full local airfoil depth (upper + lower surface) in inches.
    Formula: Jacobs, Ward & Pinkerton (1933), NACA Report 460.
    """
    import math
    x = max(x_over_c, 1e-9)
    t = t_over_c
    y = 5*t*(0.2969*math.sqrt(x) - 0.1260*x - 0.3516*x**2 + 0.2843*x**3 - 0.1015*x**4)
    return 2 * y * chord


def apply_theme(root):
    style = ttk.Style(root)
    try: style.theme_use("clam")
    except: pass
    root.configure(bg=C_BG)
    style.configure(".", background=C_PANEL, foreground=C_TEXT,
        fieldbackground=C_BG2, troughcolor=C_BG, bordercolor=C_BORDER,
        darkcolor=C_BG, lightcolor=C_PANEL, insertcolor=C_TEXT,
        selectbackground=C_ACCENT, selectforeground=C_TEXT,
        font=("Segoe UI", 9))
    style.configure("TFrame",      background=C_PANEL)
    style.configure("TLabel",      background=C_PANEL, foreground=C_TEXT)
    style.configure("Dim.TLabel",  background=C_PANEL, foreground=C_TEXT_DIM,
                    font=("Segoe UI", 8))
    style.configure("Section.TLabel", background=C_PANEL, foreground=C_ACCENT2,
                    font=("Segoe UI", 9, "bold"))
    style.configure("Value.TLabel",   background=C_PANEL, foreground=C_ACCENT2,
                    font=("Segoe UI", 9, "bold"))
    style.configure("TLabelframe",    background=C_PANEL, foreground=C_ACCENT2,
                    bordercolor=C_BORDER)
    style.configure("TLabelframe.Label", background=C_PANEL, foreground=C_ACCENT2,
                    font=("Segoe UI", 9, "bold"))
    style.configure("TEntry", fieldbackground=C_BG2, foreground=C_TEXT,
        insertcolor=C_TEXT, bordercolor=C_BORDER)
    style.map("TEntry",
        fieldbackground=[("focus", "#1a2540")],
        bordercolor=[("focus", C_ACCENT)])
    style.configure("TCombobox", fieldbackground=C_BG2, foreground=C_TEXT,
        background=C_PANEL, arrowcolor=C_ACCENT2, bordercolor=C_BORDER)
    style.map("TCombobox",
        fieldbackground=[("readonly", C_BG2)],
        foreground=[("readonly", C_TEXT)])
    style.configure("TNotebook", background=C_BG, bordercolor=C_BORDER,
                    tabmargins=[2,4,2,0])
    style.configure("TNotebook.Tab", background=C_BG, foreground=C_TEXT_DIM,
                    padding=[12,6], font=("Segoe UI", 9))
    style.map("TNotebook.Tab",
        background=[("selected", C_PANEL), ("active", C_BG2)],
        foreground=[("selected", C_ACCENT2), ("active", C_TEXT)],
        expand=[("selected", [1,1,1,0])])
    style.configure("TScrollbar", background=C_PANEL, troughcolor=C_BG,
                    arrowcolor=C_TEXT_DIM, bordercolor=C_BORDER)
    style.map("TScrollbar", background=[("active", C_ACCENT)])
    style.configure("TButton", background=C_BG2, foreground=C_TEXT,
                    bordercolor=C_BORDER, relief="flat", padding=[10,5],
                    font=("Segoe UI", 9))
    style.map("TButton",
        background=[("active", C_BORDER), ("pressed", C_BG)],
        foreground=[("active", C_TEXT)])
    style.configure("Accent.TButton", background=C_ACCENT, foreground="white",
                    bordercolor=C_ACCENT, relief="flat", padding=[14,6],
                    font=("Segoe UI", 10, "bold"))
    style.map("Accent.TButton",
        background=[("active", "#1565c0"), ("pressed", "#0d47a1")],
        foreground=[("active", "white")])
    style.configure("Export.TButton", background=C_BG2, foreground=C_ACCENT2,
                    bordercolor=C_ACCENT2, relief="flat", padding=[10,5],
                    font=("Segoe UI", 9))
    style.map("Export.TButton",
        background=[("active", "#1a2a3a")],
        foreground=[("active", C_ACCENT2)])
    style.configure("TPanedwindow", background=C_BG)
    style.configure("Sash", sashthickness=5, background=C_BORDER)
    style.configure("TCheckbutton", background=C_PANEL, foreground=C_TEXT)
    style.map("TCheckbutton",
        indicatorcolor=[("selected", C_ACCENT), ("!selected", C_BG2)])
    style.configure("TSeparator", background=C_BORDER)
    # Tk classic widgets
    root.option_add("*Listbox.background",       C_BG2)
    root.option_add("*Listbox.foreground",       C_TEXT)
    root.option_add("*Listbox.selectBackground", C_ACCENT)
    root.option_add("*Listbox.selectForeground", "white")
    root.option_add("*Listbox.relief",           "flat")
    root.option_add("*Listbox.borderWidth",      "0")
    root.option_add("*Text.background",          C_BG2)
    root.option_add("*Text.foreground",          C_TEXT)
    root.option_add("*Text.insertBackground",    C_TEXT)
    root.option_add("*Text.selectBackground",    C_ACCENT)

def section_label(parent, text, row=0):
    ttk.Label(parent, text=f"  {text.upper()}",
              style="Section.TLabel").grid(
              row=row, column=0, columnspan=4, sticky="w", padx=4, pady=(10,2))


# ─── HELPER WIDGETS ──────────────────────────────────────────────────────────

def labeled_entry(parent, label, default="", width=12, row=None, col=0, **kw):
    """Add a label+entry pair to a grid. Returns StringVar."""
    var = tk.StringVar(value=str(default))
    r = row if row is not None else 0
    ttk.Label(parent, text=label).grid(row=r, column=col,   sticky="e", padx=4, pady=2)
    ttk.Entry(parent, textvariable=var, width=width, **kw).grid(
        row=r, column=col+1, sticky="w", padx=4, pady=2)
    return var

def labeled_combo(parent, label, values, default=None, width=22, row=None, col=0):
    """Add a label+combobox pair. Returns StringVar."""
    var = tk.StringVar(value=str(default or values[0]))
    r = row if row is not None else 0
    ttk.Label(parent, text=label).grid(row=r, column=col,   sticky="e", padx=4, pady=2)
    cb = ttk.Combobox(parent, textvariable=var, values=values, width=width, state="readonly")
    cb.grid(row=r, column=col+1, sticky="w", padx=4, pady=2)
    return var

def separator(parent, row, colspan=4):
    ttk.Separator(parent, orient="horizontal").grid(
        row=row, column=0, columnspan=colspan, sticky="ew", pady=3)


# ─── ROW COUNTER HELPER ──────────────────────────────────────────────────────

class RowCounter:
    """Helper class to manage row increments in grid layouts."""
    def __init__(self, start=0):
        self.current = start
    
    def __call__(self):
        """Return current row and increment."""
        r = self.current
        self.current += 1
        return r
    
    def get(self):
        """Return current row without incrementing."""
        return self.current


# ─── SPAR FRAME ──────────────────────────────────────────────────────────────

class SparFrame(ttk.LabelFrame):
    """
    Self-contained spar input panel.
    prefix = "front_spar" or "rear_spar"
    """
    SPAR_TYPES = spar_type_names()
    METAL_MATS = aluminum_mat_names()
    WOOD_MATS  = wood_mat_names()
    ALL_MATS   = all_mat_names()

    def __init__(self, parent, prefix, label, defaults, **kw):
        super().__init__(parent, text=label, **kw)
        self.prefix  = prefix
        self.vars    = {}
        self._build(defaults)

    # Field definitions: (var_name, label, default_value)
    _TUBE_FIELDS = [
        ("od", "OD (in):", 2.0),
        ("wall", "Wall (in):", 0.065),
    ]
    
    _BUILDUP_ENTRY_FIELDS = [
        ("b_top", "b_top (in):", 1.5),
        ("t_top", "t_top (in):", 0.75),
        ("b_bot", "b_bot (in):", 1.5),
        ("t_bot", "t_bot (in):", 0.75),
        ("h_web", "h_web (in):", 4.5),
        ("t_web", "t_web (in):", 0.125),
        ("web_spacing", "Web spacing:", 1.0),
        ("b_outer", "b_outer (in):", 2.0),
        ("h_outer", "h_outer (in):", 5.0),
        ("t_cap", "t_cap (in):", 0.75),
        ("width", "Width (in):", 2.0),
        ("height", "Height (in):", 4.0),
    ]

    def _build(self, d):
        """Build the spar configuration UI with all input fields."""
        p = self.prefix
        f = self
        row = 0
        
        # Spar type selector
        self.vars["type"] = labeled_combo(
            f, "Spar type:", self.SPAR_TYPES,
            d.get(f"{p}_type", "Round Tube"), row=row
        )
        self.vars["type"].trace_add("write", lambda *_: self._refresh_fields())
        row += 1
        
        # Build tube fields frame
        self._tube_frame = ttk.Frame(f)
        self._tube_frame.grid(row=row, column=0, columnspan=4, sticky="ew")
        self._build_tube_fields(d)
        row += 1
        
        # Build built-up spar fields frame
        self._buildup_frame = ttk.Frame(f)
        self._buildup_frame.grid(row=row, column=0, columnspan=4, sticky="ew")
        self._build_buildup_fields(d)
        row += 1
        
        # Live properties display
        self._props_var = tk.StringVar(value="")
        ttk.Label(f, textvariable=self._props_var, foreground="#444",
                  font=("Courier", 8), justify="left").grid(
                      row=row, column=0, columnspan=4, sticky="w", padx=6, pady=2)
        
        # Attach traces for live update (with proper variable binding)
        for var in self.vars.values():
            var.trace_add("write", lambda *_, v=var: self._update_props())
        
        self._refresh_fields()
        self._update_props()
    
    def _build_tube_fields(self, d):
        """Build round tube input fields."""
        p = self.prefix
        tf = self._tube_frame
        field_row = 0
        
        # Create entry fields from definition
        for var_name, label, default in self._TUBE_FIELDS:
            self.vars[var_name] = labeled_entry(
                tf, label, d.get(f"{p}_{var_name}", default), row=field_row
            )
            field_row += 1
        
        # Material combo
        self.vars["mat"] = labeled_combo(
            tf, "Material:", self.METAL_MATS,
            d.get(f"{p}_mat", "6061-T6"), row=field_row
        )
        field_row += 1
        
        # Tube quick-select
        tube_descs = ["(Manual)"] + [str(t) for t in COMMON_TUBE_SIZES]
        self._tube_select_var = tk.StringVar(value="(Manual)")
        ttk.Label(tf, text="Quick-select:").grid(
            row=field_row, column=0, sticky="e", padx=4, pady=2
        )
        ttk.Combobox(tf, textvariable=self._tube_select_var,
                     values=tube_descs, width=28, state="readonly").grid(
                         row=field_row, column=1, sticky="w", padx=4, pady=2)
        self._tube_select_var.trace_add("write", self._on_tube_select)
    
    def _build_buildup_fields(self, d):
        """Build built-up spar input fields."""
        p = self.prefix
        bf = self._buildup_frame
        field_row = 0
        
        # Material combos
        self.vars["cap_mat"] = labeled_combo(
            bf, "Cap material:", self.WOOD_MATS,
            d.get(f"{p}_cap_mat", "Sitka Spruce"), row=field_row
        )
        field_row += 1
        
        self.vars["web_mat"] = labeled_combo(
            bf, "Web material:", self.ALL_MATS,
            d.get(f"{p}_web_mat", "Birch Plywood"), row=field_row
        )
        field_row += 1
        
        # Create entry fields from definition
        for var_name, label, default in self._BUILDUP_ENTRY_FIELDS:
            self.vars[var_name] = labeled_entry(
                bf, label, d.get(f"{p}_{var_name}", default), row=field_row
            )
            field_row += 1

    def _refresh_fields(self):
        t = self.vars["type"].get()
        tube = t == "Round Tube"
        # Show/hide frames
        if tube:
            self._tube_frame.grid()
            self._buildup_frame.grid_remove()
        else:
            self._tube_frame.grid_remove()
            self._buildup_frame.grid()

        # Within buildup frame, show only relevant rows
        bf = self._buildup_frame
        show_web_mat  = t in ("I-Beam","Double I-Beam","Box Spar","C-Channel")
        show_web_sp   = t == "Double I-Beam"
        show_box      = t == "Box Spar"
        show_rect     = t == "Plain Rectangular"

        def vis(widget, show):
            widget.grid() if show else widget.grid_remove()

        # Walk grid slaves and show/hide by row
        for w in bf.grid_slaves():
            ri = w.grid_info().get("row", 0)
            # Row mapping:
            # 0=cap_mat, 1=web_mat, 2=b_top,3=t_top,4=b_bot,5=t_bot,6=h_web,7=t_web
            # 8=web_spacing, 9=b_outer,10=h_outer,11=t_cap, 12=width,13=height
            show = True
            if ri in (0,): show = not show_rect  # cap_mat -- always except plain rect
            if ri in (1,): show = show_web_mat
            if ri in (2,3,4,5,6,7): show = not show_box and not show_rect
            if ri in (8,): show = show_web_sp
            if ri in (9,10,11): show = show_box
            if ri in (12,13): show = show_rect
            if show: w.grid()
            else:    w.grid_remove()

    def _on_tube_select(self, *_):
        desc = self._tube_select_var.get()
        if desc == "(Manual)": return
        tube = get_tube_by_description(desc)
        if tube:
            self.vars["od"].set(str(tube.od))
            self.vars["wall"].set(str(tube.wall))

    def _update_props(self):
        try:
            from spar_sections import build_spar as _build
            # Build a temporary spar from current values
            dummy = {k: v.get() for k, v in self.vars.items()}
            dummy = {f"{self.prefix}_{k}": v for k, v in dummy.items()}
            spar = _build(self.vars["type"].get(), dummy, self.prefix)
            p = spar.get_props(1.0)
            self._props_var.set(
                f"EI={p.EI:,.0f} lb·in²   I={p.I_tr:.4f}\"⁴   "
                f"y_max={p.y_max:.3f}\"   NA={p.NA:.3f}\"")
        except Exception:
            self._props_var.set("")

    def get_vars(self) -> dict:
        """Return flat dict of all input values, prefixed."""
        out = {}
        out[f"{self.prefix}_type"] = self.vars["type"].get()
        for k, v in self.vars.items():
            if k != "type":
                out[f"{self.prefix}_{k}"] = v.get()
        return out

    def set_vars(self, d: dict):
        """Load values from flat dict."""
        for k, v in self.vars.items():
            key = f"{self.prefix}_{k}"
            if key in d:
                v.set(str(d[key]))
        self._refresh_fields()


# ─── MAIN GUI ─────────────────────────────────────────────────────────────────

class WingStressGUI:

    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1440x960")
        self.root.minsize(1200, 820)
        self.root.after(50, lambda: self.root.state("zoomed"))
        apply_theme(self.root)

        # Icon
        try:
            if getattr(sys, "frozen", False):
                bases = [os.path.dirname(sys.executable)]
            else:
                here = os.path.dirname(os.path.abspath(__file__))
                bases = [here, os.path.join(here, "web")]
            for base in bases:
                ico = os.path.join(base, "AeroBeam.ico")
                if os.path.isfile(ico):
                    self.root.iconbitmap(ico)
                    break
        except: pass

        self.analyzer    = None
        self.current_file = None
        self._vars       = {}   # all StringVar / BooleanVar keyed by name
        self._data_cache = {}   # full key-value store including non-registered keys

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build_menu()
        self._build_layout()
        self._populate_defaults()

        self.status_var = tk.StringVar(value="Ready.")
        sb = tk.Frame(self.root, bg=C_HEADER_BG, height=22)
        sb.pack(side=tk.BOTTOM, fill=tk.X)
        sb.pack_propagate(False)
        tk.Label(sb, textvariable=self.status_var, bg=C_HEADER_BG,
                 fg=C_TEXT_DIM, font=("Segoe UI", 8),
                 anchor="w").pack(side=tk.LEFT, padx=10, fill=tk.X)

    def _on_close(self):
        try: plt.close("all")
        except: pass
        self.root.quit(); self.root.destroy(); sys.exit(0)

    # ── Menu ──────────────────────────────────────────────────────────────────

    def _build_menu(self):
        mb = tk.Menu(self.root)
        fm = tk.Menu(mb, tearoff=0)
        fm.add_command(label="New",         command=self._new)
        fm.add_command(label="Open…",       command=self._open)
        fm.add_command(label="Save",        command=self._save)
        fm.add_command(label="Save As…",    command=self._save_as)
        fm.add_separator()
        fm.add_command(label="Export PDF…", command=self._export_pdf)
        fm.add_command(label="Export Excel…", command=self._export_excel)
        fm.add_separator()
        fm.add_command(label="Exit",        command=self._on_close)
        mb.add_cascade(label="File", menu=fm)

        hm = tk.Menu(mb, tearoff=0)
        hm.add_command(label="About AeroBeam", command=self._about)
        mb.add_cascade(label="Help", menu=hm)
        self.root.config(menu=mb)

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_layout(self):
        # Header bar
        hdr = tk.Frame(self.root, bg=C_HEADER_BG, height=54)
        hdr.pack(side=tk.TOP, fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text="✈  AeroBeam", bg=C_HEADER_BG, fg=C_ACCENT2,
                 font=("Segoe UI", 15, "bold")).pack(side=tk.LEFT, padx=16, pady=10)
        tk.Label(hdr, text="v1.2.3   Wing Bending, Shear & Buckling Analysis",
                 bg=C_HEADER_BG, fg=C_TEXT_DIM,
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, pady=14)
        self._hdr_status = tk.Label(hdr, text="Ready", bg=C_HEADER_BG,
                                     fg=C_TEXT_DIM, font=("Segoe UI", 9))
        self._hdr_status.pack(side=tk.RIGHT, padx=16)
        self._hdr_dot = tk.Label(hdr, text="●", bg=C_HEADER_BG,
                                  fg=C_TEXT_DIM, font=("Segoe UI", 14))
        self._hdr_dot.pack(side=tk.RIGHT, padx=4)

        pw = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        pw.pack(fill=tk.BOTH, expand=True, padx=4, pady=(2,4))

        # Left: inputs
        left = ttk.Frame(pw, width=520)
        pw.add(left, weight=1)

        self._scroll_frame = ttk.Frame(left)
        self._scroll_frame.pack(fill=tk.BOTH, expand=True)
        self._build_inputs(self._scroll_frame)

        # Right: notebook (summary / plots)
        right = ttk.Frame(pw)
        pw.add(right, weight=2)
        self._build_right(right)

    def _create_button_row(self, parent):
        """Create and return the top button row with analysis and export controls."""
        btn_row = ttk.Frame(parent)
        btn_row.pack(side=tk.TOP, fill=tk.X, pady=(4, 2), padx=4)
        
        # Left-aligned buttons
        ttk.Button(btn_row, text="▶  ANALYZE", command=self._run_analysis,
                   style="Accent.TButton").pack(side=tk.LEFT, padx=(4, 10))
        ttk.Separator(btn_row, orient="vertical").pack(side=tk.LEFT, fill=tk.Y, pady=3, padx=4)
        ttk.Button(btn_row, text="⟳ Reset", command=self._populate_defaults
                   ).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="✈ Geometry", command=self._show_geometry
                   ).pack(side=tk.LEFT, padx=2)
        
        # Right-aligned buttons
        ttk.Separator(btn_row, orient="vertical").pack(side=tk.RIGHT, fill=tk.Y, pady=3, padx=4)
        ttk.Button(btn_row, text="⬇ Excel", command=self._export_excel,
                   style="Export.TButton").pack(side=tk.RIGHT, padx=2)
        ttk.Button(btn_row, text="⬇ PDF", command=self._export_pdf,
                   style="Export.TButton").pack(side=tk.RIGHT, padx=2)
        
        return btn_row

    def _create_summary_tab(self, notebook):
        """Create the Summary tab with styled text widget."""
        sum_tab = ttk.Frame(notebook)
        notebook.add(sum_tab, text="Summary")
        
        self._summary_text = scrolledtext.ScrolledText(
            sum_tab, font=("Courier", 9), state="disabled",
            wrap=tk.WORD, width=62)
        self._summary_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure text tags
        tag_configs = [
            ("GREEN", TAG_GREEN),
            ("YELLOW", TAG_YELLOW),
            ("RED", TAG_RED),
            ("HEAD", TAG_HEAD),
            ("BOLD", TAG_BOLD),
            ("FIX", TAG_FIX),
        ]
        for tag_name, tag_config in tag_configs:
            self._summary_text.tag_configure(tag_name, **tag_config)

    def _embed_figure(self, fig, parent):
        """Put a figure in a tab and let the tab set its size.

        ``place`` keeps the canvas from requesting the figure's pixel size,
        which otherwise grows the window and leaves the drawing clipped until
        someone resizes it by hand.
        """
        holder = ttk.Frame(parent)
        holder.pack(fill=tk.BOTH, expand=True)
        canvas = FigureCanvasTkAgg(fig, master=holder)
        widget = canvas.get_tk_widget()
        widget.place(relx=0, rely=0, relwidth=1, relheight=1)
        fig.canvas.mpl_connect("resize_event", self._relayout_figure)
        return canvas

    def _relayout_figure(self, event):
        fig = event.canvas.figure
        if fig.bbox.width < 40 or fig.bbox.height < 40:
            return
        try:
            fig.tight_layout(pad=1.1)
        except Exception:
            pass

    def _create_plots_tab(self, notebook):
        """Create the Plots tab with matplotlib figure."""
        plot_tab = ttk.Frame(notebook)
        notebook.add(plot_tab, text="Plots")
        
        # Use Figure directly — no pyplot global state contamination
        self._fig = Figure(figsize=(5, 3.5))
        self._fig.patch.set_facecolor("#1e2128")
        self._axes = self._fig.subplots(2, 2)
        self._canvas_plt = self._embed_figure(self._fig, plot_tab)

    def _create_geometry_tab(self, notebook):
        """Plan and elevation, drawn in the results pane instead of a popup."""
        self._geo_tab = ttk.Frame(notebook)
        notebook.add(self._geo_tab, text="Geometry")
        self._geo_fig = Figure(figsize=(5, 3.5))
        self._geo_fig.patch.set_facecolor("#1e2128")
        self._geo_ax_top = self._geo_fig.add_subplot(211)
        self._geo_ax_side = self._geo_fig.add_subplot(212)
        self._canvas_geo = self._embed_figure(self._geo_fig, self._geo_tab)
        self._draw_geometry_figure()

    def _create_results_notebook(self, parent):
        """Create and return the results notebook with Summary, Plots, and Geometry."""
        nb = ttk.Notebook(parent)
        nb.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # Create tabs
        self._create_summary_tab(nb)
        self._create_plots_tab(nb)
        self._create_geometry_tab(nb)
        
        return nb

    def _build_right(self, parent):
        """Build the right panel with controls and results display."""
        self._create_button_row(parent)
        self._nb = self._create_results_notebook(parent)


    # ── Inputs ────────────────────────────────────────────────────────────────

    def _v(self, name, default="", widget_type="entry", values=None, **kw):
        """Register and return a StringVar or BooleanVar."""
        if widget_type == "bool":
            var = tk.BooleanVar(value=bool(default))
        else:
            var = tk.StringVar(value=str(default))
        self._vars[name] = var
        return var

    def _le(self, parent, label, name, default="", row=0, col=0, width=10):
        """Labeled entry — registers in self._vars."""
        var = self._v(name, default)
        ttk.Label(parent, text=label).grid(row=row, column=col,   sticky="e", padx=3, pady=2)
        ttk.Entry(parent, textvariable=var, width=width).grid(
            row=row, column=col+1, sticky="w", padx=3, pady=2)
        return var

    def _lc(self, parent, label, name, values, default=None, row=0, col=0, width=22):
        """Labeled combobox — registers in self._vars."""
        var = self._v(name, default or values[0])
        ttk.Label(parent, text=label).grid(row=row, column=col,   sticky="e", padx=3, pady=2)
        cb = ttk.Combobox(parent, textvariable=var, values=values, width=width, state="readonly")
        cb.grid(row=row, column=col+1, sticky="w", padx=3, pady=2)
        return var

    def _lchk(self, parent, label, name, default=False, row=0, col=0):
        """Labeled checkbox."""
        var = tk.BooleanVar(value=bool(default))
        self._vars[name] = var
        ttk.Checkbutton(parent, text=label, variable=var).grid(
            row=row, column=col, columnspan=2, sticky="w", padx=3, pady=2)
        return var

    def _build_inputs(self, parent):
        f = parent
        nb = ttk.Notebook(f)
        nb.pack(fill=tk.BOTH, expand=True)

        tabs = {}
        for name in ("Wing Geometry", "Flight & Airfoil", "Loads & Config",
                     "Wing Structure", "Front Spar", "Rear Spar", "Buckling"):
            frm = ttk.Frame(nb, padding=4)
            nb.add(frm, text=name)
            frm.columnconfigure(0, weight=0)   # label column — fixed width
            frm.columnconfigure(1, weight=1)   # entry column — expands
            frm.rowconfigure(999, weight=1)    # empty last row absorbs extra space (anchors content to top)
            tabs[name] = frm

        self._build_geometry_tab(tabs["Wing Geometry"])
        self._build_front_spar_tab(tabs["Front Spar"])
        self._build_buckling_tab(tabs["Buckling"])
        self._build_rear_spar_tab(tabs["Rear Spar"])
        self._build_structure_tab(tabs["Wing Structure"])
        self._build_loads_tab(tabs["Loads & Config"])
        self._build_flight_tab(tabs["Flight & Airfoil"])

    # ── Wing Geometry tab ────────────────────────────────────────────────────

    def _build_geometry_tab(self, f):
        f.columnconfigure(0, weight=0); f.columnconfigure(1, weight=1); f.rowconfigure(999, weight=1)
        r = 0
        section_label(f, "Planform", row=r); r+=1
        self._le(f,"Total span (in):","b", 320.0, row=r); r+=1
        self._le(f,"Root attach offset (in):","r", 22.0, row=r); r+=1
        self._le(f,"Root chord (in):","root_chord", 54.0, row=r); r+=1
        self._le(f,"Tip chord (in):", "tip_chord",  24.0, row=r); r+=1
        self._le(f,"Taper start BL (in):","taper_start_bl", 0.0, row=r); r+=1
        ttk.Label(f,text="  0 = taper from root to tip  |  enter BL where taper begins (Cessna-style constant chord inboard)",
                  foreground=C_TEXT_DIM, font=("Segoe UI",8)).grid(
                  row=r,column=0,columnspan=4,sticky="w",padx=20,pady=(0,4)); r+=1
        self._lc(f, "Keep straight:", "taper_reference",
                 ["Leading edge", "Main spar", "Trailing edge"], "Leading edge", row=r)
        r += 1
        ttk.Label(f, text="  The chord and spar percentages stay as entered. The section shifts so that line is straight.",
                  foreground=C_TEXT_DIM, font=("Segoe UI", 8)).grid(
                  row=r, column=0, columnspan=4, sticky="w", padx=20, pady=(0, 4)); r += 1
        self._le(f,"Rib spacing (in):","rib_spacing",12.0, row=r); r+=1

        section_label(f,"Spar Positions", row=r); r+=1
        self._le(f,"Front spar % chord:","front_spar_percent",0.15, row=r); r+=1
        self._le(f,"Rear spar % chord:", "rear_spar_percent", 0.65, row=r); r+=1
        self._le(f,"Front spar load share (0.0-1.0):","front_spar_load_share",0.55, row=r); r+=1
        # Re-propose spar heights when chord or spar positions change
        for _nm in ("root_chord","front_spar_percent","rear_spar_percent","airfoil_t_c"):
            if _nm in self._vars:
                self._vars[_nm].trace_add("write", self._repropose_h_web)
        # Wire D-cell area update to chord and spar position changes
        for _nm in ("root_chord","front_spar_percent","airfoil_t_c"):
            if _nm in self._vars:
                self._vars[_nm].trace_add("write", lambda *_: self._update_dcell_area())

        section_label(f,"Lift Distribution", row=r); r+=1
        self._lc(f,"Distribution type:","lift_distribution_type",
                 ["schrenk","elliptical","chord_based","uniform"],
                 "schrenk", row=r); r+=1
        self._le(f,"Analysis stations:","num_points",201, row=r); r+=1



    # ── Front Spar tab ───────────────────────────────────────────────────────

    def _build_front_spar_tab(self, f):
        f.columnconfigure(0, weight=0); f.columnconfigure(1, weight=1); f.rowconfigure(999, weight=1)
        r = 0
        section_label(f,"Front Spar Cross-Section", row=r); r+=1

        # Spar type
        self._lc(f,"Spar type:","front_spar_type",spar_type_names(),"Round Tube",row=r); r+=1
        self._vars["front_spar_type"].trace_add("write", lambda *_: self._refresh_spar("front"))

        # Tube fields
        self._front_tube_frame = ttk.Frame(f)
        self._front_tube_frame.grid(row=r, column=0, columnspan=4, sticky="ew"); r+=1
        self._front_tube_frame.columnconfigure(0, weight=0)
        self._front_tube_frame.columnconfigure(1, weight=1)
        tf = self._front_tube_frame
        tube_descs = ["(Manual)"] + [str(t) for t in COMMON_TUBE_SIZES]
        self._front_tube_sel = tk.StringVar(value="(Manual)")
        ttk.Label(tf,text="Quick-select:").grid(row=0,column=0,sticky="e",padx=3,pady=2)
        ttk.Combobox(tf,textvariable=self._front_tube_sel,values=tube_descs,
                     width=28,state="readonly").grid(row=0,column=1,sticky="w",padx=3,pady=2)
        self._le(tf,"OD (in):","front_spar_od",3.0,row=1)
        self._le(tf,"Wall (in):","front_spar_wall",0.065,row=2)
        self._lc(tf,"Material:","front_spar_mat",aluminum_mat_names(),"6061-T6",row=3)
        self._front_tube_sel.trace_add("write", lambda *_: self._on_tube_sel("front"))

        # Built-up fields
        self._front_buildup_frame = ttk.Frame(f)
        self._front_buildup_frame.grid(row=r, column=0, columnspan=4, sticky="ew"); r+=1
        self._front_buildup_frame.columnconfigure(0, weight=0)
        self._front_buildup_frame.columnconfigure(1, weight=1)
        self._build_buildup_fields(self._front_buildup_frame, "front_spar", "Round Tube")

        # D-cell
        section_label(f,"D-Cell Leading Edge Skin", row=r); r+=1
        self._lchk(f,"Enable D-cell","dcell_enabled",False,row=r); r+=1
        self._front_dcell_frame = ttk.Frame(f)
        self._front_dcell_frame.grid(row=r, column=0, columnspan=4, sticky="ew"); r+=1
        df = self._front_dcell_frame
        df.columnconfigure(0, weight=0); df.columnconfigure(1, weight=1)
        self._lc(df,"Skin material:","dcell_skin_mat",all_mat_names(),"Birch Plywood",row=0)
        self._le(df,"Skin thickness (in):","dcell_skin_thick",0.0625,row=1)
        # Live enclosed area from the airfoil thickness curve, same as the solver
        self._dcell_area_var = tk.StringVar(value="")
        ttk.Label(df,text="Enclosed area (auto):").grid(row=2,column=0,sticky="e",padx=3,pady=2)
        ttk.Label(df,textvariable=self._dcell_area_var,foreground="#005500",
                  font=("TkDefaultFont",9,"bold")).grid(row=2,column=1,sticky="w",padx=3,pady=2)
        ttk.Label(df,text="GJ ∝ area² — wider D-cell = stiffer",
                  foreground="#666",font=("TkDefaultFont",8)).grid(
                  row=3,column=0,columnspan=2,sticky="w",padx=3,pady=0)
        for nm in ("front_spar_percent","root_chord","airfoil_t_c","dcell_skin_mat","dcell_skin_thick"):
            if nm in self._vars:
                self._vars[nm].trace_add("write", lambda *_: self._update_dcell_area())

        # Live props
        self._front_props_var = tk.StringVar(value="")
        ttk.Label(f, textvariable=self._front_props_var,
                  foreground="#444", font=("Courier",8)).grid(
                      row=r, column=0, columnspan=4, sticky="w", padx=5, pady=3)

        self._vars["dcell_enabled"].trace_add("write", lambda *_: self._refresh_dcell())
        self._refresh_spar("front")
        self._refresh_dcell()

    # ── Rear Spar tab ────────────────────────────────────────────────────────

    def _build_rear_spar_tab(self, f):
        f.columnconfigure(0, weight=0); f.columnconfigure(1, weight=1); f.rowconfigure(999, weight=1)
        r = 0
        section_label(f,"Rear Spar Cross-Section", row=r); r+=1
        self._lc(f,"Spar type:","rear_spar_type",spar_type_names(),"Round Tube",row=r); r+=1
        self._vars["rear_spar_type"].trace_add("write", lambda *_: self._refresh_spar("rear"))

        # Tube
        self._rear_tube_frame = ttk.Frame(f)
        self._rear_tube_frame.grid(row=r, column=0, columnspan=4, sticky="ew"); r+=1
        self._rear_tube_frame.columnconfigure(0, weight=0)
        self._rear_tube_frame.columnconfigure(1, weight=1)
        tf = self._rear_tube_frame
        tube_descs = ["(Manual)"] + [str(t) for t in COMMON_TUBE_SIZES]
        self._rear_tube_sel = tk.StringVar(value="(Manual)")
        ttk.Label(tf,text="Quick-select:").grid(row=0,column=0,sticky="e",padx=3,pady=2)
        ttk.Combobox(tf,textvariable=self._rear_tube_sel,values=tube_descs,
                     width=28,state="readonly").grid(row=0,column=1,sticky="w",padx=3,pady=2)
        self._le(tf,"OD (in):","rear_spar_od",2.0,row=1)
        self._le(tf,"Wall (in):","rear_spar_wall",0.065,row=2)
        self._lc(tf,"Material:","rear_spar_mat",aluminum_mat_names(),"6061-T6",row=3)
        self._rear_tube_sel.trace_add("write", lambda *_: self._on_tube_sel("rear"))

        # Built-up
        self._rear_buildup_frame = ttk.Frame(f)
        self._rear_buildup_frame.grid(row=r, column=0, columnspan=4, sticky="ew"); r+=1
        self._rear_buildup_frame.columnconfigure(0, weight=0)
        self._rear_buildup_frame.columnconfigure(1, weight=1)
        self._build_buildup_fields(self._rear_buildup_frame, "rear_spar", "Round Tube")

        self._rear_props_var = tk.StringVar(value="")
        ttk.Label(f, textvariable=self._rear_props_var,
                  foreground="#444", font=("Courier",8)).grid(
                      row=r, column=0, columnspan=4, sticky="w", padx=5, pady=3)

        self._refresh_spar("rear")

    def _build_buildup_fields(self, f, prefix, spar_type="I-Beam"):
        """Build the built-up spar geometry fields for the given spar_type."""
        from spar_sections import ANGLE_DESCRIPTIONS
        is_alum  = spar_type in ("Aluminum I-Beam","Aluminum C-Spar")
        is_ibeam = spar_type in ("I-Beam","Double I-Beam","C-Channel",
                                  "Routed (Monolithic)","Aluminum I-Beam","Aluminum C-Spar")
        is_box   = spar_type == "Box Spar"
        is_rect  = spar_type == "Plain Rectangular"
        is_cspar = spar_type == "Aluminum C-Spar"
        is_dbl   = spar_type == "Double I-Beam"
        has_web  = spar_type in ("I-Beam","Double I-Beam","Box Spar","C-Channel",
                                  "Aluminum I-Beam","Aluminum C-Spar")
        has_angle = spar_type in ("Aluminum I-Beam","Aluminum C-Spar",
                                       "I-Beam","C-Channel","Double I-Beam")

        r = 0
        # Cap material
        if not is_rect:
            cap_mats = aluminum_mat_names() if is_alum else all_mat_names()
            cap_default = "6061-T6" if is_alum else "Sitka Spruce"
            self._lc(f,"Cap material:",f"{prefix}_cap_mat",cap_mats,cap_default,row=r); r+=1

        # Web material (not for Routed or Plain Rect)
        if has_web and spar_type != "Routed (Monolithic)":
            web_mats = aluminum_mat_names() if is_alum else all_mat_names()
            web_default = "6061-T6" if is_alum else "Birch Plywood"
            self._lc(f,"Web (shear) material:",f"{prefix}_web_mat",web_mats,web_default,row=r); r+=1

        if is_ibeam:
            # Aluminum angle quick-select (before manual cap fields)
            if has_angle:
                angle_sel_var = self._vars.get(f"{prefix}_angle_sel",
                                               tk.StringVar(value="(Manual flat bar)"))
                self._vars[f"{prefix}_angle_sel"] = angle_sel_var
                ttk.Label(f,text="Angle quick-select:").grid(
                    row=r,column=0,sticky="e",padx=3,pady=2)
                ttk.Combobox(f,textvariable=angle_sel_var,values=ANGLE_DESCRIPTIONS,
                             width=22,state="readonly").grid(
                                 row=r,column=1,sticky="w",padx=3,pady=2)
                angle_sel_var.trace_add("write",
                    lambda *_, p=prefix, v=angle_sel_var: self._on_angle_sel(p, v))
                r+=1

            # Cap side (C-Spar only)
            if is_cspar:
                cap_side_var = self._vars.get(f"{prefix}_cap_side",
                                              tk.StringVar(value="top"))
                self._vars[f"{prefix}_cap_side"] = cap_side_var
                ttk.Label(f,text="Cap side (top/bottom):").grid(
                    row=r,column=0,sticky="e",padx=3,pady=2)
                ttk.Combobox(f,textvariable=cap_side_var,values=["top","bottom"],
                             width=10,state="readonly").grid(
                                 row=r,column=1,sticky="w",padx=3,pady=2)
                r+=1

            # Top cap — root size, then tip size. A blank tip matches the root.
            cap_lbl = "Cap" if is_cspar else "Top cap"
            cap_t = 0.125 if is_alum else 0.75
            self._le(f,f"Root {cap_lbl.lower()} width (in):",f"{prefix}_b_top",1.5,row=r); r+=1
            self._le(f,f"Root {cap_lbl.lower()} height (in):",f"{prefix}_t_top",cap_t,row=r); r+=1
            self._le(f,f"Tip {cap_lbl.lower()} width (in):",f"{prefix}_b_top_tip",1.5,row=r); r+=1
            self._le(f,f"Tip {cap_lbl.lower()} height (in):",f"{prefix}_t_top_tip",cap_t,row=r); r+=1

            # Bottom cap (not for C-Spar)
            if not is_cspar:
                self._le(f,"Root bottom cap width (in):",f"{prefix}_b_bot",1.5,row=r); r+=1
                self._le(f,"Root bottom cap height (in):",f"{prefix}_t_bot",cap_t,row=r); r+=1
                self._le(f,"Tip bottom cap width (in):",f"{prefix}_b_bot_tip",1.5,row=r); r+=1
                self._le(f,"Tip bottom cap height (in):",f"{prefix}_t_bot_tip",cap_t,row=r); r+=1
            ttk.Label(f, text="  Caps taper in a straight line from the taper-start station to the tip.",
                      foreground=C_TEXT_DIM, font=("Segoe UI", 8)).grid(
                      row=r, column=0, columnspan=4, sticky="w", padx=20, pady=(0, 4)); r+=1

            # Web geometry
            self._le(f,"Shear web height - clear between caps (in):",f"{prefix}_h_web",
                     5.0 if is_alum else 4.5,row=r); r+=1
            self._le(f,"Shear web thickness (in):",f"{prefix}_t_web",
                     0.050 if is_alum else 0.125,row=r); r+=1

            # Double I-Beam web spacing
            if is_dbl:
                self._le(f,"Web spacing (in):",f"{prefix}_web_spacing",1.0,row=r); r+=1

            # Live total spar height
            if f"{prefix}_h_total_disp" not in self._vars:
                self._vars[f"{prefix}_h_total_disp"] = tk.StringVar(value="")
            ttk.Label(f,text="Total spar height:",
                      foreground="#005500").grid(row=r,column=0,sticky="e",padx=3,pady=2)
            ttk.Label(f,textvariable=self._vars[f"{prefix}_h_total_disp"],
                      foreground="#005500",font=("TkDefaultFont",9,"bold")).grid(
                          row=r,column=1,sticky="w",padx=3,pady=2)
            r+=1
            for nm in (f"{prefix}_t_top",f"{prefix}_h_web"):
                if nm in self._vars:
                    self._vars[nm].trace_add("write",
                        lambda *_, p=prefix: self._update_h_total(p))
            if not is_cspar and f"{prefix}_t_bot" in self._vars:
                self._vars[f"{prefix}_t_bot"].trace_add("write",
                    lambda *_, p=prefix: self._update_h_total(p))

        elif is_box:
            self._le(f,"Root outer width (in):",f"{prefix}_b_outer",2.0,row=r); r+=1
            self._le(f,"Tip outer width (in):",f"{prefix}_b_outer_tip",2.0,row=r); r+=1
            self._le(f,"Outer height at root (in):",f"{prefix}_h_outer",5.0,row=r); r+=1
            self._le(f,"Root cap thickness (in):",f"{prefix}_t_cap",0.75,row=r); r+=1
            self._le(f,"Tip cap thickness (in):",f"{prefix}_t_cap_tip",0.75,row=r); r+=1
            self._le(f,"Web thickness (in):",f"{prefix}_t_web",0.125,row=r); r+=1
            ttk.Label(f, text="  Cap width and thickness taper from the taper-start station to the tip.",
                      foreground=C_TEXT_DIM, font=("Segoe UI", 8)).grid(
                      row=r, column=0, columnspan=4, sticky="w", padx=20, pady=(0, 4)); r+=1

        elif is_rect:
            self._le(f,"Width (in):",f"{prefix}_width",2.0,row=r); r+=1
            self._le(f,"Height (in):",f"{prefix}_height",4.0,row=r); r+=1

    # ── Buckling tab ─────────────────────────────────────────────────────────

    def _build_buckling_tab(self, f):
        f.columnconfigure(0, weight=0); f.columnconfigure(1, weight=1); f.rowconfigure(999, weight=1)
        r = 0

        section_label(f, "Web Panel Supports", row=r); r+=1
        self._le(f,"Web stiffener spacing (in):","stiffener_spacing",0.0, row=r); r+=1
        ttk.Label(f,text="  0 = use rib spacing (no intermediate stiffeners)",
                  foreground="#666",font=("TkDefaultFont",8)).grid(
                  row=r,column=0,columnspan=2,sticky="w",padx=16,pady=0); r+=1
        self._le(f,"Nose rib spacing (in):","nose_rib_spacing",0.0, row=r); r+=1
        ttk.Label(f,text="  0 = use rib spacing (no intermediate nose ribs)",
                  foreground="#666",font=("TkDefaultFont",8)).grid(
                  row=r,column=0,columnspan=2,sticky="w",padx=16,pady=0); r+=1

        section_label(f, "Web Doublers", row=r); r+=1
        ttk.Label(f,text="Doublers are added at: root fitting, strut attach, jury strut",
                  foreground="#444",font=("TkDefaultFont",8)).grid(
                  row=r,column=0,columnspan=2,sticky="w",padx=4,pady=2); r+=1
        ttk.Label(f,text="In single_strut config, strut doubler applies to front spar only.",
                  foreground="#444",font=("TkDefaultFont",8)).grid(
                  row=r,column=0,columnspan=2,sticky="w",padx=4,pady=0); r+=1

        section_label(f, "Front Spar Doubler", row=r); r+=1
        self._le(f,"Doubler thickness (in):","front_spar_doubler_t",0.0, row=r); r+=1
        ttk.Label(f,text="  0 = no doubler",
                  foreground="#666",font=("TkDefaultFont",8)).grid(
                  row=r,column=0,columnspan=2,sticky="w",padx=16,pady=0); r+=1
        self._le(f,"Extent (rib bays each side of station):","front_spar_doubler_extent",1, row=r); r+=1

        section_label(f, "Rear Spar Doubler", row=r); r+=1
        self._le(f,"Doubler thickness (in):","rear_spar_doubler_t",0.0, row=r); r+=1
        ttk.Label(f,text="  0 = no doubler",
                  foreground="#666",font=("TkDefaultFont",8)).grid(
                  row=r,column=0,columnspan=2,sticky="w",padx=16,pady=0); r+=1
        self._le(f,"Extent (rib bays each side of station):","rear_spar_doubler_extent",1, row=r); r+=1

    # ── Wing Structure tab ───────────────────────────────────────────────────

    def _build_structure_tab(self, f):
        """Build the Wing Structure tab with data-driven field configuration."""
        f.columnconfigure(0, weight=0)
        f.columnconfigure(1, weight=1)
        f.rowconfigure(999, weight=1)
        
        row = RowCounter()
        
        # Structure type selection
        self._build_structure_type_section(f, row)
        
        # Geodetic lattice box (fabric_buildup only)
        self._build_geodetic_section(f, row)
        
        # Aluminum skin (aluminum_skin only)
        self._build_skin_section(f, row)
        
        # Wood knockdown factor
        self._build_wood_knockdown_section(f, row)
        
        # Rib structure
        self._build_rib_section(f, row)
        
        # Register all trace callbacks
        self._register_structure_traces()
        
        self._refresh_structure()

    def _build_structure_type_section(self, f, row):
        """Build structure type selection section."""
        section_label(f, "Wing Structure Type", row=row())
        
        struct_types = ["fabric_tube", "fabric_buildup", "aluminum_skin"]
        struct_labels = [
            "Fabric / Tube ladder",
            "Fabric / Built-up + D-cell + optional geodetic",
            "Aluminum stressed skin"
        ]  # Reserved for future UI enhancements
        
        self._lc(f, "Structure type:", "wing_structure_type",
                 struct_types, "fabric_tube", row=row())

    def _build_geodetic_section(self, f, row):
        """Build geodetic lattice box configuration section."""
        section_label(f, "Geodetic Lattice Box (fabric_buildup only)", row=row())
        self._lchk(f, "Enable geodetic box", "geodetic_enabled", False, row=row())
        
        # Geodetic fields frame
        self._geodetic_frame = ttk.Frame(f)
        self._geodetic_frame.grid(row=row(), column=0, columnspan=4, sticky="ew")
        
        # Field definitions: (widget_type, label, var_name, default, *extra_args)
        geodetic_fields = [
            ("combo", "Strip material:", "geodetic_mat", wood_mat_names(), "Sitka Spruce"),
            ("entry", "Strip width (in):", "geodetic_w", 1.0),
            ("entry", "Strip thickness (in):", "geodetic_t", 0.125),
            ("entry", "Strips per bay (per dir):", "geodetic_strips_per_bay", 2),
            ("entry", "Strip angle (deg):", "geodetic_angle", 45.0),
        ]
        
        self._build_subsection_fields(self._geodetic_frame, geodetic_fields)
        
        # Info label
        self._geodetic_info = tk.StringVar(value="")
        ttk.Label(self._geodetic_frame, textvariable=self._geodetic_info,
                  foreground=C_TEXT_DIM, font=("Courier", 8)).grid(
                  row=len(geodetic_fields), column=0, columnspan=4, sticky="w", padx=4)

    def _build_skin_section(self, f, row):
        """Build aluminum skin configuration section."""
        section_label(f, "Aluminum Skin (aluminum_skin only)", row=row())
        
        # Skin fields frame
        self._skin_frame = ttk.Frame(f)
        self._skin_frame.grid(row=row(), column=0, columnspan=4, sticky="ew")
        
        # Field definitions
        skin_fields = [
            ("combo", "Top skin material:", "skin_top_mat", aluminum_mat_names(), "6061-T6"),
            ("entry", "Top skin thickness (in):", "skin_top_thick", 0.025),
            ("combo", "Bot skin material:", "skin_bot_mat", aluminum_mat_names(), "6061-T6"),
            ("entry", "Bot skin thickness (in):", "skin_bot_thick", 0.025),
        ]
        
        self._build_subsection_fields(self._skin_frame, skin_fields)
        
        # Info label
        self._skin_info = tk.StringVar(value="")
        ttk.Label(self._skin_frame, textvariable=self._skin_info,
                  foreground=C_TEXT_DIM, font=("Courier", 8)).grid(
                  row=len(skin_fields), column=0, columnspan=4, sticky="w", padx=4)

    def _build_wood_knockdown_section(self, f, row):
        """Build wood knockdown factor section."""
        section_label(f, "Wood Knockdown Factor", row=row())
        self._le(f, "Knockdown factor (0.75 = AC 43.13):", "wood_knockdown", 0.75, row=row())

    def _build_rib_section(self, f, row):
        """Build rib structure configuration section."""
        section_label(f, "Rib Structure (torsion transfer between spars)", row=row())
        self._rib_rows = {}

        type_row = row()
        type_var = self._v("rib_type", "Plywood web")
        type_lbl = ttk.Label(f, text="Rib type:")
        type_lbl.grid(row=type_row, column=0, sticky="e", padx=3, pady=2)
        self._rib_type_combo = ttk.Combobox(
            f, textvariable=type_var, width=28, state="readonly",
            values=("Plywood web", "Sheet aluminum formed", "Dow foam with spruce caps"))
        self._rib_type_combo.grid(row=type_row, column=1, sticky="w", padx=3, pady=2)
        self._rib_type_combo.bind("<<ComboboxSelected>>", lambda _e: self._refresh_rib(True))

        for label, name, default in (
            ("Rib web height (in):", "rib_h_web", 3.0),
            ("Rib web thickness (in):", "rib_t_web", 0.125),
            ("Rib cap width (in):", "rib_b_cap", 0.75),
            ("Rib cap thickness (in):", "rib_t_cap", 0.125),
        ):
            r = row()
            lbl = ttk.Label(f, text=label)
            lbl.grid(row=r, column=0, sticky="e", padx=3, pady=2)
            var = self._v(name, default)
            entry = ttk.Entry(f, textvariable=var, width=10)
            entry.grid(row=r, column=1, sticky="w", padx=3, pady=2)
            self._rib_rows[name] = (lbl, entry)

        r = row()
        mat_lbl = ttk.Label(f, text="Rib material:")
        mat_lbl.grid(row=r, column=0, sticky="e", padx=3, pady=2)
        mat_var = self._v("rib_mat", "Birch Plywood")
        self._rib_mat_combo = ttk.Combobox(
            f, textvariable=mat_var, values=wood_mat_names(), width=22, state="readonly")
        self._rib_mat_combo.grid(row=r, column=1, sticky="w", padx=3, pady=2)
        self._rib_rows["rib_mat"] = (mat_lbl, self._rib_mat_combo)

        self._rib_info = tk.StringVar(value="")
        ttk.Label(f, textvariable=self._rib_info, foreground=C_TEXT_DIM,
                  font=("Courier", 8), wraplength=420, justify="left").grid(
                  row=row(), column=0, columnspan=4, sticky="w", padx=4)
        type_var.trace_add("write", lambda *_: self._refresh_rib(False))
        self._refresh_rib(False)

    def _refresh_rib(self, fix_material=False):
        """Show the fields that belong to the selected rib construction."""
        if not hasattr(self, "_rib_rows"):
            return
        kind = self._vars.get("rib_type", tk.StringVar(value="Plywood web")).get()
        labels = {
            "rib_h_web": "Rib web height (in):",
            "rib_t_web": "Rib web thickness (in):",
            "rib_b_cap": "Rib cap width (in):",
            "rib_t_cap": "Rib cap thickness (in):",
        }
        info = "Bruhn/Peery plywood shear panel. Stiffness is G t h / spar gap, per rib pitch."
        mats = wood_mat_names()
        default_mat = "Birch Plywood"
        hide = set()
        if kind == "Sheet aluminum formed":
            labels["rib_h_web"] = "Sheet web height (in):"
            labels["rib_t_web"] = "Sheet thickness (in):"
            labels["rib_b_cap"] = "Formed flange width (in):"
            hide.add("rib_t_cap")
            mats = aluminum_mat_names()
            default_mat = "2024-T3"
            info = ("Formed aluminum sheet. The flange is bent from the sheet, so flange "
                    "thickness equals the sheet. The shear panel is the web only.")
        elif kind == "Dow foam with spruce caps":
            labels["rib_h_web"] = "Foam height between caps (in):"
            labels["rib_t_web"] = "Foam thickness (in):"
            labels["rib_b_cap"] = "Spruce cap width (in):"
            labels["rib_t_cap"] = "Spruce cap thickness (in):"
            hide.add("rib_mat")
            info = ("Sandwich rib. Core shear uses Dow Styrofoam Panel Core 20 minimums "
                    "(ASTM C273): G = 300 psi, shear strength = 25 psi. Sitka spruce caps "
                    "take the bending. Glue is not checked.")
        for name, (lbl, widget) in self._rib_rows.items():
            if name in labels:
                lbl.configure(text=labels[name])
            if name in hide:
                lbl.grid_remove()
                widget.grid_remove()
            else:
                lbl.grid()
                widget.grid()
        if kind != "Dow foam with spruce caps":
            self._rib_mat_combo.configure(values=mats)
            current = self._vars["rib_mat"].get()
            if fix_material and current not in mats:
                self._vars["rib_mat"].set(default_mat if default_mat in mats else mats[0])
        self._rib_info.set(info)

    def _build_subsection_fields(self, parent, field_definitions):
        """
        Build a set of fields in a subsection frame from field definitions.
        
        Args:
            parent: Parent frame widget
            field_definitions: List of tuples (widget_type, label, var_name, *args)
                - widget_type: "entry" or "combo"
                - label: Field label text
                - var_name: Variable name for self._vars
                - args: Default value and optional extra args (e.g., combo values)
        """
        for idx, field_def in enumerate(field_definitions):
            widget_type, label, var_name = field_def[:3]
            args = field_def[3:]
            
            if widget_type == "entry":
                self._le(parent, label, var_name, args[0], row=idx)
            elif widget_type == "combo":
                # args = [values_list, default_value]
                self._lc(parent, label, var_name, args[0], args[1], row=idx)

    def _register_structure_traces(self):
        """Register all trace callbacks for structure tab variables."""
        # Structure type changes trigger full refresh
        self._vars["wing_structure_type"].trace_add("write",
                                                     lambda *_: self._refresh_structure())
        self._vars["geodetic_enabled"].trace_add("write",
                                                  lambda *_: self._refresh_structure())
        
        # Geodetic info updates
        for var_name in ("rib_spacing", "geodetic_strips_per_bay", "geodetic_enabled"):
            if var_name in self._vars:
                self._vars[var_name].trace_add("write",
                                                lambda *_: self._update_geodetic_info())
    # ── Tab Grid Configuration ───────────────────────────────────────────────

    def _configure_tab_grid(self, frame):
        """Standard grid configuration for input tabs."""
        frame.columnconfigure(0, weight=0)  # Label column - fixed
        frame.columnconfigure(1, weight=1)  # Entry column - expands
        frame.rowconfigure(999, weight=1)   # Bottom spacer

    # ── Loads Tab Helper Methods ─────────────────────────────────────────────

    def _build_loads_section(self, parent, row):
        """Build Gross Weight & Loads input section."""
        section_label(parent, "Gross Weight & Loads", row=row())
        
        self._le(parent, "Gross weight (lb):", "Weight", 1750.0, row=row())
        self._le(parent, "Wing weight (lb):", "Wing_Weight", 175.0, row=row())
        self._le(parent, "Tail download at 1g (lb):", "Tail_Down_1g", 218.75, row=row())
        self._le(parent, "Pos load factor (+g):", "n", 6.0, row=row())
        self._le(parent, "Neg load factor (-g):", "n_neg", -3.0, row=row())
        self._le(parent, "ng_lift (semi-span, lb):", "ng_lift", 5381.25, row=row())
        
        # Auto-compute button
        ttk.Button(parent, text="Auto-compute ng_lift",
                   command=self._auto_ng_lift).grid(
                       row=row(), column=0, columnspan=2, sticky="w", padx=4, pady=3)
        
        self._lchk(parent, "Distribute wing weight along span",
                   "distribute_wing_weight", False, row=row())

    def _build_config_section(self, parent, row):
        """Build Configuration dropdown section."""
        section_label(parent, "Configuration", row=row())
        
        configs = ["strut_braced", "cantilever", "single_strut"]
        self._lc(parent, "Config:", "config", configs, "strut_braced", row=row())
        self._vars["config"].trace_add("write", lambda *_: self._refresh_config())

    def _build_strut_frame(self, parent, row):
        """Build strut configuration sub-frame."""
        self._strut_frame = ttk.Frame(parent)
        self._strut_frame.grid(row=row(), column=0, columnspan=4, sticky="ew")
        
        sf = self._strut_frame
        self._le(sf, "Strut BL at fuselage (in):", "strut_fuse_bl", 0.0, row=0)
        self._le(sf, "Strut BL at spar (in):", "strut_bl", 104.0, row=1)
        self._le(sf, "Strut rise (in):", "strut_vert", 44.0, row=2)
        self._lc(sf, "Strut material:", "strut_mat", strut_mat_names(),
                 "4130 Chromoly (normalized)", row=3, width=28)
        self._le(sf, "Strut OD (in):", "strut_tube_od", 3.0, row=4)
        self._le(sf, "Strut wall (in):", "strut_tube_wall", 0.065, row=5)
        
        # Info label
        self._strut_info = tk.StringVar(value="")
        ttk.Label(sf, textvariable=self._strut_info, foreground="#444",
                  font=("Courier", 8)).grid(
                      row=6, column=0, columnspan=4, sticky="w", padx=4)
        
        # Register traces for strut parameters
        self._register_strut_traces()

    def _register_strut_traces(self):
        """Register trace callbacks for strut parameter updates."""
        strut_params = ["strut_bl", "strut_fuse_bl", "strut_vert",
                        "strut_mat", "strut_tube_od", "strut_tube_wall"]
        
        for param_name in strut_params:
            if param_name in self._vars:
                # Fix closure issue by using default argument
                self._vars[param_name].trace_add(
                    "write", lambda *_, p=param_name: self._update_strut_info())

    def _build_secondary_bending_section(self, parent, row):
        """Build P-delta amplification section."""
        section_label(parent, "Secondary Bending (P-delta)", row=row())
        self._lchk(parent, "Enable P-delta amplification",
                   "secondary_bending", False, row=row())

    def _build_jury_strut_section(self, parent, row):
        """Build jury strut configuration section.

        The jury braces the lift strut, so this block follows the strut
        stations and is hidden on a cantilever wing.
        """
        self._jury_frame = ttk.Frame(parent)
        self._jury_frame.grid(row=row(), column=0, columnspan=4, sticky="ew")
        jf = self._jury_frame
        section_label(jf, "Jury Strut", row=0)
        self._lchk(jf, "Enable jury strut", "jury_strut", False, row=1)
        self._le(jf, "Jury spar BL (in):", "jury_spar_bl", 60.0, row=2)


    # ── Loads & Config tab ───────────────────────────────────────────────────

    def _build_loads_tab(self, f):
        """Build the Loads & Config tab with all input sections."""
        self._configure_tab_grid(f)
        row = RowCounter()
        
        # Configuration decides whether a lift strut, and then a jury, exist.
        self._build_config_section(f, row)
        self._build_strut_frame(f, row)
        self._build_jury_strut_section(f, row)
        self._build_secondary_bending_section(f, row)
        self._build_loads_section(f, row)
        
        self._refresh_config()
        self._update_strut_info()

    # ── Flight & Airfoil tab ─────────────────────────────────────────────────

    def _build_flight_tab(self, f):
        f.columnconfigure(0, weight=0); f.columnconfigure(1, weight=1); f.rowconfigure(999, weight=1)
        r = 0
        section_label(f,"Airfoil Selection", row=r); r+=1

        # Family filter
        from airfoil_database import airfoil_families
        fam_list = ["(All families)"] + airfoil_families()
        self._af_family_var = tk.StringVar(value="(All families)")
        ttk.Label(f,text="Family filter:").grid(row=r,column=0,sticky="e",padx=3,pady=2)
        fam_cb = ttk.Combobox(f,textvariable=self._af_family_var,values=fam_list,
                               width=26,state="readonly")
        fam_cb.grid(row=r,column=1,sticky="w",padx=3,pady=2); r+=1
        self._af_family_var.trace_add("write", lambda *_: self._filter_airfoils())

        # Search box
        self._af_search_var = tk.StringVar(value="")
        ttk.Label(f,text="Search:").grid(row=r,column=0,sticky="e",padx=3,pady=2)
        ttk.Entry(f,textvariable=self._af_search_var,width=28).grid(
            row=r,column=1,sticky="w",padx=3,pady=2); r+=1
        self._af_search_var.trace_add("write", lambda *_: self._filter_airfoils())

        # Airfoil listbox with scrollbar
        frm_lb = ttk.Frame(f)
        frm_lb.grid(row=r,column=0,columnspan=2,sticky="ew",padx=3,pady=2); r+=1
        self._af_listbox = tk.Listbox(frm_lb,height=8,width=40,
                                       font=("Courier",8),exportselection=False)
        lb_sb = ttk.Scrollbar(frm_lb,orient="vertical",command=self._af_listbox.yview)
        self._af_listbox.configure(yscrollcommand=lb_sb.set)
        self._af_listbox.pack(side=tk.LEFT,fill=tk.BOTH,expand=True)
        lb_sb.pack(side=tk.RIGHT,fill=tk.Y)
        self._af_listbox.bind("<<ListboxSelect>>", self._on_af_listbox_select)

        # Current selection display
        self._vars["airfoil"] = tk.StringVar(value="NACA 4412")
        ttk.Label(f,text="Selected:").grid(row=r,column=0,sticky="e",padx=3,pady=2)
        ttk.Label(f,textvariable=self._vars["airfoil"],
                  foreground="#003399",font=("TkDefaultFont",9,"bold")).grid(
                  row=r,column=1,sticky="w",padx=3,pady=2); r+=1

        ttk.Button(f,text="Apply selected airfoil →",
                   command=self._on_airfoil_select).grid(
                   row=r,column=0,columnspan=2,sticky="w",padx=4,pady=3); r+=1

        # Populate listbox initially
        self._filter_airfoils()

        self._le(f,"Cm_ac clean (override):","Cm_ac",-0.099,row=r); r+=1
        self._le(f,"ΔCm full flap (neg=nose-down):","Cm_flap",0.0,row=r); r+=1
        ttk.Label(f,text="  Flap Cm adds to Cm_ac for flap-extended torsion check at Va",
                  foreground=C_TEXT_DIM,font=("Segoe UI",8)).grid(
                  row=r,column=0,columnspan=4,sticky="w",padx=20,pady=(0,4)); r+=1
        self._le(f,"Cl_alpha (per rad):","Cl_alpha",6.30,row=r); r+=1
        self._le(f,"AC position (x/c):","x_ac_c",0.246,row=r); r+=1
        self._le(f,"t/c:","airfoil_t_c",0.12,row=r); r+=1
        # Re-propose spar heights when t/c is edited manually
        self._vars["airfoil_t_c"].trace_add("write", self._repropose_h_web)
        self._vars["airfoil_t_c"].trace_add("write", lambda *_: self._update_dcell_area())

        self._airfoil_info = tk.StringVar(value="")
        ttk.Label(f,textvariable=self._airfoil_info,foreground="#444",
                  font=("Courier",8),wraplength=400).grid(
                      row=r,column=0,columnspan=4,sticky="w",padx=4); r+=1

        section_label(f,"Flight Conditions", row=r); r+=1
        self._le(f,"Design dive speed Vd (mph):","Vd_mph",100.0,row=r); r+=1
        self._le(f,"Cruise speed Vc (mph):","Vc_mph",80.0,row=r); r+=1
        self._le(f,"Manoeuvre speed Va (mph):","Va_mph",60.0,row=r); r+=1
        self._le(f,"Altitude (ft):","altitude_ft",2000.0,row=r); r+=1
        self._q_var = tk.StringVar(value="q = —")
        ttk.Label(f,textvariable=self._q_var,foreground="#444",
                  font=("Courier",9)).grid(row=r,column=0,columnspan=4,sticky="w",padx=4); r+=1

        for nm in ("Vd_mph","altitude_ft"):
            self._vars[nm].trace_add("write", lambda *_: self._update_q())

        section_label(f,"Curvature", row=r); r+=1
        self._le(f,"Curvature sign (+1 or -1):","curvature_sign",1.0,row=r); r+=1

        self._update_q()

    # ── Refresh helpers ───────────────────────────────────────────────────────

    def _refresh_spar(self, which):
        typ = self._vars[f"{which}_spar_type"].get()
        tube = typ == "Round Tube"
        tf = self._front_tube_frame if which=="front" else self._rear_tube_frame
        bf = self._front_buildup_frame if which=="front" else self._rear_buildup_frame

        if tube:
            tf.grid()
            bf.grid_remove()
        else:
            tf.grid_remove()
            # Destroy old buildup widgets and rebuild for this spar type
            for w in bf.winfo_children():
                w.destroy()
            self._build_buildup_fields(bf, f"{which}_spar", typ)
            bf.grid()
        self._update_h_total(f"{which}_spar")

    def _update_h_total(self, prefix):
        """Recompute and display total spar height.
        Single-cap types (C-Channel, Aluminum C-Spar): h = t_top + h_web only.
        Two-cap types: h = t_top + h_web + t_bot.
        """
        try:
            t_top = float(self._vars[f"{prefix}_t_top"].get())
            h_web = float(self._vars[f"{prefix}_h_web"].get())
            # Determine if this spar type has a bottom cap
            spar_type = self._vars.get(f"{prefix}_type",
                         tk.StringVar(value="I-Beam")).get()
            single_cap = spar_type == "Aluminum C-Spar"   # only true single-cap type
            if single_cap:
                h_tot = t_top + h_web
                label = f"{h_tot:.3f} in  (cap + web, no bottom cap)"
            else:
                t_bot = float(self._vars[f"{prefix}_t_bot"].get())
                h_tot = t_top + h_web + t_bot
                label = f"{h_tot:.3f} in"
            self._vars[f"{prefix}_h_total_disp"].set(label)
        except (ValueError, KeyError):
            self._vars.get(f"{prefix}_h_total_disp", tk.StringVar()).set("")

    def _on_angle_sel(self, prefix, var):
        """Auto-fill b_top/t_top/b_bot/t_bot from aluminum angle selection."""
        from spar_sections import get_angle
        desc = var.get()
        if desc == "(Manual flat bar)": return
        ang = get_angle(desc)
        if ang:
            self._vars[f"{prefix}_b_top"].set(str(ang.b_equiv))
            self._vars[f"{prefix}_t_top"].set(f"{ang.t_equiv:.4f}")
            self._vars[f"{prefix}_b_bot"].set(str(ang.b_equiv))
            self._vars[f"{prefix}_t_bot"].set(f"{ang.t_equiv:.4f}")
            if f"{prefix}_b_top_tip" in self._vars:
                self._vars[f"{prefix}_b_top_tip"].set(str(ang.b_equiv))
                self._vars[f"{prefix}_t_top_tip"].set(f"{ang.t_equiv:.4f}")
            if f"{prefix}_b_bot_tip" in self._vars:
                self._vars[f"{prefix}_b_bot_tip"].set(str(ang.b_equiv))
                self._vars[f"{prefix}_t_bot_tip"].set(f"{ang.t_equiv:.4f}")

    def _refresh_dcell(self):
        enabled = self._vars.get("dcell_enabled", tk.BooleanVar(value=False)).get()
        if hasattr(self, "_front_dcell_frame"):
            if enabled: self._front_dcell_frame.grid()
            else:       self._front_dcell_frame.grid_remove()

    def _refresh_structure(self):
        st = self._vars.get("wing_structure_type", tk.StringVar(value="fabric_tube")).get()
        geo_enabled = self._vars.get("geodetic_enabled", tk.BooleanVar(value=False)).get()
        if hasattr(self, "_geodetic_frame"):
            if st == "fabric_buildup" and geo_enabled:
                self._geodetic_frame.grid()
            else:
                self._geodetic_frame.grid_remove()
        if hasattr(self, "_skin_frame"):
            if st == "aluminum_skin": self._skin_frame.grid()
            else:                     self._skin_frame.grid_remove()
        self._update_geodetic_info()

    def _refresh_config(self):
        cfg = self._vars.get("config", tk.StringVar(value="strut_braced")).get()
        has_strut = cfg in ("strut_braced","single_strut")
        if hasattr(self, "_strut_frame"):
            if has_strut: self._strut_frame.grid()
            else:         self._strut_frame.grid_remove()
        if hasattr(self, "_jury_frame"):
            if has_strut: self._jury_frame.grid()
            else:         self._jury_frame.grid_remove()

    def _update_geodetic_info(self):
        try:
            rib = float(self._vars["rib_spacing"].get())
            npb = int(float(self._vars["geodetic_strips_per_bay"].get()))
            s   = rib / max(npb, 1)
            self._geodetic_info.set(
                f"Rib spacing: {rib:.1f}\"   Strips per bay: {npb}   "
                f"→ strip spacing: {s:.2f}\" c-t-c")
        except: pass

    def _update_dcell_area(self):
        try:
            chord  = float(self._vars["root_chord"].get())
            fp_pct = float(self._vars["front_spar_percent"].get())
            t_c    = float(self._vars["airfoil_t_c"].get())
            t_skin = float(self._vars["dcell_skin_thick"].get())
            mat    = self._vars["dcell_skin_mat"].get()
            from spar_sections import DCellSkin
            af = get_airfoil(self._vars["airfoil"].get()) if "airfoil" in self._vars else None
            x_t_c = float((af or {}).get("x_t_c") or 0.30)
            tw = 0.0
            web = self._vars.get("front_spar_t_web")
            wall = self._vars.get("front_spar_wall")
            if web is not None:
                tw = float(web.get() or 0)
            if tw <= 0 and wall is not None:
                tw = float(wall.get() or 0)
            if tw <= 0:
                tw = 0.125
            c2s = fp_pct * chord
            cell = DCellSkin(
                t_skin=t_skin, skin_mat=mat, chord_to_spar=c2s,
                t_web=tw, t_c=t_c, x_t_c=x_t_c)
            geo = cell.nose_geometry(t_c * chord)
            txt = "%.1f in2  (nose to %.1f in, web %.1f in)   GJ ~= %s lb.in2" % (
                geo["area"], geo["x_spar"], geo["h_web"],
                "{:,.0f}".format(cell.GJ(t_c * chord)))
            self._dcell_area_var.set(txt)
        except (ValueError, KeyError, ZeroDivisionError, AttributeError):
            pass

    def _update_strut_info(self):
        try:
            bl       = float(self._vars["strut_bl"].get())
            fuse_bl  = float(self._vars.get("strut_fuse_bl", type("V",(),{"get":lambda s:"0"})()).get())
            vert     = float(self._vars["strut_vert"].get())
            od   = float(self._vars["strut_tube_od"].get())
            wall = float(self._vars["strut_tube_wall"].get())
            L    = math.sqrt(max(bl - fuse_bl, 1)**2 + vert**2)
            id_  = od - 2*wall
            I    = math.pi/64*(od**4-id_**4)
            mat  = self._vars["strut_mat"].get()
            E    = STRUT_MATERIALS[mat]["E"]
            Pe   = math.pi**2*E*I/L**2
            self._strut_info.set(
                f"L={L:.1f}\"  I={I:.4f} in⁴  Pe={Pe:,.0f} lb")
        except: pass

    def _update_q(self):
        try:
            V = float(self._vars["Vd_mph"].get())
            a = float(self._vars["altitude_ft"].get())
            q = dynamic_pressure_psi(V, a)
            self._q_var.set(f"q = {q:.4f} psi  (at {V:.0f} mph, {a:.0f} ft)")
        except: pass

    def _repropose_h_web(self, *_):
        """Re-propose spar heights from current airfoil t/c — called by traces."""
        try:
            t_c = float(self._vars["airfoil_t_c"].get())
            if t_c > 0:
                self._propose_h_web(t_c)
        except (ValueError, KeyError):
            pass

    def _propose_h_web(self, t_c):
        """Propose shear web height using NACA thickness at each spar chord position."""

        try:
            chord     = float(self._vars["root_chord"].get())
            front_pct = float(self._vars["front_spar_percent"].get())
            rear_pct  = float(self._vars["rear_spar_percent"].get())

            spar_positions = {
                "front_spar": front_pct,
                "rear_spar":  rear_pct,
            }
            for prefix, x_c in spar_positions.items():
                spar_type = self._vars.get(f"{prefix}_type", tk.StringVar()).get()
                if spar_type in ("I-Beam","Double I-Beam","C-Channel",
                                  "Routed (Monolithic)","Aluminum I-Beam","Aluminum C-Spar"):
                    # Airfoil depth at this spar's chord position
                    depth = naca_depth(x_c, t_c, chord)
                    # Subtract cap heights to get clear web height
                    is_c_spar = spar_type == "Aluminum C-Spar"
                    try:
                        t_top = float(self._vars.get(f"{prefix}_t_top",
                                      tk.StringVar(value="0.125")).get())
                    except ValueError:
                        t_top = 0.125
                    if is_c_spar:
                        h_web = max(depth - t_top, 0.25)
                    else:
                        try:
                            t_bot = float(self._vars.get(f"{prefix}_t_bot",
                                          tk.StringVar(value="0.125")).get())
                        except ValueError:
                            t_bot = t_top
                        h_web = max(depth - t_top - t_bot, 0.25)

                    if f"{prefix}_h_web" in self._vars:
                        self._vars[f"{prefix}_h_web"].set(f"{h_web:.3f}")
                        self._update_h_total(prefix)
        except (ValueError, KeyError):
            pass


    def _filter_airfoils(self):
        """Update listbox based on family filter and search string."""
        try:
            fam    = self._af_family_var.get()
            search = self._af_search_var.get().strip().lower()
            results = []
            for name, af in AIRFOIL_DB.items():
                if name == "Manual Entry": continue
                if fam != "(All families)" and af.get("family","") != fam:
                    continue
                if search and search not in name.lower():
                    continue
                results.append(name)
            self._af_listbox.delete(0, tk.END)
            for name in results[:500]:   # cap at 500 for responsiveness
                self._af_listbox.insert(tk.END, name)
            # If current selection is in results, highlight it
            cur = self._vars["airfoil"].get()
            if cur in results:
                idx = results.index(cur)
                self._af_listbox.selection_set(idx)
                self._af_listbox.see(idx)
        except Exception:
            pass

    def _on_af_listbox_select(self, event=None):
        """User clicked a name in the listbox — set and immediately apply airfoil data."""
        try:
            sel = self._af_listbox.curselection()
            if sel:
                name = self._af_listbox.get(sel[0])
                self._vars["airfoil"].set(name)
                self._on_airfoil_select()   # auto-apply t/c and spar heights
        except Exception:
            pass

    def _on_airfoil_select(self):
        name = self._vars["airfoil"].get()
        af   = get_airfoil(name)
        if not af: return
        if af.get("Cm_ac") is not None:
            self._vars["Cm_ac"].set(str(af["Cm_ac"]))
        if af.get("Cl_alpha") is not None:
            self._vars["Cl_alpha"].set(str(af["Cl_alpha"]))
        if af.get("x_ac_c") is not None:
            self._vars["x_ac_c"].set(str(af["x_ac_c"]))
        if af.get("t_c") is not None:
            self._vars["airfoil_t_c"].set(str(af["t_c"]))
            self._propose_h_web(af["t_c"])
        # Build info string with proposed spar depths
        try:
            chord = float(self._vars["root_chord"].get())
            fp    = float(self._vars["front_spar_percent"].get())
            rp    = float(self._vars["rear_spar_percent"].get())
            t_c   = af.get("t_c") or 0
            d_f = naca_depth(fp, t_c, chord)
            d_r = naca_depth(rp, t_c, chord)
            depth_str = "  Front=%.2fin  Rear=%.2fin" % (d_f, d_r)
        except: depth_str = ""
        fam  = af.get("family","")
        info = ("%s  (%s)  t/c=%s  Cm=%s  Cl_a=%s%s" %
                (name, fam, af.get("t_c","?"), af.get("Cm_ac","?"),
                 af.get("Cl_alpha","?"), depth_str))
        if hasattr(self, "_airfoil_info"): self._airfoil_info.set(info)


    def _on_tube_sel(self, which):
        var = self._front_tube_sel if which=="front" else self._rear_tube_sel
        desc = var.get()
        if desc == "(Manual)": return
        tube = get_tube_by_description(desc)
        if tube:
            self._vars[f"{which}_spar_od"].set(str(tube.od))
            self._vars[f"{which}_spar_wall"].set(str(tube.wall))

    def _auto_ng_lift(self):
        try:
            n  = float(self._vars["n"].get())
            W  = float(self._vars["Weight"].get())
            td = float(self._vars["Tail_Down_1g"].get())
            ng = WingStressAnalyzer.calc_ng_lift(n, W, td)
            self._vars["ng_lift"].set(f"{ng:.2f}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ── Populate defaults ─────────────────────────────────────────────────────

    def _populate_defaults(self):
        from wing_stress_analyzer import DEFAULT_INPUTS
        self._load_data(dict(DEFAULT_INPUTS))

    # ── Collect inputs ────────────────────────────────────────────────────────

    def _collect(self) -> dict:
        """
        Collect all GUI inputs into a dict for the analyzer.
        - Starts from cache (which was set on last load/save and has all keys)
        - Falls back to DEFAULT_INPUTS ONLY for keys genuinely absent from cache
        - Overlays live var values with proper type coercion
        - Never passes empty strings to the analyzer
        """
        from wing_stress_analyzer import DEFAULT_INPUTS

        bool_keys = {"dcell_enabled","geodetic_enabled","distribute_wing_weight",
                     "secondary_bending","jury_strut"}

        # Start from cache — this is the user's actual configuration
        out = dict(self._data_cache)

        # Fill any keys absent from cache with defaults (new features not yet saved)
        for k, v in DEFAULT_INPUTS.items():
            if k not in out:
                out[k] = v

        # Overlay live var values
        for k, var in self._vars.items():
            raw = var.get()
            if k in bool_keys:
                out[k] = bool(raw) if isinstance(raw, bool) else (str(raw).strip().lower() in ("1","true","yes"))
            else:
                raw_str = str(raw).strip()
                if raw_str != "":
                    try:    out[k] = parse_user_float(raw_str)
                    except ValueError: out[k] = raw_str
                # if empty: keep cache/default value

        # Normalize load share
        lsf = out.get("front_spar_load_share", 0.55)
        if isinstance(lsf, (int,float)) and lsf > 1.0:
            out["front_spar_load_share"] = lsf / 100.0

        out["num_spars"] = 2
        return out

    # ── Analysis ─────────────────────────────────────────────────────────────

    def _set_status(self, msg, colour=None):
        colour = colour or C_TEXT_DIM
        self.status_var.set(msg)
        if hasattr(self, "_hdr_status"): self._hdr_status.configure(text=msg[:60], fg=colour)
        if hasattr(self, "_hdr_dot"):    self._hdr_dot.configure(fg=colour)
        self.root.update_idletasks()

    def _run_analysis(self):
        self.status_var.set("Analyzing…")
        self.root.update_idletasks()
        try:
            inp = self._collect()
            inp, warnings = validate_inputs(inp)
            self.analyzer = WingStressAnalyzer(inp)
            self.analyzer.validation_warnings = warnings
            self.analyzer.analyze()
            self._show_summary()
            self._update_plots()
            self._nb.select(0)
            warnings = self.analyzer.validation_warnings
            if warnings:
                note = "; ".join(item.message for item in warnings[:3])
                self.status_var.set(f"Analysis complete. Check input warnings: {note}")
            else:
                self.status_var.set("Analysis complete.")
            # Show the wing in the Geometry tab once the pane has its size.
            self.root.after(100, self._show_geometry)
        except ValidationError as exc:
            messagebox.showerror("Input Error", str(exc))
            self.status_var.set("Input error — see dialog.")
        except Exception:
            tb = traceback.format_exc()
            messagebox.showerror("Analysis Error", tb)
            self.status_var.set("Error — see dialog.")

    def _show_summary(self):
        txt = self.analyzer.summary_text()
        self._summary_text.config(state="normal")
        self._summary_text.delete("1.0", tk.END)

        # Insert with colour tagging
        for line in txt.splitlines(keepends=True):
            tag = None
            if "✓" in line:   tag = "GREEN"
            elif "⚠" in line: tag = "YELLOW"
            elif "✗" in line or "***" in line: tag = "RED"
            elif line.strip().startswith(">>>"):  tag = "FIX"
            elif line.startswith("══") or line.startswith("──"): tag = "HEAD"
            self._summary_text.insert(tk.END, line, tag or "")

        self._summary_text.config(state="disabled")

    def _style_axis(self, ax):
        """Apply dark theme styling to a single axis."""
        ax.clear()
        ax.set_facecolor(PLOT_STYLE["dark_bg"])
        ax.tick_params(colors=PLOT_STYLE["tick_color"], labelcolor=PLOT_STYLE["label_color"])
        ax.spines[:].set_color(PLOT_STYLE["spine_color"])

    def _add_torsion_overlay(self, ax, x, torsion_data):
        """Add torsion twist overlay to an axis (for skinned/geodetic wings)."""
        if not torsion_data:
            return None
        
        ax_twin = ax.twinx()
        twist_deg = np.degrees(torsion_data["phi"])
        ax_twin.plot(
            x, twist_deg,
            color=PLOT_STYLE["torsion_color"],
            lw=PLOT_STYLE["torsion_lw"],
            linestyle=":",
            alpha=PLOT_STYLE["torsion_alpha"]
        )
        ax_twin.set_ylabel("Twist [°]", fontsize=7, color=PLOT_STYLE["torsion_color"])
        ax_twin.tick_params(labelsize=7, colors=PLOT_STYLE["torsion_color"])
        return ax_twin

    def _plot_data_series(self, ax, x, config, analyzer):
        """Plot a single data series based on configuration."""
        for plot_spec in config["plots"]:
            key = plot_spec["key"]
            load = plot_spec["load"]
            
            # Get data
            data = analyzer.pos[key] if load == "pos" else analyzer.neg[key]
            if plot_spec.get("negate", False):
                data = -data
            
            # Determine styling
            color = plot_spec.get("color")
            if not color:
                color = PLOT_STYLE["pos_color"] if load == "pos" else PLOT_STYLE["neg_color"]
            
            lw = plot_spec.get("lw")
            if not lw:
                lw = PLOT_STYLE["pos_lw"] if load == "pos" else PLOT_STYLE["neg_lw"]
            
            linestyle = "--" if load == "neg" else plot_spec.get("linestyle", "-")
            
            # Determine label
            label = plot_spec.get("label")
            if not label and "label_fn" in plot_spec:
                label = plot_spec["label_fn"](analyzer)
            
            # Plot
            ax.plot(x, data, color=color, lw=lw, linestyle=linestyle, label=label)
        
        # Configure axis
        ax.set(title=config["title"], xlabel=config["xlabel"])
        ax.grid(True, alpha=PLOT_STYLE["grid_alpha"])
        
        if config.get("legend"):
            ax.legend(fontsize=7)
        
        if config.get("zero_line"):
            ax.axhline(y=0, color="k", lw=0.5, alpha=0.4)

    def _should_show_torsion(self):
        """Determine if torsion overlay should be shown based on wing structure."""
        if not self.analyzer or not self.analyzer.torsion:
            return False
        
        # Show torsion for skinned or geodetic wings
        wing_type = self._vars.get("wing_structure_type", tk.StringVar()).get()
        geodetic = self._vars.get("geodetic_enabled", tk.BooleanVar()).get()
        
        return wing_type == "aluminum_skin" or geodetic

    def _update_plots(self):
        """Update all analysis plots with current data."""
        a = self.analyzer
        x = a.x
        
        # Style all axes
        for ax in self._axes.flatten():
            self._style_axis(ax)
        
        axes = self._axes.flatten()
        
        # Plot each configured subplot
        for i, config in enumerate(PLOT_CONFIGS):
            if i < len(axes):
                self._plot_data_series(axes[i], x, config, a)
                
                # Add torsion overlay if configured and applicable
                if config.get("torsion_overlay") and self._should_show_torsion():
                    self._add_torsion_overlay(axes[i], x, a.torsion)
        
        self._fig.tight_layout(pad=2.0)
        self._canvas_plt.draw()
        self._nb.select(1)

    def _show_geometry(self):
        """Select the Geometry tab and draw the current wing into it."""
        self._nb.select(self._geo_tab)
        self.root.update_idletasks()
        self._draw_geometry_figure()

    def _draw_geometry_figure(self):
        top, side = self._geo_ax_top, self._geo_ax_side
        top.clear()
        side.clear()
        if self.analyzer is None:
            for ax in (top, side):
                ax.set_facecolor("#252930")
                ax.tick_params(colors="#B9BCC2", labelcolor="#B9BCC2")
                for spine in ax.spines.values():
                    spine.set_color("#6E7F87")
                ax.set_xticks([])
                ax.set_yticks([])
            top.set_title("Run analysis to draw the wing", color="#e8eaf0")
        else:
            self.analyzer.draw_geometry(top, side)
        try:
            self._geo_fig.tight_layout(pad=1.1)
        except Exception:
            pass
        self._canvas_geo.draw_idle()

    # ── Save / Load ───────────────────────────────────────────────────────────

    def _new(self):
        self._populate_defaults()
        self.current_file = None
        self.root.title(APP_TITLE)
        self._data_cache = {}

    def _load_data(self, data: dict):
        """
        Load a flat key-value dict into the GUI.
        - Uses file data as the authority for all keys present in the file
        - Falls back to DEFAULT_INPUTS ONLY for keys missing from the file
          (handles new features added after the file was saved)
        - Normalises booleans, floats and strings before setting vars
        - Refreshes spar/config frames in the correct order
        """
        from wing_stress_analyzer import DEFAULT_INPUTS

        bool_keys = {"dcell_enabled","geodetic_enabled","distribute_wing_weight",
                     "secondary_bending","jury_strut"}

        # 1. Start from defaults for any keys NOT in the file (new features etc.)
        #    Then overlay with file data — file wins for every key it contains
        merged = {}
        for k, v in DEFAULT_INPUTS.items():
            if k not in data:
                merged[k] = v   # only use default for missing keys

        # 2. Process file data with type normalisation
        for k, v in data.items():
            if k in bool_keys:
                if isinstance(v, bool):
                    merged[k] = v
                else:
                    merged[k] = str(v).strip().lower() in ("1","true","yes")
            elif isinstance(v, str):
                v_stripped = v.strip()
                if v_stripped == "":
                    # Empty string in file — use default if available, else skip
                    if k in DEFAULT_INPUTS:
                        merged[k] = DEFAULT_INPUTS[k]
                else:
                    try:    merged[k] = float(v_stripped)
                    except: merged[k] = v_stripped
            else:
                merged[k] = v

        # 3. Normalize load share: file may store as 55 (%) or 0.55
        lsf = merged.get("front_spar_load_share", 0.55)
        if isinstance(lsf, (int,float)) and lsf > 1.0:
            merged["front_spar_load_share"] = lsf / 100.0

        # A saved file from before tip caps existed keeps the root size out to the tip.
        for prefix in ("front_spar", "rear_spar"):
            for root_name, tip_name in (
                ("b_top", "b_top_tip"), ("t_top", "t_top_tip"),
                ("b_bot", "b_bot_tip"), ("t_bot", "t_bot_tip"),
                ("b_outer", "b_outer_tip"), ("t_cap", "t_cap_tip"),
            ):
                tip_key = f"{prefix}_{tip_name}"
                root_key = f"{prefix}_{root_name}"
                if tip_key not in data and root_key in merged:
                    merged[tip_key] = merged[root_key]

        # 4. Store full merged data in cache
        self._data_cache = dict(merged)

        # 5. Set spar type / config vars FIRST so _refresh builds the right fields
        for k in ("front_spar_type","rear_spar_type","config",
                  "wing_structure_type","dcell_enabled","geodetic_enabled"):
            if k in merged and k in self._vars:
                self._vars[k].set(str(merged[k]))

        # 6. Refresh frames — rebuilds buildup/tube/config fields
        self._refresh_spar("front")
        self._refresh_spar("rear")
        self._refresh_dcell()
        self._refresh_structure()
        self._refresh_config()

        # 7. Set ALL registered vars from merged data
        skip_display = {"front_spar_h_total_disp","rear_spar_h_total_disp"}
        for k, var in self._vars.items():
            if k in skip_display:
                continue
            if k in merged:
                val = merged[k]
                if isinstance(val, float):
                    # Clean formatting: 0.9 not 0.9000000000000001
                    var.set(f"{val:g}" if val == int(val) else f"{val}")
                elif isinstance(val, bool):
                    var.set(str(val))
                else:
                    var.set(str(val))

        # 8. Update all derived displays
        self._update_h_total("front_spar")
        self._update_h_total("rear_spar")
        self._update_geodetic_info()
        self._update_strut_info()
        self._update_q()
        self._update_dcell_area()
        self._refresh_rib(False)

    def _write_file(self, path):
        """
        Save all inputs to a .aerobeam JSON file.
        - Starts from cache (preserves all keys including non-visible spar fields)
        - Overlays with current live var values
        - Coerces types properly: booleans as bool, numerics as float
        - Skips display-only keys and empty strings
        - Does NOT inject DEFAULT_INPUTS values — file reflects actual user inputs
        """
        bool_keys = {"dcell_enabled", "geodetic_enabled", "distribute_wing_weight",
                     "secondary_bending", "jury_strut"}
        skip_keys = {"front_spar_h_total_disp", "rear_spar_h_total_disp"}
        string_keys = {"airfoil"}

        # Start from cache (has all keys including hidden spar fields)
        data = dict(self._data_cache)

        # Overlay with current live var values
        for k, var in self._vars.items():
            if k in skip_keys:
                continue

            raw = var.get()
            coerced = self._coerce_value(k, raw, bool_keys, string_keys)

            if coerced is not None:
                data[k] = coerced
            # else: keep whatever is in cache from last load

        # Normalize load share to 0-1
        self._normalize_load_share(data)

        data["num_spars"] = 2

        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, default=str)
        self._set_status(f"Saved {path}", C_GREEN)

    def _coerce_to_bool(self, value):
        """Convert value to boolean, handling string representations."""
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ("1", "true", "yes")

    def _coerce_value(self, key, raw_value, bool_keys, string_keys):
        """
        Coerce value to appropriate type based on key.
        Returns None if value should be skipped (empty string for non-string keys).
        """
        if key in bool_keys:
            return self._coerce_to_bool(raw_value)

        if key in string_keys:
            return str(raw_value)

        raw_str = str(raw_value).strip()
        if raw_str == "":
            return None  # Signal to skip - keep cache value

        try:
            return float(raw_str)
        except (ValueError, TypeError):
            return raw_str

    def _normalize_load_share(self, data):
        """Normalize front_spar_load_share from percentage to 0-1 range if needed."""
        lsf = data.get("front_spar_load_share", 0.55)
        if isinstance(lsf, (int, float)) and lsf > 1.0:
            data["front_spar_load_share"] = lsf / 100.0

    def _open(self):
        path = filedialog.askopenfilename(
            filetypes=[("AeroBeam project","*.aerobeam"),("JSON","*.json"),("All","*.*")])
        if not path: return
        try:
            with open(path) as fh:
                data = json.load(fh)
            self._load_data(data)
            self.current_file = path
            self.root.title(f"{APP_TITLE}  —  {os.path.basename(path)}")
            self._set_status(f"Loaded {path}", C_GREEN)
        except Exception:
            messagebox.showerror("Open Error", traceback.format_exc())

    def _save(self):
        if not self.current_file:
            self._save_as()
            return
        try:
            self._write_file(self.current_file)
        except Exception:
            messagebox.showerror("Save Error", traceback.format_exc())

    def _save_as(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".aerobeam",
            filetypes=[("AeroBeam project","*.aerobeam"),("JSON","*.json")])
        if not path:
            return
        try:
            self._write_file(path)
        except Exception:
            messagebox.showerror("Save Error", traceback.format_exc())
            return
        self.current_file = path
        self.root.title(f"{APP_TITLE}  —  {os.path.basename(path)}")

    # ── Export ────────────────────────────────────────────────────────────────

    def _export_pdf(self):
        if self.analyzer is None:
            messagebox.showinfo("Info","Run analysis first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF","*.pdf")])
        if path:
            try:
                self.analyzer.export_pdf(path)
                self.status_var.set(f"PDF saved: {path}")
            except Exception:
                messagebox.showerror("Export Error", traceback.format_exc())

    def _export_excel(self):
        if self.analyzer is None:
            messagebox.showinfo("Info","Run analysis first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel","*.xlsx")])
        if path:
            try:
                self.analyzer.export_excel(path)
                self.status_var.set(f"Excel saved: {path}")
            except Exception:
                messagebox.showerror("Export Error", traceback.format_exc())

    # ── About ─────────────────────────────────────────────────────────────────

    def _about(self):
        msg = (f"AeroBeam v{VERSION}\n"
               f"Wing Bending & Stress Analysis\n"
               f"for Ultralight & Experimental Aircraft\n\n"
               f"Copyright (c) 2026 Phil Ramer\n"
               f"Released under the MIT License.\n\n"
               f"Divergence speed check included.\n"
               f"Results are for preliminary design only.\n"
               f"Verify all results with a licensed engineer.")
        messagebox.showinfo("About AeroBeam", msg)


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────

def main():
    root = tk.Tk()
    try:
        style = ttk.Style(root)
        if "clam" in style.theme_names():
            style.theme_use("clam")
    except: pass
    app = WingStressGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
