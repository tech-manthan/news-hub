from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


class PublisherError(RuntimeError):
    pass


def _json_response(response) -> dict:
    try:
        payload = response.json()
    except ValueError as exc:
        raise PublisherError(f"HTTP {response.status_code}: {response.text[:300]}") from exc
    if response.status_code >= 400 or "error" in payload:
        error = payload.get("error", payload)
        raise PublisherError(f"{error.get('message', error)}")
    return payload


class InstagramPublisher:
    def __init__(self, token_file: Path = DATA / "ig_token.json"):
        self.token_file = token_file
        self.version = os.getenv("META_API_VERSION", "v26.0")

    def setup(self) -> dict:
        import requests

        user_token = os.getenv("META_USER_TOKEN", "").strip()
        if not user_token:
            raise PublisherError("Set META_USER_TOKEN in .env before Instagram setup")
        graph = f"https://graph.facebook.com/{self.version}"
        response = requests.get(f"{graph}/me/accounts", params={
            "fields": "name,access_token,instagram_business_account{id,username}", "access_token": user_token,
        }, timeout=30)
        pages = _json_response(response).get("data", [])
        linked = [page for page in pages if page.get("instagram_business_account")]
        if not linked:
            raise PublisherError("No Facebook Page with a linked Instagram Professional account was found")
        page, ig = linked[0], linked[0]["instagram_business_account"]
        credentials = {"page_id": page["id"], "page_name": page["name"], "page_token": page["access_token"], "ig_user_id": ig["id"], "ig_username": ig.get("username")}
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        self.token_file.write_text(json.dumps(credentials, indent=2))
        self.token_file.chmod(0o600)
        return credentials

    def _credentials(self) -> dict:
        if not self.token_file.exists():
            raise PublisherError("Instagram is not set up; run `python publish.py --instagram-setup`")
        return json.loads(self.token_file.read_text())

    def whoami(self) -> dict:
        import requests

        credentials = self._credentials()
        graph = f"https://graph.facebook.com/{self.version}"
        response = requests.get(f"{graph}/{credentials['ig_user_id']}", params={"fields": "username,media_count", "access_token": credentials["page_token"]}, timeout=30)
        user = _json_response(response)
        return {"username": user.get("username"), "page": credentials["page_name"], "media_count": user.get("media_count")}

    def publish_reel(self, video: Path, caption: str, log=print) -> dict:
        import requests

        credentials = self._credentials()
        graph = f"https://graph.facebook.com/{self.version}"
        token, user_id = credentials["page_token"], credentials["ig_user_id"]
        response = requests.post(f"{graph}/{user_id}/media", data={"media_type": "REELS", "upload_type": "resumable", "caption": caption, "share_to_feed": "true", "access_token": token}, timeout=60)
        container = _json_response(response)
        container_id = container["id"]
        log(f"Instagram container {container_id}: uploading {video.stat().st_size / 1e6:.1f} MB")
        upload_url = container.get("uri") or f"https://rupload.facebook.com/ig-api-upload/{self.version}/{container_id}"
        upload = requests.post(upload_url, data=video.read_bytes(), headers={"Authorization": f"OAuth {token}", "offset": "0", "file_size": str(video.stat().st_size), "Content-Type": "application/octet-stream"}, timeout=600)
        _json_response(upload)
        for _ in range(60):
            status = _json_response(requests.get(f"{graph}/{container_id}", params={"fields": "status_code,status", "access_token": token}, timeout=30))
            if status.get("status_code") == "FINISHED":
                break
            if status.get("status_code") in ("ERROR", "EXPIRED"):
                raise PublisherError(f"Instagram processing failed: {status.get('status')}")
            time.sleep(10)
        else:
            raise PublisherError("Instagram processing timed out")
        published = _json_response(requests.post(f"{graph}/{user_id}/media_publish", data={"creation_id": container_id, "access_token": token}, timeout=60))
        info = _json_response(requests.get(f"{graph}/{published['id']}", params={"fields": "permalink,timestamp", "access_token": token}, timeout=30))
        return {"media_id": published["id"], "permalink": info.get("permalink"), "username": credentials.get("ig_username"), "posted_at": info.get("timestamp")}

    def list_comments(self, media_id: str) -> list[dict]:
        import requests
        credentials = self._credentials()
        graph = f"https://graph.facebook.com/{self.version}"
        return _json_response(requests.get(f"{graph}/{media_id}/comments", params={"fields": "id,text", "access_token": credentials["page_token"]}, timeout=30)).get("data", [])

    def reply_to_comment(self, comment_id: str, message: str) -> dict:
        import requests
        credentials = self._credentials()
        graph = f"https://graph.facebook.com/{self.version}"
        return _json_response(requests.post(f"{graph}/{comment_id}/replies", data={"message": message, "access_token": credentials["page_token"]}, timeout=30))


