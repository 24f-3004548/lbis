import time
from datetime import date
from typing import Optional
from dotenv import load_dotenv
from postgrest.exceptions import APIError
from db import get_db
from llm import analyse_stock
from scoring import compute_green_count, compute_ranks, compute_allocations

load_dotenv()
def _load_stocks_from_db(db) -> list[dict]:
    page_size = 1000
    start = 0
    stocks: list[dict] = []

    while True:
        end = start + page_size - 1
        res = (
            db.table("stocks")
            .select("stock_id,stock_name,date,price")
            .order("date")
            .range(start, end)
            .execute()
        )
        batch = res.data or []
        if not batch:
            break

        for row in batch:
            stock_name = (row.get("stock_name") or "").strip()
            stock_date = row.get("date")
            stock_price = row.get("price")
            if not stock_name or stock_date is None or stock_price is None:
                continue

            stocks.append({
                "stock_id": row["stock_id"],
                "stock_name": stock_name,
                "date": stock_date,
                "price": float(stock_price),
            })

        if len(batch) < page_size:
            break
        start += page_size

    return stocks


def run_rebalance(
    stocks: Optional[list[dict]] = None,
    rebalance_date: Optional[date] = None,
    total_investment: float = 0.0,
):
    db = get_db()

    if rebalance_date is None:
        rebalance_date = date.today()

    if not stocks:
        stocks = _load_stocks_from_db(db)
        stocks = stocks[:10] # to avoid hitting free api rate limits, remove later.
        print(f"Loaded {len(stocks)} stocks from DB")

    if not stocks:
        print("No stocks found to analyse.")
        return

    rebalance_date_iso = rebalance_date.isoformat()
    try:
        run = db.table("rebalance_runs").insert({
            "rebalance_date": rebalance_date_iso,
            "total_investment": total_investment
        }).execute()
        rebalance_id = run.data[0]["rebalance_id"]
        print(f"Created rebalance run {rebalance_id} for {rebalance_date}")
    except APIError as e:
        err = getattr(e, "message", {})
        is_duplicate = (isinstance(err, dict) and err.get("code") == "23505") or ("23505" in str(e))
        if is_duplicate:
            existing = db.table("rebalance_runs").select("rebalance_id").eq("rebalance_date", rebalance_date_iso).single().execute()
            rebalance_id = existing.data["rebalance_id"]
            print(f"Using existing rebalance run {rebalance_id} for {rebalance_date}")
        else:
            raise

    analyses = []
    for stock in stocks:
        print(f"  Analysing {stock['stock_name']} ({stock['date']})...")
        try:
            resolved_stock_id = stock["stock_id"]
            stock_price = float(stock["price"])
            analysis_date = stock["date"]
            result = analyse_stock(
                stock_name=stock["stock_name"],
                analysis_date=analysis_date,
                stock_price=stock_price
            )

            row = db.table("analysis").insert({
                "stock_id":               resolved_stock_id,
                "analysis_date":          analysis_date,
                "stock_price":            stock_price,
                "score_promoter":         result["scores"][0],
                "score_mgmt_exp":         result["scores"][1],
                "score_market_opp":       result["scores"][2],
                "score_govt":             result["scores"][3],
                "score_mgmt_aspiration":  result["scores"][4],
                "score_integrity":        result["scores"][5],
                "score_innovation":       result["scores"][6],
                "score_technology":       result["scores"][7],
                "score_export":           result["scores"][8],
                "score_political":        result["scores"][9],
                "score_order_completion": result["scores"][10],
                "score_project_execution":result["scores"][11],
                "score_margin":           result["scores"][12],
                "score_debtor_days":      result["scores"][13],
                "score_financial":        result["scores"][14],
                "sunrise_sector":         result["sunrise_sector"],
                "strong_brand":           result["strong_brand"],
                "capacity_expansion":     result["capacity_expansion"],
                "ma_news":                result["ma_news"],
                "govt_tailwind":          result["govt_tailwind"],
                "promoter_holding_pct":   result["promoter_holding_pct"],
                "fii_pct":                result["fii_pct"],
                "dii_pct":                result["dii_pct"],
                "mf_pct":                 result["mf_pct"],
                "target_price_3y":        result["target_price_3y"],
            }).execute()

            analysis_id = row.data[0]["analysis_id"]
            total_score = sum(result["scores"])
            return_pct  = ((result["target_price_3y"] - stock_price) / stock_price) * 100
            green_count = compute_green_count(result)

            analyses.append({
                "stock_id":    resolved_stock_id,
                "analysis_id": analysis_id,
                "total_score": total_score,
                "return_pct":  return_pct,
                "green_count": green_count,
            })

        except Exception as e:
            print(f"  ERROR on {stock['stock_name']}: {e}")
            continue

        time.sleep(0.5)  # to avoid hitting free api rate limits, remove later.

    if not analyses:
        print("No successful analyses. Skipping rebalance insert.")
        return

    analyses = compute_ranks(analyses)

    analyses = compute_allocations(analyses, total_investment)

    rebalance_rows = [{
        "rebalance_id":        rebalance_id,
        "stock_id":            a["stock_id"],
        "analysis_id":         a["analysis_id"],
        "green_count":         a["green_count"],
        "return_pct":          a["return_pct"],
        "score_rank":          a["score_rank"],
        "return_rank":         a["return_rank"],
        "composite_rank":      a["composite_rank"],
        "allocation_score":    a["allocation_score"],
        "allocation_return":   a["allocation_return"],
        "allocation_green":    a["allocation_green"],
        "total_allocation":    a["total_allocation"],
    } for a in analyses]

    db.table("rebalance").insert(rebalance_rows).execute()
    print(f"Rebalance complete. {len(rebalance_rows)} stocks processed.")
