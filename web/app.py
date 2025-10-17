# web/app.py
from flask import Flask, render_template, jsonify, abort, request
from pathlib import Path
import json
import time

app = Flask(__name__, template_folder="templates", static_folder="static")

# data/data.json 路径
DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "data.json"
# 与 data.json 同目录放一个 mute.json
MUTE_PATH = DATA_PATH.with_name("mute.json")


@app.route("/")
def main():
    return render_template("main.html")


@app.route("/view")
def view_page():
    return render_template("view.html")


@app.route("/api/data")
def api_data():
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    except FileNotFoundError:
        abort(404, description="data.json not found")


# ========= Snooze（本次告警静音，直到 MQ-2 回到 0 自动解除） =========
@app.route("/api/mute", methods=["POST"])
def api_mute_set():
    """
    点击“Mute Buzzer”调用：把 snooze 置为 True。
    main.py 每次循环会读取该标志；当 MQ-2==0 时会自动清为 False。
    """
    with open(MUTE_PATH, "w", encoding="utf-8") as f:
        json.dump({"snooze": True, "ts": int(time.time())}, f)
    return jsonify({"ok": True, "snooze": True})


@app.route("/api/mute", methods=["GET"])
def api_mute_status():
    """前端可选查询当前 snooze 状态。"""
    try:
        with open(MUTE_PATH, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    except FileNotFoundError:
        return jsonify({"snooze": False})


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=1500, debug=True)

