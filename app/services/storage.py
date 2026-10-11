from pathlib import Path
import re
from typing import List, Tuple, Optional
import zipfile
from app.core.config import settings


class StorageService:
    @staticmethod
    def get_certificate_path(job_id: str, certificate_id: str) -> Path:
        job_dir = settings.STORAGE_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        return job_dir / f"{certificate_id}.pdf"

    @staticmethod
    def get_job_zip_path(job_id: str) -> Path:
        settings.ZIP_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        return settings.ZIP_STORAGE_DIR / f"certificates_job_{job_id}.zip"

    @staticmethod
    def sanitize_filename(name: str) -> str:
        sanitized = re.sub(r'[\\/*?:"<>|]', "", name).strip()
        sanitized = re.sub(r"\s+", "_", sanitized)
        return sanitized or "certificate"

    @classmethod
    def create_job_zip(
        cls,
        job_id: str,
        certificate_entries: List[Tuple[str, str, Path]],
    ) -> Optional[Path]:
        valid_files = [(name, num, path) for name, num, path in certificate_entries if path.exists()]
        if not valid_files:
            return None

        zip_path = cls.get_job_zip_path(job_id)
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
            used_filenames = set()
            for recipient_name, cert_num, file_path in valid_files:
                base_name = cls.sanitize_filename(recipient_name)
                archive_filename = f"{base_name}_{cert_num or 'cert'}.pdf"
                counter = 1
                while archive_filename in used_filenames:
                    archive_filename = f"{base_name}_{cert_num or 'cert'}_{counter}.pdf"
                    counter += 1

                used_filenames.add(archive_filename)
                zipf.write(file_path, arcname=archive_filename)

        return zip_path
