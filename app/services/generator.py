from pathlib import Path
from typing import Optional, Dict, Any
import math
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.pdfgen import canvas


class CertificateGenerationError(Exception):
    pass


class CertificateGenerator:
    PAGE_WIDTH, PAGE_HEIGHT = landscape(letter)

    COLOR_PRIMARY = colors.HexColor("#0F172A")
    COLOR_SECONDARY = colors.HexColor("#1E293B")
    COLOR_ACCENT = colors.HexColor("#B45309")
    COLOR_ACCENT_LIGHT = colors.HexColor("#F59E0B")
    COLOR_MUTED = colors.HexColor("#64748B")
    COLOR_BG_TINT = colors.HexColor("#F8FAFC")

    @classmethod
    def generate_pdf(
        cls,
        output_path: Path,
        recipient_name: str,
        event_name: str,
        issue_date: str,
        issuer_name: str,
        certificate_title: str = "Certificate of Completion",
        description: Optional[str] = None,
        certificate_number: Optional[str] = None,
        recipient_identifier: Optional[str] = None,
        custom_attributes: Optional[Dict[str, Any]] = None,
    ) -> Path:
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            c = canvas.Canvas(str(output_path), pagesize=landscape(letter))
            w = cls.PAGE_WIDTH
            h = cls.PAGE_HEIGHT

            c.setFillColor(cls.COLOR_BG_TINT)
            c.rect(0, 0, w, h, fill=1, stroke=0)

            cls._draw_borders_and_corners(c, w, h)

            c.setFillColor(cls.COLOR_MUTED)
            c.setFont("Helvetica-Bold", 10)
            c.drawCentredString(w / 2.0, h - 85, issuer_name.upper())

            c.setFillColor(cls.COLOR_PRIMARY)
            c.setFont("Helvetica-Bold", 26)
            c.drawCentredString(w / 2.0, h - 125, certificate_title.upper())

            c.setStrokeColor(cls.COLOR_ACCENT)
            c.setLineWidth(1.5)
            c.line(w / 2.0 - 120, h - 140, w / 2.0 + 120, h - 140)
            cls._draw_diamond(c, w / 2.0, h - 140, 5, cls.COLOR_ACCENT)

            c.setFillColor(cls.COLOR_MUTED)
            c.setFont("Helvetica", 11)
            c.drawCentredString(w / 2.0, h - 175, "THIS CERTIFICATE IS PROUDLY PRESENTED TO")

            c.setFillColor(cls.COLOR_PRIMARY)
            c.setFont("Times-BoldItalic", 32)
            c.drawCentredString(w / 2.0, h - 225, recipient_name)

            c.setStrokeColor(cls.COLOR_ACCENT_LIGHT)
            c.setLineWidth(1.0)
            c.line(w / 2.0 - 160, h - 238, w / 2.0 + 160, h - 238)

            c.setFillColor(cls.COLOR_SECONDARY)
            c.setFont("Helvetica", 12)
            desc_text = description or "For successful participation and distinguished performance in"
            c.drawCentredString(w / 2.0, h - 275, desc_text)

            c.setFillColor(cls.COLOR_PRIMARY)
            c.setFont("Helvetica-Bold", 17)
            c.drawCentredString(w / 2.0, h - 305, event_name)

            meta_items = []
            if recipient_identifier:
                meta_items.append(f"ID: {recipient_identifier}")
            if custom_attributes:
                for k, v in custom_attributes.items():
                    meta_items.append(f"{k.capitalize()}: {v}")

            if meta_items:
                c.setFillColor(cls.COLOR_MUTED)
                c.setFont("Helvetica-Oblique", 9)
                meta_line = "  •  ".join(meta_items)
                c.drawCentredString(w / 2.0, h - 335, meta_line)

            cls._draw_gold_seal(c, w / 2.0, 135)

            c.setStrokeColor(cls.COLOR_MUTED)
            c.setLineWidth(0.8)
            c.line(100, 135, 240, 135)
            c.setFillColor(cls.COLOR_PRIMARY)
            c.setFont("Helvetica-Bold", 11)
            c.drawCentredString(170, 142, issue_date)
            c.setFillColor(cls.COLOR_MUTED)
            c.setFont("Helvetica", 9)
            c.drawCentredString(170, 120, "DATE OF ISSUANCE")

            c.setStrokeColor(cls.COLOR_MUTED)
            c.setLineWidth(0.8)
            c.line(w - 240, 135, w - 100, 135)
            c.setFillColor(colors.HexColor("#1E3A8A"))
            c.setFont("Times-Italic", 16)
            c.drawCentredString(w - 170, 145, issuer_name)
            c.setFillColor(cls.COLOR_MUTED)
            c.setFont("Helvetica", 9)
            c.drawCentredString(w - 170, 120, "AUTHORIZED SIGNATORY")

            if certificate_number:
                c.setFillColor(cls.COLOR_MUTED)
                c.setFont("Helvetica", 8)
                c.drawString(45, 38, f"Certificate ID: {certificate_number}")
                c.drawRightString(w - 45, 38, "Verified Digital Credential")

            c.save()
            return output_path
        except Exception as exc:
            raise CertificateGenerationError(f"Failed to generate certificate PDF: {str(exc)}") from exc

    @classmethod
    def _draw_borders_and_corners(cls, c: canvas.Canvas, w: float, h: float) -> None:
        c.setStrokeColor(cls.COLOR_PRIMARY)
        c.setLineWidth(3.0)
        c.rect(30, 30, w - 60, h - 60, fill=0, stroke=1)

        c.setStrokeColor(cls.COLOR_ACCENT)
        c.setLineWidth(1.0)
        c.rect(36, 36, w - 72, h - 72, fill=0, stroke=1)

        corner_inset = 40
        corner_size = 12
        for cx in [corner_inset, w - corner_inset - corner_size]:
            for cy in [corner_inset, h - corner_inset - corner_size]:
                c.setFillColor(cls.COLOR_ACCENT)
                c.rect(cx, cy, corner_size, corner_size, fill=1, stroke=0)
                c.setFillColor(cls.COLOR_PRIMARY)
                c.rect(cx + 3, cy + 3, corner_size - 6, corner_size - 6, fill=1, stroke=0)

    @classmethod
    def _draw_diamond(cls, c: canvas.Canvas, x: float, y: float, size: float, color: colors.Color) -> None:
        c.setFillColor(color)
        p = c.beginPath()
        p.moveTo(x, y + size)
        p.lineTo(x + size, y)
        p.lineTo(x, y - size)
        p.lineTo(x - size, y)
        p.close()
        c.drawPath(p, fill=1, stroke=0)

    @classmethod
    def _draw_gold_seal(cls, c: canvas.Canvas, cx: float, cy: float) -> None:
        c.setFillColor(cls.COLOR_ACCENT)
        r1 = c.beginPath()
        r1.moveTo(cx - 15, cy - 10)
        r1.lineTo(cx - 28, cy - 48)
        r1.lineTo(cx - 18, cy - 42)
        r1.lineTo(cx - 8, cy - 48)
        r1.lineTo(cx, cy - 10)
        r1.close()
        c.drawPath(r1, fill=1, stroke=0)

        r2 = c.beginPath()
        r2.moveTo(cx, cy - 10)
        r2.lineTo(cx + 8, cy - 48)
        r2.lineTo(cx + 18, cy - 42)
        r2.lineTo(cx + 28, cy - 48)
        r2.lineTo(cx + 15, cy - 10)
        r2.close()
        c.drawPath(r2, fill=1, stroke=0)

        c.setFillColor(cls.COLOR_ACCENT)
        num_teeth = 24
        outer_r = 30
        inner_r = 26
        star = c.beginPath()
        for i in range(num_teeth * 2):
            r = outer_r if i % 2 == 0 else inner_r
            angle = i * (math.pi / num_teeth)
            px = cx + r * math.cos(angle)
            py = cy + r * math.sin(angle)
            if i == 0:
                star.moveTo(px, py)
            else:
                star.lineTo(px, py)
        star.close()
        c.drawPath(star, fill=1, stroke=0)

        c.setFillColor(cls.COLOR_ACCENT_LIGHT)
        c.circle(cx, cy, 22, fill=1, stroke=0)

        c.setStrokeColor(colors.white)
        c.setLineWidth(1.0)
        c.circle(cx, cy, 18, fill=0, stroke=1)

        cls._draw_diamond(c, cx, cy, 7, colors.white)