class YouTubePublisher:
    SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly"]

    def __init__(self, client_secret: Path = DATA / "youtube_client_secret.json", token_file: Path = DATA / "yt_token.json"):
        self.client_secret, self.token_file = client_secret, token_file

    def setup(self) -> dict:
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
        except ImportError as exc:
            raise PublisherError("Install YouTube publishing dependencies with `python -m pip install -e '.[publish]'`") from exc
        if not self.client_secret.exists():
            raise PublisherError(f"Download a YouTube OAuth desktop client JSON to {self.client_secret}")
        flow = InstalledAppFlow.from_client_secrets_file(str(self.client_secret), self.SCOPES)
        credentials = flow.run_local_server(port=0)
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        self.token_file.write_text(credentials.to_json())
        self.token_file.chmod(0o600)
        return self.whoami()

    def _credentials(self):
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
        except ImportError as exc:
            raise PublisherError("Install YouTube publishing dependencies with `python -m pip install -e '.[publish]'`") from exc
        if not self.token_file.exists():
            raise PublisherError("YouTube is not set up; run `python publish.py --youtube-setup`")
        credentials = Credentials.from_authorized_user_info(json.loads(self.token_file.read_text()), self.SCOPES)
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            self.token_file.write_text(credentials.to_json())
        return credentials

    def _client(self):
        try:
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise PublisherError("Install YouTube publishing dependencies with `python -m pip install -e '.[publish]'`") from exc
        return build("youtube", "v3", credentials=self._credentials(), cache_discovery=False)

    def whoami(self) -> dict:
        channels = self._client().channels().list(part="snippet,statistics", mine=True).execute().get("items", [])
        if not channels:
            raise PublisherError("YouTube credentials are valid but no channel is linked")
        channel = channels[0]
        return {"channel_id": channel["id"], "title": channel["snippet"]["title"], "subscribers": channel["statistics"].get("subscriberCount"), "video_count": channel["statistics"].get("videoCount")}

    def publish_short(self, video: Path, title: str, description: str, tags: list[str] | None = None, log=print) -> dict:
        try:
            from googleapiclient.http import MediaFileUpload
        except ImportError as exc:
            raise PublisherError("Install YouTube publishing dependencies with `python -m pip install -e '.[publish]'`") from exc
        body = {"snippet": {"title": title[:100], "description": description[:5000], "tags": (tags or [])[:500], "categoryId": "28"}, "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}}
        request = self._client().videos().insert(part="snippet,status", body=body, media_body=MediaFileUpload(str(video), mimetype="video/mp4", chunksize=-1, resumable=True))
        response = None
        log(f"YouTube: uploading {video.stat().st_size / 1e6:.1f} MB")
        while response is None:
            _, response = request.next_chunk()
        video_id = response["id"]
        return {"video_id": video_id, "url": f"https://youtube.com/shorts/{video_id}", "channel": self.whoami()["title"], "posted_at": datetime.now(timezone.utc).isoformat()}

    def list_comments(self, video_id: str) -> list[dict]:
        items = self._client().commentThreads().list(part="snippet", videoId=video_id, maxResults=100, textFormat="plainText").execute().get("items", [])
        return [{"id": item["id"], "text": item["snippet"]["topLevelComment"]["snippet"].get("textDisplay", "")} for item in items]

    def reply_to_comment(self, comment_id: str, message: str) -> dict:
        return self._client().comments().insert(part="snippet", body={"snippet": {"parentId": comment_id, "textOriginal": message}}).execute()
