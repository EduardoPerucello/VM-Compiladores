# backend/vm_core.py
# Máquina Virtual Didática (MVD)
# Totalmente compatível com o app Flask e frontend (prompt RD automático)

class VMError(Exception):
    """Erro da Máquina Virtual Didática."""
    pass


class VM:
    def __init__(self):
        self.reset_all()

    def reset_all(self):
        self.P = []          # Programa (lista de instruções)
        self.M = {}          # Memória
        self.s = -1          # Topo da pilha
        self.pc = 0          # Contador de programa
        self.halted = False  # Estado de parada
        self.last_error = None
        self.output = []     # Saída (PRN)
        self.input_queue = []  # Fila de entrada (para RD)
        self.labels = {}     # Rótulos (L1, L2, etc.)

    # ========================================================
    # Carregar e reiniciar
    # ========================================================

    def load_program(self, asm_text):
        """Carrega um código Assembly, converte rótulos em endereços."""
        self.reset_all()
        lines = [l.strip() for l in asm_text.splitlines() if l.strip()]
        
        # Lista de instruções válidas da MVD
        valid_instructions = {
            'START', 'LDC', 'LDV', 'ADD', 'SUB', 'MULT', 'DIVI', 'INV',
            'AND', 'OR', 'NEG', 'CME', 'CMA', 'CEQ', 'CDIF', 'CMEQ', 'CMAQ',
            'STR', 'JMP', 'JMPF', 'NULL', 'RD', 'PRN', 'ALLOC', 'DALLOC',
            'CALL', 'RETURN', 'HLT'
        }

        # 1️⃣ Primeira varredura — detecta rótulos e monta programa
        for line in lines:
            parts = line.split()
            if not parts:
                continue
            
            # Verifica se o primeiro token é uma instrução ou um label
            first_token = parts[0].upper()
            
            if first_token in valid_instructions:
                # Linha começa com instrução (sem label)
                self.P.append(parts)
            else:
                # Primeiro token é um label (ex: L1, L2, LOOP, etc)
                label = parts[0]
                self.labels[label] = len(self.P)  # Mapeia label para índice atual
                
                # Se há instrução após o label na mesma linha
                if len(parts) > 1:
                    self.P.append(parts[1:])
                # Se não há instrução, o label aponta para a próxima linha

        # 2️⃣ Segunda varredura — substitui labels por endereços numéricos
        for i, instr in enumerate(self.P):
            new_instr = []
            for token in instr:
                # Se o token é um label conhecido, substitui pelo endereço
                if token in self.labels:
                    new_instr.append(str(self.labels[token]))
                else:
                    new_instr.append(token)
            self.P[i] = new_instr


    def reset(self):
        """Reinicia a execução mantendo o programa carregado."""
        self.M = {}
        self.s = -1
        self.pc = 0
        self.halted = False
        self.last_error = None
        self.output = []

    # ========================================================
    # Execução
    # ========================================================

    def step(self):
        """Executa uma instrução."""
        if self.halted or self.pc < 0 or self.pc >= len(self.P):
            self.halted = True
            return

        try:
            instr = self.P[self.pc]
            op = instr[0].upper()
            arg1 = int(instr[1]) if len(instr) > 1 and instr[1].lstrip('-').isdigit() else (instr[1] if len(instr) > 1 else None)
            arg2 = int(instr[2]) if len(instr) > 2 and instr[2].lstrip('-').isdigit() else (instr[2] if len(instr) > 2 else None)

            # --- Instruções principais ---
            if op == "START":
                self.s = -1
                self.pc += 1

            elif op == "LDC":
                self.s += 1
                self.M[self.s] = arg1
                self.pc += 1

            elif op == "LDV":
                self.s += 1
                self.M[self.s] = self.M.get(arg1, 0)
                self.pc += 1

            elif op == "ADD":
                self.M[self.s - 1] += self.M[self.s]
                self.s -= 1
                self.pc += 1

            elif op == "SUB":
                self.M[self.s - 1] -= self.M[self.s]
                self.s -= 1
                self.pc += 1

            elif op == "MULT":
                self.M[self.s - 1] *= self.M[self.s]
                self.s -= 1
                self.pc += 1

            elif op == "DIVI":
                if self.M[self.s] == 0:
                    raise VMError("Divisão por zero")
                self.M[self.s - 1] //= self.M[self.s]
                self.s -= 1
                self.pc += 1

            elif op == "INV":
                self.M[self.s] = -self.M[self.s]
                self.pc += 1

            elif op == "AND":
                self.M[self.s - 1] = 1 if self.M[self.s - 1] == 1 and self.M[self.s] == 1 else 0
                self.s -= 1
                self.pc += 1

            elif op == "OR":
                self.M[self.s - 1] = 1 if self.M[self.s - 1] == 1 or self.M[self.s] == 1 else 0
                self.s -= 1
                self.pc += 1

            elif op == "NEG":
                self.M[self.s] = 1 - self.M[self.s]
                self.pc += 1

            elif op == "CME":
                self.M[self.s - 1] = 1 if self.M[self.s - 1] < self.M[self.s] else 0
                self.s -= 1
                self.pc += 1

            elif op == "CMA":
                self.M[self.s - 1] = 1 if self.M[self.s - 1] > self.M[self.s] else 0
                self.s -= 1
                self.pc += 1

            elif op == "CEQ":
                self.M[self.s - 1] = 1 if self.M[self.s - 1] == self.M[self.s] else 0
                self.s -= 1
                self.pc += 1

            elif op == "CDIF":
                self.M[self.s - 1] = 1 if self.M[self.s - 1] != self.M[self.s] else 0
                self.s -= 1
                self.pc += 1

            elif op == "CMEQ":
                self.M[self.s - 1] = 1 if self.M[self.s - 1] <= self.M[self.s] else 0
                self.s -= 1
                self.pc += 1

            elif op == "CMAQ":
                self.M[self.s - 1] = 1 if self.M[self.s - 1] >= self.M[self.s] else 0
                self.s -= 1
                self.pc += 1

            elif op == "STR":
                self.M[arg1] = self.M[self.s]
                self.s -= 1
                self.pc += 1

            elif op == "JMP":
                self.pc = int(arg1)

            elif op == "JMPF":
                if self.M[self.s] == 0:
                    self.pc = int(arg1)
                else:
                    self.pc += 1
                self.s -= 1

            elif op == "NULL":
                self.pc += 1

            elif op == "RD":
                # 🚨 Lê valor ou pausa esperando entrada
                self.s += 1
                if self.input_queue:
                    self.M[self.s] = int(self.input_queue.pop(0))
                    self.pc += 1
                else:
                    # pausa aguardando entrada
                    raise VMError("RD attempted but input queue empty")

            elif op == "PRN":
                self.output.append(self.M[self.s])
                self.s -= 1
                self.pc += 1

            elif op == "ALLOC":
                m, n = arg1, arg2
                for k in range(n):
                    self.s += 1
                    self.M[self.s] = self.M.get(m + k, 0)
                self.pc += 1

            elif op == "DALLOC":
                m, n = arg1, arg2
                for k in reversed(range(n)):
                    self.M[m + k] = self.M[self.s]
                    self.s -= 1
                self.pc += 1

            elif op == "CALL":
                self.s += 1
                self.M[self.s] = self.pc + 1
                self.pc = int(arg1)

            elif op == "RETURN":
                self.pc = self.M[self.s]
                self.s -= 1

            elif op == "HLT":
                self.halted = True

            else:
                raise VMError(f"Instrução inválida: {op}")

        except VMError as e:
            # ⚙️ Só pausa totalmente se o erro não for RD
            self.last_error = str(e)
            if "RD attempted" in str(e):
                self.halted = False  # apenas aguarda input
            else:
                self.halted = True
            raise
        except Exception as e:
            self.halted = True
            self.last_error = f"Erro inesperado: {e}"
            raise VMError(self.last_error)

    def run(self, step_limit=1000000):
        count = 0
        while not self.halted and count < step_limit:
            self.step()
            count += 1
        if count >= step_limit:
            raise VMError("Limite de passos atingido")

    # ========================================================
    # Utilitários
    # ========================================================

    def enqueue_input(self, value):
        """Adiciona valor de entrada e desbloqueia VM se estava aguardando RD."""
        self.input_queue.append(value)
        if self.last_error and "RD attempted" in str(self.last_error):
            self.halted = False
            self.last_error = None

    def snapshot(self):
        return {
            "pc": self.pc,
            "stack": [self.M.get(i, 0) for i in range(self.s + 1)],
            "mem": {k: v for k, v in sorted(self.M.items())},
            "output": self.output,
            "halted": self.halted,
            "last_error": self.last_error,
            "next_instr": self.P[self.pc] if 0 <= self.pc < len(self.P) else None
        }

    def dump_program(self):
        return "\n".join(f"{i}: {' '.join(map(str, p))}" for i, p in enumerate(self.P))