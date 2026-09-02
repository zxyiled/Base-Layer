import datetime
import tkinter as tk
from tkinter import ttk, messagebox

class Matrix:

    MAX_DIMENSION = 20

    def __init__(self, data):

        if not data or not data[0]:
            raise ValueError("La matriz no puede estar vacía.")
        columns = len(data[0])
        for row in data:
            if len(row) != columns:
                raise ValueError("Todas las filas deben tener la misma cantidad de columnas.")
        if len(data) > self.MAX_DIMENSION or columns > self.MAX_DIMENSION:
            raise ValueError(
                f"Las dimensiones no pueden superar "
                f"{self.MAX_DIMENSION}x{self.MAX_DIMENSION}."
            )
        self.data = [row[:] for row in data]
        self.rows = len(self.data)
        self.columns = len(self.data[0])

    def __str__(self):

        return "\n".join("\t".join(f"{x:8.4f}" for x in row) for row in self.data)

    def _validate_size(self, other):

        if self.rows != other.rows or self.columns != other.columns:
            raise ValueError(
                f"Dimensiones incompatibles: ({self.rows}x{self.columns}) vs ({other.rows}x{other.columns})"
            )

    def is_square(self):

        return self.rows == self.columns

    def add(self, other):

        self._validate_size(other)
        return Matrix([
            [self.data[i][j] + other.data[i][j] for j in range(self.columns)]
            for i in range(self.rows)
        ])

    def subtract(self, other):

        self._validate_size(other)
        return Matrix([
            [self.data[i][j] - other.data[i][j] for j in range(self.columns)]
            for i in range(self.rows)
        ])

    def multiply(self, other):

        if self.columns != other.rows:
            raise ValueError(
                f"Dimensiones incompatibles para multiplicación: "
                f"({self.rows}x{self.columns}) * ({other.rows}x{other.columns})"
            )
        result = [[0.0] * other.columns for _ in range(self.rows)]
        for i in range(self.rows):
            for j in range(other.columns):
                result[i][j] = sum(self.data[i][k] * other.data[k][j] for k in range(self.columns))
        return Matrix(result)

    def scalar_multiply(self, scalar):

        return Matrix([
            [self.data[i][j] * scalar for j in range(self.columns)]
            for i in range(self.rows)
        ])

    def transpose(self):
 
        return Matrix([
            [self.data[i][j] for i in range(self.rows)]
            for j in range(self.columns)
        ])

    def trace(self):

        if not self.is_square():
            raise ValueError("La matriz debe ser cuadrada para calcular la traza.")
        return sum(self.data[i][i] for i in range(self.rows))

    def determinant(self):

        if not self.is_square():
            raise ValueError("La matriz debe ser cuadrada para calcular el determinante.")
        return self._determinant_lu(self.data)

    @staticmethod
    def _determinant_lu(matrix):

        n = len(matrix)
        work = [row[:] for row in matrix]
        det = 1.0
        for i in range(n):
            pivot_row = max(range(i, n), key=lambda r: abs(work[r][i]))
            if abs(work[pivot_row][i]) < 1e-12:
                return 0.0
            if pivot_row != i:
                work[i], work[pivot_row] = work[pivot_row], work[i]
                det = -det
            det *= work[i][i]
            for r in range(i + 1, n):
                factor = work[r][i] / work[i][i]
                if factor != 0.0:
                    for c in range(i + 1, n):
                        work[r][c] -= factor * work[i][c]
        return det

    def adjoint(self):
 
        if not self.is_square():
            raise ValueError("La matriz debe ser cuadrada para calcular la adjunta.")
        n = self.rows
        if n == 1:
            return Matrix([[1.0]])
        cofactors = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                minor = [
                    [self.data[r][c] for c in range(n) if c != j]
                    for r in range(n) if r != i
                ]
                cofactors[i][j] = ((-1) ** (i + j)) * Matrix._determinant_lu(minor)
        return Matrix(cofactors).transpose()

    def inverse(self):

        if not self.is_square():
            raise ValueError("La matriz debe ser cuadrada para calcular la inversa.")
        det = self.determinant()
        if det == 0:
            raise ValueError("La matriz es singular (determinante = 0), no tiene inversa.")
        n = self.rows
        identity = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
        copy = [row[:] for row in self.data]
        for i in range(n):
            pivot = copy[i][i]
            if pivot == 0:
                for k in range(i + 1, n):
                    if copy[k][i] != 0:
                        copy[i], copy[k] = copy[k], copy[i]
                        identity[i], identity[k] = identity[k], identity[i]
                        pivot = copy[i][i]
                        break
                else:
                    raise ValueError("La matriz no es invertible.")
            for j in range(n):
                copy[i][j] /= pivot
                identity[i][j] /= pivot
            for k in range(n):
                if k != i:
                    factor = copy[k][i]
                    for j in range(n):
                        copy[k][j] -= factor * copy[i][j]
                        identity[k][j] -= factor * identity[i][j]
        return Matrix(identity)


def register_history(operation, result_str):

    try:
        with open("historial.txt", "a", encoding="utf-8") as f:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"{timestamp} | {operation}\n")
            f.write(f"Resultado:\n{result_str}\n")
            f.write("-" * 50 + "\n")
    except Exception as e:
        print(f"Error al guardar historial: {e}")


def parse_matrix_text(text):

    if not text.strip():
        raise ValueError("El campo de la matriz está vacío.")
    rows = []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        values = [float(x) for x in line.split()]
        rows.append(values)
    if not rows:
        raise ValueError("No se encontraron datos válidos en la matriz.")
    col_count = len(rows[0])
    for i, row in enumerate(rows):
        if len(row) != col_count:
            raise ValueError(
                f"Fila {i + 1} tiene {len(row)} valores, se esperaban {col_count}."
            )
    return Matrix(rows)


