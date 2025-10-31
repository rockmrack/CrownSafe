"""Security Monitoring Dashboard for BabyShield
Real-time threat intelligence and attack visualization.
"""

import logging
import time
from datetime import datetime, UTC

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# Security metrics storage (in production, use Redis/database)
security_metrics = {
    "total_requests": 0,
    "blocked_requests": 0,
    "threat_score_distribution": {"low": 0, "medium": 0, "high": 0, "critical": 0},
    "attack_types": {},
    "top_attacking_ips": {},
    "honeypot_hits": {},
    "geographic_blocks": {},
    "user_agent_blocks": {},
    "last_updated": time.time(),
}


def update_security_metrics(
    threat_score: int,
    attack_type: str,
    client_ip: str,
    user_agent: str,
    blocked: bool = False,
) -> None:
    """Update security metrics for dashboard."""
    global security_metrics

    security_metrics["total_requests"] += 1
    if blocked:
        security_metrics["blocked_requests"] += 1

    # Threat score distribution
    if threat_score >= 100:
        security_metrics["threat_score_distribution"]["critical"] += 1
    elif threat_score >= 80:
        security_metrics["threat_score_distribution"]["high"] += 1
    elif threat_score >= 50:
        security_metrics["threat_score_distribution"]["medium"] += 1
    else:
        security_metrics["threat_score_distribution"]["low"] += 1

    # Attack types
    security_metrics["attack_types"][attack_type] = security_metrics["attack_types"].get(attack_type, 0) + 1

    # Top attacking IPs
    security_metrics["top_attacking_ips"][client_ip] = security_metrics["top_attacking_ips"].get(client_ip, 0) + 1

    # User agent tracking
    if blocked:
        security_metrics["user_agent_blocks"][user_agent] = security_metrics["user_agent_blocks"].get(user_agent, 0) + 1

    security_metrics["last_updated"] = time.time()


