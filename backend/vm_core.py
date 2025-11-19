# backend/vm_core.py
# Máquina Virtual Didática (MVD)
#
# - Montador em duas passagens (detecta labels), mas NÃO substitui tokens por endereços.
# - Execução (step) usa bloco de instruções fiel ao while True que você forneceu,
#   executando exatamente uma instrução por chamada a step().
# - CALL empilha retorno na pilha de dados; RETURN desempilha.
# - RD levanta VMError quando fila de input vazia; enqueue_input "acorda" a VM.

class VMError(Exception):
    pass


class VM:
    def __init__(self):
        self.reset_all()

    def reset_all(self):
        # Programa / montagem
        self.P = []            # lista de instruções tokenizadas
        self.labels = {}       # mapa label -> endereço (índice em P)

        # Memória / pilha de dados
        self.M = {}            # memória (endereço:int -> valor:int)
        self.s = -1            # topo da pilha (sp)

        # Controle de execução
        self.pc = 0
        self.halted = False
        self.last_error = None
        self.output = []

        # I/O
        self.input_queue = []

    # -----------------------
    # Montador / Carregador
    # -----------------------
    def load_program(self, asm_text):
        """
        Carrega programa Assembly:
         - aceita labels no início da linha (numéricos ou textuais), com ou sem ':'.
         - registra labels em self.labels -> índice em P.
         - mantém as instruções em self.P sem substituir tokens.
        """
        # reset parcial
        self.P = []
        self.labels = {}
        self.M = {}
        self.s = -1
        self.pc = 0
        self.halted = False
        self.last_error = None
        self.output = []
        self.input_queue = []

        valid_instr = {
            'START', 'LDC', 'LDV', 'ADD', 'SUB', 'MULT', 'DIVI', 'INV',
            'AND', 'OR', 'NEG', 'CME', 'CMA', 'CEQ', 'CDIF', 'CMEQ', 'CMAQ',
            'STR', 'JMP', 'JMPF', 'NULL', 'RD', 'PRN',
            'ALLOC', 'DALLOC',
            'CALL', 'RETURN', 'HLT'
        }

        raw_lines = asm_text.splitlines()

        # 1ª passagem: registrar labels e construir P (sem substituir)
        for raw in raw_lines:
            if raw is None:
                continue
            line = raw.strip()
            if not line:
                continue

            parts = line.split()
            if not parts:
                continue

            first_token = parts[0]
            t_clean = first_token.rstrip(':')

            # se é número puro no início -> label numérico
            if t_clean.isdigit():
                label = t_clean
                self.labels[label] = len(self.P)
                # criar alias L<num>
                l_alias = 'L' + label
                if l_alias not in self.labels:
                    self.labels[l_alias] = self.labels[label]
                # se tiver instrução depois do label, anexa
                if len(parts) > 1:
                    self.P.append(parts[1:])
                else:
                    # label sozinho -> tratamos como NULL (linha de rótulo)
                    self.P.append(['NULL'])
                continue

            # se termina com ':' -> label textual
            if first_token.endswith(':'):
                label = t_clean
                self.labels[label] = len(self.P)
                # alias numérico se for L<num>
                if label.upper().startswith('L') and label[1:].isdigit():
                    num = label[1:]
                    if num not in self.labels:
                        self.labels[num] = self.labels[label]
                # se houver instrução na mesma linha
                if len(parts) > 1:
                    self.P.append(parts[1:])
                else:
                    self.P.append(['NULL'])
                continue

            # se começa com instrução válida -> instrução normal
            if t_clean.upper() in valid_instr:
                self.P.append(parts)
                continue

            # se começa com palavra não-instrucao e próxima token é NULL, tratamos como label
            if len(parts) >= 2 and parts[1].upper() == 'NULL':
                label = t_clean
                self.labels[label] = len(self.P)
                if label.upper().startswith('L') and label[1:].isdigit():
                    num = label[1:]
                    if num not in self.labels:
                        self.labels[num] = self.labels[label]
                if label.isdigit():
                    lalias = 'L' + label
                    if lalias not in self.labels:
                        self.labels[lalias] = self.labels[label]
                self.P.append(['NULL'])
                continue

            # caso geral: linha começa com token não-instrucao -> tratamos como label sem ':'
            if t_clean not in valid_instr:
                label = t_clean
                self.labels[label] = len(self.P)
                if label.upper().startswith('L') and label[1:].isdigit():
                    num = label[1:]
                    if num not in self.labels:
                        self.labels[num] = self.labels[label]
                if len(parts) > 1:
                    self.P.append(parts[1:])
                else:
                    self.P.append(['NULL'])
                continue

            # fallback: tratar como instrução
            self.P.append(parts)

        # OBS: NÃO fazemos substituição de tokens por endereços aqui.
        # Em tempo de execução (step) usamos self.labels[label] para JMP/CALL/JMPF.

    # -----------------------
    # Reiniciar execução (mantém programa carregado)
    # -----------------------
    def reset(self):
        self.M = {}
        self.s = -1
        self.pc = 0
        self.halted = False
        self.last_error = None
        self.output = []
        self.input_queue = []

    # -----------------------
    # Execução: step (1 instrução por vez)
    # -----------------------
    def step(self):
        # condições de parada
        if self.halted or self.pc < 0 or self.pc >= len(self.P):
            self.halted = True
            return

        try:
            instr = self.P[self.pc]
            if not instr:
                # linha vazia ou None -> avança
                self.pc += 1
                return

            # Prepare variáveis no estilo do seu while True
            operation = instr
            opcode = str(operation[0]).upper()

            # M, sp, pc locais (iremos reatribuir para self no final)
            M = self.M
            sp = self.s
            pc = self.pc
            labels = self.labels

            # helpers push/pop mantendo sp e M locais
            def push_M(v):
                nonlocal sp, M
                sp += 1
                M[sp] = v

            def pop_M():
                nonlocal sp
                if sp < 0:
                    raise VMError("Pilha vazia")
                sp -= 1

            jumped = False

            # ============= bloco de instruções (copiado do seu while True) =============

            if opcode == "HLT":
                self.halted = True

            elif opcode == "START":
                sp = -1

            elif opcode == "LDC":
                value = int(operation[1])
                push_M(value)

            elif opcode == "LDV":
                value = int(operation[1])
                push_M(M.get(value, 0))

            elif opcode == "ADD":
                M[sp - 1] = M.get(sp - 1, 0) + M.get(sp, 0)
                pop_M()

            elif opcode == "SUB":
                M[sp - 1] = M.get(sp - 1, 0) - M.get(sp, 0)
                pop_M()

            elif opcode == "MULT":
                M[sp - 1] = M.get(sp - 1, 0) * M.get(sp, 0)
                pop_M()

            elif opcode == "DIVI":
                # cuidado com divisão por zero (vai lançar se M[sp] == 0)
                if M.get(sp, 0) == 0:
                    raise VMError("Divisão por zero")
                M[sp - 1] = M.get(sp - 1, 0) // M.get(sp, 0)
                pop_M()

            elif opcode == "INV":
                M[sp] = -M.get(sp, 0)

            elif opcode == "AND":
                M[sp - 1] = 1 if M.get(sp - 1, 0) == 1 and M.get(sp, 0) == 1 else 0
                pop_M()

            elif opcode == "OR":
                M[sp - 1] = 0 if M.get(sp - 1, 0) == 0 and M.get(sp, 0) == 0 else 1
                pop_M()

            elif opcode == "NEG":
                M[sp] = 1 - M.get(sp, 0)

            elif opcode == "CME":
                M[sp - 1] = 1 if M.get(sp - 1, 0) < M.get(sp, 0) else 0
                pop_M()

            elif opcode == "CMA":
                M[sp - 1] = 1 if M.get(sp - 1, 0) > M.get(sp, 0) else 0
                pop_M()

            elif opcode == "CEQ":
                M[sp - 1] = 1 if M.get(sp - 1, 0) == M.get(sp, 0) else 0
                pop_M()

            elif opcode == "CDIF":
                M[sp - 1] = 1 if M.get(sp - 1, 0) != M.get(sp, 0) else 0
                pop_M()

            elif opcode == "CMEQ":
                M[sp - 1] = 1 if M.get(sp - 1, 0) <= M.get(sp, 0) else 0
                pop_M()

            elif opcode == "CMAQ":
                M[sp - 1] = 1 if M.get(sp - 1, 0) >= M.get(sp, 0) else 0
                pop_M()

            elif opcode == "STR":
                value = int(operation[1])
                M[value] = M.get(sp, 0)
                pop_M()

            elif opcode == "JMP":
                label = str(operation[1])
                if label not in labels:
                    raise VMError(f"JMP: rótulo '{label}' não encontrado")
                pc = labels[label]
                jumped = True

            elif opcode == "JMPF":
                label = str(operation[1])
                if sp < 0:
                    raise VMError("JMPF: pilha vazia")
                if M.get(sp, 0) == 0:
                    if label not in labels:
                        raise VMError(f"JMPF: rótulo '{label}' não encontrado")
                    pc = labels[label]
                else:
                    pc += 1
                pop_M()
                jumped = True

            elif opcode == "NULL":
                # nada a fazer
                pass

            elif opcode == "RD":
                # consome da fila de input; se vazia, sinaliza erro para frontend
                if not self.input_queue:
                    raise VMError("RD attempted but input queue empty")
                value = int(self.input_queue.pop(0))
                push_M(value)

            elif opcode == "PRN":
                self.output.append(M.get(sp, 0))
                pop_M()

            elif opcode == "ALLOC":
                # ALLOC m n -> para k in 0..n-1: push M[m+k]
                if len(operation) < 3:
                    raise VMError("ALLOC: argumentos ausentes")
                m = int(operation[1])
                n = int(operation[2])
                for k in range(n):
                    push_M(M.get(m + k, 0))

            elif opcode == "DALLOC":
                # DALLOC m n -> para k=n-1..0: M[m+k] = pop()
                if len(operation) < 3:
                    raise VMError("DALLOC: argumentos ausentes")
                m = int(operation[1])
                n = int(operation[2])
                if sp < n - 1:
                    raise VMError("DALLOC: pilha insuficiente")
                for k in reversed(range(n)):
                    M[m + k] = M.get(sp, 0)
                    pop_M()

            elif opcode == "CALL":
                label = str(operation[1])
                if label not in labels:
                    raise VMError(f"CALL: rótulo '{label}' não encontrado")
                # empilha endereço de retorno e salta
                push_M(pc + 1)
                pc = labels[label]
                jumped = True

            elif opcode == "RETURN":
                if sp < 0:
                    raise VMError("RETURN: pilha vazia")
                pc = int(M.get(sp, 0))
                pop_M()
                jumped = True

            else:
                raise VMError(f"Instrução inválida: {opcode}")

            # ============= fim do bloco de instruções =============

            # gravar de volta os valores locais para o objeto
            self.s = sp
            self.M = M
            # se houve salto, pc já ajustado; caso contrário incrementa
            self.pc = pc if jumped else (pc + 1)

        except VMError as e:
            # em caso de RD sem input, não marcamos halted permanentemente (frontend lida com isso)
            self.last_error = str(e)
            if "RD attempted" in str(e):
                self.halted = False
            else:
                self.halted = True
            # propaga para o Flask (app.py captura e devolve)
            raise
        except Exception as e:
            self.halted = True
            self.last_error = f"Erro inesperado: {e}"
            raise VMError(self.last_error)

    # -----------------------
    # run / utilitários
    # -----------------------
    def run(self, step_limit=1000000):
        count = 0
        while not self.halted and count < step_limit:
            self.step()
            count += 1
        if count >= step_limit:
            raise VMError("Limite de passos atingido")

    def enqueue_input(self, value):
        try:
            self.input_queue.append(int(value))
        except Exception:
            raise VMError("enqueue_input: valor inválido")
        if self.last_error and "RD attempted" in str(self.last_error):
            # limpa erro para permitir continuação
            self.last_error = None

    def snapshot(self):
        return {
            "pc": self.pc,
            "stack": [self.M.get(i, 0) for i in range(self.s + 1)],
            "mem": {k: v for k, v in sorted(self.M.items())},
            "output": self.output.copy(),
            "halted": self.halted,
            "last_error": self.last_error,
            "next_instr": ' '.join(map(str, self.P[self.pc])) if 0 <= self.pc < len(self.P) else None
        }

    def dump_program(self):
        # tenta reconstruir labels inversos (exibindo um dos nomes possíveis)
        labels_rev = {}
        for k, v in self.labels.items():
            # para cada endereço guarda o primeiro label encontrado
            if v not in labels_rev:
                labels_rev[v] = k
        lines = []
        for i, instr in enumerate(self.P):
            lbl = labels_rev.get(i, "")
            label_str = (lbl + ":") if lbl else ""
            lines.append(f"{i:03d} {label_str}\t{' '.join(map(str, instr))}")
        return "\n".join(lines)
