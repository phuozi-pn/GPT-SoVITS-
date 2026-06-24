"""Generate authorization certificate PDF (REQ-018)."""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO

from fpdf import FPDF

from voice_platform.job.schemas import AuthorizationCertificateResponse


class AuthorizationPdf(FPDF):
    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", size=8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, "Voice Studio - AI synthesis authorization record", align="C")


def _qr_png_bytes(url: str) -> bytes:
    import qrcode

    qr = qrcode.QRCode(version=1, box_size=4, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def build_authorization_pdf(cert: AuthorizationCertificateResponse) -> bytes:
    pdf = AuthorizationPdf()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Voice Authorization Certificate", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", size=11)
    pdf.ln(4)

    if cert.verify_url:
        pdf.set_font("Helvetica", "B", 11)
        pdf.multi_cell(pdf.epw, 6, "Public verification (scan QR or open URL):")
        try:
            qr_buf = BytesIO(_qr_png_bytes(cert.verify_url))
            pdf.image(qr_buf, w=40)
            pdf.ln(2)
        except Exception:
            pass
        pdf.set_font("Helvetica", size=10)
        pdf.set_text_color(0, 80, 160)
        pdf.multi_cell(pdf.epw, 5, cert.verify_url)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(3)

    issued = cert.issued_at.isoformat() if cert.issued_at else "-"
    expires = cert.expires_at.isoformat() if cert.expires_at else "none"

    rows = [
        ("Authorization ID", str(cert.authorization_id)),
        ("Platform", cert.platform),
        ("Voice Title", cert.voice_title[:120]),
        ("License Type", cert.license_type),
        ("Status", cert.status),
        ("Seller User ID", str(cert.seller_user_id)),
        ("Buyer User ID", str(cert.buyer_user_id)),
        ("Voice Version ID", str(cert.voice_version_id)),
        ("Catalog ID", str(cert.catalog_id)),
        ("Char Quota Total", str(cert.char_quota_total)),
        ("Char Quota Used", str(cert.char_quota_used)),
        ("Issued At (UTC)", issued),
        ("Expires At (UTC)", expires),
        ("Signature (HMAC-SHA256)", cert.signature),
        ("Verify Path", f"/api/v1/authorizations/{cert.authorization_id}/verify"),
    ]

    for label, value in rows:
        pdf.set_font("Helvetica", "B", 10)
        pdf.multi_cell(pdf.epw, 6, f"{label}:")
        pdf.set_font("Helvetica", size=10)
        pdf.multi_cell(pdf.epw, 5, value)
        pdf.ln(2)

    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(
        pdf.epw,
        5,
        "This document certifies a mock-marketplace purchase authorization. "
        "Third parties may verify status via the public verify API.",
    )
    pdf.ln(2)
    pdf.set_font("Helvetica", size=8)
    pdf.cell(0, 5, f"Generated at {datetime.now(timezone.utc).isoformat()}Z", new_x="LMARGIN", new_y="NEXT")

    buf = BytesIO()
    pdf.output(buf)
    return buf.getvalue()
