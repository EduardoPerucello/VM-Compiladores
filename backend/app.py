"""
Servidor Flask da Máquina Virtual Didática (MVD)
------------------------------------------------
Endpoints:
- POST /load    -> Carrega um programa Assembly (texto)
- POST /step    -> Executa uma instrução
- POST /run     -> Executa até HLT
- POST /reset   -> Reinicia a VM
- GET  /state   -> Retorna o estado atual (memória, pilha, saída, etc.)
- POST /input   -> Envia um valor de entrada (para instrução RD)
- GET  /examples -> Retorna exemplos de programas Assembly

Requer vm_core.py (VM completa).
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from vm_core import VM, VMError

# --- Caminhos ---
HERE = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.normpath(os.path.join(HERE, '..', 'frontend'))

# --- Flask app ---
app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
CORS(app)

# --- Instância única da VM ---
vm = VM()

# =========================
# Rotas principais
# =========================

@app.route('/')
def index():
    """Serve o index.html do frontend."""
    return send_from_directory(FRONTEND_DIR, 'index.html')


@app.route('/static/<path:p>')
def static_proxy(p):
    """Serve arquivos estáticos do frontend."""
    return send_from_directory(FRONTEND_DIR, p)


@app.route('/load', methods=['POST'])
def load_program():
    """Carrega e monta um programa Assembly."""
    data = request.get_json(silent=True) or {}
    asm = data.get('asm', '')
    try:
        vm.load_program(asm)
        print("\n=== Programa MVD carregado ===")
        print(vm.dump_program())
        print("==============================\n")
        return jsonify({'status': 'ok', 'prog_len': len(vm.P)})
    except VMError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/state', methods=['GET'])
def state():
    """Retorna o estado atual da VM."""
    return jsonify(vm.snapshot())


@app.route('/step', methods=['POST'])
def step():
    if vm.halted:
        return jsonify({'status': 'halted', 'msg': 'VM já parada', 'snapshot': vm.snapshot()})
    try:
        vm.step()
        return jsonify({'status': 'ok', 'snapshot': vm.snapshot()})
    except VMError as e:
        # 🔹 Retorna erro para o frontend (prompt RD)
        return jsonify({
            'status': 'error',
            'message': str(e),
            'snapshot': vm.snapshot()
        }), 200


@app.route('/run', methods=['POST'])
def run():
    if vm.halted:
        return jsonify({'status': 'halted', 'msg': 'VM já parada', 'snapshot': vm.snapshot()})
    body = request.get_json(silent=True) or {}
    limit = int(body.get('limit', 1000000))
    try:
        vm.run(step_limit=limit)
        return jsonify({'status': 'ok', 'snapshot': vm.snapshot()})
    except VMError as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'snapshot': vm.snapshot()
        }), 200




@app.route('/reset', methods=['POST'])
def reset():
    """Reinicia a VM (mantendo o programa atual)."""
    vm.reset()
    return jsonify({'status': 'ok', 'snapshot': vm.snapshot()})


@app.route('/input', methods=['POST'])
def input_value():
    """Adiciona um valor de entrada para ser consumido por RD."""
    data = request.get_json(silent=True) or {}
    try:
        v = int(data.get('value'))
        vm.enqueue_input(v)
        return jsonify({'status': 'ok', 'input_queue': vm.input_queue})
    except Exception:
        return jsonify({'status': 'error', 'message': 'Valor inválido para RD'}), 400


@app.route('/examples', methods=['GET'])
def examples():
    """Retorna exemplos básicos de programas MVD."""
    ex = {
        "soma_simples": (
            "START\n"
            "LDC 5\n"
            "LDC 3\n"
            "ADD\n"
            "PRN\n"
            "HLT"
        ),
        "comparacao": (
            "START\n"
            "LDC 4\n"
            "LDC 7\n"
            "CME\n"
            "PRN\n"
            "HLT"
        ),
        "procedimento": (
            "START\n"
            "ALLOC 0 1\n"
            "LDC 10\n"
            "STR 0\n"
            "CALL L1\n"
            "PRN\n"
            "HLT\n"
            "L1:\n"
            "LDV 0\n"
            "LDC 5\n"
            "ADD\n"
            "RETURN"
        ),
        "leitura_soma": (
            "START\n"
            "RD\n"
            "STR 0\n"
            "RD\n"
            "STR 1\n"
            "LDV 0\n"
            "LDV 1\n"
            "ADD\n"
            "PRN\n"
            "HLT"
        )
    }
    return jsonify(ex)

# =========================
# Execução local
# =========================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"\n🔹 Servidor Flask iniciado na porta {port}")
    print(f"🔹 Acesse: http://127.0.0.1:{port}\n")
    app.run(host='127.0.0.1', port=port, debug=True)
