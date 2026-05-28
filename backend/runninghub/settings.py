import os

from .provider import (
    preserve_runninghub_hidden_overrides,
    runninghub_model_headers,
    runninghub_models_url,
    runninghub_wallet_key_env,
)


def apply_runninghub_provider_payload(provider, payload, env_updates):
    if provider.get("id") != "runninghub":
        return provider
    provider = preserve_runninghub_hidden_overrides(provider)
    wallet_env = runninghub_wallet_key_env()
    if getattr(payload, "clear_wallet_key", False):
        env_updates[wallet_env] = ""
    elif getattr(payload, "wallet_api_key", None) is not None and payload.wallet_api_key.strip():
        env_updates[wallet_env] = payload.wallet_api_key.strip()
    provider["protocol"] = "runninghub"
    return provider


def saved_runninghub_api_key(provider_id, provider_key_env):
    if provider_id != "runninghub":
        return ""
    return os.getenv(runninghub_wallet_key_env(), "") or os.getenv(provider_key_env(provider_id), "")


def runninghub_upstream_models_url(base_url):
    return runninghub_models_url(base_url)


def runninghub_upstream_model_headers(api_key):
    return runninghub_model_headers(api_key)


def runninghub_endpoint_label():
    return "/openapi/v2/models"
