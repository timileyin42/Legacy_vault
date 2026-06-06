"""PDF rendering for downloadable succession reports (screen 21 "Download PDF").

Uses fpdf2 (pure-Python) so there is no native/system dependency. Text is
sanitised to the core font's latin-1 range to avoid encoding errors on names
with characters outside it.
"""

from fpdf import FPDF

INDIGO = (45, 35, 120)
DARK = (20, 28, 40)
MUTED = (90, 100, 115)
LINE = (210, 215, 225)


def _s(value: object) -> str:
    return str(value if value is not None else "").encode("latin-1", "replace").decode("latin-1")


class _ReportPDF(FPDF):
    def header(self) -> None:
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(*INDIGO)
        self.cell(0, 10, "LegacyVault", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*MUTED)
        self.cell(0, 6, "Legacy Succession Report", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        self.set_draw_color(*LINE)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*MUTED)
        self.cell(0, 10, "Store once. Protect forever.  -  Page " + str(self.page_no()), align="C")

    def section(self, title: str) -> None:
        self.ln(2)
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*DARK)
        self.cell(0, 8, _s(title), new_x="LMARGIN", new_y="NEXT")

    def field(self, label: str, value: str) -> None:
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*MUTED)
        self.cell(45, 7, _s(label))
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*DARK)
        self.multi_cell(0, 7, _s(value), new_x="LMARGIN", new_y="NEXT")


def render_succession_report_pdf(report: dict) -> bytes:
    """Render a succession-report payload (model_dump of SuccessionReportResponse) to PDF bytes."""
    pdf = _ReportPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    pdf.field("Reference", report.get("reference", ""))
    pdf.field("Estate of", report.get("decedent_name", ""))
    pdf.field("Status", str(report.get("status", "")).replace("_", " ").title())
    pdf.field("Integrity hash", report.get("content_hash", ""))
    pdf.field("Generated", report.get("generated_at", ""))

    pdf.section("Asset transfer summary")
    assets = report.get("asset_transfer_summary", [])
    if assets:
        for asset in assets:
            value = asset.get("value_estimate")
            value_label = f"{value:,.2f} {asset.get('currency', '')}" if value is not None else "-"
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*DARK)
            pdf.multi_cell(
                0, 7, _s(f"- {asset.get('name', '')} ({asset.get('category', '')}): {value_label}"),
                new_x="LMARGIN", new_y="NEXT",
            )
    else:
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(*MUTED)
        pdf.cell(0, 7, "No assets catalogued.", new_x="LMARGIN", new_y="NEXT")

    pdf.section("Distribution logic")
    distribution = report.get("distribution", [])
    if distribution:
        for entry in distribution:
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*DARK)
            pdf.multi_cell(
                0, 7,
                _s(f"- {entry.get('full_name', '')} ({entry.get('relationship', '')}): "
                   f"{entry.get('allocation_percent', 0)}%"),
                new_x="LMARGIN", new_y="NEXT",
            )
    else:
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(*MUTED)
        pdf.cell(0, 7, "No beneficiaries designated.", new_x="LMARGIN", new_y="NEXT")

    final_message = report.get("final_message")
    if final_message:
        pdf.section("Final message")
        pdf.set_font("Helvetica", "I", 11)
        pdf.set_text_color(*DARK)
        pdf.multi_cell(0, 7, _s(final_message), new_x="LMARGIN", new_y="NEXT")

    output = pdf.output()
    return bytes(output)
