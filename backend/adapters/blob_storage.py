"""
Durable private resume storage adapter.
Supports Azure Blob Storage with automatic fallback to durable local filesystem storage.
Ensures session-isolated, non-public storage with opaque identifiers.
"""

import os
import re
import logging
from typing import Optional, Tuple
from backend.config import settings

logger = logging.getLogger("safeapply.blob_storage")


class BlobStorageAdapter:
    _blob_service_client = None
    _container_initialized = False

    @classmethod
    def _get_blob_client(cls):
        conn_str = settings.azure_storage_connection_string.strip()
        if not conn_str:
            return None

        if cls._blob_service_client is None:
            try:
                from azure.storage.blob import BlobServiceClient
                cls._blob_service_client = BlobServiceClient.from_connection_string(conn_str)
            except Exception as exc:
                logger.warning(f"Failed to initialize Azure BlobServiceClient: {exc}. Falling back to local storage.")
                return None

        if not cls._container_initialized and cls._blob_service_client:
            try:
                container_client = cls._blob_service_client.get_container_client(settings.azure_storage_container)
                if not container_client.exists():
                    cls._blob_service_client.create_container(settings.azure_storage_container)
                cls._container_initialized = True
            except Exception as exc:
                logger.warning(f"Could not verify/create Azure Blob container: {exc}")

        return cls._blob_service_client

    @classmethod
    def upload_resume(
        cls, user_id: str, filename: str, content: bytes, content_type: str
    ) -> Tuple[str, str]:
        """
        Upload resume bytes to Azure Blob Storage or private local storage.
        Returns: (opaque_blob_id, sanitized_filename)
        """
        clean_name = re.sub(r"[^\w\.-]", "_", os.path.basename(filename))
        safe_user = re.sub(r"[^\w]", "_", user_id)[:32]
        blob_name = f"resumes/{safe_user}/{clean_name}"

        blob_svc = cls._get_blob_client()
        if blob_svc:
            try:
                from azure.storage.blob import ContentSettings
                container = blob_svc.get_container_client(settings.azure_storage_container)
                blob_client = container.get_blob_client(blob_name)
                blob_client.upload_blob(
                    content,
                    overwrite=True,
                    content_settings=ContentSettings(content_type=content_type),
                    metadata={"user_id": user_id, "original_filename": clean_name},
                )
                opaque_ref = f"azure-blob://{settings.azure_storage_container}/{blob_name}"
                return opaque_ref, clean_name
            except Exception as exc:
                logger.error(f"Azure Blob upload failed ({exc}), falling back to local storage.")

        # Local fallback
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        upload_dir = os.path.join(project_root, settings.uploads_dir, safe_user)
        os.makedirs(upload_dir, exist_ok=True)
        local_path = os.path.abspath(os.path.join(upload_dir, clean_name))

        with open(local_path, "wb") as f:
            f.write(content)

        opaque_ref = f"local-blob://{safe_user}/{clean_name}"
        return opaque_ref, clean_name

    @classmethod
    def download_resume(cls, opaque_ref: str, user_id: str) -> Optional[Tuple[bytes, str, str]]:
        """
        Download resume bytes. Verifies session ownership based on path/metadata.
        Returns: (content_bytes, filename, content_type) or None if not found.
        """
        if not opaque_ref:
            return None

        safe_user = re.sub(r"[^\w]", "_", user_id)[:32]

        if opaque_ref.startswith("azure-blob://"):
            blob_svc = cls._get_blob_client()
            if blob_svc:
                try:
                    # Strip azure-blob://container/
                    prefix = f"azure-blob://{settings.azure_storage_container}/"
                    blob_name = opaque_ref[len(prefix):] if opaque_ref.startswith(prefix) else opaque_ref.split("/", 3)[-1]
                    
                    # Security check: verify user prefix
                    if not blob_name.startswith(f"resumes/{safe_user}/"):
                        logger.warning(f"Denied unauthorized blob download attempt across sessions: {blob_name}")
                        return None

                    container = blob_svc.get_container_client(settings.azure_storage_container)
                    blob_client = container.get_blob_client(blob_name)
                    data = blob_client.download_blob().readall()
                    props = blob_client.get_blob_properties()
                    ctype = props.content_settings.content_type or "application/octet-stream"
                    fname = os.path.basename(blob_name)
                    return data, fname, ctype
                except Exception as exc:
                    logger.error(f"Error downloading from Azure Blob Storage: {exc}")
                    return None

        # Local fallback
        clean_name = os.path.basename(opaque_ref)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        local_path = os.path.join(project_root, settings.uploads_dir, safe_user, clean_name)

        if not os.path.exists(local_path):
            # Also check old flat uploads_dir pattern
            flat_path = os.path.join(project_root, settings.uploads_dir, f"resume_{safe_user}_{clean_name}")
            if os.path.exists(flat_path):
                local_path = flat_path
            else:
                return None

        try:
            with open(local_path, "rb") as f:
                content = f.read()
            ext = os.path.splitext(clean_name)[1].lower()
            ctype = "application/pdf" if ext == ".pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document" if ext == ".docx" else "text/plain"
            return content, clean_name, ctype
        except OSError as exc:
            logger.error(f"Error reading local resume file: {exc}")
            return None

    @classmethod
    def delete_resume(cls, opaque_ref: str, user_id: str) -> bool:
        """Permanently delete resume from Azure Blob Storage or local storage."""
        if not opaque_ref:
            return False

        safe_user = re.sub(r"[^\w]", "_", user_id)[:32]
        deleted = False

        if opaque_ref.startswith("azure-blob://"):
            blob_svc = cls._get_blob_client()
            if blob_svc:
                try:
                    prefix = f"azure-blob://{settings.azure_storage_container}/"
                    blob_name = opaque_ref[len(prefix):] if opaque_ref.startswith(prefix) else opaque_ref.split("/", 3)[-1]
                    container = blob_svc.get_container_client(settings.azure_storage_container)
                    blob_client = container.get_blob_client(blob_name)
                    if blob_client.exists():
                        blob_client.delete_blob()
                        deleted = True
                except Exception as exc:
                    logger.error(f"Error deleting Azure Blob: {exc}")

        # Clean local storage as well
        clean_name = os.path.basename(opaque_ref)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        local_path = os.path.join(project_root, settings.uploads_dir, safe_user, clean_name)
        if os.path.exists(local_path):
            try:
                os.remove(local_path)
                deleted = True
            except OSError:
                pass

        flat_path = os.path.join(project_root, settings.uploads_dir, f"resume_{safe_user}_{clean_name}")
        if os.path.exists(flat_path):
            try:
                os.remove(flat_path)
                deleted = True
            except OSError:
                pass

        return deleted

    @classmethod
    def purge_user_resumes(cls, user_id: str) -> int:
        """Delete all resume files/blobs belonging to this session."""
        safe_user = re.sub(r"[^\w]", "_", user_id)[:32]
        count = 0

        # Azure Blob purge
        blob_svc = cls._get_blob_client()
        if blob_svc:
            try:
                container = blob_svc.get_container_client(settings.azure_storage_container)
                blobs = container.list_blobs(name_starts_with=f"resumes/{safe_user}/")
                for b in blobs:
                    container.delete_blob(b.name)
                    count += 1
            except Exception as exc:
                logger.error(f"Error purging Azure blobs for {user_id}: {exc}")

        # Local storage purge
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        user_dir = os.path.join(project_root, settings.uploads_dir, safe_user)
        if os.path.isdir(user_dir):
            try:
                import shutil
                shutil.rmtree(user_dir, ignore_errors=True)
                count += 1
            except OSError:
                pass

        # Also purge any flat files
        upload_root = os.path.join(project_root, settings.uploads_dir)
        if os.path.isdir(upload_root):
            for fname in os.listdir(upload_root):
                if fname.startswith(f"resume_{safe_user}"):
                    try:
                        os.remove(os.path.join(upload_root, fname))
                        count += 1
                    except OSError:
                        pass

        return count
