import json
import re
from pathlib import Path

STATUS_LABELS = {"enrolled": "재학생", "on_leave": "휴학생", "graduating": "졸업예정자", "graduated": "졸업생"}
AI_SW_TOPIC = re.compile(
    r"(?<![A-Za-z0-9])(?:AI|SW)(?![A-Za-z0-9])|인공\s*지능|소프트웨어|머신\s*러닝|딥\s*러닝|프로그래밍|코딩",
    re.IGNORECASE,
)
PUBLISHER = re.compile(r"(?:국립)?순천대학교|SW\s*중심\s*대학(?:\s*사업단)?|AI\s*인재\s*양성\s*부트캠프\s*사업단", re.IGNORECASE)
TOPIC_LINE = re.compile(
    r"^\s*(?:[○●▶•*\-]\s*|\d+[.)]\s*)?(?:주제|프로그램\s*(?:명|내용|소개)?|활동\s*(?:명|내용|소개)?|교육\s*(?:명|내용|소개)?|모집\s*인원)\s*[:：\-]\s*(.+)$"
)

def normalized(value):
    return "".join(value.split()).casefold()

def has_ai_sw_topic(title, body_text):
    title = PUBLISHER.sub("", title)
    if AI_SW_TOPIC.search(title):
        return True
    for line in body_text.splitlines():
        match = TOPIC_LINE.match(line)
        if match and AI_SW_TOPIC.search(PUBLISHER.sub("", match[1])):
            return True
    return False

def load_policy():
    p = json.loads((Path(__file__).resolve().parents[2] / "config/recommendation-policy.json").read_text(encoding="utf-8"))
    if set(p["weights"]) != {"field", "department", "academic_status", "grade", "activity"}:
        raise ValueError("Unknown recommendation dimensions; time-based scores are forbidden.")
    if sum(p["weights"].values()) != 100 or any(v < 0 for v in p["weights"].values()):
        raise ValueError("Weights must be nonnegative and sum to 100.")
    if not 0 <= p["all_departments_score"] <= p["weights"]["department"]:
        raise ValueError("Invalid all-departments score")
    if not 0 <= p["topic_department_score"] <= p["weights"]["department"]:
        raise ValueError("Invalid topic-department score")
    if len({normalized(name) for name in p["ai_sw_departments"]}) != len(p["ai_sw_departments"]):
        raise ValueError("Duplicate AI/SW department")
    if not 0 <= p["all_grades_score"] <= p["weights"]["grade"]:
        raise ValueError("Invalid all-grades score")
    return p

def score_notice(data, profile, policy, *, title="", body_text=""):
    """No dates or posted timestamps are accepted by this function."""
    known = data.eligibility_confirmed
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
    if known and match_dept:
        department_score, department_reason = w["department"], f"{profile['department']} 대상"
    elif known and data.all_departments:
        department_score, department_reason = policy["all_departments_score"], "전 학과 대상 명시"
    elif (normalized(profile["department"]) in {normalized(name) for name in policy["ai_sw_departments"]}
          and has_ai_sw_topic(title, body_text)):
        department_score = policy["topic_department_score"]
        department_reason = f"{profile['department']}와 AI·SW 주제가 관련 있어요"
    else:
        department_score, department_reason = 0, None
    part("department", department_score, department_reason)
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
