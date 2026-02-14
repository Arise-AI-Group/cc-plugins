"""AContext API client for sessions, disk, skills, and sandboxes."""

import requests
from typing import Optional, Any
from pathlib import Path
import tempfile


class AContextClient:
    """Client for the AContext REST API."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })

    def _url(self, path: str) -> str:
        return f"{self.base_url}/api/v1{path}"

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        r = self.session.get(self._url(path), params=params)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, json: Optional[dict] = None) -> dict:
        r = self.session.post(self._url(path), json=json)
        r.raise_for_status()
        return r.json()

    def _delete(self, path: str) -> dict:
        r = self.session.delete(self._url(path))
        r.raise_for_status()
        return r.json()

    def _put(self, path: str, json: Optional[dict] = None) -> dict:
        r = self.session.put(self._url(path), json=json)
        r.raise_for_status()
        return r.json()

    def _patch(self, path: str, json: Optional[dict] = None) -> dict:
        r = self.session.patch(self._url(path), json=json)
        r.raise_for_status()
        return r.json()

    def _post_multipart(self, path: str, data: dict, files: dict) -> dict:
        headers = {"Authorization": self.session.headers["Authorization"]}
        r = requests.post(self._url(path), data=data, files=files, headers=headers)
        r.raise_for_status()
        return r.json()

    # === Sessions ===

    def list_sessions(self) -> dict:
        return self._get("/session")

    def create_session(self, name: Optional[str] = None) -> dict:
        payload = {}
        if name:
            payload["configs"] = {"name": name}
        return self._post("/session", payload)

    def delete_session(self, session_id: str) -> dict:
        return self._delete(f"/session/{session_id}")

    def get_session_configs(self, session_id: str) -> dict:
        return self._get(f"/session/{session_id}/configs")

    def update_session_configs(self, session_id: str, configs: dict) -> dict:
        return self._put(f"/session/{session_id}/configs", {"configs": configs})

    def get_messages(
        self,
        session_id: str,
        limit_tokens: Optional[int] = None,
        format: str = "openai",
    ) -> dict:
        params = {"format": format}
        if limit_tokens is not None:
            params["limit_tokens"] = limit_tokens
        return self._get(f"/session/{session_id}/messages", params)

    def store_message(
        self,
        session_id: str,
        role: str,
        content: str,
        format: str = "openai",
        meta: Optional[dict] = None,
    ) -> dict:
        payload: dict[str, Any] = {
            "format": format,
            "blob": {"role": role, "content": content},
        }
        if meta:
            payload["meta"] = meta
        return self._post(f"/session/{session_id}/messages", payload)

    def flush_session(self, session_id: str) -> dict:
        return self._post(f"/session/{session_id}/flush")

    def get_token_counts(self, session_id: str) -> dict:
        return self._get(f"/session/{session_id}/token_counts")

    def get_tasks(self, session_id: str) -> dict:
        return self._get(f"/session/{session_id}/task")

    # === Disk ===

    def list_disks(self) -> dict:
        return self._get("/disk")

    def create_disk(self) -> dict:
        return self._post("/disk")

    def delete_disk(self, disk_id: str) -> dict:
        return self._delete(f"/disk/{disk_id}")

    def list_artifacts(self, disk_id: str, path: str = "/") -> dict:
        return self._get(f"/disk/{disk_id}/artifact/ls", {"path": path})

    def get_artifact(
        self, disk_id: str, file_path: str, with_content: bool = True
    ) -> dict:
        return self._get(
            f"/disk/{disk_id}/artifact",
            {"file_path": file_path, "with_content": str(with_content).lower()},
        )

    def upload_artifact(
        self, disk_id: str, file_path: str, content: str, meta: Optional[dict] = None
    ) -> dict:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=Path(file_path).suffix, delete=False
        ) as f:
            f.write(content)
            f.flush()
            tmp_path = f.name

        try:
            data = {"file_path": file_path}
            if meta:
                import json
                data["meta"] = json.dumps(meta)
            with open(tmp_path, "rb") as fh:
                files = {"file": (Path(file_path).name, fh)}
                return self._post_multipart(
                    f"/disk/{disk_id}/artifact", data=data, files=files
                )
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def delete_artifact(self, disk_id: str, file_path: str) -> dict:
        return self._delete(
            f"/disk/{disk_id}/artifact?file_path={file_path}"
        )

    def glob_artifacts(self, disk_id: str, pattern: str) -> dict:
        return self._get(f"/disk/{disk_id}/artifact/glob", {"pattern": pattern})

    def grep_artifacts(self, disk_id: str, pattern: str) -> dict:
        return self._get(f"/disk/{disk_id}/artifact/grep", {"pattern": pattern})

    # === Agent Skills ===

    def list_skills(self) -> dict:
        return self._get("/agent_skills")

    def get_skill(self, skill_id: str) -> dict:
        return self._get(f"/agent_skills/{skill_id}")

    def create_skill(self, name: str, description: str, meta: Optional[dict] = None) -> dict:
        payload: dict[str, Any] = {"name": name, "description": description}
        if meta:
            payload["meta"] = meta
        return self._post("/agent_skills", payload)

    def delete_skill(self, skill_id: str) -> dict:
        return self._delete(f"/agent_skills/{skill_id}")

    # === Health ===

    def health(self) -> dict:
        r = self.session.get(f"{self.base_url}/health")
        r.raise_for_status()
        return r.json()