class MatrixCalculatorApp:

    # (Etiqueta del botón, nombre del método de Matrix, ¿requiere B?)
    OPERATIONS = [
        ("Suma (A + B)", "add", True),
        ("Resta (A - B)", "subtract", True),
        ("Multiplicación (A × B)", "multiply", True),
        ("Multiplicación escalar (k × A)", "scalar_multiply", False),
        ("Transpuesta (Aᵀ)", "transpose", False),
        ("Trazo (tr(A))", "trace", False),
        ("Determinante (det(A))", "determinant", False),
        ("Adjunta (adj(A))", "adjoint", False),
        ("Inversa (A⁻¹)", "inverse", False),
    ]

    def __init__(self, root):

        self.root = root
        self.root.title("Calculadora de Matrices")
        self.root.resizable(False, False)
        self._build_ui()
        self.root.after(50, self._center_on_screen)

    def _center_on_screen(self):

        self.root.update_idletasks()
        w = self.root.winfo_reqwidth()
        h = self.root.winfo_reqheight()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):

        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        matrix_frame = ttk.Frame(main_frame)
        matrix_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(matrix_frame, text="Matriz A:").grid(row=0, column=0, sticky=tk.W)
        self.text_a = tk.Text(matrix_frame, width=30, height=8, font=("Courier", 10))
        self.text_a.grid(row=1, column=0, padx=(0, 10))

        ttk.Label(matrix_frame, text="Matriz B:").grid(row=0, column=2, sticky=tk.W)
        self.text_b = tk.Text(matrix_frame, width=30, height=8, font=("Courier", 10))
        self.text_b.grid(row=1, column=2)

        scalar_frame = ttk.Frame(main_frame)
        scalar_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(scalar_frame, text="Escalar (k):").pack(side=tk.LEFT)
        self.scalar_entry = ttk.Entry(scalar_frame, width=10)
        self.scalar_entry.pack(side=tk.LEFT, padx=(5, 0))
        self.scalar_entry.insert(0, "1.0")

        ops_frame = ttk.LabelFrame(main_frame, text="Operaciones", padding=5)
        ops_frame.pack(fill=tk.X, pady=(0, 10))

        for idx, (label, _, _) in enumerate(self.OPERATIONS):
            btn = ttk.Button(
                ops_frame,
                text=label,
                command=lambda i=idx: self._execute(i),
            )
            btn.grid(row=idx // 3, column=idx % 3, padx=3, pady=3, sticky=tk.EW)

        for col in range(3):
            ops_frame.columnconfigure(col, weight=1)

        history_btn = ttk.Button(main_frame, text="Ver historial", command=self._show_history)
        history_btn.pack(pady=(0, 10))

        result_frame = ttk.LabelFrame(main_frame, text="Resultado", padding=5)
        result_frame.pack(fill=tk.BOTH, expand=True)

        self.result_text = tk.Text(
            result_frame, width=60, height=10, font=("Courier", 10), state=tk.DISABLED
        )
        self.result_text.pack(fill=tk.BOTH, expand=True)

    def _get_matrices(self):

        a = parse_matrix_text(self.text_a.get("1.0", tk.END))
        b = parse_matrix_text(self.text_b.get("1.0", tk.END))
        return a, b

    def _show_result(self, text):

        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, text)
        self.result_text.config(state=tk.DISABLED)

    def _execute(self, op_index):

        label, method_name, needs_b = self.OPERATIONS[op_index]
        try:
            a = parse_matrix_text(self.text_a.get("1.0", tk.END))
            b = parse_matrix_text(self.text_b.get("1.0", tk.END)) if needs_b else None

            if method_name == "scalar_multiply":
                try:
                    scalar = float(self.scalar_entry.get().strip())
                except ValueError:
                    raise ValueError("El escalar debe ser un número válido.")

            if needs_b:
                result_matrix = getattr(a, method_name)(b)
            elif method_name == "scalar_multiply":
                result_matrix = a.scalar_multiply(scalar)
            else:
                result_matrix = getattr(a, method_name)()

            if isinstance(result_matrix, Matrix):
                result_str = str(result_matrix)
                op_label = f"{label} | A: {a.rows}x{a.columns}"
                if b is not None:
                    op_label += f", B: {b.rows}x{b.columns}"
                if method_name == "scalar_multiply":
                    op_label += f", k={scalar}"
            else:
                result_str = f"{result_matrix:.4f}"
                op_label = f"{label} | A: {a.rows}x{a.columns}"

            register_history(op_label, result_str)

            display = f"{label}\n\n{result_str}"
            self._show_result(display)

        except (ValueError, ZeroDivisionError) as e:
            self._show_result(f"Error: {e}")
        except Exception as e:
            self._show_result(f"Error inesperado: {e}")

    def _show_history(self):
 
        win = tk.Toplevel(self.root)
        win.title("Historial de Operaciones")
        win.geometry("500x400")
        text = tk.Text(win, font=("Courier", 10), state=tk.NORMAL)
        text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        try:
            with open("historial.txt", "r", encoding="utf-8") as f:
                content = f.read()
            if content.strip():
                text.insert(tk.END, content)
            else:
                text.insert(tk.END, "El historial está vacío.")
        except FileNotFoundError:
            text.insert(tk.END, "No hay historial aún.")
        text.config(state=tk.DISABLED)


if __name__ == "__main__":
    # Punto de entrada: crea la ventana raíz e inicia el bucle principal de la GUI.
    root = tk.Tk()
    app = MatrixCalculatorApp(root)
    root.mainloop()
