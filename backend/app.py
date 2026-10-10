import os
import psycopg2
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
CORS(app)


def get_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def passes(rule, student):
    v = student.get(rule["field"])
    if v is None or str(v).strip() == "":
        return False
    op, target = rule["operator"], rule["value"]
    if op == "in":
        return str(v).strip() in [x.strip() for x in target.split(",")]
    if op == "=":
        return str(v).strip().lower() == target.strip().lower()
    try:
        if op == "<=":
            return float(v) <= float(target)
        if op == ">=":
            return float(v) >= float(target)
    except ValueError:
        return False
    return False


def load_schemes():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("select id, name, benefit, documents, apply_link, last_verified from schemes order by id")
    schemes = {}
    for row in cur.fetchall():
        schemes[row[0]] = {
            "id": row[0], "name": row[1], "benefit": row[2],
            "documents": row[3], "apply_link": row[4],
            "last_verified": str(row[5]) if row[5] else None,
            "rules": [],
        }
    cur.execute("select scheme_id, field, operator, value from rules")
    for scheme_id, field, operator, value in cur.fetchall():
        if scheme_id in schemes:
            schemes[scheme_id]["rules"].append({"field": field, "operator": operator, "value": value})
    cur.close()
    conn.close()
    return list(schemes.values())


def match(schemes, student):
    return [s for s in schemes if all(passes(r, student) for r in s["rules"])]


@app.route("/")
def health():
    return jsonify({"status": "ok"})


@app.route("/match", methods=["POST"])
def match_route():
    student = request.get_json(force=True) or {}
    return jsonify({"matches": match(load_schemes(), student)})
