# Agent OS Token Consumption Calculator
# ======================================

# Agent Configuration
agents = {
    "SCOUT": {
        "interval_minutes": 360,
        "model": "kimi-k2-thinking",
        "input_price": 0.60,  # per 1M tokens
        "output_price": 2.50,  # per 1M tokens
        "avg_input_tokens": 4000,  # per run
        "avg_output_tokens": 2000,  # per run
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

# Calculations
MINUTES_PER_WEEK = 7 * 24 * 60
MINUTES_PER_MONTH = 30 * 24 * 60

print("=" * 80)
print("AGENT OS - HAFTALIK TOKEN TÜKETİM HESAPLAMASI")
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
    # Weekly runs
    weekly_runs = MINUTES_PER_WEEK / config["interval_minutes"]
    monthly_runs = MINUTES_PER_MONTH / config["interval_minutes"]
    
    # Token calculations
    weekly_input = weekly_runs * config["avg_input_tokens"]
    weekly_output = weekly_runs * config["avg_output_tokens"]
    monthly_input = monthly_runs * config["avg_input_tokens"]
    monthly_output = monthly_runs * config["avg_output_tokens"]
    
    # Cost calculations (per 1M tokens)
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
    
    print(f"📊 {agent_name} ({config['model']})")
    print(f"   Görev: {config['description']}")
    print(f"   Sıklık: Her {config['interval_minutes']} dk ({weekly_runs:.1f} kez/hafta)")
    print(f"   Haftalık Input: {weekly_input:,.0f} tokens")
    print(f"   Haftalık Output: {weekly_output:,.0f} tokens")
    print(f"   Haftalık Maliyet: ${weekly_cost_total:.2f}")
    print(f"   Aylık Maliyet: ${monthly_cost_total:.2f}")
    print()

print("=" * 80)
print("📈 TOPLAM TÜKETİM")
print("=" * 80)
print()
print(f"🔢 HAFTALIK:")
print(f"   Toplam Çalışma: {sum(r['weekly_runs'] for r in results):,} kez")
print(f"   Input Tokens: {total_weekly_input:,.0f} ({total_weekly_input/1_000_000:.3f}M)")
print(f"   Output Tokens: {total_weekly_output:,.0f} ({total_weekly_output/1_000_000:.3f}M)")
print(f"   TOPLAM TOKEN: {total_weekly_input + total_weekly_output:,.0f} ({(total_weekly_input + total_weekly_output)/1_000_000:.3f}M)")
print(f"   MALİYET: ${total_weekly_cost:.2f}")
print()
print(f"🔢 AYLIK (Tahmini):")
print(f"   Input Tokens: {total_monthly_input:,.0f} ({total_monthly_input/1_000_000:.3f}M)")
print(f"   Output Tokens: {total_monthly_output:,.0f} ({total_monthly_output/1_000_000:.3f}M)")
print(f"   TOPLAM TOKEN: {total_monthly_input + total_monthly_output:,.0f} ({(total_monthly_input + total_monthly_output)/1_000_000:.3f}M)")
print(f"   MALİYET: ${total_monthly_cost:.2f}")
print()
print(f"🔢 YILLIK (Tahmini):")
print(f"   Yıllık Maliyet: ${total_monthly_cost * 12:.2f}")
print()
print("=" * 80)
print("💡 ÖNEMLİ NOTLAR")
print("=" * 80)
print()
print("1. ZARA en yüksek maliyeti oluşturuyor (30 dk interval = 336 kez/hafta)")
print("2. SETH en düşük maliyet (haftada 1 kez çalışıyor)")
print("3. Cache Hit kullanımı maliyeti %83 düşürebilir ($0.10 vs $0.60)")
print("4. Output/Input oranı: {:.1f}% (prompt engineering ile optimize edilebilir)".format(
    (total_weekly_output/total_weekly_input)*100))
print()
print("=" * 80)
