def compute_green_count(result: dict) -> int:
    count = 0

    if result.get("ma_news"):           count += 1
    if result.get("sunrise_sector"):    count += 1
    if result.get("capacity_expansion"):count += 1
    if result.get("strong_brand"):      count += 1

    scores = result["scores"]
    if scores[2]  > 90: count += 1
    if scores[12] > 90: count += 1
    if scores[3]  > 90: count += 1
    if scores[0]  > 90: count += 1
    if scores[4]  > 90: count += 1

    return count


def compute_ranks(analyses: list[dict]) -> list[dict]:
    n = len(analyses)

    sorted_by_score = sorted(analyses, key=lambda x: x["total_score"], reverse=True)
    for rank, a in enumerate(sorted_by_score, start=1):
        a["score_rank"] = rank

    sorted_by_return = sorted(analyses, key=lambda x: x["return_pct"], reverse=True)
    for rank, a in enumerate(sorted_by_return, start=1):
        a["return_rank"] = rank

    for a in analyses:
        a["composite_rank"] = a["score_rank"] + a["return_rank"]

    return analyses


def compute_allocations(analyses: list[dict], total_investment: float) -> list[dict]:
    n = len(analyses)
    y = total_investment / 3

    analyses = sorted(analyses, key=lambda x: x["composite_rank"])

    cutoff = max(22, int(n * 0.10))

    top     = analyses[:cutoff]
    rest    = analyses[cutoff:]

    for criterion in ["total_score", "return_pct", "green_count"]:
        alloc_key = {
            "total_score": "allocation_score",
            "return_pct":  "allocation_return",
            "green_count": "allocation_green"
        }[criterion]

        top_pool  = y * 0.70
        rest_pool = y * 0.30

        top_total  = sum(a[criterion] for a in top)
        rest_total = sum(a[criterion] for a in rest)

        for a in top:
            share = (a[criterion] / top_total) if top_total else (1 / len(top))
            a[alloc_key] = round(top_pool * share, 2)

        for a in rest:
            share = (a[criterion] / rest_total) if rest_total else (1 / len(rest)) if rest else 0
            a[alloc_key] = round(rest_pool * share, 2)


    for a in analyses:
        a["total_allocation"] = round(
            a["allocation_score"] + a["allocation_return"] + a["allocation_green"], 2
        )

    return analyses