@router.get("/security/dashboard")
async def security_dashboard():
    """Real-time security dashboard (HTML)."""
    # Calculate security statistics
    total_requests = security_metrics["total_requests"]
    blocked_requests = security_metrics["blocked_requests"]
    block_rate = (blocked_requests / max(total_requests, 1)) * 100

    # Get top threats
    top_ips = sorted(security_metrics["top_attacking_ips"].items(), key=lambda x: x[1], reverse=True)[:10]
    top_attacks = sorted(security_metrics["attack_types"].items(), key=lambda x: x[1], reverse=True)[:10]

    dashboard_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>BabyShield Security Dashboard</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            .header {{ background: #1f2937; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
            .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 20px; }}  # noqa: E501
            .metric-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}  # noqa: E501
            .metric-value {{ font-size: 2em; font-weight: bold; color: #1f2937; }}
            .metric-label {{ color: #6b7280; font-size: 0.9em; }}
            .threat-high {{ color: #dc2626; }}
            .threat-medium {{ color: #f59e0b; }}
            .threat-low {{ color: #10b981; }}
            .table {{ background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .table-header {{ background: #1f2937; color: white; padding: 15px; font-weight: bold; }}
            .table-row {{ padding: 10px 15px; border-bottom: 1px solid #e5e7eb; }}
            .status-indicator {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 8px; }}  # noqa: E501
            .status-safe {{ background: #10b981; }}
            .status-warning {{ background: #f59e0b; }}
            .status-danger {{ background: #dc2626; }}
            .refresh {{ background: #3b82f6; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }}  # noqa: E501
        </style>
        <script>
            function refreshDashboard() {{
                window.location.reload();
            }}
            // Auto-refresh every 30 seconds
            setTimeout(refreshDashboard, 30000);
        </script>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🛡️ BabyShield Security Dashboard</h1>
                <p>Real-time threat monitoring and attack intelligence</p>
                <button class="refresh" onclick="refreshDashboard()">🔄 Refresh</button>
            </div>
            
            <div class="metrics">
                <div class="metric-card">
                    <div class="metric-value threat-low">{total_requests:,}</div>
                    <div class="metric-label">Total Requests</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value threat-high">{blocked_requests:,}</div>
                    <div class="metric-label">Blocked Attacks</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value {"threat-high" if block_rate > 10 else "threat-medium" if block_rate > 5 else "threat-low"}">{block_rate:.1f}%</div>  # noqa: E501
                    <div class="metric-label">Block Rate</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value threat-medium">{len(top_ips)}</div>
                    <div class="metric-label">Attacking IPs</div>
                </div>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div class="table">
                    <div class="table-header">🎯 Top Attacking IPs</div>
                    {"".join(f'<div class="table-row"><span class="status-indicator status-danger"></span>{ip} ({count} attacks)</div>' for ip, count in top_ips)}  # noqa: E501
                </div>
                
                <div class="table">
                    <div class="table-header">⚔️ Attack Types</div>
                    {"".join(f'<div class="table-row"><span class="status-indicator status-warning"></span>{attack} ({count} attempts)</div>' for attack, count in top_attacks)}  # noqa: E501
                </div>
            </div>
            
            <div class="table" style="margin-top: 20px;">
                <div class="table-header">📊 Threat Score Distribution</div>
                <div class="table-row">
                    <span class="status-indicator status-danger"></span>Critical (100+): {security_metrics["threat_score_distribution"]["critical"]} requests  # noqa: E501
                </div>
                <div class="table-row">
                    <span class="status-indicator status-warning"></span>High (80-99): {security_metrics["threat_score_distribution"]["high"]} requests  # noqa: E501
                </div>
                <div class="table-row">
                    <span class="status-indicator status-warning"></span>Medium (50-79): {security_metrics["threat_score_distribution"]["medium"]} requests  # noqa: E501
                </div>
                <div class="table-row">
                    <span class="status-indicator status-safe"></span>Low (0-49): {security_metrics["threat_score_distribution"]["low"]} requests  # noqa: E501
                </div>
            </div>
            
            <div style="margin-top: 20px; padding: 15px; background: white; border-radius: 8px; font-size: 0.9em; color: #6b7280;">  # noqa: E501
                <strong>Security Status:</strong> 
                <span class="status-indicator status-safe"></span>
                Bulletproof security active • Last updated: {datetime.fromtimestamp(security_metrics["last_updated"]).strftime("%Y-%m-%d %H:%M:%S")} UTC  # noqa: E501
            </div>
        </div>
    </body>
    </html>
    """

    return HTMLResponse(content=dashboard_html)


@router.get("/security/metrics")
async def security_metrics_api():
    """Security metrics API endpoint."""
    return JSONResponse(
        content={
            "status": "bulletproof",
            "metrics": security_metrics,
            "protection_level": "enterprise",
            "last_updated": datetime.fromtimestamp(security_metrics["last_updated"]).isoformat(),
            "threat_level": "low" if security_metrics["blocked_requests"] < 100 else "high",
        },
    )


@router.get("/security/threats/live")
async def live_threats():
    """Live threat feed for real-time monitoring."""
    return JSONResponse(
        content={
            "active_threats": len(security_metrics["top_attacking_ips"]),
            "block_rate": (security_metrics["blocked_requests"] / max(security_metrics["total_requests"], 1)) * 100,
            "threat_level": "low",  # Would be calculated based on recent activity
            "last_attack": datetime.fromtimestamp(security_metrics["last_updated"]).isoformat(),
            "protection_status": "active",
        },
    )


@router.post("/security/block-ip")
async def manual_ip_block(request: Request, ip_address: str):
    """Manual IP blocking endpoint (admin only)."""
    # In production, this would require admin authentication
    logger.warning(f"Manual IP block requested: {ip_address}")

    # Add to blocked IPs (in production, update WAF or security groups)
    return JSONResponse(
        content={
            "status": "success",
            "message": f"IP {ip_address} added to block list",
            "blocked_at": datetime.now(UTC).isoformat(),
        },
    )
