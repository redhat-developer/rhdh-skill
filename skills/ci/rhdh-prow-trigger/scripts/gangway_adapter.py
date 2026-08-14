#!/usr/bin/env python3
"""Credential-owning OpenShift CI Gangway adapter.

The public workflow passes only a kubeconfig path and request data. This module
retrieves the native ``oc`` credential transiently, authenticates the request,
and returns credential-free response data.
"""

from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.request
from typing import Any

GANGWAY_URL = "https://gangway-ci.apps.ci.l2s4.p1.openshiftapps.com/v1/executions"


class GangwayAdapterError(RuntimeError):
    """A credential-opaque failure from the Gangway adapter."""


class GangwayAdapter:
    """Authenticate and execute Gangway requests behind a credential-free interface."""

    def __init__(self, kubeconfig: str, *, executable: str = "oc") -> None:
        self.kubeconfig = kubeconfig
        self.executable = executable

    def _token(self) -> str:
        result = subprocess.run(
            [self.executable, "--kubeconfig", self.kubeconfig, "whoami", "-t"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            shell=False,
        )
        token = result.stdout.strip()
        if result.returncode != 0 or not token:
            raise GangwayAdapterError("OpenShift CI authentication is missing or expired")
        return token

    def _request(
        self, url: str, *, method: str = "GET", payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {self._token()}",
                "Content-Type": "application/json",
                "User-Agent": "rhdh-skills",
            },
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            raise GangwayAdapterError(f"Gangway returned HTTP {error.code}") from error
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as error:
            raise GangwayAdapterError(f"Gangway request failed: {error}") from error

    def trigger(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request(GANGWAY_URL, method="POST", payload=payload)

    def status(self, job_id: str) -> dict[str, Any]:
        return self._request(f"{GANGWAY_URL}/{job_id}")
