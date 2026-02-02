# Agent OS Token Consumption Calculator
# ======================================

# Agent Configuration
agents = {
    "SCOUT": {
        "interval_minutes": 360,
        "model": "kimi-k2-thinking",
        "input_price": 0.60,
        "output_price": 2.50,
        "avg_input_tokens": 4000,
        "avg_output_tokens": 2000,
        "description": "Market intelligence & trend analysis"
    },
    "ORACLE": {
        "interval_minutes": 360,
        "model": "kimi-k2-thinking",
        "input_price": 0.60,
        "output_price": 2.50,
        "avg_input_tokens": 3000,
        "avg_output_tokens": 1500,
        "description": "Opportunity validation & analysis"
    },
    "ELON": {
        "interval_minutes": 1440,
        "model": "kimi-k2-0905-preview",
        "input_price": 0.60,
        "output_price": 2.50,
        "avg_input_tokens": 2500,
        "avg_output_tokens": 1500,
        "description": "Growth experiments & ICE scoring"
    },
    "SETH": {
        "interval_minutes": 10080,
        "model": "kimi-k2-0905-preview",
        "input_price": 0.60,
        "output_price": 2.50,
        "avg_input_tokens": 3000,
        "avg_output_tokens": 2000,
        "description": "SEO content generation"
    },
    "ZARA": {
        "interval_minutes": 30,
        "model": "kimi-k2-0905-preview",
        "input_price": 0.60,
        "output_price": 2.50,
        "avg_input_tokens": 1500,
        "avg_output_tokens": 800,
        "description": "Community engagement"
    },
    "ECE": {
        "interval_minutes": 1440,
        "model": "kimi-k2-0905-preview",
        "input_price": 0.60,
        "output_price": 2.50,
        "avg_input_tokens": 2000,
        "avg_output_tokens": 1000,
        "description": "Visual content (prompt optimization)"
    }
}

MINUTES_PER_WEEK = 7 * 24 * 60
MINUTES_PER_MONTH = 30 * 24 * 60

print("=" * 80)
print("AGENT OS - HAFTALIK TOKEN TUKETIM HESAPLAMASI")
print("=" * 80)
print()

total_weekly_input = 0
total_weekly_output = 0
total_monthly_input = 0
total_monthly_output = 0
total_weekly_cost = 0
total_monthly_cost = 0

results = []

for agent_name, config in agents.items():
    weekly_runs = MINUTES_PER_WEEK / config["interval_minutes"]
    monthly_runs = MINUTES_PER_MONTH / config["interval_minutes"]
    
    weekly_input = weekly_runs * config["avg_input_tokens"]
    weekly_output = weekly_runs * config["avg_output_tokens"]
    monthly_input = monthly_runs * config["avg_input_tokens"]
    monthly_output = monthly_runs * config["avg_output_tokens"]
    
    weekly_cost_input = (weekly_input / 1_000_000) * config["input_price"]
    weekly_cost_output = (weekly_output / 1_000_000) * config["output_price"]
    weekly_cost_total = weekly_cost_input + weekly_cost_output
    
    monthly_cost_input = (monthly_input / 1_000_000) * config["input_price"]
    monthly_cost_output = (monthly_output / 1_000_000) * config["output_price"]
    monthly_cost_total = monthly_cost_input + monthly_cost_output
    
    total_weekly_input += weekly_input
    total_weekly_output += weekly_output
    total_monthly_input += monthly_input
    total_monthly_output += monthly_output
    total_weekly_cost += weekly_cost_total
    total_monthly_cost += monthly_cost_total
    
    results.append({
        "agent": agent_name,
        "weekly_runs": round(weekly_runs),
        "weekly_input_tokens": round(weekly_input),
        "weekly_output_tokens": round(weekly_output),
        "weekly_cost": round(weekly_cost_total, 2),
        "monthly_cost": round(monthly_cost_total, 2)
    })
    
    print(f"[AGENT] {agent_name} ({config['model']})")
    print(f"   Gorev: {config['description']}")
    print(f"   Siklik: Her {config['interval_minutes']} dk ({weekly_runs:.1f} kez/hafta)")
    print(f"   Haftalik Input: {weekly_input:,.0f} tokens")
    print(f"   Haftalik Output: {weekly_output:,.0f} tokens")
    print(f"   Haftalik Maliyet: ${weekly_cost_total:.2f}")
    print(f"   Aylik Maliyet: ${monthly_cost_total:.2f}")
    print()

print("=" * 80)
print("TOPLAM TUKETIM")
print("=" * 80)
print()
print(f"HAFTALIK:")
print(f"   Toplam Calisma: {sum(r['weekly_runs'] for r in results):,} kez")
print(f"   Input Tokens: {total_weekly_input:,.0f} ({total_weekly_input/1_000_000:.3f}M)")
print(f"   Output Tokens: {total_weekly_output:,.0f} ({total_weekly_output/1_000_000:.3f}M)")
print(f"   TOPLAM TOKEN: {total_weekly_input + total_weekly_output:,.0f} ({(total_weekly_input + total_weekly_output)/1_000_000:.3f}M)")
print(f"   MALIYET: ${total_weekly_cost:.2f}")
print()
print(f"AYLIK (Tahmini):")
print(f"   Input Tokens: {total_monthly_input:,.0f} ({total_monthly_input/1_000_000:.3f}M)")
print(f"   Output Tokens: {total_monthly_output:,.0f} ({total_monthly_output/1_000_000:.3f}M)")
print(f"   TOPLAM TOKEN: {total_monthly_input + total_monthly_output:,.0f} ({(total_monthly_input + total_monthly_output)/1_000_000:.3f}M)")
print(f"   MALIYET: ${total_monthly_cost:.2f}")
print()
print(f"YILLIK (Tahmini):")
print(f"   Yillik Maliyet: ${total_monthly_cost * 12:.2f}")
print()
print("=" * 80)
print("ONEMLI NOTLAR")
print("=" * 80)
print()
print("1. ZARA en yuksek maliyeti olusturuyor (30 dk interval = 336 kez/hafta)")
print("2. SETH en dusuk maliyet (haftada 1 kez calisiyor)")
print("3. Cache Hit kullanimi maliyeti %83 dusurebilir ($0.10 vs $0.60)")
print("4. Output/Input orani: {:.1f}%".format((total_weekly_output/total_weekly_input)*100))
print()
print("=" * 80)
