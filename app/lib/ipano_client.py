import http.client
import builtins
import json
import mimetypes
import os
import ssl
import uuid
from pathlib import Path
from urllib.parse import urlparse


class IPanoError(Exception):
    pass


def _tr(text):
    return getattr(builtins, '_', lambda value: value)(text)


class IPanoClient:
    def __init__(self, base_url='https://ipano.ru', timeout=60):
        self.base_url = (base_url or 'https://ipano.ru').strip().rstrip('/')
        if not self.base_url.startswith(('http://', 'https://')):
            self.base_url = 'https://' + self.base_url
        self.timeout = timeout
        self._parsed = urlparse(self.base_url)

    def login(self, login, password):
        data = self.post_form('/api/users/login', {
            'login': login,
            'passw': password,
        })
        if not data.get('ok'):
            raise IPanoError(data.get('message') or _tr('Authorization failed'))
        key = data.get('key') or ''
        if not key:
            raise IPanoError(_tr('Authorization key was not returned'))
        return key

    def projects(self, key):
        data = self.post_form('/api/projects/get_all', {'key': key})
        self._raise_for_api_error(data)
        return data.get('result') or []

    def add_project(self, key, name):
        data = self.post_form('/api/projects/add', {'key': key, 'name': name})
        if data.get('error') or data.get('ok') is False:
            raise IPanoError(data.get('message') or _tr('Could not create project'))
        pk = data.get('pk')
        if not pk:
            projects = self.projects(key)
            for project in projects:
                if project.get('title') == name:
                    return project.get('pk')
            raise IPanoError(_tr('Project id was not returned'))
        return pk

    def upload_pano(self, key, project_pk, file_path, progress=None):
        data = self.post_multipart(
            '/api/pano/add',
            fields={'key': key, 'project': project_pk},
            files=[('file', file_path)],
            progress=progress,
        )
        self._raise_for_api_error(data)
        return data

    def post_form(self, path, fields):
        body = '&'.join(
            f'{_quote(str(k))}={_quote(str(v))}' for k, v in (fields or {}).items()
        ).encode('utf-8')
        return self._request_json(
            'POST',
            path,
            body=body,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
                'Content-Length': str(len(body)),
            },
        )

    def post_multipart(self, path, fields, files, progress=None):
        boundary = '----PanoPatcher' + uuid.uuid4().hex
        parts = []
        total = 0
        for name, value in (fields or {}).items():
            raw = (
                f'--{boundary}\r\n'
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                f'{value}\r\n'
            ).encode('utf-8')
            parts.append(('bytes', raw))
            total += len(raw)

        for field_name, file_path in files:
            path_obj = Path(file_path)
            filename = path_obj.name
            content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
            header = (
                f'--{boundary}\r\n'
                f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'
                f'Content-Type: {content_type}\r\n\r\n'
            ).encode('utf-8')
            footer = b'\r\n'
            size = path_obj.stat().st_size
            parts.append(('bytes', header))
            parts.append(('file', path_obj, size))
            parts.append(('bytes', footer))
            total += len(header) + size + len(footer)

        closing = f'--{boundary}--\r\n'.encode('utf-8')
        parts.append(('bytes', closing))
        total += len(closing)

        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'Content-Length': str(total),
        }
        conn = self._connection()
        sent = 0
        try:
            conn.putrequest('POST', self._url(path))
            for key, value in headers.items():
                conn.putheader(key, value)
            conn.endheaders()
            for part in parts:
                if part[0] == 'bytes':
                    chunk = part[1]
                    conn.send(chunk)
                    sent += len(chunk)
                    if progress:
                        progress(sent, total)
                    continue

                file_path = part[1]
                with open(file_path, 'rb') as fh:
                    while True:
                        chunk = fh.read(1024 * 512)
                        if not chunk:
                            break
                        conn.send(chunk)
                        sent += len(chunk)
                        if progress:
                            progress(sent, total)
            response = conn.getresponse()
            data = response.read()
            return self._decode_json(response.status, data)
        finally:
            conn.close()

    def _request_json(self, method, path, body, headers):
        conn = self._connection()
        try:
            conn.request(method, self._url(path), body=body, headers=headers)
            response = conn.getresponse()
            data = response.read()
            return self._decode_json(response.status, data)
        finally:
            conn.close()

    def _connection(self):
        port = self._parsed.port
        host = self._parsed.hostname
        if self._parsed.scheme == 'https':
            return http.client.HTTPSConnection(host, port=port, timeout=self.timeout, context=ssl.create_default_context())
        return http.client.HTTPConnection(host, port=port, timeout=self.timeout)

    def _url(self, path):
        base_path = (self._parsed.path or '').rstrip('/')
        return base_path + '/' + str(path or '').lstrip('/')

    def _decode_json(self, status, data):
        text = data.decode('utf-8', errors='replace')
        try:
            payload = json.loads(text)
        except Exception:
            payload = {}
        if status >= 400:
            raise IPanoError(self._payload_message(payload) or f'HTTP {status}')
        return payload

    def _raise_for_api_error(self, payload):
        if not isinstance(payload, dict):
            return
        if payload.get('error') or payload.get('ok') is False:
            raise IPanoError(self._payload_message(payload) or _tr('Server returned an error'))

    def _payload_message(self, payload):
        if not isinstance(payload, dict):
            return ''
        for key in ('message', 'error', 'detail', 'errors'):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ''


def _quote(value):
    from urllib.parse import quote_plus
    return quote_plus(value)
