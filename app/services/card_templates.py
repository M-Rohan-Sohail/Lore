import json

def get_base_html(title: str, content: str) -> str:
    """Provides a base HTML template with a sleek dark mode glassmorphism theme."""
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;800&display=swap" rel="stylesheet">
        <style>
            :root {{
                --bg-color: #0f172a;
                --text-main: #f8fafc;
                --text-muted: #94a3b8;
                --accent: #3b82f6;
                --accent-glow: rgba(59, 130, 246, 0.5);
                --glass-bg: rgba(30, 41, 59, 0.7);
                --glass-border: rgba(255, 255, 255, 0.1);
            }}
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{
                font-family: 'Outfit', sans-serif;
                background-color: var(--bg-color);
                color: var(--text-main);
                width: 1080px;
                height: 1920px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                position: relative;
                overflow: hidden;
            }}
            .bg-glow-1 {{
                position: absolute;
                width: 800px; height: 800px;
                background: radial-gradient(circle, var(--accent-glow) 0%, transparent 70%);
                top: -200px; left: -200px;
                filter: blur(100px);
                z-index: 0;
            }}
            .bg-glow-2 {{
                position: absolute;
                width: 600px; height: 600px;
                background: radial-gradient(circle, rgba(168, 85, 247, 0.4) 0%, transparent 70%);
                bottom: -100px; right: -100px;
                filter: blur(100px);
                z-index: 0;
            }}
            .card {{
                background: var(--glass-bg);
                backdrop-filter: blur(20px);
                border: 2px solid var(--glass-border);
                border-radius: 40px;
                padding: 80px;
                width: 860px;
                z-index: 10;
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
                display: flex;
                flex-direction: column;
                gap: 40px;
            }}
            .header h1 {{
                font-size: 80px;
                font-weight: 800;
                margin-bottom: 10px;
                background: linear-gradient(to right, #60a5fa, #c084fc);
                -webkit-background-clip: text;
                color: transparent;
            }}
            .header p {{
                font-size: 40px;
                color: var(--text-muted);
            }}
            .content {{
                font-size: 45px;
                line-height: 1.4;
                font-weight: 400;
            }}
            .stats {{
                display: flex;
                flex-wrap: wrap;
                gap: 20px;
                margin-top: 20px;
            }}
            .stat-badge {{
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid var(--glass-border);
                padding: 20px 40px;
                border-radius: 20px;
                font-size: 35px;
                font-weight: 600;
                display: flex;
                align-items: center;
                gap: 15px;
            }}
            .stat-value {{ color: #38bdf8; font-weight: 800; }}
            .footer {{
                margin-top: 60px;
                text-align: center;
                font-size: 35px;
                color: var(--text-muted);
                border-top: 2px solid var(--glass-border);
                padding-top: 40px;
            }}
            .url {{
                color: #e2e8f0;
                font-weight: 600;
                margin-top: 15px;
                display: block;
            }}
        </style>
    </head>
    <body>
        <div class="bg-glow-1"></div>
        <div class="bg-glow-2"></div>
        {content}
    </body>
    </html>
    """

def _build_stats_html(stats: dict) -> str:
    if not stats: return ""
    badges = [f'<div class="stat-badge"><span class="stat-label">{k.upper()}</span> <span class="stat-value">{v}</span></div>' for k, v in stats.items()]
    return f'<div class="stats">{"".join(badges)}</div>'

def build_payload(kind: str, raw_data: dict, referral_code: str) -> str:
    """
    Enforces FR-7.2 content-minimization contract. Only allowed fields per kind are included.
    Returns rendered HTML string ready for Playwright.
    """
    url = f"lore.app/j/{referral_code}" if referral_code else "lore.app"
    
    if kind == "character":
        # Allowed: display_name, class_name, base_stats, founding_player
        name = raw_data.get("display_name") or "Adventurer"
        c_class = raw_data.get("class_name") or "Unknown"
        stats = raw_data.get("base_stats") or {}
        founding = raw_data.get("founding_player", False)
        
        founding_html = '<div style="margin-bottom:20px; color:#fcd34d; font-size:35px; font-weight:bold;">★ Founding Player</div>' if founding else ""
        
        content = f'''
        <div class="card">
            {founding_html}
            <div class="header">
                <p>New Character</p>
                <h1>{name}</h1>
                <p style="color: #cbd5e1; font-weight: 600;">{c_class}</p>
            </div>
            {_build_stats_html(stats)}
            <div class="footer">
                Join the adventure
                <span class="url">{url}</span>
            </div>
        </div>
        '''
        return get_base_html("Character Card", content)
        
    elif kind == "level_up":
        # Allowed: display_name, level, class_name, founding_player
        name = raw_data.get("display_name") or "Adventurer"
        level = raw_data.get("level") or 1
        c_class = raw_data.get("class_name") or "Unknown"
        founding = raw_data.get("founding_player", False)
        
        founding_html = '<div style="margin-bottom:20px; color:#fcd34d; font-size:35px; font-weight:bold;">★ Founding Player</div>' if founding else ""
        
        content = f'''
        <div class="card" style="border-color: rgba(250, 204, 21, 0.3);">
            {founding_html}
            <div class="header">
                <p>Level Up!</p>
                <h1>{name} reached Lvl {level}</h1>
                <p style="color: #cbd5e1; font-weight: 600;">{c_class}</p>
            </div>
            <div class="footer">
                Join the adventure
                <span class="url">{url}</span>
            </div>
        </div>
        '''
        return get_base_html("Level Up Card", content)

    elif kind == "weekly_recap":
        # Allowed: display_name, episode_title, episode_number, stat_deltas, narrator_quote
        name = raw_data.get("display_name") or "Adventurer"
        ep_title = raw_data.get("episode_title") or "A New Chapter"
        ep_num = raw_data.get("episode_number")
        ep_label = f"EP.{ep_num:02d}" if ep_num else "EPISODE"
        deltas = raw_data.get("stat_deltas") or {}
        quote = raw_data.get("narrator_quote") or "The story continues."
        
        content = f'''
        <div class="card">
            <div class="header">
                <p>{name}'s Week • {ep_label}</p>
                <h1>{ep_title}</h1>
            </div>
            <div class="content" style="font-style: italic; border-left: 8px solid var(--accent); padding-left: 30px;">
                "{quote}"
            </div>
            {_build_stats_html(deltas)}
            <div class="footer">
                Join the adventure
                <span class="url">{url}</span>
            </div>
        </div>
        '''
        return get_base_html("Weekly Recap", content)
        
    elif kind == "party_recap":
        # Allowed: party_name, episode_title, episode_number, member_lines (list of dicts)
        p_name = raw_data.get("party_name") or "The Party"
        ep_title = raw_data.get("episode_title") or "A Shared Journey"
        ep_num = raw_data.get("episode_number")
        ep_label = f"EP.{ep_num:02d}" if ep_num else "EPISODE"
        
        lines_html = ""
        for m in (raw_data.get("member_lines") or []):
            m_name = m.get("display_name", "Member")
            m_line = m.get("line", "")
            lines_html += f'<div style="margin-top: 20px;"><strong>{m_name}:</strong> <span style="color: var(--text-muted);">{m_line}</span></div>'
            
        content = f'''
        <div class="card">
            <div class="header">
                <p>{p_name} • {ep_label}</p>
                <h1 style="background: linear-gradient(to right, #f472b6, #fb923c); -webkit-background-clip: text;">{ep_title}</h1>
            </div>
            <div class="content" style="font-size: 38px;">
                {lines_html}
            </div>
            <div class="footer">
                Join the party
                <span class="url">{url}</span>
            </div>
        </div>
        '''
        return get_base_html("Party Recap", content)
        
    elif kind == "quiet_week":
        name = raw_data.get("display_name") or "Adventurer"
        content = f'''
        <div class="card">
            <div class="header">
                <p>{name}'s Week</p>
                <h1 style="background: linear-gradient(to right, #94a3b8, #cbd5e1); -webkit-background-clip: text;">Taking a Breath</h1>
            </div>
            <div class="content">
                Every hero needs to rest. Ready for the next adventure when you are.
            </div>
            <div class="footer">
                Join the adventure
                <span class="url">{url}</span>
            </div>
        </div>
        '''
        return get_base_html("Quiet Week", content)

    else:
        # Fallback empty card
        return get_base_html("Unknown", f'<div class="card"><h1>Unknown Card Type</h1></div>')
