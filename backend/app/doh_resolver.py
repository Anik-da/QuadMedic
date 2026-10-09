import socket
import logging
import requests
import urllib3

# Disable InsecureRequestWarning for direct IP DoH requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger("quadmedic.doh_resolver")

original_getaddrinfo = socket.getaddrinfo

# In-memory DNS cache to avoid querying DoH endpoints repeatedly
DNS_CACHE = {}

TARGET_DOMAINS = [
    "router.huggingface.co",
    "api-inference.huggingface.co",
    "huggingface.co"
]

def doh_resolve(host: str) -> list[str]:
    """Resolve a host name to IP addresses using DNS-over-HTTPS (DoH)."""
    if host in DNS_CACHE:
        return DNS_CACHE[host]
        
    logger.info(f"Resolving '{host}' via custom DNS-over-HTTPS...")
    ips = []
    
    # 1. Try Cloudflare DoH (via direct IP address)
    try:
        url = f"https://1.1.1.1/dns-query?name={host}"
        r = requests.get(url, headers={"accept": "application/dns-json"}, timeout=3, verify=False)
        if r.status_code == 200:
            data = r.json()
            for ans in data.get("Answer", []):
                if ans.get("type") == 1: # A record
                    ips.append(ans.get("data"))
    except Exception as e:
        logger.warning(f"Cloudflare DoH resolution failed for {host}: {e}")
        
    # 2. Try Google DoH as a fallback (via direct IP address)
    if not ips:
        try:
            url = f"https://8.8.8.8/resolve?name={host}"
            r = requests.get(url, timeout=3, verify=False)
            if r.status_code == 200:
                data = r.json()
                for ans in data.get("Answer", []):
                    if ans.get("type") == 1: # A record
                        ips.append(ans.get("data"))
        except Exception as e:
            logger.warning(f"Google DoH resolution failed for {host}: {e}")
            
    if ips:
        logger.info(f"Successfully resolved '{host}' to IPs: {ips}")
        DNS_CACHE[host] = ips
        return ips
        
    logger.error(f"Failed to resolve '{host}' using custom DoH.")
    return []

def custom_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    """Custom getaddrinfo monkeypatch to intercept target domains."""
    if host in TARGET_DOMAINS:
        resolved_ips = doh_resolve(host)
        if resolved_ips:
            res = []
            for ip in resolved_ips:
                sockaddr = (ip, port)
                # socket.AF_INET (2), socket.SOCK_STREAM (1), proto TCP (6)
                res.append((socket.AF_INET, socket.SOCK_STREAM, 6, '', sockaddr))
            return res
            
    return original_getaddrinfo(host, port, family, type, proto, flags)

# Apply monkeypatch immediately
socket.getaddrinfo = custom_getaddrinfo
logger.info("Custom DNS-over-HTTPS (DoH) monkeypatch applied.")
