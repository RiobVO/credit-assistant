"""One-shot generator: writes docs/screenshots/architecture.svg.

Manual run, not part of the build pipeline. Kept in scripts/ so the SVG
source-of-truth lives next to other tooling; delete after the visual
upgrade lands if you do not want to keep regenerating.
"""

from __future__ import annotations

import os

W, H = 1400, 1000
lines: list[str] = []
lines.append(
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
    f'width="{W}" height="{H}" '
    f'font-family="Inter, -apple-system, Segoe UI, system-ui, sans-serif">'
)

lines.append("  <defs>")
lines.append('    <linearGradient id="gInterfaces" x1="0" y1="0" x2="0" y2="1">')
lines.append('      <stop offset="0" stop-color="#eff6ff"/>')
lines.append('      <stop offset="1" stop-color="#dbeafe"/>')
lines.append("    </linearGradient>")
lines.append('    <linearGradient id="gApplication" x1="0" y1="0" x2="0" y2="1">')
lines.append('      <stop offset="0" stop-color="#eef2ff"/>')
lines.append('      <stop offset="1" stop-color="#e0e7ff"/>')
lines.append("    </linearGradient>")
lines.append('    <linearGradient id="gDomain" x1="0" y1="0" x2="0" y2="1">')
lines.append('      <stop offset="0" stop-color="#fef3c7"/>')
lines.append('      <stop offset="1" stop-color="#fde68a"/>')
lines.append("    </linearGradient>")
lines.append('    <linearGradient id="gInfra" x1="0" y1="0" x2="0" y2="1">')
lines.append('      <stop offset="0" stop-color="#f8fafc"/>')
lines.append('      <stop offset="1" stop-color="#e2e8f0"/>')
lines.append("    </linearGradient>")
lines.append('    <linearGradient id="gBox" x1="0" y1="0" x2="0" y2="1">')
lines.append('      <stop offset="0" stop-color="#ffffff"/>')
lines.append('      <stop offset="1" stop-color="#f8fafc"/>')
lines.append("    </linearGradient>")
lines.append('    <filter id="shadow" x="-10%" y="-10%" width="120%" height="120%">')
lines.append(
    '      <feDropShadow dx="0" dy="2" stdDeviation="3" '
    'flood-color="#0f172a" flood-opacity="0.08"/>'
)
lines.append("    </filter>")
lines.append(
    '    <marker id="arrowBlue" viewBox="0 0 10 10" refX="9" refY="5" '
    'markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
)
lines.append('      <path d="M0,0 L10,5 L0,10 z" fill="#2563eb"/>')
lines.append("    </marker>")
lines.append(
    '    <marker id="arrowSlate" viewBox="0 0 10 10" refX="9" refY="5" '
    'markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
)
lines.append('      <path d="M0,0 L10,5 L0,10 z" fill="#64748b"/>')
lines.append("    </marker>")
lines.append("  </defs>")

lines.append(f'  <rect width="{W}" height="{H}" fill="#f8fafc"/>')

lines.append(
    '  <text x="60" y="48" font-size="26" font-weight="700" fill="#0f172a">'
    "credit-assistant — Clean Hexagonal Architecture</text>"
)
lines.append(
    '  <text x="60" y="74" font-size="14" fill="#475569">'
    "Dependency direction flows inward: Interfaces → Application → Domain. "
    "Infrastructure implements ports.</text>"
)

LX = 60
LW = W - 2 * LX
LAYER_R = 14
BOX_PAD = 24
BOX_GAP = 24
inner_w = LW - 2 * BOX_PAD


def draw_box(x: int, y: int, w: int, h: int, title: str, sub: str, accent: str = "#1e3a8a") -> None:
    lines.append(
        f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" '
        f'fill="url(#gBox)" stroke="#cbd5e1" stroke-width="1" filter="url(#shadow)"/>'
    )
    lines.append(
        f'  <text x="{x + 16}" y="{y + 28}" font-size="14" font-weight="700" '
        f'fill="{accent}">{title}</text>'
    )
    lines.append(
        f'  <text x="{x + 16}" y="{y + 52}" font-size="12" fill="#475569">{sub}</text>'
    )


