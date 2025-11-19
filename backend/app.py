from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from vm_core import VM, VMError

HERE = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
CORS(app)

vm = VM()

@app.route('/')
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/static/<path:p>')
def static_proxy(p):
    return send_from_directory(FRONTEND_DIR, p)

@app.post('/upload_program')
def upload_program():
    try:
        data = request.get_json()
        program = data.get("program", "")
        vm.load_program(program)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})

@app.post('/load')
def load_program():
    data = request.get_json(silent=True) or {}
    asm = data.get('asm', '')
    try:
        vm.load_program(asm)
        return jsonify({'status': 'ok', 'prog_len': len(vm.P)})
    except VMError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.get('/state')
def state():
    return jsonify(vm.snapshot())

@app.post('/step')
def step():
    if vm.halted:
        return jsonify({'status': 'halted', 'snapshot': vm.snapshot()})
    try:
        vm.step()
        return jsonify({'status': 'ok', 'snapshot': vm.snapshot()})
    except VMError as e:
        return jsonify({'status': 'error', 'message': str(e), 'snapshot': vm.snapshot()}), 200

@app.post('/run')
def run():
    if vm.halted:
        return jsonify({'status': 'halted', 'snapshot': vm.snapshot()})
    body = request.get_json(silent=True) or {}
    limit = int(body.get('limit', 1000000))
    try:
        vm.run(step_limit=limit)
        return jsonify({'status': 'ok', 'snapshot': vm.snapshot()})
    except VMError as e:
        return jsonify({'status': 'error', 'message': str(e), 'snapshot': vm.snapshot()}), 200

@app.post('/reset')
def reset():
    vm.reset()
    return jsonify({'status': 'ok', 'snapshot': vm.snapshot()})

@app.post('/input')
def input_value():
    data = request.get_json(silent=True) or {}
    try:
        v = int(data.get('value'))
        vm.enqueue_input(v)
        return jsonify({'status': 'ok', 'input_queue': vm.input_queue})
    except Exception:
        return jsonify({'status': 'error', 'message': 'Valor inválido'}), 400

@app.get('/examples')
def examples():
    return jsonify({
        "soma": "START\nLDC 5\nLDC 3\nADD\nPRN\nHLT"
    })

if __name__ == '__main__':
    app.run(port=5000, debug=True)
