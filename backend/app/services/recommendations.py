import json
from pathlib import Path

STATUS_LABELS = {"enrolled": "재학생", "on_leave": "휴학생", "graduating": "졸업예정자", "graduated": "졸업생"}

def load_policy():
    p = json.loads((Path(__file__).resolve().parents[2] / "config/recommendation-policy.json").read_text(encoding="utf-8"))
    if set(p["weights"]) != {"field", "department", "academic_status", "grade", "activity"}:
        raise ValueError("Unknown recommendation dimensions; time-based scores are forbidden.")
    if sum(p["weights"].values()) != 100 or any(v < 0 for v in p["weights"].values()):
        raise ValueError("Weights must be nonnegative and sum to 100.")
    if not 0 <= p["all_departments_score"] <= p["weights"]["department"]:
        raise ValueError("Invalid all-departments score")
    if not 0 <= p["all_grades_score"] <= p["weights"]["grade"]:
        raise ValueError("Invalid all-grades score")
    return p

def score_notice(data, profile, policy):
    """No dates or posted timestamps are accepted by this function."""
    known = data.eligibility_confirmed
    def normalized(value):
        return "".join(value.split()).casefold()
    depts = [normalized(x) for x in data.target_departments]
    match_dept = normalized(profile["department"]) in depts
    match_grade = profile["grade"] in data.target_grades
    match_status = profile["academic_status"] in data.target_statuses
    if known:
        if depts and not match_dept:
            return None
        if data.target_grades and not match_grade:
            return None
        if data.target_statuses and not match_status:
            return None
    user_fields = {x["id"]:x["name"] for x in profile["interests"] if x["type"]=="field"}
    user_activities = {x["id"]:x["name"] for x in profile["interests"] if x["type"]=="activity"}
    field_hits = sorted(set(user_fields) & set(data.field_ids))
    activity_hits = sorted(set(user_activities) & set(data.activity_ids))
    w = policy["weights"]
    parts = []
    def part(name, score, reason=None):
        parts.append({"criterion": name, "score": score, "max_score": w[name], "reason": reason if score else None})
    part("field", w["field"] if field_hits else 0,
         "관심 분야 일치: " + ", ".join(user_fields[x] for x in field_hits))
    part("department", w["department"] if known and match_dept else
         policy["all_departments_score"] if known and data.all_departments else 0,
         f"{profile['department']} 대상" if match_dept else "전 학과 대상 명시")
    part("academic_status", w["academic_status"] if known and match_status else 0,
         f"{STATUS_LABELS[profile['academic_status']]} 대상 명시")
    part("grade", w["grade"] if known and match_grade else
         policy["all_grades_score"] if known and data.all_grades else 0,
         f"{profile['grade']}학년 대상" if match_grade else "전 학년 대상 명시")
    part("activity", w["activity"] if activity_hits else 0,
         "관심 활동 일치: " + ", ".join(user_activities[x] for x in activity_hits))
    score = sum(p["score"] for p in parts)
    reasons = [p["reason"] for p in sorted(parts, key=lambda p: -p["score"]) if p["score"] > 0][:3]
    return {"score": score, "grade": "매우 적합" if score >= 85 else "적합" if score >= 70 else
            "관심 가능" if score >= 50 else "낮은 관련성", "reasons": reasons,
            "breakdown": parts, "policy_version": policy["version"]}
