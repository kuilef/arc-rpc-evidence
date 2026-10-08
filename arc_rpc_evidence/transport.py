"""HTTPS requests to a single fixed official preset; no proxy or redirect."""
import json
import math
import time
import urllib.request
from http.client import HTTPException
from typing import Any
from urllib.error import HTTPError, URLError

from .core import MAX_RESPONSE_BYTES, is_hash, quantity, resolve_preset


def reject_constant(value: str) -> Any:
    raise ValueError("Non-JSON numeric constant")


def finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Nonfinite JSON float")
    return number


def unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def parse_payload(payload: bytes, request_id: int) -> dict[str, Any]:
    try:
        value = json.loads(payload, parse_constant=reject_constant, parse_float=finite_float,
                           object_pairs_hook=unique_keys)
    except (ValueError, UnicodeError, RecursionError):
        return {"status": "malformed"}
    if (not isinstance(value, dict) or value.get("jsonrpc") != "2.0"
            or type(value.get("id")) is not int or value["id"] != request_id
            or ("result" in value) == ("error" in value)):
        return {"status": "malformed"}
    if "result" in value:
        return {"status": "ok", "result": value["result"]}
    error = value["error"]
    if not isinstance(error, dict) or type(error.get("code")) is not int:
        return {"status": "malformed"}
    # Provider messages can contain echoed private data; retain only numeric codes.
    return {"status": "rpc-error", "code": error["code"]}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: urllib.request.Request, fp: Any, code: int,
                         msg: str, headers: Any, newurl: str) -> None:
        raise HTTPError(req.full_url, code, "redirect rejected", headers, fp)


def validate_request(method: str, params: list[Any]) -> None:
    valid = False
    if method in ("eth_chainId", "eth_blockNumber"):
        valid = params == []
    elif method in ("eth_getTransactionByHash", "eth_getTransactionReceipt"):
        valid = len(params) == 1 and is_hash(params[0])
    elif method in ("eth_getBlockByNumber", "eth_getBlockByHash"):
        valid = (len(params) == 2 and params[1] is False
                 and (is_hash(params[0]) if method.endswith("Hash") else quantity(params[0]) is not None))
    if not valid:
        raise ValueError("Only bounded chain/head/block/transaction/receipt reads are allowed.")


class HttpTransport:
    def __init__(self, preset: str = "mainnet") -> None:
        self.endpoint = resolve_preset(preset)
        self.sequence = 0
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def call(self, method: str, params: list[Any], timeout: float) -> dict[str, Any]:
        validate_request(method, params)
        if not 0 < timeout <= 5:
            raise ValueError("Socket timeout must be >0 and <=5 seconds.")
        self.sequence += 1
        payload = json.dumps({"jsonrpc": "2.0", "id": self.sequence,
                              "method": method, "params": params}).encode("utf-8")
        # endpoint comes exclusively from the fixed HTTPS preset (tested), never user URLs.
        request = urllib.request.Request(self.endpoint, data=payload, method="POST", headers={  # noqa: S310
            "Content-Type": "application/json", "Accept": "application/json",
            "Accept-Encoding": "identity", "User-Agent": "arc-rpc-evidence/0.1"})
        started = time.monotonic()
        try:
            with self.opener.open(request, timeout=timeout) as response:
                chunks: list[bytes] = []
                size = 0
                while True:
                    if time.monotonic() - started >= timeout:
                        return {"status": "timeout"}
                    chunk = response.read1(min(8192, MAX_RESPONSE_BYTES + 1 - size))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    size += len(chunk)
                    if size > MAX_RESPONSE_BYTES:
                        return {"status": "response-too-large"}
            return parse_payload(b"".join(chunks), self.sequence)
        except HTTPError as error:
            status = "rate-limit" if error.code == 429 else "redirect-rejected" if 300 <= error.code < 400 else "http-error"
            error.close()
            return {"status": status, "http_status": error.code}
        except TimeoutError:
            return {"status": "timeout"}
        except URLError as error:
            return {"status": "timeout" if isinstance(error.reason, TimeoutError) else "network-error"}
        except HTTPException:
            return {"status": "protocol-error"}
        except (OSError, ValueError):
            return {"status": "network-error"}