# Layer 1: Interfaces
L1_Y, L1_H = 100, 150
lines.append(
    f'  <rect x="{LX}" y="{L1_Y}" width="{LW}" height="{L1_H}" rx="{LAYER_R}" '
    f'fill="url(#gInterfaces)" stroke="#93c5fd" stroke-width="1"/>'
)
lines.append(
    f'  <text x="{LX + 18}" y="{L1_Y + 28}" font-size="13" font-weight="700" '
    f'fill="#1e3a8a" letter-spacing="1.5">INTERFACES · entry points</text>'
)
BOX_Y = L1_Y + 48
box_w1 = (inner_w - 2 * BOX_GAP) // 3
x0 = LX + BOX_PAD
draw_box(x0, BOX_Y, box_w1, 84, "FastAPI routers", "bank · accountant · shared")
draw_box(x0 + box_w1 + BOX_GAP, BOX_Y, box_w1, 84, "Admin CLI", "seed · migrations · smoke")
draw_box(
    x0 + 2 * (box_w1 + BOX_GAP), BOX_Y, box_w1, 84,
    "Next.js 15 App Router", "web/ frontend — RU + UZ",
)

# Layer 2: Application
L2_Y, L2_H = L1_Y + L1_H + 40, 170
lines.append(
    f'  <rect x="{LX}" y="{L2_Y}" width="{LW}" height="{L2_H}" rx="{LAYER_R}" '
    f'fill="url(#gApplication)" stroke="#a5b4fc" stroke-width="1"/>'
)
lines.append(
    f'  <text x="{LX + 18}" y="{L2_Y + 28}" font-size="13" font-weight="700" '
    f'fill="#3730a3" letter-spacing="1.5">APPLICATION · orchestration</text>'
)
BOX2_Y = L2_Y + 48
box_w2 = (inner_w - 3 * BOX_GAP) // 4
x0 = LX + BOX_PAD
draw_box(x0, BOX2_Y, box_w2, 104, "Use cases",
         "build_borrower_snapshot · render_dossier_pdf · authenticate", accent="#3730a3")
draw_box(x0 + box_w2 + BOX_GAP, BOX2_Y, box_w2, 104, "Services",
         "scoring · observations · KPI · readiness", accent="#3730a3")
draw_box(x0 + 2 * (box_w2 + BOX_GAP), BOX2_Y, box_w2, 104, "Ports",
         "AuthnPort · BorrowerRepoPort · PdfReportPort · PiiEncryptorPort", accent="#3730a3")
draw_box(x0 + 3 * (box_w2 + BOX_GAP), BOX2_Y, box_w2, 104, "DTOs",
         "request / response shapes between layers", accent="#3730a3")

# Layer 3: Domain — highlighted
L3_Y, L3_H = L2_Y + L2_H + 40, 160
lines.append(
    f'  <rect x="{LX - 4}" y="{L3_Y - 4}" width="{LW + 8}" height="{L3_H + 8}" '
    f'rx="{LAYER_R + 2}" fill="none" stroke="#d97706" stroke-width="2.5"/>'
)
lines.append(
    f'  <rect x="{LX}" y="{L3_Y}" width="{LW}" height="{L3_H}" rx="{LAYER_R}" '
    f'fill="url(#gDomain)" stroke="#fbbf24" stroke-width="1"/>'
)
lines.append(
    f'  <text x="{LX + 18}" y="{L3_Y + 28}" font-size="13" font-weight="700" '
    f'fill="#78350f" letter-spacing="1.5">DOMAIN · pure business logic</text>'
)
lines.append(
    f'  <text x="{LX + LW - 18}" y="{L3_Y + 28}" font-size="12" font-weight="600" '
    f'fill="#92400e" text-anchor="end">PURE — zero external imports</text>'
)
BOX3_Y = L3_Y + 48
box_w3 = (inner_w - 2 * BOX_GAP) // 3
x0 = LX + BOX_PAD
draw_box(x0, BOX3_Y, box_w3, 94, "Entities",
         "Borrower · FinancialReport · Counterparty · Invoice", accent="#78350f")
draw_box(x0 + box_w3 + BOX_GAP, BOX3_Y, box_w3, 94, "Value objects",
         "INN · Money · period identifiers", accent="#78350f")
draw_box(x0 + 2 * (box_w3 + BOX_GAP), BOX3_Y, box_w3, 94, "24 red-flag rules",
         "financial · counterparty · payment · structural", accent="#78350f")

