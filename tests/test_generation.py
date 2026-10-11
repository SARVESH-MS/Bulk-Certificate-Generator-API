from pathlib import Path
import tempfile
from app.services.generator import CertificateGenerator


def test_certificate_pdf_rendering():
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_path = Path(tmp_dir) / "output.pdf"
        result_path = CertificateGenerator.generate_pdf(
            output_path=out_path,
            recipient_name="Eleanor Vance",
            event_name="Quantum Computing Symposium",
            issue_date="October 11, 2026",
            issuer_name="Global Science Institute",
            certificate_title="Certificate of Merit",
            description="For exceptional research paper contribution.",
            certificate_number="CERT-2026-TEST-9999",
            recipient_identifier="QC-8871",
            custom_attributes={"Division": "Quantum Hardware", "Score": "99.4%"},
        )

        assert result_path.exists()
        assert result_path.stat().st_size > 1000

        with open(result_path, "rb") as f:
            header = f.read(5)
            assert header == b"%PDF-"
