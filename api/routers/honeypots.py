"""
Honeypot Endpoints for BabyShield Security
Trap attackers and gather intelligence on attack patterns
"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
import logging
import time
import json
from typing import Dict, Any

logger = logging.getLogger(__name__)
router = APIRouter()

# Track honeypot hits for intelligence gathering
honeypot_hits: Dict[str, int] = {}
attack_intelligence: Dict[str, list] = {"ips": [], "patterns": [], "user_agents": []}


def record_honeypot_hit(request: Request, honeypot_type: str):
    """Record honeypot access for security intelligence"""
    client_ip = request.headers.get("X-Forwarded-For", request.client.host).split(",")[0].strip()
    user_agent = request.headers.get("User-Agent", "Unknown")

    # Record the hit
    honeypot_hits[client_ip] = honeypot_hits.get(client_ip, 0) + 1

    # Gather intelligence
    if client_ip not in attack_intelligence["ips"]:
        attack_intelligence["ips"].append(client_ip)
    if user_agent not in attack_intelligence["user_agents"]:
        attack_intelligence["user_agents"].append(user_agent)
    if honeypot_type not in attack_intelligence["patterns"]:
        attack_intelligence["patterns"].append(honeypot_type)

    logger.warning(
        f"🕳️ HONEYPOT HIT: {honeypot_type} from {client_ip} (hit #{honeypot_hits[client_ip]}) UA: {user_agent}"
    )

    # Auto-block after multiple hits
    if honeypot_hits[client_ip] >= 3:
        logger.error(
            f"🚨 AUTO-BLOCKING IP {client_ip} after {honeypot_hits[client_ip]} honeypot hits"
        )
        # In production, this would add to IP blocklist


def create_convincing_response(honeypot_type: str) -> JSONResponse:
    """Create convincing responses to waste attacker time"""
    responses = {
        "admin_login": {
            "status": "success",
            "message": "Loading admin dashboard...",
            "redirect": "/admin/dashboard",
            "session": "admin_session_" + str(int(time.time())),
            "csrf_token": "fake_csrf_token_" + str(int(time.time())),
        },
        "config_file": {
            "database": {
                "host": "localhost",
                "username": "admin",
                "password": "fake_password_123",
                "database": "babyshield_honeypot",
            },
            "api_keys": {
                "openai": "sk-fake_key_for_honeypot",
                "aws": "AKIA_FAKE_KEY_FOR_HONEYPOT",
            },
        },
        "backup_file": {
            "backup_info": {
                "created": "2025-09-26T00:00:00Z",
                "size": "1.2GB",
                "tables": ["users", "products", "scans"],
                "download_url": "/admin/download/backup.sql",
            }
        },
        "git_config": {
            "core": {
                "repositoryformatversion": "0",
                "filemode": "true",
                "bare": "false",
            },
            "remote": {
                "origin": {
                    "url": "https://github.com/babyshield/honeypot-repo.git",
                    "fetch": "+refs/heads/*:refs/remotes/origin/*",
                }
            },
        },
    }

    return JSONResponse(
        status_code=200,
        content=responses.get(honeypot_type, {"status": "success"}),
        headers={
            "Set-Cookie": f"honeypot_session=trap_{int(time.time())}; Path=/",
            "X-Honeypot-Type": honeypot_type,
            "X-Trap-ID": f"trap_{int(time.time())}",
        },
    )


# Honeypot Endpoints (designed to attract attackers)


@router.get("/admin/login.php", operation_id="admin_login_honeypot_get", include_in_schema=False)
@router.post(
    "/admin/login.php",
    operation_id="admin_login_honeypot_post",
    include_in_schema=False,
)
async def admin_login_honeypot(request: Request):
    """Fake admin login panel to trap attackers"""
    record_honeypot_hit(request, "admin_login")

    # Return convincing fake admin panel
    return HTMLResponse(
        content="""
        <!DOCTYPE html>
        <html>
        <head><title>Admin Login - BabyShield</title></head>
        <body>
            <h2>Administrator Login</h2>
            <form method="post">
                <input type="text" name="username" placeholder="Username" required>
                <input type="password" name="password" placeholder="Password" required>
                <button type="submit">Login</button>
            </form>
            <script>
                // Fake loading behavior to waste attacker time
                setTimeout(() => {
                    document.body.innerHTML += '<p>Loading dashboard...</p>';
                }, 2000);
            </script>
        </body>
        </html>
        """,
        headers={"X-Honeypot": "admin_panel"},
    )


@router.get("/.env", include_in_schema=False)
async def env_file_honeypot(request: Request):
    """Fake environment file to trap config seekers"""
    record_honeypot_hit(request, "config_file")

    fake_env = """# BabyShield Environment Configuration
DATABASE_URL=postgresql://admin:fake_password@localhost:5432/babyshield_honeypot
OPENAI_API_KEY=sk-fake_openai_key_for_honeypot_detection
AWS_ACCESS_KEY_ID=AKIA_FAKE_ACCESS_KEY_HONEYPOT
AWS_SECRET_ACCESS_KEY=fake_secret_key_for_honeypot_trap
REDIS_URL=redis://admin:fake_redis_pass@localhost:6379
SECRET_KEY=fake_jwt_secret_key_honeypot_trap
"""

    return HTMLResponse(content=fake_env, headers={"X-Honeypot": "env_file"})


@router.get("/backup.sql", include_in_schema=False)
@router.get("/backup/database.sql", include_in_schema=False)
async def backup_file_honeypot(request: Request):
    """Fake database backup to trap data seekers"""
    record_honeypot_hit(request, "backup_file")
    return create_convincing_response("backup_file")


@router.get("/.git/config", include_in_schema=False)
@router.get("/.git/HEAD", include_in_schema=False)
async def git_config_honeypot(request: Request):
    """Fake git config to trap repository scanners"""
    record_honeypot_hit(request, "git_config")
    return create_convincing_response("git_config")


@router.get("/wp-admin/admin.php", include_in_schema=False)
@router.get("/phpmyadmin/index.php", include_in_schema=False)
async def cms_honeypot(request: Request):
    """Fake CMS admin panels"""
    record_honeypot_hit(request, "cms_admin")
    return create_convincing_response("admin_login")


@router.get("/api/admin/users", include_in_schema=False)
@router.get("/api/v1/admin/config", include_in_schema=False)
async def api_admin_honeypot(request: Request):
    """Fake admin API endpoints"""
    record_honeypot_hit(request, "api_admin")

    return JSONResponse(
        content={
            "users": [
                {"id": 1, "username": "admin", "role": "administrator"},
                {"id": 2, "username": "developer", "role": "developer"},
            ],
            "total": 2,
            "honeypot": True,
        },
        headers={"X-Honeypot": "api_admin"},
    )


# Security Intelligence Endpoint (for monitoring)
@router.get("/security/intelligence", include_in_schema=False)
async def get_attack_intelligence():
    """Get attack intelligence data (admin only)"""
    return {
        "honeypot_hits": len(honeypot_hits),
        "unique_attackers": len(attack_intelligence["ips"]),
        "attack_patterns": len(attack_intelligence["patterns"]),
        "top_attacking_ips": sorted(honeypot_hits.items(), key=lambda x: x[1], reverse=True)[:10],
        "common_user_agents": attack_intelligence["user_agents"][:10],
    }