# Layer 4: Infrastructure
L4_Y, L4_H = L3_Y + L3_H + 40, 200
lines.append(
    f'  <rect x="{LX}" y="{L4_Y}" width="{LW}" height="{L4_H}" rx="{LAYER_R}" '
    f'fill="url(#gInfra)" stroke="#cbd5e1" stroke-width="1"/>'
)
lines.append(
    f'  <text x="{LX + 18}" y="{L4_Y + 28}" font-size="13" font-weight="700" '
    f'fill="#1e293b" letter-spacing="1.5">INFRASTRUCTURE · adapters (implement ports)</text>'
)
BOX4_Y = L4_Y + 48
box_w4 = (inner_w - 5 * BOX_GAP) // 6
x0 = LX + BOX_PAD
infra = [
    ("SQLAlchemy", "models · mappers · Alembic"),
    ("Soliq parsers", "xltx · Excel"),
    ("ESF CSV", "e-invoice adapter"),
    ("WeasyPrint", "RU / UZ PDF renderer"),
    ("Auth", "JWT · LDAP · TOTP · Fernet PII"),
    ("Observability", "logs · metrics · tracing"),
]
for i, (t, s) in enumerate(infra):
    draw_box(x0 + i * (box_w4 + BOX_GAP), BOX4_Y, box_w4, 120, t, s, accent="#1e293b")

# Arrows
mid_x = W / 2


def arrow(x1: float, y1: float, x2: float, y2: float, color: str = "#2563eb",
          marker: str = "arrowBlue", width: float = 2, dash: str | None = None,
          label: str | None = None) -> None:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    lines.append(
        f'  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
        f'stroke-width="{width}"{dash_attr} marker-end="url(#{marker})"/>'
    )
    if label:
        lx = (x1 + x2) / 2
        ly = (y1 + y2) / 2
        approx_w = len(label) * 7 + 14
        lines.append(
            f'  <rect x="{lx - approx_w / 2}" y="{ly - 11}" width="{approx_w}" '
            f'height="16" rx="4" fill="#ffffff" opacity="0.95" stroke="#e2e8f0"/>'
        )
        lines.append(
            f'  <text x="{lx}" y="{ly + 1}" font-size="11" font-weight="600" '
            f'fill="{color}" text-anchor="middle">{label}</text>'
        )


# Interfaces -> Application (center)
arrow(mid_x, L1_Y + L1_H, mid_x, L2_Y - 2, label="depends on")
# Application -> Domain (center)
arrow(mid_x, L2_Y + L2_H, mid_x, L3_Y - 6, label="depends on")
# Infrastructure -> Application (dashed, going UP, label "implements ports")
arrow(mid_x - 220, L4_Y, mid_x - 220, L3_Y + L3_H + 6,
      color="#64748b", marker="arrowSlate", width=1.8, dash="6,4", label="implements ports")
# Infrastructure -> Domain (going UP — Infrastructure depends on Domain entities)
arrow(mid_x + 220, L4_Y, mid_x + 220, L3_Y + L3_H + 6, label="depends on")

# Legend
LEG_Y = H - 60
lines.append(
    f'  <rect x="{LX}" y="{LEG_Y - 22}" width="{LW}" height="42" rx="8" '
    f'fill="#ffffff" stroke="#e2e8f0"/>'
)
lines.append(
    f'  <text x="{LX + 18}" y="{LEG_Y - 4}" font-size="12" font-weight="600" '
    f'fill="#0f172a">Legend</text>'
)
lines.append(
    f'  <line x1="{LX + 100}" y1="{LEG_Y - 8}" x2="{LX + 160}" y2="{LEG_Y - 8}" '
    f'stroke="#2563eb" stroke-width="2" marker-end="url(#arrowBlue)"/>'
)
lines.append(
    f'  <text x="{LX + 172}" y="{LEG_Y - 4}" font-size="12" '
    f'fill="#475569">runtime dependency</text>'
)
lines.append(
    f'  <line x1="{LX + 380}" y1="{LEG_Y - 8}" x2="{LX + 440}" y2="{LEG_Y - 8}" '
    f'stroke="#64748b" stroke-width="1.8" stroke-dasharray="6,4" marker-end="url(#arrowSlate)"/>'
)
lines.append(
    f'  <text x="{LX + 452}" y="{LEG_Y - 4}" font-size="12" fill="#475569">'
    "implements (port → adapter binding)</text>"
)
lines.append(
    f'  <rect x="{LX + 780}" y="{LEG_Y - 17}" width="20" height="14" rx="3" '
    f'fill="none" stroke="#d97706" stroke-width="2"/>'
)
lines.append(
    f'  <text x="{LX + 810}" y="{LEG_Y - 4}" font-size="12" fill="#475569">'
    "Domain — pure layer (zero external imports)</text>"
)

lines.append("</svg>")

os.makedirs("docs/screenshots", exist_ok=True)
with open("docs/screenshots/architecture.svg", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"SVG written: {len(lines)} lines, {sum(len(line) for line in lines)} chars")
